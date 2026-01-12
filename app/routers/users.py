from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import User
from app.auth import get_current_user, create_access_token
from app.schemas import UserRead, OTPRequest, OTPVerifyRequest, UserOnboardingRequest, UpdateProfileRequest
from app.services.otp import OTPService

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
    
    # FIXED: Check college_slug instead of college_id
    if not current_user.college_slug and update_data.selected_college_slug:
        current_user.college_slug = update_data.selected_college_slug
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
    
    return {
        "username": user.username,
        "name": user.name,
        "college": user.college.name if user.college else "Unverified",
        "picture": user.picture
    }

@router.post("/users/send-otp")
def send_otp(
    data: OTPRequest,
    session: Session = Depends(get_session)
):
    existing_user = session.exec(select(User).where(User.phone_number == data.phone_number, User.is_phone_verified == True)).first()
    if existing_user:
         raise HTTPException(status_code=400, detail="Phone number already in use.")

    OTPService.create_and_send(session, data.phone_number)
    return {"message": "OTP sent successfully"}

@router.post("/users/verify-otp")
def verify_otp(
    data: OTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    is_valid = OTPService.verify_otp(session, data.phone_number, data.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or Expired OTP")
    
    current_user.phone_number = data.phone_number
    current_user.is_phone_verified = True
    session.add(current_user)
    session.commit()
    
    return {"message": "Phone verified"}

# --- Onboarding Route ---

@router.patch("/users/onboarding", response_model=dict)
def complete_onboarding(
    data: UserOnboardingRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # 1. Check Phone Verification
    if not current_user.is_phone_verified or current_user.phone_number != data.phone_number:
        raise HTTPException(status_code=400, detail="Please verify phone number first.")

    # 2. Update Basic Info
    current_user.gender = data.gender
    current_user.official_name = data.official_name

    # 3. Handle College Logic
    if data.college_slug is not None:
        if current_user.college_slug != data.college_slug:
            current_user.college_slug = data.college_slug
            current_user.is_college_verified = False 

    # 4. Handle Roll Number
    if data.roll_number:
        if current_user.roll_number != data.roll_number:
             current_user.roll_number = data.roll_number
             current_user.is_college_verified = False 

    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    # --- 5. REGENERATE TOKEN ---
    is_onboarded = True 

    new_access_token = create_access_token(
        data={
            "sub": current_user.email, 
            "user_id": current_user.id,
            "username": current_user.username,
            "college_slug": current_user.college_slug,
            "is_verified": current_user.is_college_verified,
            "is_onboarded": is_onboarded
        }
    )

    return {
        "user": current_user,
        "access_token": new_access_token,
        "token_type": "bearer"
    }