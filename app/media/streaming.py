# app/media/streaming.py
from __future__ import annotations
import os, hashlib, time
from mimetypes import guess_type
from fastapi import APIRouter, HTTPException, Request
from starlette.responses import FileResponse, Response
from app.core.config import settings

router = APIRouter()

def _etag(stat: os.stat_result) -> str:
    base = f"{stat.st_mtime_ns}-{stat.st_size}".encode()
    return hashlib.md5(base).hexdigest()  # suficiente para cache

def _headers(abs_path: str) -> dict:
    stat = os.stat(abs_path)
    etag = _etag(stat)
    ct, _ = guess_type(abs_path)
    return {
        "Accept-Ranges": "bytes",
        "Content-Type": ct or "application/octet-stream",
        # 🎯 video estático: cachea 1 año + immutable
        "Cache-Control": "public, max-age=31536000, immutable",
        "ETag": etag,
        "Last-Modified": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(int(stat.st_mtime))),
        # Opcionalmente ayuda a Android webview
        "Cross-Origin-Resource-Policy": "cross-origin",
    }

@router.head("/media/{path:path}")
async def head_media(path: str, request: Request):
    abs_path = os.path.join(settings.MEDIA_DIR, path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="file not found")
    headers = _headers(abs_path)
    # Soporte condicional simple
    inm = request.headers.get("if-none-match")
    if inm and inm == headers["ETag"]:
        return Response(status_code=304, headers=headers)
    # Content-Length lo añade FileResponse, pero aquí devolvemos vacío:
    size = os.path.getsize(abs_path)
    headers["Content-Length"] = str(size)
    return Response(status_code=200, headers=headers)

@router.get("/media/{path:path}")
async def stream_media(path: str, request: Request):
    abs_path = os.path.join(settings.MEDIA_DIR, path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="file not found")
    headers = _headers(abs_path)
    inm = request.headers.get("if-none-match")
    if inm and inm == headers["ETag"]:
        return Response(status_code=304, headers=headers)
    # Starlette maneja Range (200/206) y sendfile bajo el capó
    return FileResponse(abs_path, headers=headers)
