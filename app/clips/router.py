
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Header,
    UploadFile,
    File,
    Query,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.json import UTF8JSONResponse
from app.core.security import decode_access_token
from app.db.session import get_session
from app.media.storage import save_clip_media
from app.clips.repository import create_clip, get_latest_clip_by_user
from app.clips.schemas import ClipOut

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

    return ClipOut(
        id=clip.id,
        media=_to_media_url(clip.media_path),
        created_at=clip.created_at,
    )


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
    )
