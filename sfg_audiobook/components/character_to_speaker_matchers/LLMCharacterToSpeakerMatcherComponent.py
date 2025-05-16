from pydantic import BaseModel, Field

from sfg_audiobook.components.ComponentsRegister import ComponentsRegister
from sfg_audiobook.sfg_types import PipelineData, TextPart, TextPartType
from sfg_audiobook.components.abstract import AbstractStructuredLLMComponent
from sfg_types import Character, CharacterType


class CharacterMatch(BaseModel):
    character_id: str = Field(default_factory=lambda: "", description="Identifier of the character.")
    voice: str = Field(default_factory=lambda: "", description="The voice assigned to the character.")

class CharacterVoiceMatches(BaseModel):
    matches: list[CharacterMatch] = Field(default_factory=lambda: {}, description="A dictionary of character names and their corresponding voices.")


class LLMCharacterToSpeakerMatcherComponent(AbstractStructuredLLMComponent):
    """
    Use LLMs with Jinja2 prompt templates to match characters with voices.
    This component uses litellm to support many different LLM backends.
    """

    def __init__(self, params: dict[str, str], name: str = None, *args, **kwargs) -> None:
        super().__init__(params, name, *args, **kwargs)

    @staticmethod
    def get_help() -> str:
        return f"""Uses LLMs with Jinja2 prompt templates to match characters with voices.
{LLMCharacterToSpeakerMatcherComponent.get_attributes_help_text()}
"""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        assert data.available_voices, "No available voices. Please set available_voices in the pipeline data."
        # Add a default narrator if not present
        if not any(character.type == CharacterType.NARRATOR for character in data.characters):
            print("No narrator found in characters. Adding a default narrator.")
            data.characters.append(Character(name="narrator", identifier="NARRATOR", type=CharacterType.NARRATOR))

        matches_list, stats = self.predict(data, data.original_text, CharacterVoiceMatches)
        if matches_list is None:
            raise ValueError("Matched characters to voices list is None. Character extraction failed.")

        available_voices_ids = [voice.id for voice in data.available_voices]
        for character in data.characters:
            match = next((m for m in matches_list.matches if m.character_id == character.identifier), None)
            if match:
                if match.voice not in available_voices_ids:
                    print(f"Warning: Voice {match.voice} not found in available voices but assigned by LLM. Setting to None.")
                    character.assigned_voice_id = None
                else:
                    character.assigned_voice_id = match.voice
            else:
                print(f"Warning: No voice assigned to character {character.identifier}.")
                character.assigned_voice_id = None

        data.additional_attributes["llm_characters_matcher_stats"] = {
            "llm_all_stats": stats,
            "llm_total_input_tokens": stats["prompt_tokens"],
            "llm_total_output_tokens": stats["completion_tokens"],
        }


ComponentsRegister.register_component("llm_character_to_speaker_matcher", LLMCharacterToSpeakerMatcherComponent)
