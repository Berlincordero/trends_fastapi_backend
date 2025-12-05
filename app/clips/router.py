# app/clips/router.py
from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
    Query,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from jose import JWTError

from app.db.session import get_session
from app.core.security import decode_access_token
from app.users.models import User
from app.profile.models import Profile
from app.media.storage import save_clip_media, delete_post_media
from app.clips import repository as repo
from app.clips.models import Clip, ClipStar
from app.clips.schemas import (
    ClipOut,
    ClipAuthorOut,
    ClipMusicIn,
    ClipMusicOut,
    ClipViewersOut,
    ClipViewTrackOut,
    ClipStarToggleOut,
    ClipStarUserOut,
)
from app.clips.repository import (
    get_clip_by_id,
    get_latest_clip_by_user,
    list_clips_with_authors,
    list_clips_by_user,
    track_clip_view,
    list_clip_viewers,
    count_clip_viewers,
    toggle_clip_star,
    list_clip_stars,
    count_clip_stars,
)

router = APIRouter(prefix="/api/clips", tags=["clips"])


# ======================= AUTH LOCAL =======================

async def get_current_user(
    token: str = Query(..., description="access token"),
    db: AsyncSession = Depends(get_session),
) -> User:
    """
    Versión local del get_current_user:
    - Lee ?token=... del querystring.
    - Decodifica el JWT.
    - Busca el usuario en la BD.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Token requerido")

    try:
        sub = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    try:
        user_id = int(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return user


# ======================= HELPERS =======================

def _author_from(user: User, profile: Profile | None) -> ClipAuthorOut:
    avatar = getattr(profile, "avatar", None) or getattr(user, "avatar", None)
    return ClipAuthorOut(
        id=user.id,
        username=user.username,
        avatar=avatar,
    )


def _clip_media_rel(clip: Clip) -> str:
    # lo que el front espera como `media`
    return f"media/{clip.media_path}"


async def _user_starred_clip(
    db: AsyncSession, clip_id: int, user_id: int
) -> bool:
    q = select(ClipStar).where(
        ClipStar.clip_id == clip_id,
        ClipStar.user_id == user_id,
    )
    res = await db.execute(q)
    return res.scalar_one_or_none() is not None


# ======================= CLIPS CRUD =======================


@router.post("/", response_model=ClipOut)
async def create_clip_view(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    media_rel = save_clip_media(file)
    clip = await repo.create_clip(db, user_id=user.id, media_path=media_rel)
    await db.commit()
    return ClipOut(
        id=clip.id,
        media=_clip_media_rel(clip),
        created_at=clip.created_at,
        author=_author_from(user, getattr(user, "profile", None)),
        stars_count=0,
        starred=False,
    )


@router.get("/", response_model=list[ClipOut])
async def list_clips_view(
    limit: int = 32,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    rows = await list_clips_with_authors(db, limit=limit, offset=offset)

    out: list[ClipOut] = []
    for clip, author, profile in rows:
        total_stars = await count_clip_stars(db, clip.id)
        starred = await _user_starred_clip(db, clip.id, user.id)
        out.append(
            ClipOut(
                id=clip.id,
                media=_clip_media_rel(clip),
                created_at=clip.created_at,
                author=_author_from(author, profile),
                stars_count=total_stars,
                starred=starred,
            )
        )
    return out


@router.get("/me/", response_model=ClipOut | None)
async def my_latest_clip_view(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    clip = await get_latest_clip_by_user(db, user_id=user.id)
    if not clip:
        return None

    total_stars = await count_clip_stars(db, clip.id)
    starred = await _user_starred_clip(db, clip.id, user.id)

    return ClipOut(
        id=clip.id,
        media=_clip_media_rel(clip),
        created_at=clip.created_at,
        author=_author_from(user, getattr(user, "profile", None)),
        stars_count=total_stars,
        starred=starred,
    )


@router.get("/user/{user_id}/", response_model=list[ClipOut])
async def clips_by_user_view(
    user_id: int,
    limit: int = 32,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    rows = await list_clips_by_user(db, user_id=user_id, limit=limit, offset=offset)

    out: list[ClipOut] = []
    for clip, author, profile in rows:
        total_stars = await count_clip_stars(db, clip.id)
        starred = await _user_starred_clip(db, clip.id, current_user.id)

        out.append(
            ClipOut(
                id=clip.id,
                media=_clip_media_rel(clip),
                created_at=clip.created_at,
                author=_author_from(author, profile),
                stars_count=total_stars,
                starred=starred,
            )
        )
    return out


@router.delete("/{clip_id}/")
async def delete_clip_view(
    clip_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    clip = await get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip no encontrado")

    if clip.user_id != user.id:
        raise HTTPException(status_code=403, detail="No puedes eliminar este clip")

    media_rel = clip.media_path
    await db.delete(clip)
    await db.commit()

    # borrar archivo físico (opcional)
    try:
        delete_post_media(media_rel)
    except Exception:
        pass

    return {"ok": True}


# ======================= MÚSICA =======================


@router.get("/{clip_id}/music/", response_model=ClipMusicOut)
async def get_clip_music_view(
    clip_id: int,
    db: AsyncSession = Depends(get_session),
):
    clip = await get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip no encontrado")

    return ClipMusicOut(clip_id=clip.id, track_id=clip.music_track_id)


@router.post("/{clip_id}/music/", response_model=ClipMusicOut)
async def set_clip_music_view(
    clip_id: int,
    payload: ClipMusicIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    clip = await get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip no encontrado")

    if clip.user_id != user.id:
        raise HTTPException(status_code=403, detail="No puedes editar este clip")

    clip.music_track_id = payload.track_id
    db.add(clip)
    await db.commit()
    await db.refresh(clip)

    return ClipMusicOut(clip_id=clip.id, track_id=clip.music_track_id)


# ======================= VISTAS =======================


@router.post("/{clip_id}/view/", response_model=ClipViewTrackOut)
async def track_clip_view_view(
    clip_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    clip = await get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip no encontrado")

    total = await track_clip_view(db, clip_id=clip_id, user_id=user.id)
    await db.commit()

    return ClipViewTrackOut(clip_id=clip_id, views_count=total)


@router.get("/{clip_id}/viewers/", response_model=ClipViewersOut)
async def list_clip_viewers_view(
    clip_id: int,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    clip = await get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip no encontrado")

    if clip.user_id != user.id:
        # Solo el autor puede ver quién vio
        raise HTTPException(status_code=403, detail="No autorizado")

    rows = await list_clip_viewers(db, clip_id, limit=limit, offset=offset)
    total = await count_clip_viewers(db, clip_id)

    viewers = []
    for view, u, profile in rows:
        avatar = getattr(profile, "avatar", None) or getattr(u, "avatar", None)
        viewers.append(
            {
                "id": u.id,
                "username": u.username,
                "avatar": avatar,
            }
        )

    return ClipViewersOut(
        total=total,
        viewers=viewers,
    )


# ======================= ESTRELLAS =======================


@router.post("/{clip_id}/star/", response_model=ClipStarToggleOut)
async def toggle_clip_star_view(
    clip_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    clip = await get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip no encontrado")

    total, starred = await toggle_clip_star(db, clip_id=clip_id, user_id=user.id)
    await db.commit()

    return ClipStarToggleOut(
        clip_id=clip_id,
        stars_count=total,
        starred=starred,
    )


@router.get("/{clip_id}/stars/", response_model=list[ClipStarUserOut])
async def list_clip_stars_view(
    clip_id: int,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
):
    clip = await get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip no encontrado")

    rows = await list_clip_stars(db, clip_id, limit=limit, offset=offset)

    out: list[ClipStarUserOut] = []
    for star, u, profile in rows:
        avatar = getattr(profile, "avatar", None) or getattr(u, "avatar", None)
        out.append(
            ClipStarUserOut(
                id=u.id,
                username=u.username,
                avatar=avatar,
            )
        )
    return out
