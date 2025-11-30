#app/comments/router.py
from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Header,
    Query,
    UploadFile,
    File,
)
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_session
from app.core.security import decode_access_token
from app.comments.schemas import (
    CommentOut,
    CommentCreate,
    CommentReply,
    CommentStarOut,
    CommentPostStats,
)
from app.comments import repository as repo
from app.media.storage import save_comment_media

router = APIRouter(prefix="/api/comments", tags=["comments"])


def _extract_token(token: str | None, authorization: str | None) -> str:
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="missing token")
    return token


async def _get_user_id(token: str) -> int:
    try:
        return int(decode_access_token(token))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")


def _abs_media(rel: str | None) -> str | None:
    if not rel:
        return None
    if rel.startswith("/media/"):
        return rel
    if rel.startswith("/"):
        return f"/media{rel}"
    return f"/media/{rel}"


@router.get("/post/{post_id}/", response_model=List[CommentOut])
async def comments_for_post(
    post_id: int,
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    tok = _extract_token(token, authorization)
    user_id = await _get_user_id(tok)

    # 1) traemos todos los comentarios
    comments = await repo.list_post_comments(db, post_id)
    ids = [c.id for c in comments]

    # 2) cuáles de esos el usuario ya los estrelló
    starred_set = await repo.list_user_starred_comment_ids(db, user_id, ids)

    hydrated: list[dict] = []
    for c in comments:
        author = await repo.hydrate_author(db, c)
        hydrated.append(
            {
                "id": c.id,
                "post_id": c.post_id,
                "parent_id": c.parent_id,
                "text": c.text,
                "media": _abs_media(c.media),
                "gift": c.gift,
                "style": c.style or {},
                "created_at": c.created_at,
                "author": author,
                "stars_count": c.stars_count or 0,
                "starred": c.id in starred_set,
            }
        )

    tree = repo.build_tree(hydrated)
    return tree


@router.post("/", response_model=CommentOut)
async def create_comment_endpoint(
    payload: CommentCreate,
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    tok = _extract_token(token, authorization)
    user_id = await _get_user_id(tok)

    c = await repo.create_comment(
        db,
        user_id=user_id,
        post_id=payload.post_id,
        parent_id=payload.parent_id,
        text=payload.text,
        gift=payload.gift,
        style=payload.style,
    )
    await db.commit()

    author = await repo.hydrate_author(db, c)
    return {
        "id": c.id,
        "post_id": c.post_id,
        "parent_id": c.parent_id,
        "text": c.text,
        "media": _abs_media(c.media),
        "gift": c.gift,
        "style": c.style or {},
        "created_at": c.created_at,
        "author": author,
        "stars_count": c.stars_count or 0,
        "starred": False,
        "replies": [],
    }


@router.post("/{comment_id}/reply/", response_model=CommentOut)
async def reply_comment_endpoint(
    comment_id: int,
    payload: CommentReply,
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    tok = _extract_token(token, authorization)
    user_id = await _get_user_id(tok)

    parent = await repo.get_comment(db, comment_id)
    if not parent:
        raise HTTPException(status_code=404, detail="comment not found")

    c = await repo.create_comment(
        db,
        user_id=user_id,
        post_id=parent.post_id,
        parent_id=parent.id,
        text=payload.text,
        gift=payload.gift,
        style=payload.style,
    )
    await db.commit()

    author = await repo.hydrate_author(db, c)
    return {
        "id": c.id,
        "post_id": c.post_id,
        "parent_id": c.parent_id,
        "text": c.text,
        "media": _abs_media(c.media),
        "gift": c.gift,
        "style": c.style or {},
        "created_at": c.created_at,
        "author": author,
        "stars_count": c.stars_count or 0,
        "starred": False,
        "replies": [],
    }


@router.post("/{comment_id}/media/", response_model=CommentOut)
async def comment_upload_media(
    comment_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    tok = _extract_token(token, authorization)
    user_id = await _get_user_id(tok)

    c = await repo.get_comment(db, comment_id)
    if not c:
        raise HTTPException(status_code=404, detail="comment not found")

    if c.user_id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")

    rel = save_comment_media(file)
    c.media = rel
    await db.flush()
    await db.commit()

    author = await repo.hydrate_author(db, c)
    return {
        "id": c.id,
        "post_id": c.post_id,
        "parent_id": c.parent_id,
        "text": c.text,
        "media": _abs_media(c.media),
        "gift": c.gift,
        "style": c.style or {},
        "created_at": c.created_at,
        "author": author,
        "stars_count": c.stars_count or 0,
        "starred": True if c.user_id == user_id else False,
        "replies": [],
    }


# ⭐ toggle star
@router.post("/{comment_id}/star/", response_model=CommentStarOut)
async def toggle_comment_star(
    comment_id: int,
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    tok = _extract_token(token, authorization)
    user_id = await _get_user_id(tok)

    c = await repo.get_comment(db, comment_id)
    if not c:
        raise HTTPException(status_code=404, detail="comment not found")

    starred, new_count = await repo.toggle_star_on_comment(
        db, user_id=user_id, comment=c
    )
    await db.commit()

    return CommentStarOut(
        id=c.id,
        stars_count=new_count,
        starred=starred,
    )


# 📊 stats para el feed
@router.get("/post/{post_id}/stats/", response_model=CommentPostStats)
async def comment_stats_for_post(
    post_id: int,
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    _ = _extract_token(token, authorization)
    stats = await repo.get_post_comment_stats(db, post_id)
    return CommentPostStats(**stats)
