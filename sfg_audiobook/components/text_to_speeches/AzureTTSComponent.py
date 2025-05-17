import os
from pathlib import Path

import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import VoiceInfo
import xml.etree.ElementTree as ET
from pydub import AudioSegment

from sfg_audiobook.components.ComponentsRegister import ComponentsRegister
from sfg_audiobook.sfg_types import PipelineData, TextPartType
from sfg_audiobook.structure import AbstractComponent
from sfg_audiobook.sfg_types import TTSVoice, CharacterType


class AzureTTSComponent(AbstractComponent):
    """
    Use Azure TTS to convert text parts to speech with a specified speaker for each character.
    """
    MAX_VOICE_ELEMENTS = 50  # Limit of voice elements in SSML in Azure TTS

    def __init__(self, params: dict[str, str], *args, **kwargs) -> None:
        super().__init__(params, *args, **kwargs)

        self._out_file = params.get('out_file', None)
        if not self._out_file:
            raise ValueError("out_file parameter is required.")
        self._out_file = Path(self._out_file)

        self._lang = params.get('lang', 'en-US')

        self._selected_voices = params.get('voices', "")
        self._selected_voices = [voice.strip() for voice in self._selected_voices.split(';') if voice.strip()]
        print(f"Selected voices: {self._selected_voices if self._selected_voices else 'all voices'}")

        self._speech_key = os.environ.get("SPEECH_KEY")
        if not self._speech_key:
            raise ValueError("SPEECH_KEY environment variable is required.")

        self._speech_region = os.environ.get("SPEECH_REGION")
        if not self._speech_region:
            raise ValueError("SPEECH_REGION environment variable is required.")

        self._speech_config = None

        self._available_voices: list[VoiceInfo] = []

    @staticmethod
    def get_help() -> str:
        return f"""Uses Azure TTS to convert text parts to speech with specified speaker for each character.
\tAttribute: out_file (str): Output filename where to save resulting audio.
\tAttribute (optional): lang (str): Language code for the TTS in BCP-47 standard. Default is 'en-US'.
\tAttribute (optional): voices (str): List of voice short names to use separated by semicolon ';'. If not defined, use all voices for language.
\tEnvironment Variable: SPEECH_KEY: Azure Speech service subscription key.
\tEnvironment Variable: SPEECH_REGION: Azure Speech service region.
"""

    def _get_voices(self) -> list[VoiceInfo]:
        """
        Get all available voices from Azure TTS.
        """
        if not self._speech_key or not self._speech_region:
            raise ValueError("Azure Speech credentials are not set. Please set SPEECH_KEY and SPEECH_REGION environment variables.")

        self._speech_config = speechsdk.SpeechConfig(subscription=self._speech_key, region=self._speech_region)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=self._speech_config)
        result = synthesizer.get_voices_async().get()

        if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
            return result.voices
        else:
            print(f"Failed to retrieve voices: {result.reason}")
            if result.reason == speechsdk.ResultReason.Canceled:
                print(f"CANCELED, error details: {result.error_details}")
                raise ValueError(f"Error retrieving voices: {result.error_details}")

    def setup(self, data: PipelineData):
        """
        Load all available voices in the defined language from the Azure API.
        """
        if not self._speech_key or not self._speech_region:
            raise ValueError("Azure Speech credentials are not set. Please set SPEECH_KEY and SPEECH_REGION environment variables.")

        self._speech_config = speechsdk.SpeechConfig(subscription=self._speech_key, region=self._speech_region)

        # Get voices
        voices = self._get_voices()

        if self._selected_voices:
            # If user selected voices, check if they are available
            self._available_voices = [voice for voice in voices if voice.short_name in self._selected_voices]
            if len(self._available_voices) != len(self._selected_voices):
                missing_voices = set(self._selected_voices) - {voice.short_name for voice in self._available_voices}
                print(f"Warning: The following selected voices are not available: {', '.join(missing_voices)}")
                raise ValueError(f"Some selected voices are not available ({len(missing_voices)}): {', '.join(missing_voices)}")

        else:
            # Get all voices for selected language
            if not self._lang:
                raise ValueError("Language code is required if not specifying voices. Please set the lang parameter or leave it default.")

            # Filter voices by the specified language
            self._available_voices = [voice for voice in voices
                                     if voice.locale.startswith(self._lang)
                                      # and "HD" in voice.short_name  # Exclude HD voices
                                      # and "Turbo" not in voice.short_name  # Exclude Turbo voices as they do not sound as good.
                                      ]

            if not self._available_voices:
                print(f"Warning: No voices found for language '{self._lang}'. Available languages: " +
                      ", ".join(set(voice.locale for voice in voices)))
            else:
                data.available_voices = [
                    TTSVoice(id=voice.short_name, gender=voice.gender.name, locale=voice.locale, description=voices_descriptions.get(voice.short_name, ""))
                    for voice in self._available_voices
                ]
                print(f"Loaded {len(self._available_voices)} voices for language '{self._lang}'")


    def _to_ssml_elements(self, data: PipelineData) -> list[ET.Element]:
        """
        Convert text parts to SSML format for Azure TTS using ElementTree.
        Returns a list of voice elements.
        """
        all_available_voice_ids = [voice.id for voice in data.available_voices]
        characters_with_unavailable_voices = [character for character in data.characters if character.assigned_voice_id not in all_available_voice_ids]
        if characters_with_unavailable_voices:
            raise ValueError(f"Some characters have unavailable or no voices: {', '.join([character.assigned_voice_id for character in characters_with_unavailable_voices])}")

        narrator_voice_id = next((character.assigned_voice_id for character in data.characters if character.type == CharacterType.NARRATOR), None)
        if not narrator_voice_id:
            raise ValueError("Narrator voice not found in the provided characters.")

        character_id_to_voice_id_mapping = {character.identifier: character.assigned_voice_id for character in data.characters}

        ssml_parts = []
        for part in data.text_as_parts:
            voice_element = ET.Element('voice')

            if part.type == TextPartType.OTHER:
                voice_element.set('name', narrator_voice_id)
                voice_element.text = part.text  # Remove the first and last character
            elif part.type == TextPartType.QUOTE:
                character_voice_id = character_id_to_voice_id_mapping.get(part.character_identifier)
                voice_element.set('name', character_voice_id)
                voice_element.text = part.text
            else:
                raise ValueError(f"Unsupported text part type: {part.type}")

            # Add a break element between voice
            break_element = ET.Element('break')
            break_element.set('time', '200ms')
            voice_element.append(break_element)

            ssml_parts.append(voice_element)

        return ssml_parts

    def _synthetize_speech_from_ssml_to_file(self, ssml: str, filename: str | Path):
        self._speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(filename))
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=self._speech_config, audio_config=audio_config)

        result = synthesizer.speak_ssml_async(ssml).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"Speech synthesized successfully to {filename}")
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print(f"Speech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print(f"Error details: {cancellation_details.error_details}")
            raise ValueError(f"TTS synthesis error: {cancellation_details.error_details}")

    def _ssml_parts_to_ssml_string(self, ssml_parts: list[ET.Element]) -> str:
        # Create the root 'speak' element
        root = ET.Element('speak')
        root.set('version', '1.0')
        root.set('xml:lang', self._lang)

        # Add voice elements together
        for voice_element in ssml_parts:
            root.append(voice_element)

        # Convert the XML tree to a string
        return ET.tostring(root, encoding='unicode')


    def run(self, data: PipelineData):
        # Make sure the output directory exists
        os.makedirs(self._out_file.parent, exist_ok=True)

        # 1. Convert text parts to SSML
        ssml_parts = self._to_ssml_elements(data)

        # 2. Synthesize speech from the SSML to file
        split_ssml_parts = [ssml_parts[i:i + self.MAX_VOICE_ELEMENTS] for i in range(0, len(ssml_parts), self.MAX_VOICE_ELEMENTS)]
        ssml_strings = [self._ssml_parts_to_ssml_string(part) for part in split_ssml_parts]
        data.additional_attributes["azure_tts_ssml_strings"] = ssml_strings
        parts_files = []

        # Synthesize each part and save to file
        for i, ssml in enumerate(ssml_strings):
            output_file = self._out_file.with_name(f"{self._out_file.stem}_{i}{self._out_file.suffix}")
            self._synthetize_speech_from_ssml_to_file(ssml, output_file)
            parts_files.append(output_file)
            print(f"SSML part {i} synthesized to {output_file}")

        # 3. Combine all parts into a single audio file
        combined_file = self._out_file
        combined = AudioSegment.empty()
        for part_file in parts_files:
            part_audio = AudioSegment.from_file(part_file)
            combined += part_audio
        combined.export(self._out_file, format=self._out_file.suffix[1:])  # Remove the dot from the suffix
        print(f"Combined audio file saved to {combined_file}")

        # Clean up individual part files
        for part_file in parts_files:
            if part_file.exists():
                part_file.unlink()
                print(f"Deleted temporary file {part_file}")


ComponentsRegister.register_component("azure_tts", AzureTTSComponent)

# From the Azure AI speech studio (May 2025)
voices_descriptions = {
    'ko-KR-SoonBokNeural': 'An animated and bright voice which will be suitable for narrating and chat.',
    'en-US-AIGenerate1Neural': 'A voice that speaks clearly and carefully that can adapt to a wide variety of use cases.',
    'en-US-MultiTalker-Ava-Andrew:DragonHDLatestNeural': 'A group model of Ava and Andrew, which captures the natural flow of dialogue between speakers, seamlessly incorporating pauses, interjections, and contextual shifts that result in a highly realistic and engaging conversational experience.',
    'ja-JP-NanamiNeural': 'A bright and cheerful voice, offering a lively and uplifting tone for every situation.',
    'de-DE-Florian:DragonHDLatestNeural': 'HD version of Florian, a warm and cheerful voice, perfect for chatting or audiobooks, with great versatility to adapt to any use case and speak clearly for easy understanding',
    'zh-CN-XiaoxiaoMultilingualNeural': 'Xiaoxiao voice with multilingual capability',
    'it-IT-AlessioMultilingualNeural': 'A cheerful and friendly voice, full of warmth and positive energy for every interaction.',
    'fr-CA-ThierryNeural': 'An engaging and caring voice, showing empathy and warmth in every interaction.',
    'en-US-Andrew:DragonHDLatestNeural': 'HD version of Andrew with tones that feel natural and adaptable, perfect for conversations, podcasts, and chats.',
    'fr-FR-Remy:DragonHDLatestNeural': 'HD version of Remy, a bright and cheerful voice suitable for both lively chats and audiobooks, bringing an uplifting and cheerful tone to every conversation',
    'pt-PT-FernandaNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'en-US-ElizabethNeural': "A professorial voice that's clear and authoritative, great for delivering educational content in a way that's easy to understand.",
    'en-AU-WilliamNeural': 'An engaging and strong voice, delivering messages with energy and confidence.',
    'en-GB-LibbyNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'pt-BR-MacerioMultilingualNeural': 'A clear and confident voice with an upbeat tone',
    'zh-CN-Yunyi:DragonHDFlashLatestNeural': 'HD Flash version of Yunyi, with Chinese and English bilingual capability and  gentle, casual tone in any context',
    'es-AR-ElenaNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'zh-CN-YunyiMultilingualNeural': 'A gentle, casual, and friendly voice, creating a calm and approachable tone in any context.',
    'ko-KR-SunHiNeural': 'A confident and formal voice, projecting authority and professionalism.',
    'en-GB-RyanNeural': 'A bright and engaging voice, capturing attention with its vibrant and inviting tone.',
    'en-US-NancyMultilingualNeural': "A confident-sounding voice that's perfect for delivering important information with a professional and authoritative tone that inspires trust.",
    'en-US-AndrewNeural': 'A warm, engaging voice that sounds like someone you want to know, perfect for building a connection with listeners.',
    'zh-CN-XiaochenNeural': 'A casual and relaxing voice used for spontaneous conversations and meeting transcriptions.',
    'zh-CN-XiaoxiaoNeural': 'A lively and warm voice with multiple scenario styles and emotions.',
    'en-US-PhoebeMultilingualNeural': 'A confident and upbeat voice with youthful energy.',
    'it-IT-DiegoNeural': 'An animated and upbeat voice, perfect for keeping conversations fun and energetic.',
    'en-US-AvaNeural': "A bright, engaging voice with a beautiful tone that's perfect for delivering search results and capturing users' attention.",
    'de-DE-KatjaNeural': 'A calm and pleasant voice that creates a peaceful and relaxing atmosphere.',
    'es-ES-ElviraNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'zh-CN-XiaohanNeural': 'A warm and sweet voice with rich emotions that can be used in many conversation scenarios.',
    'en-US-EmmaNeural': "A friendly, sincere voice with a light-hearted and pleasant tone that's ideal for education and explanations.",
    'it-IT-PierinaNeural': "A child voice that's great at conveying curiousity",
    'de-DE-AmalaNeural': 'An animated and bright voice with a well-rounded tone, perfect for keeping conversations engaging and energetic.',
    'en-US-NovaTurboMultilingualNeural': 'Turbo version for Nova, a deep, resonant female voice',
    'zh-CN-XiaozhenNeural': 'A calm, serious, and confident voice that instills trust and focus with each word.',
    'pt-BR-YaraNeural': 'A bright and animated voice with well-rounded tones that create a lively and energetic atmosphere.',
    'en-US-JennyMultilingualNeural': 'A youthful voice with a wide range of expressions, perfect for customer service and keeping users satisfied.',
    'en-US-CoraMultilingualNeural': 'A softer voice with a touch of melancholy that conveys understanding and empathy, delivering content in a sensitive and compassionate way.',
    'fr-FR-RemyMultilingualNeural': 'A bright and cheerful voice suitable for both lively chats and audiobooks, bringing an uplifting and cheerful tone to every conversation.',
    'en-US-SteffanMultilingualNeural': 'A pleasant sounding voice that can be someone you know.',
    'fr-FR-VivienneMultilingualNeural': 'A warm and casual voice perfect for advertisements, creating a welcoming and relaxed atmosphere for listeners.',
    'en-US-AvaMultilingualNeural': "A bright, engaging voice with a beautiful tone that's perfect for delivering search results and capturing users' attention.",
    'zh-CN-YunjianNeural': 'A deep, casual, and engaging voice, blending authority with approachability to make conversations comfortable.',
    'en-US-Brian:DragonHDLatestNeural': 'HD versions of Brian, featuring a youthful and cheerful voice that can handle any task you throw its way, well-suited to a wide variety of contexts.',
    'zh-CN-YunfanMultilingualNeural': 'A clear, warm, and youthful voice which is good for different scenarios',
    'nl-NL-ColetteNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'zh-CN-XiaoyanNeural': 'A skilled and comfort voice used for customer service and conversation scenarios.',
    'en-US-AmberNeural': "An engaging voice for children's stories that's warm and approachable, perfect for capturing the attention of young listeners.",
    'es-MX-JorgeMultilingualNeural': 'A deep and confident voice, delivering authority and assurance with every word.',
    'pt-BR-AntonioNeural': 'A bright and upbeat voice, adding energy and enthusiasm to every message.',
    'ko-KR-InJoonNeural': 'A casual and friendly voice, creating a relaxed and approachable atmosphere.',
    'en-US-EvelynMultilingualNeural': 'A youthful voice suite for casual scenarios.',
    'es-MX-JorgeNeural': 'A deep and confident voice, delivering authority and assurance with every word.',
    'zh-CN-XiaoyiNeural': 'A bright, emotional, and engaging voice that adds passion and depth to every dialogue.',
    'en-US-BrandonNeural': "An honest and soft-spoken voice that's warm and good for conversation, connecting with users on a personal level and building trust.",
    'it-IT-IsabellaMultilingualNeural': 'A friendly and pleasant voice, making every conversation feel approachable and welcoming.',
    'zh-CN-YunhaoNeural': 'A warm, soft, and upbeat voice, bringing comfort and energy in a balanced way for any conversation.',
    'ja-JP-AoiNeural': "A child voice that's great at conveying curiousity",
    'en-US-Adam:DragonHDLatestNeural': 'HD version of Adam with a deep, engaging voice that feels warm and inviting',
    'nl-NL-MaartenNeural': 'A formal and upbeat voice, blending professionalism with a positive and lively tone.',
    'pt-BR-ThalitaNeural': 'A confident and formal voice, conveying professionalism and authority in every conversation.',
    'zh-CN-XiaoyuMultilingualNeural': 'A deep, confident, and approachable voice to deliver concrete information.',
    'en-GB-MaisieNeural': "A child voice that's great at conveying curiousity.",
    'en-US-BlueNeural': 'An objective neutral-sounding voice, good for conveying content without bias.',
    'en-US-AmandaMultilingualNeural': 'A bright and clear voice with a youthful energy.',
    'en-US-DerekMultilingualNeural': 'A formal, knowledgeable voice that exudes confidence.',
    'ko-KR-HyunsuNeural': 'A casually bright voice perfect for engaging chats and captivating narrations, delivering content with a vibrant and approachable tone.',
    'en-US-DavisNeural': 'A generally calm and relaxed voice that can switch between tones seamlessly and be highly expressive when needed.',
    'de-DE-ConradNeural': 'An engaging and friendly voice, perfect for maintaining a warm and inviting conversation.',
    'en-US-Phoebe:DragonHDLatestNeural': 'HD version of Phoebe, a confident and upbeat voice with youthful energy',
    'es-MX-MarinaNeural': "A child voice that's great at conveying curiousity",
    'es-ES-XimenaNeural': 'A crisp and cheerful voice, bringing clarity and positivity to the conversation.',
    'en-US-JasonNeural': "An early-20s male voice that's polite and unassuming, perhaps a little shy, with a respectful and professional tone that leaves a good impression.",
    'zh-HK-HiuGaaiNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'ru-RU-DariyaNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.  ",
    'en-US-SaraNeural': 'A female teenager voice with a wide range of expressive capabilities that can convey any emotion with ease and keep users engaged.',
    'zh-CN-Xiaochen:DragonHDFlashLatestNeural': 'HD Flash versions of Xiaochen, with Chinese and English bilingual capability while maintaining the same feature as HD version',
    'it-IT-IsabellaNeural': 'An upbeat and bright voice, adding energy and cheerfulness to the conversation.',
    'en-AU-NatashaNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'ca-ES-AlbaNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'pl-PL-ZofiaNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'en-US-CoraNeural': 'A softer voice with a touch of melancholy that conveys understanding and empathy, delivering content in a sensitive and compassionate way.',
    'zh-CN-shaanxi-XiaoniNeural': 'A confident, engaging, and casual voice that keeps the conversation both lively and relaxed.',
    'en-US-DustinMultilingualNeural': 'A voice good for news and podcasts with a unique timbre.',
    'en-US-MichelleNeural': 'An honest voice that conveys confidence and understanding.',
    'fr-FR-HenriNeural': 'A strong and calm voice, projecting both power and serenity in communication.',
    'pt-PT-RaquelNeural': 'A calm and bright voice, balancing serenity with positivity to create an optimistic tone.',
    'es-ES-Ximena:DragonHDLatestNeural': 'HD version of Ximena, a crisp and cheerful voice, bringing clarity and positivity to the conversation',
    'zh-CN-XiaoshuangNeural': 'A cute and lovely voice that can be applied in many child related scenarios.',
    'zh-CN-XiaochenMultilingualNeural': 'A friendly, casual, and upbeat voice, perfect for energizing conversations and lighthearted exchanges.',
    'en-US-JennyNeural': 'A youthful voice with a wide range of expressions, perfect for customer service and keeping users satisfied.',
    'en-US-SerenaMultilingualNeural': 'A mature, formal voice that commands confidence and respect.',
    'fi-FI-NooraNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'en-US-RyanMultilingualNeural': 'A straightforward voice that  works well for delivering information quickly and concisely',
    'zh-CN-XiaomengNeural': 'A gentle, upbeat, and friendly voice, perfect for adding warmth and positivity to every conversation.',
    'en-AU-CarlyNeural': "A child voice that's great at conveying curiousity",
    'ar-OM-AyshaNeural': 'A young voice with a wide range of expressions',
    'en-GB-AdaMultilingualNeural': 'A cheerful and friendly voice, bringing a positive and engaging energy to every conversation.',
    'zh-CN-YunfengNeural': 'A confident, animated, and emotional voice, full of energy and depth, delivering every message with conviction.',
    'en-US-LunaNeural': 'A warm, sincere, and pleasant voice that conveys genuine care and trustworthiness in every interaction.',
    'en-US-TonyNeural': 'A versatile voice that can sound both casual and professional, adaptable to any use case and situation.',
    'en-US-Serena:DragonHDLatestNeural': 'HD version of Serena, a mature, formal voice that commands confidence and respect',
    'en-US-LewisMultilingualNeural': 'A confident, formal voice that conveys expertise and authority.',
    'it-IT-GiuseppeNeural': 'A bright and warm voice, perfect for both casual chats and engaging audiobooks, creating an inviting and cheerful atmosphere.',
    'ko-KR-HyunsuMultilingualNeural': 'A voice good for fact information and knowledge.',
    'en-US-AshTurboMultilingualNeural': 'A warm, confident voice for conversation.',
    'fr-FR-Vivienne:DragonHDLatestNeural': 'HD version of Vivienne, a warm and casual voice perfect for advertisements, creating a welcoming and relaxed atmosphere for listeners',
    'hr-HR-SreckoNeural': 'A friendly voice with slightly whimsical undertones but with a wide expressive range',
    'en-US-SamuelMultilingualNeural': 'An expressive voice that feels warm and sincere.',
    'de-DE-SeraphinaMultilingualNeural': 'A casually charming voice, ideal for both casual chats and audiobooks, offering a relaxed yet engaging tone.',
    'zh-CN-liaoning-YunbiaoNeural': 'A confident, casual, and cheerful voice, offering positivity and assurance in a balanced tone.',
    'de-DE-Seraphina:DragonHDLatestNeural': 'HD version of Andrew with tones that feel natural and adaptable, perfect for conversations, podcasts, and chats.',
    'ar-MA-MounaNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'zh-CN-YunzeNeural': 'A deep, confident, and formal voice, ideal for delivering important information with authority and clarity.',
    'de-AT-JonasNeural': 'A friendly voice with slightly whimsical undertones but with a wide expressive range',
    'zh-TW-HsiaoChenNeural': 'A soft and caring voice, offering warmth and compassion in every interaction.',
    'zh-CN-guangxi-YunqiNeural': 'An engaging, casual, and animated voice that keeps conversations lively and full of energy.',
    'ja-JP-Masaru:DragonHDLatestNeural': 'HD version of Masaru with a versatile array of tones to enhance conversational experiences and immersive audiobooks.',
    'zh-CN-liaoning-XiaobeiNeural': 'A friendly, casual, and gentle voice that makes interactions feel approachable and soothing.',
    'en-US-Andrew3:DragonHDLatestNeural': 'HD version of Andrew with a more engaging, conversational tone, ideal for podcast content.',
    'zh-CN-XiaoqiuNeural': 'An intellectual and comfort voice that is good for reading long contents.',
    'zh-CN-YunyeNeural': 'A mature and relaxing voice with multiple emotions that is optimized for audio books.',
    'fr-FR-YvetteNeural': 'An animated and bright voice which will be suitable for narrating and chat.',
    'wuu-CN-XiaotongNeural': 'A warm, friendly, and soothing voice, providing comfort and a relaxed tone for a pleasant conversation.',
    'pt-PT-DuarteNeural': 'A serious and deep voice, offering a tone of gravity and importance in critical discussions.',
    'es-MX-DaliaMultilingualNeural': 'A bright and upbeat voice, perfect for adding enthusiasm and energy to any dialogue.',
    'en-US-ChristopherMultilingualNeural': 'A warm voice for imparting information, especially for conversation,  great for conveying information in a fun and approachable way.',
    'ja-JP-KeitaNeural': 'A casual and engaging voice, making the conversation feel relaxed yet lively.',
    'zh-CN-Xiaoxiao:DragonHDFlashLatestNeural': 'HD Flash version of Xiaoxiao, with Chinese and English bilingual capability suitable for multiple scenario styles and emotions',
    'en-US-LolaMultilingualNeural': 'A calm and sincere voice with a warm, reassuring tone.',
    'zh-CN-sichuan-YunxiNeural': 'A casual, animated, and gentle voice, offering a lively yet soft and calming presence.',
    'yue-CN-YunSongNeural': 'A deep, calm, and formal voice, exuding authority and professionalism in a composed manner.',
    'en-GB-SoniaNeural': 'A gentle and soft voice, providing a calm and soothing presence.',
    'en-US-AshleyNeural': 'A young voice that sounds a little shy but honest and sincere, conveying a sense of authenticity and approachability.',
    'en-US-DavisMultilingualNeural': 'A generally calm and relaxed voice that can switch between tones seamlessly and be highly expressive when needed.',
    'zh-CN-XiaoruiNeural': 'A mature and wise voice with rich emotions that is optimized for audio books.',
    'ar-AE-FatimaNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'af-ZA-AdriNeural': 'A bright and clear voice with a youthful energy.',
    'en-US-AnaNeural': "A child voice that's great at conveying curiosity and engaging users with a fun and playful tone that's sure to delight.",
    'en-IE-ConnorNeural': 'A friendly voice with slightly whimsical undertones but with a wide expressive range',
    'en-US-SteffanNeural': 'A great voice for imparting information, especially in a learning environment.',
    'en-US-AIGenerate2Neural': 'A somewhat serious voice to convey information in an objective manner',
    'zh-CN-XiaoxiaoDialectsNeural': 'Xiaoxiao voice that can speaks several Chinese dialects',
    'en-US-Andrew2:DragonHDLatestNeural': 'HD version of Andrew with a more casual, laid-back tone ideal for friendly conversations.',
    'ar-KW-NouraNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'en-US-Emma:DragonHDLatestNeural': 'HD versions of Emma delivering an energetic, dynamic tone, suited for podcasts, chats, and lively storytelling.',
    'en-CA-ClaraNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'fr-FR-EloiseNeural': "A child voice that's great at conveying curiousity",
    'en-US-Steffan:DragonHDLatestNeural': 'HD versions of Steffan with a wider range of styles, perfectly suited for audiobook narration and storytelling.',
    'it-IT-MarcelloMultilingualNeural': 'A warm and pleasant voice, offering a soothing and comforting tone to all dialogues.',
    'en-US-EmmaMultilingualNeural': "A friendly, sincere voice with a light-hearted and pleasant tone that's ideal for education and explanations.",
    'zh-CN-YunxiNeural': 'A lively and sunshine voice with rich emotions that can be used in many conversation scenarios.',
    'de-DE-FlorianMultilingualNeural': 'A warm and cheerful voice, perfect for chatting or audiobooks, with great versatility to adapt to any use case and speak clearly for easy understanding.',
    'tr-TR-EmelNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'en-US-RogerNeural': 'A friendly voice that conveys information in a approachable manner',
    'en-US-Ava:DragonHDLatestNeural': 'HD versions of Ava featuring a bright, versatile voice, engaging for podcasts, storytelling, and conversational chats.',
    'wuu-CN-YunzheNeural': 'A calm, deep, and gentle voice, bringing serenity and trust to each word spoken.',
    'en-US-Nova:DragonHDLatestNeural': 'HD versions of Nova, a deep and resonant voice',
    'en-US-BrandonMultilingualNeural': "An honest and soft-spoken voice that's warm and good for conversation, connecting with users on a personal level and building trust.",
    'en-US-Emma2:DragonHDLatestNeural': 'HD versions of Emma with a calm, deeper tone, making it ideal for thoughtful conversations and easy chats.',
    'fr-FR-LucienMultilingualNeural': 'A warm, confident voice with a formal touch',
    'it-IT-PalmiraNeural': 'An animated and bright voice which will be suitable for narrating and chat.',
    'es-ES-AlvaroNeural': 'A confident and animated voice, full of energy and self-assurance.',
    'en-US-BrianNeural': 'A youthful, cheerful, and versatile voice that can handle any task you throw its way, well-suited to a wide variety of contexts.',
    'ja-JP-Nanami:DragonHDLatestNeural': 'HD version of Nanami, a bright and cheerful voice, offering a lively and uplifting tone for every situation',
    'th-TH-AcharaNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'nb-NO-IselinNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'zh-CN-YunxiaoMultilingualNeural': 'A calm, approachable, and clear voice for friendly chat.',
    'en-US-EricNeural': 'A friendly voice that conveys soft-spoken confidence, inspiring trust and reliability with a calm and collected tone.',
    'es-ES-TristanMultilingualNeural': 'A trustworthy voice to deliver fact and information.',
    'es-ES-XimenaMultilingualNeural': 'A serious yet upbeat voice with a formal tone.',
    'en-US-KaiNeural': 'A sincere, pleasant, and warm voice, offering a heartfelt and approachable tone to the conversation.',
    'en-US-MonicaNeural': 'A mature voice that conveys a strong sense of believability, perfect for delivering content in the best possible way',
    'es-ES-ArabellaMultilingualNeural': 'A warm and pleasant voice, adding a touch of calm and comfort to any situation.',
    'zh-TW-YunJheNeural': 'An engaging and gentle voice, providing a lively yet soothing presence.',
    'en-US-AdamMultilingualNeural': 'A deep, engaging voice that feels warm and inviting.',
    'ar-DZ-AminaNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'sv-SE-HilleviNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'bg-BG-BorislavNeural': 'A friendly voice with slightly whimsical undertones but with a wide expressive range',
    'en-US-JaneNeural': "An early-20s female voice like the girl next door that's warm and friendly, great for building a connection with users.",
    'en-US-Alloy:DragonHDLatestNeural': 'HD version of Alloy which suitable for various contexts.',
    'zh-CN-XiaoyouNeural': 'An angelic and clear voice that can be applied in many child related scenarios.',
    'en-US-FableTurboMultilingualNeural': 'Turbo version for Fable, a voice with a touch of mystery and intrigue (gender unspecified)',
    'ja-JP-MasaruMultilingualNeural': 'A bright and warm voice ideal for conversational chats and immersive audiobooks, infusing warmth and brightness into every interaction.',
    'en-GB-OllieMultilingualNeural': 'A friendly and pleasant voice, perfect for creating a comfortable and approachable atmosphere.',
    'ar-SY-AmanyNeural': 'A young voice with a wide range of expressions',
    'en-US-AndrewMultilingualNeural': 'A warm, engaging voice that sounds like someone you want to know, perfect for building a connection with listeners.',
    'zh-CN-YunxiaNeural': 'A cheerful, friendly, and emotional voice, bringing warmth and feeling to every interaction.',
    'en-US-OnyxTurboMultilingualNeural': 'Turbo version for Onyx, a confident and authoritative male voice',
    'es-ES-IsidoraMultilingualNeural': 'A cheerful and casual voice, bringing a laid-back and positive vibe to conversations.',
    'pt-BR-FranciscaNeural': 'A cheerful and crisp voice, providing a clear and positive tone for effective communication.',
    'en-US-AriaNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'it-IT-GiuseppeMultilingualNeural': 'An upbeat, expressive voice with youthful enthusiasm',
    'en-US-Ava3:DragonHDLatestNeural': 'HD version of Ava with a more engaging, conversational tone, ideal for podcast content.',
    'en-US-BrianMultilingualNeural': 'A youthful, cheerful, and versatile voice that can handle any task you throw its way, well-suited to a wide variety of contexts.',
    'zh-CN-henan-YundengNeural': 'A casual, friendly, and animated voice that adds fun and energy to relaxed conversations.',
    'zh-CN-YunyangNeural': 'A professional and fluent voice with multiple scenario styles.',
    'pt-BR-ThalitaMultilingualNeural': 'A confident and formal voice, conveying professionalism and authority in every conversation.',
    'de-DE-GiselaNeural': "A child voice that's great at conveying curiousity",
    'ja-JP-MayuNeural': 'An animated and bright voice which will be suitable for narrating and chat.',
    'es-ES-IreneNeural': "A child voice that's great at conveying curiousity",
    'zh-TW-HsiaoYuNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'en-US-Davis:DragonHDLatestNeural': 'HD versions of Davis  with a soothing, relaxed tone, perfect for calming conversations and easygoing chats.',
    'en-US-JacobNeural': "A mature voice that conveys a strong sense of believability, delivering content in a way that's straightforward and to the point.",
    'zh-CN-Yunxiao:DragonHDFlashLatestNeural': 'HD Flash version of Yunxiao, with Chinese and English bilingual capability and calm, approachable persona for friendly chat',
    'zh-CN-Yunfan:DragonHDLatestNeural': 'HD version of Yunfan, a clear, warm, and youthful voice which is good for different scenarios.',
    'nl-NL-FennaNeural': 'A bright and confident voice, delivering clarity and self-assurance in every interaction.',
    'zh-CN-XiaorouNeural': 'A cheerful, engaging, and pleasant voice that creates a happy and inviting environment.',
    'zh-CN-Xiaoxiao2:DragonHDFlashLatestNeural': 'HD Flash version of Xiaoxiao, with Chinese and English bilingual capability suitable for conversational scenarios',
    'en-US-NancyNeural': "A confident-sounding voice that's perfect for delivering important information with a professional and authoritative tone that inspires trust.",
    'zh-HK-WanLungNeural': 'A calm and formal voice, delivering information with both serenity and professionalism.',
    'zh-CN-XiaomoNeural': 'A clear and relaxing voice with rich role-play and emotions that is optimized for audio books.',
    'en-US-ShimmerTurboMultilingualNeural': 'Turbo version for Shimmer, a bright and engaging female voice',
    'ms-MY-OsmanNeural': 'A friendly voice with slightly whimsical undertones but with a wide expressive range',
    'en-US-GuyNeural': 'A friendly voice with slightly whimsical undertones and a wide expressive range that can convey any emotion with ease.',
    'zh-CN-Xiaochen:DragonHDLatestNeural': 'HD versions of Xiaochen featuring a friendly, natural tone, ideal for smooth, engaging conversation.',
    'en-US-AlloyTurboMultilingualNeural': 'Turbo version for Alloy, a versatile male voice suitable for various contexts.',
    'en-US-Jenny:DragonHDLatestNeural': 'HD versions of Jenny with a youthful voice, offering a more natural tone tailored for casual conversations and chats.',
    'zh-HK-HiuMaanNeural': 'A bright and upbeat voice that brings energy and positivity to any conversation.',
    'pt-BR-LeticiaNeural': "A child voice that's great at conveying curiousity",
    'yue-CN-XiaoMinNeural': 'A bright, crisp, and confident voice, delivering clarity and assurance in every statement.',
    'es-ES-LiaNeural': 'An animated and bright voice which will be suitable for narrating and chat.',
    'en-US-Bree:DragonHDLatestNeural': 'HD version, Bree is a teenager girl, a bright and bubbly voice, radiating youthful energy and a playful charm in every word.',
    'hu-HU-TamasNeural': 'A friendly voice with slightly whimsical undertones but with a wide expressive range',
    'en-US-Aria:DragonHDLatestNeural': 'HD versions of Aria with a diverse range of natural tones, optimized for engaging dialogue and more.',
    'en-US-EchoTurboMultilingualNeural': 'Turbo version for Echo, a clear and expressive male voice',
    'ko-KR-SeoHyeonNeural': "A child voice that's great at conveying curiousity",
    'es-MX-DaliaNeural': 'A bright and upbeat voice, perfect for adding enthusiasm and energy to any dialogue.',
    'ar-TN-ReemNeural': 'A young voice with a wide range of expressions',
    'ar-EG-SalmaNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'en-US-ChristopherNeural': 'A warm voice for imparting information, especially for conversation,  great for conveying information in a fun and approachable way.',
    'zh-CN-shandong-YunxiangNeural': 'A casual, animated, and strong voice, full of energy and strength, ideal for captivating listeners.',
    'it-IT-ElsaNeural': 'A confident and crisp voice, delivering messages with clarity and self-assurance.',
    'zh-CN-YunjieNeural': 'A casual, confident, and warm voice that offers both professionalism and friendliness in a relaxed tone.',
    'ar-SA-ZariyahNeural': "A clear-sounding voice with great versatility that can adapt to any use case and speak in a way that's easy to understand.",
    'es-ES-Tristan:DragonHDLatestNeural': 'HD version of Tristan, a trustworthy voice to deliver fact and information',
    'fr-FR-DeniseNeural': 'A bright and engaging voice, ideal for capturing attention and keeping conversations lively.'
}
