from typing import List
from pydantic import BaseModel
from sfg_audiobook.components.ComponentsRegister import ComponentsRegister
from sfg_audiobook.sfg_types import PipelineData, Character
from sfg_audiobook.components.abstract import AbstractStructuredLLMComponent


class CharactersList(BaseModel):
    characters: List[Character]

class LLMCharacterExtractor(AbstractStructuredLLMComponent):
    """
    Use LLMs with Jinja2 prompt templates to extract all characters from the text.
    This component uses litellm to support many different LLM backends.
    """

    def __init__(self, params: dict[str, str], name: str = None, *args, **kwargs) -> None:
        super().__init__(params, name, *args, **kwargs)

    @staticmethod
    def get_help() -> str:
        return f"""Uses LLMs with Jinja2 prompt templates to extract all characters from the text.
{LLMCharacterExtractor.get_attributes_help_text()}
"""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        characters_list, stats = self.predict(data, data.original_text, CharactersList)
        if characters_list is None:
            raise ValueError("Extracted characters list is None. Character extraction failed.")

        data.characters = characters_list.characters
        data.additional_attributes["llm_characters_extraction_stats"] = {
            "llm_all_stats": stats,
            "llm_total_input_tokens": stats["prompt_tokens"],
            "llm_total_output_tokens": stats["completion_tokens"],
        }


ComponentsRegister.register_component("llm_character_extractor", LLMCharacterExtractor)
