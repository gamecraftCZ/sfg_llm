from pydantic import BaseModel


class TextPart(BaseModel):
    text: str
    type: str  # "quote" or "other"
    character_identifier: str | None = None  # The unique identifier of the character who said that quote
