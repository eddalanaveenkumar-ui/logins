from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    uid = Column(String, unique=True, index=True, nullable=True) # Firebase UID
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Profile Fields
    display_name = Column(String, nullable=True)
    state = Column(String, nullable=True)
    language = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    bio = Column(String, nullable=True)