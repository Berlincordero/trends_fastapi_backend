# app/media/hls.py
from __future__ import annotations

import os
import shutil
import subprocess
from typing import List

from app.core.config import settings


def _ffmpeg() -> str:
    """
    Devuelve la ruta de ffmpeg o lanza error si no está instalado.
    """
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg no está instalado o no está en PATH.")
    return path


def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def hls_abs_dir(post_id: int) -> str:
    """
    Carpeta absoluta donde se guarda el HLS de un post.
    Ej: ./media/hls/123/
    """
    return os.path.join(settings.HLS_DIR, str(post_id))


def hls_abs_master(post_id: int) -> str:
    """
    Ruta absoluta al master.m3u8 de un post.
    """
    return os.path.join(hls_abs_dir(post_id), "master.m3u8")


def hls_master_rel(post_id: int) -> str:
    """
    Ruta relativa HTTP al master.m3u8.
    Ej: hls/123/master.m3u8 (se servirá desde /hls/...)
    """
    return f"hls/{post_id}/master.m3u8"


def generate_hls_single(src_abs: str, post_id: int) -> str:
    """
    Genera HLS con 1 sola calidad.
    Devuelve la ruta absoluta del master.m3u8.
    """
    outdir = hls_abs_dir(post_id)
    _ensure_dir(outdir)

    seg = settings.HLS_SEG_SECONDS

    cmd = [
        _ffmpeg(),
        "-y",
        "-v",
        "error",
        "-i",
        src_abs,
        "-c:v",
        "libx264",
        "-profile:v",
        "main",
        "-level",
        "3.1",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ac",
        "2",
        "-ar",
        "48000",
        "-preset",
        "veryfast" if settings.HLS_FAST_TRANSCODE else "medium",
        "-hls_time",
        str(seg),
        "-hls_playlist_type",
        "vod",
        "-hls_segment_filename",
        os.path.join(outdir, "seg_%06d.ts"),
        os.path.join(outdir, "master.m3u8"),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    master = os.path.join(outdir, "master.m3u8")
    if proc.returncode != 0 or not os.path.exists(master):
        raise RuntimeError(proc.stderr or proc.stdout or "ffmpeg error (HLS single)")

    return master


def generate_hls_ladder(src_abs: str, post_id: int) -> str:
    """
    Genera 3 calidades (240p, 360p, 480p) y un master.m3u8 con variantes (ABR).
    Devuelve ruta absoluta al master.m3u8.
    """
    outdir = hls_abs_dir(post_id)
    _ensure_dir(outdir)

    seg = settings.HLS_SEG_SECONDS
    preset = "veryfast" if settings.HLS_FAST_TRANSCODE else "medium"

    # name, scale, video_bitrate, audio_bitrate
    variants = [
        ("240p", "-vf", "scale=-2:240", "400k", "96k"),
        ("360p", "-vf", "scale=-2:360", "800k", "96k"),
        ("480p", "-vf", "scale=-2:480", "1200k", "128k"),
    ]

    variant_playlists: List[tuple[str, str]] = []

    for name, vf_flag, vf_val, v_b, a_b in variants:
        vdir = os.path.join(outdir, name)
        _ensure_dir(vdir)

        playlist = os.path.join(vdir, f"{name}.m3u8")
        cmd = [
            _ffmpeg(),
            "-y",
            "-v",
            "error",
            "-i",
            src_abs,
            vf_flag,
            vf_val,
            "-c:v",
            "libx264",
            "-b:v",
            v_b,
            "-profile:v",
            "main",
            "-level",
            "3.1",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            a_b,
            "-ac",
            "2",
            "-ar",
            "48000",
            "-preset",
            preset,
            "-hls_time",
            str(seg),
            "-hls_playlist_type",
            "vod",
            "-hls_segment_filename",
            os.path.join(vdir, f"{name}_%06d.ts"),
            playlist,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(playlist):
            raise RuntimeError(proc.stderr or proc.stdout or f"ffmpeg error ({name})")

        variant_playlists.append((name, playlist))

    master = os.path.join(outdir, "master.m3u8")
    with open(master, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, pl in variant_playlists:
            res_map = {
                "240p": "426x240",
                "360p": "640x360",
                "480p": "854x480",
            }
            bw_map = {
                "240p": "400000",
                "360p": "800000",
                "480p": "1200000",
            }
            res = res_map[name]
            bw = bw_map[name]
            rel = os.path.relpath(pl, outdir).replace("\\", "/")
            f.write(
                f'#EXT-X-STREAM-INF:BANDWIDTH={bw},RESOLUTION={res},NAME="{name}"\n{rel}\n'
            )

    return master


def generate_hls(src_abs: str, post_id: int) -> str:
    """
    Dispatcher: ladder (ABR) o 1 sola calidad según config.
    """
    if settings.HLS_USE_LADDER:
        return generate_hls_ladder(src_abs, post_id)
    return generate_hls_single(src_abs, post_id)


def delete_hls(post_id: int) -> None:
    """
    Elimina por completo la carpeta HLS de un post (si existe).
    No lanza error si falta.
    """
    d = hls_abs_dir(post_id)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
