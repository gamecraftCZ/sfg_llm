import numpy as np
import re
from sfg_audiobook.sfg_types import TextPart


def merge_neighbouring_text_parts_of_the_same_type_and_character(text_parts: list[TextPart], separator: str = "") -> list[TextPart]:
    """
    Takes list of text parts and merges neighbouring text parts of the same type and character.
    :param text_parts:
    :param separator: When two text parts are merged, this string is used to separate them.
    :return:
    """
    merged_text_parts = []
    current_part = None

    for part in text_parts:
        if current_part is None:
            current_part = part.model_copy()
        elif current_part.character_identifier == part.character_identifier and current_part.type == part.type:
            # Merge parts if they are quote from the same character and type (merges both quotes and other text)
            current_part.text += separator + part.text
        else:
            merged_text_parts.append(current_part)
            current_part = part.model_copy()

    if current_part is not None:
        merged_text_parts.append(current_part)

    return merged_text_parts


def remove_empty_text_parts(text_parts: list[TextPart]) -> list[TextPart]:
    """
    Removes all text parts containing only blank characters.
    """
    return [part for part in text_parts if part.text.strip() != ""]


def remove_duplicate_spaces(text_parts: list[TextPart], strip: bool = False) -> list[TextPart]:
    """
    If there are two or more spaces in a row, remove all but one.
    :param text_parts:
    :param strip: If True, also strip leading and trailing spaces from each text part.
    :return:
    """
    _RE_COMBINE_WHITESPACE = re.compile(r"\s+")
    for part in text_parts:
        part.text = _RE_COMBINE_WHITESPACE.sub(" ", part.text)
        if strip:
            part.text = part.text.strip()
    return text_parts


def array_to_ranges(arr: np.ndarray) -> list[tuple[int, int]]:
    """
    Convert a sorted array of integers into ranges represented as (start, end) tuples.
    Each range is inclusive.

    Args:
        arr: A sorted numpy array of integers

    Returns:
        A list of tuples, each representing a range (start, end)
    """
    if len(arr) == 0:
        return []

    # Ensure array is sorted
    arr = np.sort(arr)

    # Find where consecutive differences are not 1
    # This marks the boundaries between ranges
    diff = np.diff(arr)
    split_indices = np.where(diff > 1)[0]

    # Initialize the ranges list
    ranges = []

    # Start of the first range
    start_idx = 0

    # Iterate through split points
    for end_idx in split_indices:
        ranges.append((arr[start_idx], arr[end_idx] + 1))
        start_idx = end_idx + 1

    # Add the last range
    ranges.append((arr[start_idx], arr[-1]))

    return ranges


def split_into_chunks_with_overlap(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
        Split text into chunks of specified size with overlap between consecutive chunks.

        Args:
            text: Text to split
            chunk_size: Maximum size of each chunk (all except the last one will be of this size)
            overlap: Number of characters to overlap between chunks

        Returns:
            List of text chunks
    """
    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0:
        raise ValueError("overlap must be non-negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])

        # Move to next chunk, accounting for overlap
        start = end - overlap if end < len(text) else len(text)

    return chunks

