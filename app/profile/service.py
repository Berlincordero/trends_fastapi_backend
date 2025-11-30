# app/profile/service.py
from __future__ import annotations
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.profile.repository import get_by_user_id, create_profile

async def ensure_profile(
    db: AsyncSession,
    user_id: int,
    *,
    birth_date: date | None = None,
    sex: str | None = None,
):
    """
    Garantiza que el usuario tenga perfil y actualiza birth_date/sex si llegan.
    No hace commit (lo hace el caller).
    """
    prof = await get_by_user_id(db, user_id)
    if prof:
        changed = False
        if birth_date is not None and prof.birth_date != birth_date:
            prof.birth_date = birth_date
            changed = True
        if sex is not None and prof.sex != sex:
            prof.sex = sex
            changed = True
        if changed:
            await db.flush()
        return prof

    return await create_profile(db, user_id, birth_date=birth_date, sex=sex)
