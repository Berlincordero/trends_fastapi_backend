# app/gif/router.py
from fastapi import APIRouter, Query, HTTPException, Header
from typing import Optional

from app.gif import service as gif_svc

router = APIRouter(prefix="/api/gif", tags=["gif"])


@router.get("/search/")
async def gif_search(
    q: str = Query(..., description="término a buscar en los GIFs"),
    limit: int = Query(12, ge=1, le=200),
    pos: str | None = Query(None),
    locale: str | None = Query(None, description="p.ej. es_CR, es_MX, en_US"),
    contentfilter: str | None = Query(None),
    # 👇 los dejamos porque tu front los manda, pero aquí no los usamos
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Proxy simple hacia el servicio de GIFs.
    Ahora el servicio lee de /media/gifs/, pero la firma se mantiene.
    """
    try:
        data = await gif_svc.search_gif(
            q=q,
            limit=limit,
            pos=pos,
            locale=locale,
            contentfilter=contentfilter,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"gif search failed: {e!r}")


@router.get("/trending/")
async def gif_trending(
    limit: int = Query(12, ge=1, le=200),
    pos: str | None = Query(None),
    locale: str | None = Query(None),
    contentfilter: str | None = Query(None),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Devuelve los GIFs más recientes en /media/gifs/ (nuestro “trending” local).
    """
    try:
        data = await gif_svc.trending_gif(
            limit=limit,
            pos=pos,
            locale=locale,
            contentfilter=contentfilter,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"gif trending failed: {e!r}")


@router.get("/categories/")
async def gif_categories(
    locale: str | None = Query(None),
    type: str = Query("featured", description="featured | emoji | trending"),
    contentfilter: str | None = Query(None),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Lo dejamos por compatibilidad: ahora mismo devuelve lista vacía.
    """
    try:
        data = await gif_svc.categories_gif(
            locale=locale,
            type_=type,
            contentfilter=contentfilter,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"gif categories failed: {e!r}")


@router.get("/autocomplete/")
async def gif_autocomplete(
    q: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    locale: str | None = Query(None),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Ahora mismo devuelve [] siempre, pero mantenemos la ruta.
    """
    try:
        data = await gif_svc.autocomplete_gif(
            q=q,
            limit=limit,
            locale=locale,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"gif autocomplete failed: {e!r}")


@router.get("/suggestions/")
async def gif_suggestions(
    q: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    locale: str | None = Query(None),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Igual que autocomplete: la dejamos para no romper el front.
    """
    try:
        data = await gif_svc.search_suggestions_gif(
            q=q,
            limit=limit,
            locale=locale,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"gif search_suggestions failed: {e!r}")


@router.post("/registershare/")
async def gif_register_share(
    id: str = Query(..., description="id del GIF que compartiste"),
    q: str | None = Query(None, description="término original de búsqueda"),
    locale: str | None = Query(None),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    """
    Antes avisaba a Tenor; ahora solo responde ok, pero mantenemos el endpoint.
    """
    try:
        data = await gif_svc.register_share_gif(
            gif_id=id,
            query=q,
            locale=locale,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"gif registershare failed: {e!r}")
