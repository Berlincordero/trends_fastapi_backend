# app/clips/router.py
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Header,
    UploadFile,
    File,
    Query,
    Response,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.json import UTF8JSONResponse
from app.core.security import decode_access_token
from app.db.session import get_session
from app.media.storage import save_clip_media
from app.clips.repository import (
    create_clip,
    get_latest_clip_by_user,
    list_clips_with_authors,
    list_clips_by_user,
    get_clip_by_id,
)
from app.clips.schemas import ClipOut, ClipMusicIn, ClipMusicOut

router = APIRouter(
    prefix="/api/clips",
    tags=["clips"],
    default_response_class=UTF8JSONResponse,
)


def _extract_token(token: str | None, authorization: str | None) -> str:
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="missing token")
    return token


def _to_media_url(rel: str | None) -> str | None:
    if not rel:
        return None
    return f"/media/{rel}"


@router.post("/", response_model=ClipOut)
async def publish_clip(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Sube un clip de Vibes (imagen o video).
    - Si es video, se normaliza a MP4 y se recorta a máximo 120s.
    - Se guarda bajo /media/clips/...
    """
    tok = _extract_token(token, authorization)
    try:
        user_id = int(decode_access_token(tok))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    rel = save_clip_media(file)
    clip = await create_clip(db, user_id=user_id, media_path=rel)
    await db.commit()

    # en este endpoint no devolvemos el autor completo porque ya lo sabes (eres tú)
    return ClipOut(
        id=clip.id,
        media=_to_media_url(clip.media_path),
        created_at=clip.created_at,
        author=None,
    )


@router.get("/", response_model=list[ClipOut])
async def list_clips(
    db: AsyncSession = Depends(get_session),
    limit: int = Query(32, ge=1, le=100),
    offset: int = Query(0, ge=0),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Devuelve un feed global de clips (vibes) de todos los usuarios.
    Similar a las historias de Instagram.
    """
    tok = _extract_token(token, authorization)
    try:
        # Sólo validamos el token (no filtramos por usuario)
        decode_access_token(tok)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    # AHORA VIENEN (Clip, User, Profile | None)
    rows = await list_clips_with_authors(db, limit=limit, offset=offset)

    out: list[ClipOut] = []
    for clip, user, prof in rows:
        avatar = getattr(prof, "avatar", None) if prof is not None else None

        out.append(
            ClipOut(
                id=clip.id,
                media=_to_media_url(clip.media_path),
                created_at=clip.created_at,
                author={
                    "id": user.id,
                    "username": user.username,
                    "avatar": avatar,
                },
            )
        )
    return out


@router.get("/user/{user_id}/", response_model=list[ClipOut])
async def list_user_clips(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    limit: int = Query(32, ge=1, le=100),
    offset: int = Query(0, ge=0),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Devuelve los clips de un usuario específico (para el carrusel en VibePlayer).
    """
    tok = _extract_token(token, authorization)
    try:
        # Sólo validamos el token (no tiene que ser el dueño)
        decode_access_token(tok)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    rows = await list_clips_by_user(db, user_id=user_id, limit=limit, offset=offset)

    out: list[ClipOut] = []
    for clip, user, prof in rows:
        avatar = getattr(prof, "avatar", None) if prof is not None else None

        out.append(
            ClipOut(
                id=clip.id,
                media=_to_media_url(clip.media_path),
                created_at=clip.created_at,
                author={
                    "id": user.id,
                    "username": user.username,
                    "avatar": avatar,
                },
            )
        )
    return out


@router.get("/me/", response_model=ClipOut | None)
async def my_clip(
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Devuelve el último clip del usuario actual, o null si no tiene.
    """
    tok = _extract_token(token, authorization)
    try:
        user_id = int(decode_access_token(tok))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    clip = await get_latest_clip_by_user(db, user_id)
    if not clip:
        return None

    return ClipOut(
        id=clip.id,
        media=_to_media_url(clip.media_path),
        created_at=clip.created_at,
        author=None,
    )


@router.delete("/{clip_id}/", status_code=204)
async def delete_clip(
    clip_id: int,
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Elimina un clip. Solo el autor puede hacerlo.
    """
    tok = _extract_token(token, authorization)
    try:
        user_id = int(decode_access_token(tok))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    clip = await get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="clip not found")

    if clip.user_id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")

    await db.delete(clip)
    await db.commit()
    return Response(status_code=204)


# ----------------- Música asociada a un clip -----------------


@router.get("/{clip_id}/music/", response_model=ClipMusicOut)
async def get_clip_music(
    clip_id: int,
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Devuelve el track_id asociado a un clip, o null si no tiene.
    Cualquier usuario autenticado puede consultar esto (es público).
    """
    tok = _extract_token(token, authorization)
    try:
        decode_access_token(tok)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    clip = await get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="clip not found")

    return ClipMusicOut(clip_id=clip.id, track_id=clip.music_track_id)


@router.post("/{clip_id}/music/", response_model=ClipMusicOut)
async def set_clip_music(
    clip_id: int,
    payload: ClipMusicIn,
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Asocia (o limpia) un track_id a un clip.
    Solo el dueño del clip puede modificarlo.
    """
    tok = _extract_token(token, authorization)
    try:
        user_id = int(decode_access_token(tok))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    clip = await get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="clip not found")

    if clip.user_id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")

    clip.music_track_id = payload.track_id
    await db.flush()
    await db.refresh(clip)
    await db.commit()

    return ClipMusicOut(clip_id=clip.id, track_id=clip.music_track_id)
