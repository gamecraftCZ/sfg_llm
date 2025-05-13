from sfg_audiobook.components.ComponentsRegister import ComponentsRegister
from sfg_audiobook.sfg_types import PipelineData, TTSSpeaker
from sfg_audiobook.structure.AbstractComponent import AbstractComponent


class DummyTextToSpeechComponent(AbstractComponent):
    """
    Dummy Text To Speech. On setup adds a dummy speaker to the available speakers list. Otherwise does nothing.
    """

    @staticmethod
    def get_help() -> str:
        return """Dummy Text To Speech. On setup adds a dummy speaker to the available speakers list. Otherwise does nothing."""

    def setup(self, data: PipelineData):
        data.available_speakers = [
            TTSSpeaker(id="dummy_speaker", description="Dummy TTS speaker")
        ]

    def run(self, data: PipelineData):
        pass


ComponentsRegister.register_component("dummy_tts", DummyTextToSpeechComponent)
