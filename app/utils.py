import re
import random
import string
import os
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlmodel import Session, select
from app.models import User

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def verify_google_token(token: str):
    try:
        id_info = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        return id_info
    except ValueError:
        return None

def generate_slug(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    return slug

def generate_unique_username(email: str, session: Session) -> str:
    base_username = generate_slug(email.split("@")[0])
    username = base_username
    
    # If username exists, append random digits
    while session.exec(select(User).where(User.username == username)).first():
        suffix = ''.join(random.choices(string.digits, k=3))
        username = f"{base_username}-{suffix}"
    
    return username