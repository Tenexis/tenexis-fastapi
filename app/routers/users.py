from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import User
from app.schemas import UserRead, UpdateProfileRequest
from app.auth import get_current_user

router = APIRouter(prefix="/api", tags=["users"])

@router.get("/users/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/users/me/complete-profile", response_model=UserRead)
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

@router.get("/u/{username}")
def get_user_profile(username: str, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Manual dict return is fine here, or define a PublicUserRead model
    return {
        "username": user.username,
        "name": user.name,
        "college": user.college.name if user.college else "Unverified",
        "picture": user.picture
    }