# app/comments/repository.py
from __future__ import annotations

from typing import List, Sequence, Set
from sqlalchemy import select, func, delete, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.comments.models import Comment, CommentStar
from app.users.models import User
from app.profile.models import Profile


async def create_comment(
    db: AsyncSession,
    *,
    user_id: int,
    post_id: int,
    parent_id: int | None = None,
    text: str | None = None,
    media: str | None = None,
    gift: str | None = None,
    style: dict | None = None,
) -> Comment:
    c = Comment(
        user_id=user_id,
        post_id=post_id,
        parent_id=parent_id,
        text=text,
        media=media,
        gift=gift,
        style=style,
    )
    db.add(c)
    await db.flush()
    await db.refresh(c)
    return c


async def get_comment(db: AsyncSession, comment_id: int) -> Comment | None:
    res = await db.execute(select(Comment).where(Comment.id == comment_id))
    return res.scalar_one_or_none()


async def list_post_comments(db: AsyncSession, post_id: int) -> List[Comment]:
    # traemos TODOS los comentarios de ese post, ordenados por fecha (y por id para desempatar)
    res = await db.execute(
        select(Comment)
        .where(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
    )
    return list(res.scalars())


async def hydrate_author(db: AsyncSession, comment: Comment) -> dict:
    ures = await db.execute(select(User).where(User.id == comment.user_id))
    user = ures.scalar_one()

    pres = await db.execute(select(Profile).where(Profile.user_id == user.id))
    prof = pres.scalar_one_or_none()

    return {
        "id": user.id,
        "username": user.username,
        "avatar": prof.avatar if prof else None,
    }


def build_tree(raw: list[dict]) -> list[dict]:
    by_id = {c["id"]: c for c in raw}

    for c in raw:
        c["replies"] = []

    roots: list[dict] = []

    for c in raw:
        pid = c["parent_id"]
        if pid and pid in by_id:
            by_id[pid]["replies"].append(c)
        else:
            roots.append(c)

    return roots


# -------------------------
# ⭐ estrellas de comentarios
# -------------------------


async def list_user_starred_comment_ids(
    db: AsyncSession,
    user_id: int,
    comment_ids: list[int],
) -> Set[int]:
    if not comment_ids:
        return set()
    res = await db.execute(
        select(CommentStar.comment_id).where(
            CommentStar.user_id == user_id,
            CommentStar.comment_id.in_(comment_ids),
        )
    )
    return {row[0] for row in res.all()}


async def toggle_star_on_comment(
    db: AsyncSession,
    *,
    user_id: int,
    comment: Comment,
) -> tuple[bool, int]:
    """
    Devuelve (starred, new_count)
    """
    # ¿ya existe?
    res = await db.execute(
        select(CommentStar).where(
            CommentStar.user_id == user_id,
            CommentStar.comment_id == comment.id,
        )
    )
    existing = res.scalar_one_or_none()

    if existing:
        # quitar
        await db.execute(
            delete(CommentStar).where(CommentStar.id == existing.id)
        )
        comment.stars_count = max(0, (comment.stars_count or 0) - 1)
        await db.flush()
        return False, comment.stars_count

    # crear
    star = CommentStar(user_id=user_id, comment_id=comment.id)
    db.add(star)
    comment.stars_count = (comment.stars_count or 0) + 1
    await db.flush()
    return True, comment.stars_count


# -------------------------
# 📊 stats para FeedVideoCard
# -------------------------


async def get_post_comment_stats(
    db: AsyncSession,
    post_id: int,
) -> dict:
    """
    Devuelve:
    - comments_count: solo raíz
    - replies_count: las que tienen parent_id
    - total_count: todas
    - stars_count: suma de stars_count de los comentarios de ese post
    IMPORTANTE: usamos sqlalchemy.case (NO func.case) porque func.case
    en SQLAlchemy 2.x no acepta else_ → eso era lo que te tiraba 500.
    """

    roots_case = case(
        (Comment.parent_id.is_(None), 1),
        else_=0,
    )
    replies_case = case(
        (Comment.parent_id.is_not(None), 1),
        else_=0,
    )

    res = await db.execute(
        select(
            func.count(Comment.id).label("total"),
            func.sum(roots_case).label("roots"),
            func.sum(replies_case).label("replies"),
            func.coalesce(func.sum(Comment.stars_count), 0).label("stars"),
        ).where(Comment.post_id == post_id)
    )
    row = res.one()

    total = int(row.total or 0)
    roots = int(row.roots or 0)
    replies = int(row.replies or 0)
    stars = int(row.stars or 0)

    return {
        "comments_count": roots,
        "replies_count": replies,
        "total_count": total,
        "stars_count": stars,
    }
