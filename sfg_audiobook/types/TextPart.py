from dataclasses import dataclass

@dataclass
class TextPart:
    text: str
    
@dataclass
class Quote(TextPart):
    character_identifier: str  # The unique identifier of the character who said that quote
