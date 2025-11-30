# app/main.py
import os
import logging
import mimetypes
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.json import UTF8JSONResponse
from app.core.config import settings
from app.core.limiter import init_limiter
from app.db.init_db import init_models

# routers
from app.users.router import router as users_router
from app.profile.router import router as profile_router
from app.feed.router import router as feed_router
from app.media.streaming import router as media_router
from app.comments.router import router as comments_router
from app.gif.router import router as gif_router
from app.clips.router import router as clips_router  # 👈 NUEVO

log = logging.getLogger("uvicorn")

# ⚙️ HLS mime-types
mimetypes.add_type("application/vnd.apple.mpegurl", ".m3u8")
mimetypes.add_type("video/mp2t", ".ts")

app = FastAPI(
    title="Trends API",
    default_response_class=UTF8JSONResponse,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# directorios
os.makedirs(settings.MEDIA_DIR, exist_ok=True)
os.makedirs(settings.HLS_DIR, exist_ok=True)

# montar HLS
app.mount("/hls", StaticFiles(directory=settings.HLS_DIR, html=False), name="hls")


@app.middleware("http")
async def cache_static_hls_media(request: Request, call_next):
    """
    Cache fuerte para /hls y /media inmutables.
    """
    response = await call_next(request)
    p = request.url.path
    if (
        p.startswith("/hls/")
        or p.startswith("/media/posts/")
        or p.startswith("/media/comments/")
        or p.startswith("/media/clips/")  # 👈 clips también cacheables
    ):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    # content-type ya viene con charset por UTF8JSONResponse,
    # pero si otra response lo quitó, lo restauramos:
    ct = response.headers.get("content-type", "")
    if ct.startswith("application/json") and "charset=" not in ct:
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response


@app.on_event("startup")
async def on_startup():
    log.info("🚀 Iniciando servicio…")
    await init_limiter()
    await init_models()
    log.info("✅ Startup listo.")


@app.get("/api/health/")
async def health():
    # incluye emojis para testear transporte UTF-8
    return {"ok": True, "service": "fastapi", "msg": "healthy ✨🔥🇨🇷"}


# routers
app.include_router(users_router)     # /api/users/...
app.include_router(profile_router)   # /api/profile/...
app.include_router(feed_router)      # /api/feed/...
app.include_router(comments_router)  # /api/comments/...
app.include_router(gif_router)       # /api/gif/...
app.include_router(media_router)     # /media/...
app.include_router(clips_router)     # /api/clips/... 👈 NUEVO
