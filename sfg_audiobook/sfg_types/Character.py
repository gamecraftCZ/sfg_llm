from enum import Enum

from pydantic import BaseModel, Field


class CharacterType(str, Enum):
    MAIN = "main"
    SUPPORT = "support"
    MINOR = "minor"
    UNKNOWN = "unknown"

    def __str__(self):
        return self.value


class CharacterGender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value

class Character(BaseModel):
    name: str = Field(..., description="Name of the character")
    identifier: str = Field(..., description="Unique character identifier")
    type: CharacterType = Field(default=CharacterType.UNKNOWN, description="Type of character (e.g., main, support, minor)")
    gender: CharacterGender = Field(default=CharacterGender.UNKNOWN, description="Gender of the character (male, female, other, unknown)")
    personality: str = Field(default="", description="Personality traits of the character")
    assigned_speaker_id: str | None = Field(None, description="The unique assigned speaker ID for the character")
