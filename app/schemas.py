from pydantic import BaseModel
from typing import Optional

# --- Response Models (Read) ---
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
    # Simplified College object to prevent infinite loops
    college: Optional[CollegeRead] = None

# --- Request Models ---
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