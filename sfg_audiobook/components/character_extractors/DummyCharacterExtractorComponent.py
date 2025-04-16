from components.ComponentsRegister import ComponentsRegister
from sfg_types import Character, PipelineData
from structure.AbstractComponent import AbstractComponent


class DummyCharacterExtractorComponent(AbstractComponent):
    """
    Dummy Character Extractor. Always returns the same characters list.
    """

    @staticmethod
    def get_help() -> str:
        return """Dummy character extractor. Always returns the same characters list."""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        data.characters = [
            Character(name="Anthony sr.", identifier="ANTHONY_1", type="main", gender="male",
                      personality="warm and friendly", assigned_speaker_id=None),
            Character(name="Little girl", identifier="LITTLE_BOY_2", type="minor", gender="female",
                      personality="happy", assigned_speaker_id=None),
            Character(name="Servant", identifier="SERVANT_1", type="minor", gender="unknown",
                      personality="obedient", assigned_speaker_id=None),
            Character(name="Anthony jr.", identifier="ANTHONY_1", type="support", gender="male",
                      personality="sad", assigned_speaker_id=None),
        ]


ComponentsRegister.register_component("dummy_character_extractor", DummyCharacterExtractorComponent)
