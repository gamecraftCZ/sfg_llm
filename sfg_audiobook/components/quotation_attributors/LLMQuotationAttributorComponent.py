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
        test_parts = self.predict(data, TextParts)
        if test_parts is None:
            raise ValueError("Extracted segments list is None. Quotation attribution failed.")

        data.text_as_parts = test_parts.segments


ComponentsRegister.register_component("llm_quotation_attributor", LLMQuotationAttributorComponent)
