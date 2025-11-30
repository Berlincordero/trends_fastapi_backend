# app/feed/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Any


class AuthorMini(BaseModel):
    id: int
    username: str
    avatar: str | None = None  # ruta relativa


class StarUserOut(BaseModel):
    id: int
    username: str
    avatar: str | None = None


class PostOut(BaseModel):
    id: int
    media: str              # URL absoluta /media/...
    caption: str | None
    created_at: datetime
    views_count: int
    author: AuthorMini

    # ⭐ NUEVO
    stars_count: int
    starred: bool

    # 👇 NUEVO: meta estructurada del caption (texto + estilo + fuente)
    caption_meta: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class PostUpdate(BaseModel):
    """
    Payload para edición de post (por ahora solo caption).
    """
    caption: str | None = None
