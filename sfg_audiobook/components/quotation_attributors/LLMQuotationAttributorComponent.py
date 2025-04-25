from pydantic import BaseModel
from components.ComponentsRegister import ComponentsRegister
from sfg_types import PipelineData, TextPart
from components.abstract import AbstractStructuredLLMComponent


class TextParts(BaseModel):
    segments: list[TextPart]

class LLMQuotationAttributorComponent(AbstractStructuredLLMComponent):
    """
    Use LLMs with Jinja2 prompt templates to extract and attribute quotations in the text.
    This component uses litellm to support many different LLM backends.
    """

    def __init__(self, params: dict[str, str], name: str = None, *args, **kwargs) -> None:
        super().__init__(params, name, *args, **kwargs)

    @staticmethod
    def get_help() -> str:
        return f"""Uses LLMs with Jinja2 prompt templates to extract and attribute quotations in the text.
{LLMQuotationAttributorComponent.get_attributes_help_text()}
"""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        # TODO - add support for splitting the text into smaller parts and then recombining them

        test_parts, stats = self.predict(data, data.original_text, TextParts)
        if test_parts is None:
            raise ValueError("Extracted segments list is None. Quotation attribution failed.")

        data.text_as_parts = test_parts.segments
        for i, part in enumerate(data.text_as_parts):
            part.id = i + 1  # Make sure predicted id is unique by setting new ids
        data.additional_attributes["llm_quotation_attribution_stats"] = stats


ComponentsRegister.register_component("llm_quotation_attributor", LLMQuotationAttributorComponent)
