# app/media/jobs.py
from __future__ import annotations

import os
import threading

from app.core.config import settings
from app.media.hls import generate_hls, hls_abs_master


def _abs_media(rel: str) -> str:
    return os.path.join(settings.MEDIA_DIR, rel)


def spawn_hls_build(post_id: int, src_rel: str) -> None:
    """
    Lanza un hilo que genera el HLS para el post dado.
    No bloquea la petición HTTP de publicación.
    """
    src_abs = _abs_media(src_rel)

    def _run():
        try:
            # si ya existe master.m3u8, no hace nada
            if os.path.exists(hls_abs_master(post_id)):
                return
            generate_hls(src_abs, post_id)
        except Exception as e:
            # en dev verás esto en consola
            print(f"[HLS] Error generando HLS para post {post_id}: {e!r}")

    th = threading.Thread(target=_run, daemon=True)
    th.start()
