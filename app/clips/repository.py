# app/clips/repository.py
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.clips.models import Clip, ClipView, ClipStar
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
    """Devuelve el último clip creado por el usuario."""
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


# ------------------ VIEWERS: quién vio un clip ------------------


async def track_clip_view(
    db: AsyncSession,
    clip_id: int,
    user_id: int,
) -> int:
    """
    Registra que el usuario vio el clip (idempotente).
    Devuelve el total de viewers únicos del clip.
    """
    # ¿ya existe?
    q = select(ClipView).where(
        ClipView.clip_id == clip_id,
        ClipView.user_id == user_id,
    )
    res = await db.execute(q)
    existing = res.scalar_one_or_none()

    if existing is None:
        view = ClipView(clip_id=clip_id, user_id=user_id)
        db.add(view)
        await db.flush()

    # total viewers
    q_count = select(func.count(ClipView.id)).where(ClipView.clip_id == clip_id)
    res_count = await db.execute(q_count)
    total = res_count.scalar() or 0
    return int(total)


async def list_clip_viewers(
    db: AsyncSession,
    clip_id: int,
    limit: int = 50,
    offset: int = 0,
):
    """
    Devuelve filas (ClipView, User, Profile | None) ordenadas
    del más reciente al más antiguo.
    """
    q = (
        select(ClipView, User, Profile)
        .join(User, User.id == ClipView.user_id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .where(ClipView.clip_id == clip_id)
        .order_by(desc(ClipView.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(q)
    return res.all()


async def count_clip_viewers(
    db: AsyncSession,
    clip_id: int,
) -> int:
    q = select(func.count(ClipView.id)).where(ClipView.clip_id == clip_id)
    res = await db.execute(q)
    return int(res.scalar() or 0)


# ------------------ STARS: quién dio estrella a un clip ------------------


async def toggle_clip_star(
    db: AsyncSession,
    clip_id: int,
    user_id: int,
) -> tuple[int, bool]:
    """
    Marca/desmarca la estrella de un clip para un usuario.
    Devuelve (total_estrellas, starred).
    """
    q = select(ClipStar).where(
        ClipStar.clip_id == clip_id,
        ClipStar.user_id == user_id,
    )
    res = await db.execute(q)
    existing = res.scalar_one_or_none()

    if existing:
        # quitar estrella
        await db.delete(existing)
        await db.flush()
        starred = False
    else:
        star = ClipStar(clip_id=clip_id, user_id=user_id)
        db.add(star)
        await db.flush()
        starred = True

    # contar estrellas
    q_count = select(func.count(ClipStar.id)).where(ClipStar.clip_id == clip_id)
    res_count = await db.execute(q_count)
    total = res_count.scalar() or 0
    return int(total), starred


async def list_clip_stars(
    db: AsyncSession,
    clip_id: int,
    limit: int = 100,
    offset: int = 0,
):
    """
    Devuelve filas (ClipStar, User, Profile | None) ordenadas del más reciente.
    """
    q = (
        select(ClipStar, User, Profile)
        .join(User, User.id == ClipStar.user_id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .where(ClipStar.clip_id == clip_id)
        .order_by(desc(ClipStar.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(q)
    return res.all()


async def count_clip_stars(
    db: AsyncSession,
    clip_id: int,
) -> int:
    q = select(func.count(ClipStar.id)).where(ClipStar.clip_id == clip_id)
    res = await db.execute(q)
    return int(res.scalar() or 0)
