# app/profile/repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.profile.models import Profile

async def get_by_user_id(db: AsyncSession, user_id: int) -> Profile | None:
    res = await db.execute(select(Profile).where(Profile.user_id == user_id))
    return res.scalar_one_or_none()

async def create_profile(db: AsyncSession, user_id: int, *, birth_date=None, sex=None) -> Profile:
    prof = Profile(user_id=user_id, birth_date=birth_date, sex=sex)
    db.add(prof)
    await db.flush()
    await db.refresh(prof)
    return prof
