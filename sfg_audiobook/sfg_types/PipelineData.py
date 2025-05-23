from typing import Any
from pydantic import BaseModel, Field

from .Character import Character
from .TTSVoice import TTSVoice
from .TextPart import TextPart


class PipelineData(BaseModel):
    original_text: str = Field(default_factory=lambda: "")
    characters: list[Character] = Field(default_factory=lambda: [])
    text_as_parts: list[TextPart] = Field(default_factory=lambda: [])
    available_voices: list[TTSVoice] = Field(default_factory=lambda: [])
    additional_attributes: dict[str, Any] = Field(default_factory=lambda: {})  # Can be used by components to store additional data
