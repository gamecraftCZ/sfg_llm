from dataclasses import dataclass

@dataclass
class Character:
    name: str  # Name of the character
    identifier: str  # Unique character identifier
    type: str  # Type of character (e.g., main, support, minor)
    gender: str  # male, female, other, unknown
    personality: str  # Personality traits of the character
    assigned_speaker: str  # The unique assigned speaker id for the character
