from abc import ABC, abstractmethod

from sfg_audiobook.types.Character import Character
from sfg_audiobook.types.TextPart import TextPart


class AbstractQuotationAttributor(ABC):
    """
    Abstract class for quotation attributors.
    """

    def __init__(self) -> None:
        pass

    @abstractmethod
    def attribute_text(self, text: str, characters_list: list[Character]) -> list[TextPart]:
        raise NotImplementedError()
