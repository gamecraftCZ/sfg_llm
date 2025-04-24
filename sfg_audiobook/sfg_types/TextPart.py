from enum import Enum

from pydantic import BaseModel, Field


class TextPartType(str, Enum):
    QUOTE = "quote"
    OTHER = "other"

    def __str__(self):
        return self.value


class TextPart(BaseModel):
    text: str = Field(..., description="The exact text (including all whitespaces) of the text.")
    type: TextPartType = Field(..., description="The type of text part.")
    character_identifier: str | None = Field(default=None, description="The unique identifier of the character who said that quote")
