from pydantic import BaseModel


class TTSVoice(BaseModel):
    id: str  # Unique id of the speaker
    gender: str  # Gender of the speaker
    description: str  # Speaker voice description
    locale: str | None = None  # Locale of the speaker (e.g., en-US, fr-FR)
