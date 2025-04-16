from components.ComponentsRegister import ComponentsRegister
from sfg_types import PipelineData, TextPart
from structure.AbstractComponent import AbstractComponent


class DummyQuotationAttributorComponent(AbstractComponent):
    """
    Dummy quotation attributor. Splits the text into same number of words text parts. May omit few words at the end.
    Always assigns the first available character to all quotes parts (or None if none available).
    """

    @staticmethod
    def get_help() -> str:
        return """Dummy quotation attributor. Always assigns the first available character to all quotes parts (or None if none available)."""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        # Split text to chunks
        words = data.original_text.split()
        chunks_count, chunk_size = len(words), 8
        word_chunks = [words[i:i + chunk_size] for i in range(0, chunks_count, chunk_size)]
        data.text_as_parts = [TextPart(text=" ".join(chunk), type=("other" if i % 2 == 0 else "quote"))
                              for i, chunk in enumerate(word_chunks)]

        # Assign characters to quotes
        for text_part in data.text_as_parts:
            if text_part.type == "quote":
                text_part.character_identifier = data.characters[0].identifier if len(data.characters) > 0 else None


ComponentsRegister.register_component("dummy_quotation_attributor", DummyQuotationAttributorComponent)
