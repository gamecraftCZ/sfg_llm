from components.ComponentsRegister import ComponentsRegister
from sfg_types import PipelineData
from structure.AbstractComponent import AbstractComponent


class DummyCharacterToSpeakerMatcherComponent(AbstractComponent):
    """
    Dummy Character to speaker matcher. Always assigns the first available speaker to all characters (or "default_speaker_id")
    """

    @staticmethod
    def get_help() -> str:
        return """Dummy character to speaker matcher. Always assigns the first available speaker to all characters (or "default_speaker_id")"""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        for character in data.characters:
            if character.assigned_speaker_id is None:
                character.assigned_speaker_id = data.available_speakers[0].id if len(data.available_speakers) > 0 else "default_speaker_id"


ComponentsRegister.register_component("dummy_character_to_speaker_matcher", DummyCharacterToSpeakerMatcherComponent)
