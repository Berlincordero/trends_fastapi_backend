# app/users/schemas.py
from pydantic import BaseModel, EmailStr, Field, AliasChoices
from datetime import date

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    # Acepta birth_date | date_of_birth | dob
    birth_date: date | None = Field(
        default=None,
        validation_alias=AliasChoices("birth_date", "date_of_birth", "dob"),
    )
    # Acepta sex | gender | g
    sex: str | None = Field(
        default=None,
        validation_alias=AliasChoices("sex", "gender", "g"),
    )

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr

    class Config:
        from_attributes = True
