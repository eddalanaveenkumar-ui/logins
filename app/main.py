from fastapi import FastAPI, Depends, HTTPException, status, Header, Query
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from datetime import datetime

from . import models, schemas, database, firebase_config

# Create Database Tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Triangle Auth Backend (Postgres)")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependencies ---
def get_current_user(authorization: Annotated[str | None, Header()] = None, db: Session = Depends(database.get_db)):
    """
    Verifies the Firebase ID Token from the Authorization header.
    Returns the User model from Postgres.
    """
    if authorization is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")
    
    id_token = parts[1]
    decoded_token = firebase_config.verify_token(id_token)
    
    if not decoded_token:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    uid = decoded_token.get('uid')
    user = db.query(models.User).filter(models.User.uid == uid).first()
    if user is None:
        # User authenticated with Firebase but not in Postgres yet
        # This might happen during registration flow, but for protected routes we expect user to exist
        raise HTTPException(status_code=404, detail="User not found in database")
    return user

# --- Routes ---

@app.get("/")
def root():
    return {"status": "Postgres Auth Backend Running"}

# --- User Routes (Matching Frontend Expectations) ---

@app.post("/user/register")
def register_user(
    user_data: schemas.UserBase, 
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(database.get_db)
):
    # Verify token manually since user might not exist in DB yet
    if not authorization: raise HTTPException(401, "No token")
    decoded_token = firebase_config.verify_token(authorization.split()[1])
    if not decoded_token: raise HTTPException(401, "Invalid token")
    
    uid = decoded_token.get('uid')

    # Check username uniqueness
    if db.query(models.User).filter(models.User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    new_user = models.User(
        uid=uid,
        email=user_data.email,
        username=user_data.username,
        display_name=user_data.display_name
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"status": "User registered successfully", "user": new_user}

@app.post("/user/google-login")
def google_login(request: schemas.GoogleLoginRequest, db: Session = Depends(database.get_db)):
    # 1. Verify Firebase Token
    decoded_token = firebase_config.verify_token(request.id_token)
    if not decoded_token:
        raise HTTPException(status_code=401, detail="Invalid Google Token")
    
    uid = decoded_token.get('uid')
    email = decoded_token.get('email')
    
    # 2. Check if user exists in Postgres
    user = db.query(models.User).filter(models.User.uid == uid).first()
    
    if not user:
        # New user
        base_username = email.split("@")[0] if email else f"user_{uid[:8]}" 
        # Ensure unique username
        count = 0
        username = base_username
        while db.query(models.User).filter(models.User.username == username).first():
            count += 1
            username = f"{base_username}{count}"

        new_user = models.User(
            email=email,
            username=username,
            uid=uid,
            hashed_password=None,
            display_name=decoded_token.get('name'),
            photo_url=decoded_token.get('picture')
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Return profile format expected by frontend
        return {
            "new_user": True, 
            "profile": {
                "uid": new_user.uid,
                "username": new_user.username,
                "email": new_user.email,
                "created_at": new_user.created_at,
                "display_name": new_user.display_name,
                "photo_url": new_user.photo_url,
                "state": new_user.state,
                "language": new_user.language
            }
        }

    # Existing user
    return {
        "new_user": False, 
        "profile": {
            "uid": user.uid,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at,
            "display_name": user.display_name,
            "photo_url": user.photo_url,
            "state": user.state,
            "language": user.language
        }
    }

@app.get("/user/profile")
def get_user_profile(current_user: models.User = Depends(get_current_user)):
    return {
        "uid": current_user.uid,
        "username": current_user.username,
        "email": current_user.email,
        "created_at": current_user.created_at,
        "display_name": current_user.display_name,
        "photo_url": current_user.photo_url,
        "state": current_user.state,
        "language": current_user.language,
        "bio": current_user.bio
    }

@app.post("/user/profile")
def update_user_profile(
    profile_data: schemas.UserProfileUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    if profile_data.display_name: current_user.display_name = profile_data.display_name
    if profile_data.state: current_user.state = profile_data.state
    if profile_data.language: current_user.language = profile_data.language
    if profile_data.photo_url: current_user.photo_url = profile_data.photo_url
    if profile_data.bio: current_user.bio = profile_data.bio
    
    db.commit()
    db.refresh(current_user)
    return {"status": "Profile updated successfully", "profile": {
        "uid": current_user.uid,
        "username": current_user.username,
        "email": current_user.email,
        "state": current_user.state,
        "language": current_user.language,
        "photo_url": current_user.photo_url
    }}

@app.post("/user/lookup")
def lookup_user(data: dict, db: Session = Depends(database.get_db)):
    username = data.get("username")
    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        return {"email": user.email}
    raise HTTPException(status_code=404, detail="User ID not found")