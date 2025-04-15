from abc import ABC, abstractmethod

from sfg_audiobook.types.Character import Character


class AbstractCharacterExtractor(ABC):
    """
    Abstract class Character extraction from text
    """

    def __init__(self) -> None:
        pass

    @abstractmethod
    def attribute_text(self, text: str) -> list[Character]:
        raise NotImplementedError()
