from pydantic import BaseModel
from typing import Optional, List
from app.models import ProductType, ProductVisibility

class ProductRead(BaseModel):
    id: int
    title: str
    description: str | None
    price: float
    # Add other product fields you want to send, but NOT the 'user' relationship
    
    class Config:
        from_attributes = True

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
    official_name: str | None
    college_slug: str | None
    is_college_verified: bool
    college: Optional[CollegeRead] = None
    products: List[ProductRead] = []

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
    selected_college_slug: str | None = None

# --- Product Response ---
class ProductRead(BaseModel):
    title: str
    slug: str
    price: float | None
    product_type: ProductType
    visibility: ProductVisibility
    description: str
    city: str | None
    images: List[str] = [] # List of URLs
    # We might add 'user' info here depending on privacy settings

# --- Product Create Request ---
class ProductBase(BaseModel):
    title: str
    description: str
    price: float | None = None # Optional for Lost/Found
    product_type: ProductType
    visibility: ProductVisibility = ProductVisibility.public
    
    is_digital: bool = False
    
    # Location
    pickup_address: str | None = None
    city: str | None = None
    state: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    
    category_id: int | None = None
    new_category_name: str | None = None

class ProductCreateResponse(BaseModel):
    slug: str
    status: str

# --- College Actions ---
class CollegeCreateRequest(BaseModel):
    name: str
    domain: str | None = None
    city: str | None = None

# --- OTP Actions ---
class OTPRequest(BaseModel):
    phone_number: str

class OTPVerifyRequest(BaseModel):
    phone_number: str
    code: str

# --- Onboarding / Profile Update ---
class UserOnboardingRequest(BaseModel):
    phone_number: str
    gender: str
    official_name: str
    
    # Optional because they might already have it from Google Login
    college_slug: str | None = None 
    roll_number: str | None = None # Required if college_id is present