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

    # ⭐ opcional: si quieres que el feed devuelva ya contadores
    stars_count: int = 0
    starred: bool = False

    class Config:
        from_attributes = True


class ClipMusicIn(BaseModel):
    # id de la canción (string) o null para limpiar
    track_id: str | None = None


class ClipMusicOut(BaseModel):
    clip_id: int
    track_id: str | None = None


# --------- VIEWERS (quién vio las historias) ---------


class ClipViewerUserOut(BaseModel):
    id: int
    username: str
    avatar: str | None = None


class ClipViewersOut(BaseModel):
    total: int
    viewers: list[ClipViewerUserOut]


class ClipViewTrackOut(BaseModel):
    clip_id: int
    views_count: int


# --------- STARS (quién dio estrella al clip) ---------


class ClipStarToggleOut(BaseModel):
    clip_id: int
    stars_count: int
    starred: bool


class ClipStarUserOut(BaseModel):
    id: int
    username: str
    avatar: str | None = None
