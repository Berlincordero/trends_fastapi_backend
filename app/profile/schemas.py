# app/profile/schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import date

class ProfileOut(BaseModel):
    user_id: int
    birth_date: Optional[date] = None
    sex: Optional[str] = None
    avatar: Optional[str] = None
    cover: Optional[str] = None

    class Config:
        from_attributes = True
