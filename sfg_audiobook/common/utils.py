import numpy as np

from sfg_types import TextPart


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
