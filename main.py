from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select, Relationship
from typing import Optional, List
from google.oauth2 import id_token
from google.auth.transport import requests
from jose import jwt
from datetime import datetime, timedelta
import os
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text

from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

# --- Database Setup (SQLModel) ---
engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

app = FastAPI()

# --- 1. Database Tables (With Relationships) ---
class College(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    domain: str | None = Field(unique=True, index=True)
    logo_url: str | None = None
    address: str | None = None
    
    # This causes the loop if included in API response
    students: List["User"] = Relationship(back_populates="college")

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    username: str = Field(index=True, unique=True)
    
    name: str | None = None
    picture: str | None = None
    
    # Verification
    phone_number: str | None = None
    is_phone_verified: bool = Field(default=False)
    gender: str | None = None 
    roll_number: str | None = None
    official_name: str | None = None
    
    # College Link
    college_id: int | None = Field(default=None, foreign_key="college.id")
    college: Optional[College] = Relationship(back_populates="students")
    is_college_verified: bool = Field(default=False)


# --- 2. Response Models (The Fix for Circular Dependency) ---
# These models define exactly what we send to the frontend.
# Notice we DO NOT include 'students' list in CollegeRead.

class CollegeRead(BaseModel):
    name: str
    slug: str
    domain: str | None
    logo_url: str | None

class UserRead(BaseModel):
    id: int
    email: str
    username: str
    name: str | None
    picture: str | None
    phone_number: str | None
    is_phone_verified: bool
    gender: str | None
    roll_number: str | None
    college_id: int | None
    is_college_verified: bool
    # We include a simplified College object, not the full table
    college: Optional[CollegeRead] = None


# --- Pydantic Models for Requests ---
class GoogleLoginRequest(BaseModel):
    credential: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class UpdateProfileRequest(BaseModel):
    phone_number: str
    gender: str
    roll_number: str
    official_name: str
    selected_college_id: int | None = None 

# --- Helpers ---
def verify_google_token(token: str):
    try:
        id_info = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        return id_info
    except ValueError:
        return None

def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=7)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

import re
import random
import string

def generate_slug(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    return slug

def generate_unique_username(email: str, session: Session) -> str:
    base_username = generate_slug(email.split("@")[0])
    username = base_username
    while session.exec(select(User).where(User.username == username)).first():
        suffix = ''.join(random.choices(string.digits, k=3))
        username = f"{base_username}-{suffix}"
    return username


# --- Routes ---
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.post("/api/auth/google", response_model=TokenResponse)
def login_google(request: GoogleLoginRequest, session: Session = Depends(get_session)):
    google_user = verify_google_token(request.credential)
    if not google_user:
        raise HTTPException(status_code=400, detail="Invalid Google Token")
    print(google_user)
    email = google_user.get("email")
    domain = email.split("@")[-1]
    
    user = session.exec(select(User).where(User.email == email)).first()
    
    # We define known_college outside so we can access it for token generation
    known_college = None 

    if not user:
        # A. Find College (Using SQL LIKE for subdomains)
        statement = select(College).where(text(f"'{domain}' LIKE '%' || domain"))
        known_college = session.exec(statement).first()
        
        college_id = known_college.id if known_college else None
        is_verified = True if known_college else False
        
        # B. Generate Unique Username
        new_username = generate_unique_username(email, session)

        user = User(
            email=email,
            username=new_username,
            name=google_user.get("name"),
            picture=google_user.get("picture"),
            college_id=college_id,
            is_college_verified=is_verified
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    else:
        # If user exists, load their college for the token
        if user.college_id:
            known_college = user.college

    # Determine slug safely
    c_slug = None
    if known_college:
        c_slug = known_college.slug
    elif user.college:
        c_slug = user.college.slug
    print(user)
    access_token = create_access_token(
        data={
            "sub": user.email, 
            "user_id": user.id,
            "username": user.username,
            "college_slug": c_slug,
            "is_verified": user.is_college_verified
        }
    )

    return {"access_token": access_token, "token_type": "bearer"}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# --- IMPORTANT: Use UserRead here ---
@app.get("/api/users/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    print(current_user)
    return current_user


@app.patch("/api/users/me/complete-profile", response_model=UserRead)
def complete_profile(
    update_data: UpdateProfileRequest, 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    current_user.phone_number = update_data.phone_number
    current_user.gender = update_data.gender
    current_user.roll_number = update_data.roll_number
    current_user.official_name = update_data.official_name
    
    if not current_user.college_id and update_data.selected_college_id:
        current_user.college_id = update_data.selected_college_id
        current_user.is_college_verified = False 
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@app.get("/api/colleges/{college_slug}", response_model=CollegeRead)
def get_college_public(college_slug: str, session: Session = Depends(get_session)):
    college = session.exec(select(College).where(College.slug == college_slug)).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    return college


@app.get("/api/u/{username}")
def get_user_profile(username: str, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "username": user.username,
        "name": user.name,
        "college": user.college.name if user.college else "Unverified",
        "picture": user.picture
    }