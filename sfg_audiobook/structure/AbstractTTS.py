from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from sfg_audiobook.types.Character import Character
from sfg_audiobook.types.TTSSpeaker import TTSSpeaker
from sfg_audiobook.types.TextPart import TextPart


class AbstractTTS(ABC):
    """
    Abstract to convert text parts to spoken voice
    """

    def __init__(self) -> None:
        pass

    @abstractmethod
    def tts(self, characters: list[Character], speakers: list[TTSSpeaker], text_parts: list[TextPart],
            out_voice_filename: Path) -> None:
        raise NotImplementedError()
