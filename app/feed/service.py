# app/feed/service.py
import os
import json
import base64
import unicodedata
from typing import Any, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.feed.models import Post, PostStar
from app.users.models import User
from app.profile.models import Profile
from app.media.hls import hls_abs_master


def normalize_caption(text: str | None) -> str | None:
    """
    Normaliza a NFC para evitar pérdida de diacríticos/ZWJ en algunos
    renderers Android cuando mezclan tipografías y pesos.
    No toca el contenido, solo la forma de codificación Unicode.
    """
    if text is None:
        return None
    try:
        # NFC conserva emojis y acentos como un solo grapheme
        return unicodedata.normalize("NFC", text)
    except Exception:
        return text


# Fuentes permitidas (las mismas keys que usas en el front)
ALLOWED_FONT_FAMILIES: set[str] = {
    "System",
    "Poppins_400Regular",
    "Montserrat_500Medium",
    "Inter_500Medium",
    "Roboto_400Regular",
    "OpenSans_400Regular",
    "Lato_400Regular",
    "Nunito_600SemiBold",
    "Raleway_500Medium",
    "PlayfairDisplay_500Medium",
    "Merriweather_400Regular",
    "DMSans_500Medium",
    "Manrope_500Medium",
    "Rubik_500Medium",
    "BebasNeue_400Regular",
}


def _sanitize_style(style: Any) -> dict | None:
    """
    Limpia y valida el objeto style que viene del front.
    Solo deja las propiedades esperadas y valida fontFamily.
    """
    if not isinstance(style, dict):
        return None

    out: dict[str, Any] = {}

    for key in ("color", "align", "fontSize", "shadowColor", "bubbleColor", "fontFamily"):
        if key not in style:
            continue
        value = style[key]
        if key == "fontFamily":
            if isinstance(value, str) and value in ALLOWED_FONT_FAMILIES:
                out[key] = value
            # si viene una fuente rara, la ignoramos
            continue
        out[key] = value

    return out or None


def _parse_caption_payload(raw: str | None) -> Tuple[str | None, dict | None]:
    """
    Interpreta el caption enviado por el front.

    - Si es JSON del tipo:
        {"kind":"text","text":"...","style":{...}}
      → extrae text + style, normaliza el texto y devuelve:
        (caption_str_json, caption_meta_dict)

    - Si es texto plano → normaliza y devuelve (texto_normalizado, None)
    """
    if raw is None:
        return None, None

    txt = raw.strip()
    if not txt:
        return None, None

    # ¿es JSON de texto?
    try:
        obj = json.loads(txt)
        if isinstance(obj, dict) and obj.get("kind") == "text" and isinstance(obj.get("text"), str):
            text_norm = normalize_caption(obj.get("text"))
            style_clean = _sanitize_style(obj.get("style"))
            meta = {
                "kind": "text",
                "text": text_norm,
                "style": style_clean,
            }
            # caption como string JSON (para el front actual)
            caption_str = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
            return caption_str, meta
    except Exception:
        # no era JSON → tratamos como texto plano
        pass

    # texto plano
    return normalize_caption(txt), None


def process_caption_inputs(
    caption: str | None,
    caption_b64: str | None,
) -> Tuple[str | None, dict | None]:
    """
    Decide cuál es la fuente "real" del caption (plain o base64)
    y devuelve (caption_str, caption_meta).

    El front te está mandando:
      - caption: string (igual al JSON/texto)
      - caption_b64: el mismo contenido pero en base64 UTF-8

    Aquí priorizamos caption_b64 (más seguro) y luego caption.
    """
    raw: str | None = None

    if caption_b64:
        try:
            raw = base64.b64decode(caption_b64).decode("utf-8")
        except Exception:
            raw = None

    if raw is None:
        raw = caption

    return _parse_caption_payload(raw)


def to_media_url(rel: str | None) -> str | None:
    """Convierte una ruta relativa en /media/... para el front."""
    if not rel:
        return None
    return f"/media/{rel}"


def _maybe_hls_url(post_id: int) -> str | None:
    """
    Si ya existe master.m3u8 para este post → /hls/<id>/master.m3u8.
    Si no, devolvemos None y se usará el MP4 normal.
    """
    master_abs = hls_abs_master(post_id)
    if os.path.exists(master_abs):
        return f"/hls/{post_id}/master.m3u8"
    return None


async def _count_stars(db: AsyncSession, post_id: int) -> int:
    res = await db.execute(
        select(func.count()).select_from(PostStar).where(PostStar.post_id == post_id)
    )
    return int(res.scalar_one() or 0)


async def _viewer_starred(
    db: AsyncSession, post_id: int, viewer_id: int | None
) -> bool:
    if not viewer_id:
        return False
    res = await db.execute(
        select(PostStar).where(
            PostStar.post_id == post_id,
            PostStar.user_id == viewer_id,
        )
    )
    return res.scalar_one_or_none() is not None


async def hydrate_post_out(
    db: AsyncSession, post: Post, *, viewer_id: int | None = None
):
    """
    Devuelve el dict que espera el front para un Post:
    - autor + avatar
    - stars_count + starred
    - views_count
    - media: prioridad HLS (m3u8), fallback MP4 normalizado
    - caption: tal cual se guardó (string JSON o texto)
    - caption_meta: dict estructurado (texto + estilo + fuente)
    """
    # autor
    ures = await db.execute(select(User).where(User.id == post.user_id))
    user = ures.scalar_one()

    # avatar
    pres = await db.execute(select(Profile).where(Profile.user_id == post.user_id))
    prof = pres.scalar_one_or_none()

    stars_count = await _count_stars(db, post.id)
    starred = await _viewer_starred(db, post.id, viewer_id)

    # caption: usamos lo que hay en DB; si falta pero hay meta, lo reconstruimos
    caption = post.caption
    meta = post.caption_meta

    if not caption and meta:
        try:
            caption = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            # fallback: solo el texto
            text = meta.get("text") if isinstance(meta, dict) else None
            caption = normalize_caption(text) if text else None

    media_url = _maybe_hls_url(post.id) or to_media_url(post.media_path)

    return {
        "id": post.id,
        "media": media_url,
        "caption": caption,
        "created_at": post.created_at,
        "views_count": post.views_count,
        "author": {
            "id": user.id,
            "username": user.username,
            "avatar": prof.avatar if prof else None,
        },
        "stars_count": stars_count,
        "starred": starred,
        "caption_meta": meta,  # 👈 aquí viaja el meta al front
    }
