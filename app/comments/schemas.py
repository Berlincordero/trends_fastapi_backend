# app/comments/schemas.py
from pydantic import BaseModel
from datetime import datetime


class CommentAuthor(BaseModel):
    id: int
    username: str
    avatar: str | None = None


class CommentBase(BaseModel):
    post_id: int
    parent_id: int | None = None
    text: str | None = None
    gift: str | None = None
    style: dict | None = None


class CommentCreate(CommentBase):
    pass


class CommentReply(BaseModel):
    text: str | None = None
    gift: str | None = None
    style: dict | None = None


class CommentOut(BaseModel):
    id: int
    post_id: int
    parent_id: int | None
    text: str | None
    media: str | None
    gift: str | None
    style: dict | None
    created_at: datetime
    author: CommentAuthor
    # ⭐ nuevo
    stars_count: int = 0
    starred: bool = False
    replies: list["CommentOut"] = []

    class Config:
        from_attributes = True


CommentOut.model_rebuild()


class CommentStarOut(BaseModel):
    id: int               # comment_id
    stars_count: int
    starred: bool


class CommentPostStats(BaseModel):
    comments_count: int
    replies_count: int
    total_count: int
    stars_count: int
