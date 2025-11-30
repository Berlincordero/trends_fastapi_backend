from pydantic import BaseModel
from datetime import datetime


class ClipOut(BaseModel):
    id: int
    media: str
    created_at: datetime

    class Config:
        from_attributes = True
