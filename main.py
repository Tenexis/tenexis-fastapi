# main.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select
from google.oauth2 import id_token
from google.auth.transport import requests
from jose import jwt
from datetime import datetime, timedelta
import os

from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

# --- Database Setup (SQLModel) ---
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str | None = None
    picture: str | None = None

engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

app = FastAPI()

# --- Pydantic Models ---
class GoogleLoginRequest(BaseModel):
    credential: str # The token from Google

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# --- Helper: Verify Google Token ---
def verify_google_token(token: str):
    try:
        id_info = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        return id_info
    except ValueError:
        return None

# --- Helper: Create JWT ---
def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=7)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Routes ---
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.post("/api/auth/google", response_model=TokenResponse)
def login_google(request: GoogleLoginRequest, session: Session = Depends(get_session)):
    # 1. Verify Token with Google
    google_user = verify_google_token(request.credential)
    if not google_user:
        raise HTTPException(status_code=400, detail="Invalid Google Token")

    email = google_user.get("email")
    
    # 2. Check/Create User in DB
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    
    if not user:
        user = User(
            email=email, 
            name=google_user.get("name"), 
            picture=google_user.get("picture")
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    # 3. Generate our OWN Session Token (JWT)
    # This token grants access to your whole ecosystem
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})

    # Return token string (We won't set cookie here, Next.js will do it)
    return {"access_token": access_token, "token_type": "bearer"}