# app/profile/router.py
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.security import decode_access_token
from app.users.repository import get_by_id
from app.profile.repository import get_by_user_id, create_profile
from app.profile.schemas import ProfileOut

# ⚠️ Primero se define el router
router = APIRouter(prefix="/api/profile", tags=["profile"])


# ---------------------------
# GET /api/profile/me/
# ---------------------------
@router.get("/me/", response_model=ProfileOut)
async def my_profile(
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    # token por query o Authorization: Bearer XXX
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="missing token")

    try:
        user_id = int(decode_access_token(token))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    # Verifica que el usuario exista
    user = await get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    # Busca perfil y, si no existe, devuelve estructura vacía
    prof = await get_by_user_id(db, user_id)
    if not prof:
        return {
            "user_id": user_id,
            "birth_date": None,
            "sex": None,
            "avatar": None,
            "cover": None,
        }
    return prof


# ---------------------------
# PATCH /api/profile/me/
# (opcional para actualizar sexo/fecha)
# ---------------------------
class ProfilePatch(BaseModel):
    birth_date: Optional[date] = None
    sex: Optional[str] = None

@router.patch("/me/", response_model=ProfileOut)
async def update_my_profile(
    payload: ProfilePatch,
    db: AsyncSession = Depends(get_session),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    # token por query o Authorization: Bearer XXX
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="missing token")

    try:
        user_id = int(decode_access_token(token))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    # Asegura perfil
    prof = await get_by_user_id(db, user_id)
    if not prof:
        prof = await create_profile(db, user_id)

    # Actualiza campos
    if payload.sex is not None:
        prof.sex = payload.sex
    if payload.birth_date is not None:
        prof.birth_date = payload.birth_date

    await db.flush()
    await db.commit()
    await db.refresh(prof)
    return prof
