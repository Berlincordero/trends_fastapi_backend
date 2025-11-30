# app/feed/repository.py
from sqlalchemy import select, desc, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.feed.models import Post, PostStar
from app.users.models import User
from app.profile.models import Profile


# -------------------------
# POSTS
# -------------------------
async def create_post(
    db: AsyncSession,
    user_id: int,
    media_path: str,
    caption: str | None,
    caption_meta: dict | None = None,  # 👈 NUEVO
):
    post = Post(
        user_id=user_id,
        media_path=media_path,
        caption=caption,
        caption_meta=caption_meta,  # 👈 se guarda meta (texto + estilo + fuente)
    )
    db.add(post)
    await db.flush()
    await db.refresh(post)
    return post


async def list_posts(
    db: AsyncSession,
    limit: int = 10,
    offset: int = 0,
):
    q = (
        select(Post)
        .order_by(desc(Post.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(q)
    return list(res.scalars())


async def list_posts_by_user(
    db: AsyncSession,
    user_id: int,
    limit: int = 30,
    offset: int = 0,
):
    """
    Devuelve publicaciones de un usuario en orden descendente por fecha.
    """
    q = (
        select(Post)
        .where(Post.user_id == user_id)
        .order_by(desc(Post.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(q)
    return list(res.scalars())


async def get_post(db: AsyncSession, post_id: int):
    res = await db.execute(select(Post).where(Post.id == post_id))
    return res.scalar_one_or_none()


async def increment_views(db: AsyncSession, post_id: int) -> int:
    res = await db.execute(select(Post).where(Post.id == post_id))
    post = res.scalar_one_or_none()
    if not post:
        return 0
    post.views_count += 1
    await db.flush()
    return post.views_count


# -------------------------
# ⭐ STARS SOBRE POSTS
# -------------------------
async def count_post_stars(db: AsyncSession, post_id: int) -> int:
    q = select(func.count()).select_from(PostStar).where(PostStar.post_id == post_id)
    res = await db.execute(q)
    return int(res.scalar_one() or 0)


async def viewer_starred_post(
    db: AsyncSession,
    post_id: int,
    viewer_id: int,
) -> bool:
    q = select(PostStar).where(
        PostStar.post_id == post_id,
        PostStar.user_id == viewer_id,
    )
    res = await db.execute(q)
    return res.scalar_one_or_none() is not None


async def toggle_post_star(
    db: AsyncSession,
    post_id: int,
    user_id: int,
) -> tuple[bool, int]:
    """
    Activa/desactiva la estrella de un usuario sobre un post.
    Devuelve (starred, total_stars)
    """
    q = select(PostStar).where(
        PostStar.post_id == post_id,
        PostStar.user_id == user_id,
    )
    res = await db.execute(q)
    existing = res.scalar_one_or_none()

    if existing:
        # quitar
        await db.execute(delete(PostStar).where(PostStar.id == existing.id))
        await db.flush()
        total = await count_post_stars(db, post_id)
        return False, total

    # crear
    star = PostStar(post_id=post_id, user_id=user_id)
    db.add(star)
    await db.flush()
    total = await count_post_stars(db, post_id)
    return True, total


async def list_post_stars(
    db: AsyncSession,
    post_id: int,
    limit: int = 100,
    offset: int = 0,
):
    """
    Devuelve los usuarios (con avatar si existe) que reaccionaron con ⭐ a ese post.
    """
    q = (
        select(User, Profile)
        .join(PostStar, PostStar.user_id == User.id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .where(PostStar.post_id == post_id)
        .order_by(PostStar.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(q)
    rows = res.all()

    items: list[dict] = []
    for user, prof in rows:
        items.append(
            {
                "id": user.id,
                "username": user.username,
                "avatar": prof.avatar if prof else None,
            }
        )
    return items
