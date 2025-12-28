from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr
    display_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    state: Optional[str] = None
    language: Optional[str] = None
    photo_url: Optional[str] = None
    bio: Optional[str] = None

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class GoogleLoginRequest(BaseModel):
    id_token: str

class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    state: Optional[str] = None
    language: Optional[str] = None
    photo_url: Optional[str] = None
    bio: Optional[str] = None