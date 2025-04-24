from typing import List
from pydantic import BaseModel
from components.ComponentsRegister import ComponentsRegister
from sfg_types import PipelineData, Character
from components.abstract import AbstractStructuredLLMComponent


class CharactersList(BaseModel):
    characters: List[Character]

class LLMCharacterExtractor(AbstractStructuredLLMComponent):
    """
    Use LLMs with Jinja2 prompt templates to extract and attribute quotations in the text.
    This component uses litellm to support many different LLM backends.
    """

    def __init__(self, params: dict[str, str], name: str = None, *args, **kwargs) -> None:
        super().__init__(params, name, *args, **kwargs)

    @staticmethod
    def get_help() -> str:
        return f"""Uses LLMs with Jinja2 prompt templates to extract and attribute quotations in the text.
{LLMCharacterExtractor.get_attributes_help_text()}
"""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        characters_list = self.predict(data, CharactersList)
        if characters_list is None:
            raise ValueError("Extracted characters list is None. Quotation attribution failed.")

        data.characters = characters_list.characters


ComponentsRegister.register_component("llm_character_extractor", LLMCharacterExtractor)
