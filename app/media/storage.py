import os
import uuid
import shutil
import subprocess
from typing import Tuple

from fastapi import UploadFile

from app.core.config import settings

# 📁 Rutas base
MEDIA_DIR = settings.MEDIA_DIR
POSTS_DIR = os.path.join(MEDIA_DIR, "posts")
AVATARS_DIR = os.path.join(MEDIA_DIR, "avatars")
TMP_DIR = os.path.join(MEDIA_DIR, "_tmp")
COMMENTS_DIR = os.path.join(MEDIA_DIR, "comments")
CLIPS_DIR = os.path.join(MEDIA_DIR, "clips")  # 👈 NUEVO para vibes/clips

# Asegura carpetas
os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(AVATARS_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(COMMENTS_DIR, exist_ok=True)
os.makedirs(CLIPS_DIR, exist_ok=True)

VIDEO_EXTS = {".mp4", ".m4v", ".mov", ".3gp", ".3gpp", ".webm", ".mkv"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Máximo de duración para clips (vibes)
CLIP_MAX_SECONDS = 120  # 2 minutos


def _ffmpeg_path() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg no está instalado o no está en PATH.")
    return path


def _is_video(upload: UploadFile, ext: str) -> bool:
    ct = (upload.content_type or "").lower()
    return ct.startswith("video/") or ext.lower() in VIDEO_EXTS


def _write_tmp(upload: UploadFile) -> str:
    """
    Vuelca el UploadFile a un archivo temporal y devuelve su ruta.
    """
    tmp_path = os.path.join(TMP_DIR, f"{uuid.uuid4().hex}.bin")
    with open(tmp_path, "wb") as out:
        shutil.copyfileobj(upload.file, out)
    try:
        upload.file.seek(0)
    except Exception:
        pass
    return tmp_path


def _new_rel(subdir: str, ext: str) -> Tuple[str, str]:
    """
    Devuelve (relativa, absoluta) para un archivo nuevo con extensión ext.
    """
    name = f"{uuid.uuid4().hex}{ext}"
    rel = f"{subdir}/{name}"
    abs_path = os.path.join(MEDIA_DIR, rel)
    return rel, abs_path


def _normalize_video(src_path: str, dst_path: str) -> None:
    """
    Normaliza el video a MP4 H.264 baseline + yuv420p + faststart
    (perfil compatible con Android/iOS y evita “Invalid NAL length”).
    """
    cmd = [
        _ffmpeg_path(),
        "-y",
        "-v",
        "error",
        "-i",
        src_path,
        "-c:v",
        "libx264",
        "-profile:v",
        "baseline",
        "-level:v",
        "3.1",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
        dst_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(dst_path):
        raise RuntimeError(
            f"FFmpeg falló: {proc.stderr.strip() or proc.stdout.strip()}"
        )


def _normalize_clip_video(src_path: str, dst_path: str) -> None:
    """
    Normaliza el video a MP4 H.264 baseline + yuv420p + faststart
    y lo recorta a un máximo de CLIP_MAX_SECONDS (2 minutos).
    Ideal para los clips de vibes.
    """
    cmd = [
        _ffmpeg_path(),
        "-y",
        "-v",
        "error",
        "-i",
        src_path,
        "-t",
        str(CLIP_MAX_SECONDS),
        "-c:v",
        "libx264",
        "-profile:v",
        "baseline",
        "-level:v",
        "3.1",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
        dst_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(dst_path):
        raise RuntimeError(
            f"FFmpeg falló (clip): {proc.stderr.strip() or proc.stdout.strip()}"
        )


def save_local(file: UploadFile, subdir: str = "avatars") -> str:
    """
    Copia tal cual (ideal para avatares u otras imágenes).
    Devuelve la ruta relativa dentro de /media (p. ej. 'avatars/abc.jpg').
    """
    base = MEDIA_DIR
    os.makedirs(os.path.join(base, subdir), exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    rel = f"{subdir}/{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(base, rel)
    with open(abs_path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    return rel


def save_post_media(file: UploadFile) -> str:
    """
    Guarda una publicación en /media/posts:
    - Si es video → normaliza con FFmpeg a .mp4 (baseline/yuv420p/faststart).
    - Si es imagen → guarda tal cual.
    Devuelve la ruta relativa (p. ej. 'posts/xxxx.mp4').
    """
    filename = file.filename or "upload.bin"
    ext = os.path.splitext(filename)[1].lower()
    is_video = _is_video(file, ext)

    tmp_src = _write_tmp(file)
    try:
        if is_video:
            rel, dst = _new_rel("posts", ".mp4")
            _normalize_video(tmp_src, dst)
            return rel
        else:
            if ext not in IMAGE_EXTS:
                ext = ".jpg"
            rel, dst = _new_rel("posts", ext)
            shutil.copyfile(tmp_src, dst)
            return rel
    finally:
        try:
            os.remove(tmp_src)
        except FileNotFoundError:
            pass


def save_comment_media(file: UploadFile) -> str:
    """
    Guarda imagen/gif/foto que el usuario adjunta en un comentario.
    Se guarda en /media/comments/
    Devuelve la ruta relativa (p. ej. 'comments/xxxx.png')
    """
    base = MEDIA_DIR
    os.makedirs(COMMENTS_DIR, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    if ext not in IMAGE_EXTS:
        ext = ".jpg"

    rel = f"comments/{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(base, rel)
    with open(abs_path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    return rel


def save_clip_media(file: UploadFile) -> str:
    """
    Guarda un clip de Vibes en /media/clips:
    - Si es video → normaliza + recorta a máx 120s.
    - Si es imagen → copia tal cual.
    Devuelve la ruta relativa (p. ej. 'clips/xxxx.mp4').
    """
    filename = file.filename or "clip.bin"
    ext = os.path.splitext(filename)[1].lower()
    is_video = _is_video(file, ext)

    tmp_src = _write_tmp(file)
    try:
        if is_video:
            rel, dst = _new_rel("clips", ".mp4")
            _normalize_clip_video(tmp_src, dst)
            return rel
        else:
            if ext not in IMAGE_EXTS:
                ext = ".jpg"
            rel, dst = _new_rel("clips", ext)
            shutil.copyfile(tmp_src, dst)
            return rel
    finally:
        try:
            os.remove(tmp_src)
        except FileNotFoundError:
            pass


def delete_post_media(rel: str | None) -> None:
    """
    Elimina el archivo físico de una publicación (si existe) en /media.
    No lanza error si ya no está.
    """
    if not rel:
        return
    abs_path = os.path.join(MEDIA_DIR, rel)
    try:
        os.remove(abs_path)
    except FileNotFoundError:
        pass
