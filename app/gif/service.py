# app/gif/service.py
from __future__ import annotations
import os
from typing import Any, List, Tuple
from urllib.parse import quote

from app.core.config import settings

# Carpeta local de GIFs (./media/gifs)
GIFS_DIR = os.path.join(settings.MEDIA_DIR, "gifs")
os.makedirs(GIFS_DIR, exist_ok=True)

# Extensiones que vamos a servir
ALLOWED_EXTS = {".gif", ".webp", ".mp4"}


def _iter_files() -> List[Tuple[str, str]]:
    """
    Lista los archivos en /media/gifs/ que sean de una extensión permitida.
    Los ordena por fecha de modificación descendente (más nuevos primero).
    """
    files: list[tuple[str, str]] = []
    try:
      for name in os.listdir(GIFS_DIR):
          full = os.path.join(GIFS_DIR, name)
          if not os.path.isfile(full):
              continue
          ext = os.path.splitext(name)[1].lower()
          if ext not in ALLOWED_EXTS:
              continue
          files.append((name, full))
    except FileNotFoundError:
      pass

    # más recientes primero
    files.sort(key=lambda t: os.path.getmtime(t[1]), reverse=True)
    return files


def _get_dims(path: str) -> tuple[int | None, int | None]:
    """
    Intenta obtener dimensiones. Si no hay Pillow, no pasa nada.
    """
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
            return int(w), int(h)
    except Exception:
        return None, None


def _file_to_item(name: str, path: str) -> dict[str, Any]:
    """
    Convierte un archivo local a un item que el front pueda usar:
    { id, title, url, width?, height? }
    """
    stem, _ = os.path.splitext(name)
    width, height = _get_dims(path)
    # importante: escapamos el nombre por si tiene espacios
    rel_url = f"/media/gifs/{quote(name)}"
    return {
        "id": stem,
        "title": stem.replace("_", " "),
        "url": rel_url,
        "width": width,
        "height": height,
    }


async def search_gif(
    q: str,
    limit: int = 20,
    pos: str | None = None,
    locale: str | None = None,
    contentfilter: str | None = None,
    media_filter: str | None = None,
    ar_range: str | None = None,
) -> list[dict[str, Any]]:
    """
    Búsqueda local por nombre de archivo.
    Coincide si 'q' está contenido en el nombre (case-insensitive).
    """
    ql = (q or "").strip().lower()
    out: list[dict[str, Any]] = []

    for name, path in _iter_files():
        if ql and ql not in name.lower():
            continue
        out.append(_file_to_item(name, path))
        if len(out) >= max(1, int(limit or 20)):
            break

    return out


async def trending_gif(
    limit: int = 20,
    pos: str | None = None,
    locale: str | None = None,
    contentfilter: str | None = None,
    media_filter: str | None = None,
    ar_range: str | None = None,
) -> list[dict[str, Any]]:
    """
    Trending local = los archivos más recientes en /media/gifs/
    """
    items = [_file_to_item(name, path) for name, path in _iter_files()]
    return items[: max(1, int(limit or 20))]


async def categories_gif(
    locale: str | None = None,
    type_: str = "featured",
    contentfilter: str | None = None,
) -> list[dict[str, Any]]:
    # lo dejamos por compatibilidad con tu router
    return []


async def autocomplete_gif(
    q: str,
    limit: int = 20,
    locale: str | None = None,
) -> list[str]:
    return []


async def search_suggestions_gif(
    q: str,
    limit: int = 20,
    locale: str | None = None,
) -> list[str]:
    return []


async def register_share_gif(
    gif_id: str,
    query: str | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    # antes esto hablaba con Tenor; ahora solo devolvemos ok
    return {"ok": True, "id": gif_id}
