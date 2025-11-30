# app/comments/service.py
from __future__ import annotations

from typing import List, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.comments.models import Comment, CommentStar
from app.users.models import User
from app.profile.models import Profile


def to_media_url(rel: str | None) -> str | None:
    if not rel:
        return None
    if rel.startswith("/media/"):
        return rel
    if rel.startswith("/"):
        return f"/media{rel}"
    return f"/media/{rel}"


async def hydrate_author(db: AsyncSession, user_id: int) -> dict:
    ures = await db.execute(select(User).where(User.id == user_id))
    user = ures.scalar_one()
    pres = await db.execute(select(Profile).where(Profile.user_id == user_id))
    prof = pres.scalar_one_or_none()
    return {
        "id": user.id,
        "username": user.username,
        "avatar": prof.avatar if prof else None,
    }


async def build_comment_tree(
    db: AsyncSession,
    comments: List[Comment],
    current_user_id: int | None = None,
) -> List[Dict]:
    author_cache: dict[int, dict] = {}
    star_set: set[int] = set()

    if current_user_id:
        ids = [c.id for c in comments]
        if ids:
            res = await db.execute(
                select(CommentStar.comment_id).where(
                    CommentStar.user_id == current_user_id,
                    CommentStar.comment_id.in_(ids),
                )
            )
            star_set = {row[0] for row in res.all()}

    async def get_author(uid: int) -> dict:
        if uid in author_cache:
            return author_cache[uid]
        data = await hydrate_author(db, uid)
        author_cache[uid] = data
        return data

    by_id: dict[int, dict] = {}
    roots: list[dict] = []

    for c in comments:
        by_id[c.id] = {
            "id": c.id,
            "post_id": c.post_id,
            "parent_id": c.parent_id,
            "text": c.text,
            "media": to_media_url(c.media),
            "gift": c.gift,
            "style": c.style or {},
            "created_at": c.created_at,
            "author": None,
            "stars_count": c.stars_count or 0,
            "starred": c.id in star_set,
            "replies": [],
        }

    for c in comments:
        data = by_id[c.id]
        data["author"] = await get_author(c.user_id)

    for c in comments:
        data = by_id[c.id]
        if c.parent_id:
            parent = by_id.get(c.parent_id)
            if parent:
                parent["replies"].append(data)
            else:
                roots.append(data)
        else:
            roots.append(data)

    return roots
