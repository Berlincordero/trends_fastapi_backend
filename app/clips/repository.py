# app/clips/repository.py
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.clips.models import Clip
from app.users.models import User
from app.profile.models import Profile


async def create_clip(
    db: AsyncSession,
    user_id: int,
    media_path: str,
) -> Clip:
    clip = Clip(user_id=user_id, media_path=media_path)
    db.add(clip)
    await db.flush()
    await db.refresh(clip)
    return clip


async def get_clip_by_id(
    db: AsyncSession,
    clip_id: int,
) -> Clip | None:
    q = select(Clip).where(Clip.id == clip_id)
    res = await db.execute(q)
    return res.scalar_one_or_none()


async def get_latest_clip_by_user(
    db: AsyncSession,
    user_id: int,
) -> Clip | None:
    """
    Devuelve el último clip creado por el usuario.
    """
    q = (
        select(Clip)
        .where(Clip.user_id == user_id)
        .order_by(desc(Clip.created_at))
        .limit(1)
    )
    res = await db.execute(q)
    return res.scalar_one_or_none()


async def list_clips_with_authors(
    db: AsyncSession,
    limit: int = 32,
    offset: int = 0,
):
    """
    Lista global de clips (vibes) , más recientes primero.
    Devuelve filas (Clip, User, Profile | None).
    """
    q = (
        select(Clip, User, Profile)
        .join(User, User.id == Clip.user_id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .order_by(desc(Clip.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(q)
    return res.all()


async def list_clips_by_user(
    db: AsyncSession,
    user_id: int,
    limit: int = 32,
    offset: int = 0,
):
    """
    Lista de clips (vibes) de UN usuario, más recientes primero.
    Devuelve filas (Clip, User, Profile | None).
    """
    q = (
        select(Clip, User, Profile)
        .join(User, User.id == Clip.user_id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .where(Clip.user_id == user_id)
        .order_by(desc(Clip.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(q)
    return res.all()
