# app/feed/router.py
from typing import List
from os.path import splitext

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Header,
    Query,
    UploadFile,
    File,
    Form,
    Response,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.json import UTF8JSONResponse  # JSON siempre UTF-8
from app.db.session import get_session
from app.core.security import decode_access_token
from app.media.storage import save_post_media, delete_post_media, VIDEO_EXTS
from app.media.jobs import spawn_hls_build
from app.media.hls import delete_hls

from app.feed.repository import (
    create_post,
    list_posts,
    list_posts_by_user,
    get_post,
    increment_views,
    toggle_post_star,
    list_post_stars,
)
from app.feed.schemas import PostOut, StarUserOut, PostUpdate
from app.feed.service import (
    hydrate_post_out,
    normalize_caption,
    process_caption_inputs,  # 👈 IMPORTANTE: usa la lógica de estilos/fuentes
)

router = APIRouter(
    prefix="/api/feed",
    tags=["feed"],
    default_response_class=UTF8JSONResponse,
)


def _extract_token(token: str | None, authorization: str | None) -> str:
    """
    NO TOCAR: lógica de extracción de token, usada en todos los endpoints.
    """
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="missing token")
    return token


# ============ Utilidad de DEBUG =============
@router.get("/_echo/", response_model=dict)
async def echo_debug(q: str = Query("Hola día 🌴🏖️ — Test 🇨🇷❤️‍🔥")):
    """
    Endpoint para verificar transporte/normalización de Unicode desde el backend.
    Devuelve el texto normalizado en NFC.
    """
    return {"echo": normalize_caption(q)}
# ===========================================


@router.post("/", response_model=PostOut)
async def publish(
    caption: str | None = Form(None),
    caption_b64: str | None = Form(None),  # 👈 viene del front, base64 UTF-8
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Publicar nueva pieza de feed (imagen o video).
    Aquí es donde tomamos el caption (texto o JSON) y generamos caption_meta.
    """
    # 🔐 NO TOCAR: validación de token
    tok = _extract_token(token, authorization)
    try:
        user_id = int(decode_access_token(tok))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    # Guarda el archivo (imagen o video)
    rel_path = save_post_media(file)

    # 🧠 Procesar caption (plain / JSON / base64) → (caption_str, caption_meta)
    # process_caption_inputs:
    #  - prioriza caption_b64 (más seguro)
    #  - soporta JSON tipo {kind:"text", text:"...", style:{...}}
    #  - limpia style y valida fontFamily contra ALLOWED_FONT_FAMILIES
    caption_str, caption_meta = process_caption_inputs(caption, caption_b64)

    # Crea el post guardando:
    #  - caption: string (JSON o texto plano, normalizado)
    #  - caption_meta: dict estructurado (texto + estilo + fuente)
    post = await create_post(
        db,
        user_id=user_id,
        media_path=rel_path,
        caption=caption_str,
        caption_meta=caption_meta,
    )
    await db.commit()

    # 💡 SOLO generar HLS si es un VIDEO (según extensión de rel_path)
    try:
        ext = splitext(rel_path)[1].lower()
        if ext in VIDEO_EXTS:
            spawn_hls_build(post.id, rel_path)
    except Exception:
        # En desarrollo puedes loguear el error si quieres
        pass

    return await hydrate_post_out(db, post, viewer_id=user_id)


@router.get("/", response_model=List[PostOut])
async def feed_list(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    tok = _extract_token(token, authorization)
    try:
        viewer_id = int(decode_access_token(tok))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    posts = await list_posts(db, limit=limit, offset=offset)
    return [await hydrate_post_out(db, p, viewer_id=viewer_id) for p in posts]


@router.get("/me/", response_model=List[PostOut])
async def my_posts(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    tok = _extract_token(token, authorization)
    try:
        viewer_id = int(decode_access_token(tok))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    posts = await list_posts_by_user(db, viewer_id, limit=limit, offset=offset)
    return [await hydrate_post_out(db, p, viewer_id=viewer_id) for p in posts]


@router.get("/user/{user_id}/", response_model=List[PostOut])
async def user_posts(
    user_id: int,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    tok = _extract_token(token, authorization)
    try:
        viewer_id = int(decode_access_token(tok))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    posts = await list_posts_by_user(db, user_id, limit=limit, offset=offset)
    return [await hydrate_post_out(db, p, viewer_id=viewer_id) for p in posts]


@router.patch("/{post_id}/", response_model=PostOut)
async def edit_post(
    post_id: int,
    body: PostUpdate,
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Edita una publicación (por ahora solo el caption).
    Solo el autor puede editar.

    ⚠️ Importante: también recalculamos caption_meta a partir del nuevo caption,
    para que no se pierdan estilos/fuente si el caption viene en JSON.
    """
    tok = _extract_token(token, authorization)
    try:
        user_id = int(decode_access_token(tok))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    post = await get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")

    if post.user_id != user_id:
        raise HTTPException(status_code=403, detail="not your post")

    # Reprocesar el caption (en edición solo llega body.caption, sin base64)
    # Esto soporta:
    #  - texto plano
    #  - JSON {kind:"text", text:"...", style:{...}} para posts de texto
    new_caption, new_meta = process_caption_inputs(body.caption, None)

    post.caption = new_caption
    post.caption_meta = new_meta
    await db.flush()
    await db.commit()

    return await hydrate_post_out(db, post, viewer_id=user_id)


@router.post("/{post_id}/view/")
async def add_view(
    post_id: int,
    db: AsyncSession = Depends(get_session),
):
    post = await get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")

    new_count = await increment_views(db, post_id)
    await db.commit()
    return {"views_count": new_count}


@router.post("/{post_id}/star/")
async def toggle_star_on_post(
    post_id: int,
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    tok = _extract_token(token, authorization)
    try:
        user_id = int(decode_access_token(tok))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    post = await get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")

    starred, count = await toggle_post_star(db, post_id, user_id)
    await db.commit()
    return {"post_id": post_id, "stars_count": count, "starred": starred}


@router.get("/{post_id}/stars/", response_model=List[StarUserOut])
async def list_stars_on_post(
    post_id: int,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    _ = _extract_token(token, authorization)

    post = await get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")

    users = await list_post_stars(db, post_id, limit=limit, offset=offset)
    return users


@router.delete("/{post_id}/", status_code=204)
async def delete_post_endpoint(
    post_id: int,
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Elimina una publicación.
    Solo el autor puede borrar.
    También intenta borrar el archivo físico y la carpeta HLS.
    """
    tok = _extract_token(token, authorization)
    try:
        user_id = int(decode_access_token(tok))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    post = await get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")

    if post.user_id != user_id:
        raise HTTPException(status_code=403, detail="not your post")

    media_rel = post.media_path

    # Borramos la fila en DB
    await db.delete(post)
    await db.flush()
    await db.commit()

    # 🧹 best-effort: borrar archivo y carpeta HLS (si existen)
    try:
        if media_rel:
            delete_post_media(media_rel)
        delete_hls(post_id)
    except Exception:
        # En dev podrías loguear el error si quieres
        pass

    return Response(status_code=204)
