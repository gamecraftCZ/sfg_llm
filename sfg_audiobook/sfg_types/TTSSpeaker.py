from pydantic import BaseModel


class TTSSpeaker(BaseModel):
    id: str  # Unique id of the speaker
    description: str  # Speaker voice description
