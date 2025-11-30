from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.clips.models import Clip


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
