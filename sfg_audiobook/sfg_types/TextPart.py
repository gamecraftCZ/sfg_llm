from enum import Enum

from pydantic import BaseModel, Field


class TextPartType(str, Enum):
    QUOTE = "quote"
    OTHER = "other"

    def __str__(self):
        return self.value


class TextPart(BaseModel):
    id: int = Field(..., description="The unique identifier of the text part starting at 1.")
    text: str = Field(..., description="The exact text (including all whitespaces) of the text.")
    type: TextPartType = Field(..., description="The type of text part.")
    character_identifier: str | None = Field(default=None, description="The unique identifier of the character who said that quote")

    def remove_newlines(self):
        self.text = self.text.replace("\n", " ")
        return self
