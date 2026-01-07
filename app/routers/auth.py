from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy import text
from app.database import get_session
from app.models import User, College
from app.schemas import GoogleLoginRequest, TokenResponse
from app.utils import verify_google_token, generate_unique_username
from app.auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/google", response_model=TokenResponse)
def login_google(request: GoogleLoginRequest, session: Session = Depends(get_session)):
    google_user = verify_google_token(request.credential)
    if not google_user:
        raise HTTPException(status_code=400, detail="Invalid Google Token")

    email = google_user.get("email")
    domain = email.split("@")[-1]
    
    user = session.exec(select(User).where(User.email == email)).first()
    
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
        # If user exists, load their college for the token slug
        if user.college_id:
            known_college = user.college

    # Determine slug safely for token
    c_slug = None
    if known_college:
        c_slug = known_college.slug
    elif user.college:
        c_slug = user.college.slug

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