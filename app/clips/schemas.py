# app/clips/schemas.py
from pydantic import BaseModel
from datetime import datetime


class ClipAuthorOut(BaseModel):
    id: int
    username: str
    avatar: str | None = None

    class Config:
        from_attributes = True


class ClipOut(BaseModel):
    id: int
    media: str
    created_at: datetime
    author: ClipAuthorOut | None = None

    class Config:
        from_attributes = True


class ClipMusicIn(BaseModel):
    # id de la canción (string) o null para limpiar
    track_id: str | None = None


class ClipMusicOut(BaseModel):
    clip_id: int
    track_id: str | None = None
