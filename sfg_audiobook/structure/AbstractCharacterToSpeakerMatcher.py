from abc import ABC, abstractmethod
from typing import Optional

from sfg_audiobook.types.Character import Character
from sfg_audiobook.types.TTSSpeaker import TTSSpeaker


class AbstractCharacterToSpeakerMatcher(ABC):
    """
    Abstract class to match characters to specificTTS speakers.
    """

    def __init__(self) -> None:
        pass

    @abstractmethod
    def match_characters_with_speaker(self, characters: list[Character], speaker: list[TTSSpeaker], text: Optional[str])\
            -> list[Character]:
        raise NotImplementedError()
