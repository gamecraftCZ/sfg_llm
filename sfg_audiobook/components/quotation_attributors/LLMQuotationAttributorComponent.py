from pydantic import BaseModel, Field
import Levenshtein
from tqdm.contrib.concurrent import thread_map
from common.utils import split_into_chunks_with_overlap, merge_neighbouring_text_parts_of_the_same_type_and_character
from components.ComponentsRegister import ComponentsRegister
from sfg_types import PipelineData, TextPart, TextPartType
from components.abstract import AbstractStructuredLLMComponent

class PredictedTextPart(BaseModel):
    text: str = Field(..., description="The exact text (including all whitespaces) of the text.")
    type: TextPartType = Field(..., description="The type of text part.")
    character_identifier: str | None = Field(default=None, description="The unique identifier of the character who said that quote")

class TextParts(BaseModel):
    segments: list[PredictedTextPart]

    def as_text_parts_list(self) -> list[TextPart]:
        return [TextPart(id=i, text=segment.text, type=segment.type, character_identifier=segment.character_identifier) for i, segment in enumerate(self.segments)]

class LLMQuotationAttributorComponent(AbstractStructuredLLMComponent):
    """
    Use LLMs with Jinja2 prompt templates to extract and attribute quotations in the text.
    This component uses litellm to support many different LLM backends.
    Predicts chunk by chunk with chink size of [chunk_size] characters.
    """

    def __init__(self, params: dict[str, str], name: str = None, *args, **kwargs) -> None:
        super().__init__(params, name, *args, **kwargs)
        self._chunk_size = int(params.get('chunk_size', 12000))  # Around 5000 output tokens.
        self._chunk_overlap = int(params.get('chunk_overlap', 512))
        self._concurrent_requests = int(params.get('concurrent_requests', 32))

    @staticmethod
    def get_help() -> str:
        return f"""Uses LLMs with Jinja2 prompt templates to extract and attribute quotations in the text.
{LLMQuotationAttributorComponent.get_attributes_help_text()}
\tAttribute (optional): chunk_size (str): Number of characters in chunk sent to LLM. Default 4096
\tAttribute (optional): chunk_overlap (str): Overlapping characters between chunks. Default 512
\tAttribute (optional): _concurrent_requests (int): Number of concurrent request to the model. Default: 32
"""

    def setup(self, data: PipelineData):
        pass

    @staticmethod
    def _chunk_label_start_end_inplace_and_get_text(chunk: list[TextPart]):
        text = ""
        start = 0
        for text_part in chunk:
            text_part.start = start
            start += len(text_part.text)
            text_part.end = start

            text += text_part.text
        return text

    @staticmethod
    def _add_displacement_to_chunk_start_ends_in_place(chunk: list[TextPart], displacement: int):
        for text_part in chunk:
            text_part.start += displacement
            text_part.end += displacement

    @staticmethod
    def _find_best_displacement(text1: str, text2: str, min_overlap: int, max_overlap: int) -> int:
        best_overlap, min_distance, min_last_chars_distance = None, (1000 * len(text1) + len(text2)), 999

        for overlap in range(min_overlap, max_overlap + 1):
            # Get the text with the overlap
            text1_overlap = text1[-overlap:]  # Last overlap characters of text1
            text2_overlap = text2[:overlap]   # First overlap characters of text2

            # Get the distance between the two texts
            ops = Levenshtein.editops(text1_overlap, text2_overlap)
            ops_last = Levenshtein.editops(text1_overlap[-16:], text2_overlap[-16:])
            if len(ops_last) < min_last_chars_distance:
                best_overlap = overlap
                min_last_chars_distance = len(ops_last)
                min_distance = len(ops)
            elif len(ops_last) == min_last_chars_distance and len(ops) < min_distance:
                best_overlap = overlap
                min_distance = len(ops)

        print(min_last_chars_distance, min_distance)
        return best_overlap


    def _glue_text_part(self, all_chunks_text_parts: list[list[TextPart]]):
        if not all_chunks_text_parts:
            return []
        if len(all_chunks_text_parts) == 1:
            return all_chunks_text_parts[0]

        final_text = LLMQuotationAttributorComponent._chunk_label_start_end_inplace_and_get_text(all_chunks_text_parts[0])
        displacements = [0]

        # Glue two together
        for text_part in all_chunks_text_parts[1:]:
            # Get the text from the chunk
            text = LLMQuotationAttributorComponent._chunk_label_start_end_inplace_and_get_text(text_part)

            displacement = LLMQuotationAttributorComponent._find_best_displacement(final_text, text, self._chunk_overlap // 2, self._chunk_overlap * 2)
            displacements.append(displacement)

            # Add the displacement to the start and end of the chunk
            # LLMQuotationAttributorComponent._add_displacement_to_chunk_start_ends_in_place(text_part, len(final_text) - displacement)

            # Add the displaced text to the final text
            final_text += text[displacement:]

        # Merge together
        final_text_parts = []
        for displacement, chunks in zip(displacements, all_chunks_text_parts):
            for text_part in chunks:
                if text_part.end < displacement:
                    continue

                # Set new start
                old_start = text_part.start
                new_start = max(displacement, old_start)
                text_part.text = text_part.text[new_start - old_start:]
                text_part.start = new_start

                final_text_parts.append(text_part)

        merged_text_parts = merge_neighbouring_text_parts_of_the_same_type_and_character(final_text_parts)
        # Set correct start and end to the final text_parts
        start = 0
        for text_part in merged_text_parts:
            text_part.start = start
            start += len(text_part.text)
            text_part.end = start
        return merged_text_parts

    def run(self, data: PipelineData):
        # Split into chunks
        chunks = split_into_chunks_with_overlap(data.original_text, self._chunk_size, self._chunk_overlap)#[:4]  # TODO remove the limit of four chunks for testing!

        # Predict chunk by chunk in parallel
        results = thread_map(lambda chunk: self.predict(data, chunk, TextParts), chunks, max_workers=self._concurrent_requests)
        chunks_text_parts = [r[0].as_text_parts_list() for r in results]
        chunks_stats = [r[1] for r in results]

        # Glue the overlapping text parts back together
        final_text_parts = self._glue_text_part(chunks_text_parts)

        # Output the text parts
        data.text_as_parts = final_text_parts
        for i, part in enumerate(data.text_as_parts):
            part.id = i + 1  # Make sure predicted id is unique by setting new ids
        data.additional_attributes["llm_quotation_attribution_stats"] = {
            "chunk_size": self._chunk_size,
            "chunk_overlap": self._chunk_overlap,
            "num_chunks": len(chunks),
            "num_text_parts": len(data.text_as_parts),

            "predicted_text_parts_chunks_list": chunks_text_parts,

            # LLM info
            "llm_raw_stats": chunks_stats,
            "llm_total_input_tokens": sum([s["prompt_tokens"] for s in chunks_stats]),
            "llm_total_output_tokens": sum([s["completion_tokens"] for s in chunks_stats]),
        }


ComponentsRegister.register_component("llm_quotation_attributor", LLMQuotationAttributorComponent)
