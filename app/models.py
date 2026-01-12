from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum

# --- Enums ---
class ProductType(str, Enum):
    buy = "buy"
    rent = "rent"
    sell = "sell"
    lost = "lost"   # <-- New
    found = "found" # <-- New

class ProductStatus(str, Enum):
    pending = "pending"
    active = "active"
    sold = "sold"
    found = "found" # Item recovered
    rejected = "rejected"

class ProductVisibility(str, Enum):
    public = "public"    # Visible to everyone
    college = "college"  # Only my college
    city = "city"        # Only my city
    gender = "gender"    # Only my gender (e.g. Hostel items)

# --- 1. College ---
class College(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    domain: str | None = Field(unique=True, index=True)
    logo_url: str | None = None
    
    # Location
    address: str | None = None
    city: str | None = Field(default=None, index=True)
    district: str | None = None
    state: str | None = None
    country: str | None = Field(default="India")
    
    students: List["User"] = Relationship(back_populates="college")

# --- 2. Categories ---
class Category(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    slug: str = Field(unique=True, index=True)
    is_verified: bool = Field(default=False)
    
    products: List["Product"] = Relationship(back_populates="category")

# --- 3. Products ---
class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    slug: str = Field(unique=True, index=True)
    description: str
    
    # Price is Optional now (Lost items = None or 0)
    price: float | None = Field(default=None)
    
    product_type: ProductType = Field(index=True)
    status: ProductStatus = Field(default=ProductStatus.pending, index=True)
    
    # Privacy / Visibility
    visibility: ProductVisibility = Field(default=ProductVisibility.public, index=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Location Logic
    is_digital: bool = Field(default=False)
    pickup_address: str | None = None
    city: str | None = Field(default=None, index=True)
    state: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    
    # Relationships
    category_id: int | None = Field(default=None, foreign_key="category.id")
    category: Optional[Category] = Relationship(back_populates="products")
    
    user_id: int = Field(foreign_key="user.id")
    user: "User" = Relationship(back_populates="products")
    
    images: List["ProductImage"] = Relationship(back_populates="product")

# --- 4. Product Images ---
class ProductImage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    url: str
    product_id: int = Field(foreign_key="product.id")
    product: Product = Relationship(back_populates="images")

# --- User ---
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    username: str = Field(index=True, unique=True)
    name: str | None = None
    picture: str | None = None
    
    phone_number: str | None = None
    is_phone_verified: bool = Field(default=False)
    gender: str | None = None 
    roll_number: str | None = None
    official_name: str | None = None
    
    college_slug: str | None = Field(default=None, foreign_key="college.slug")
    college: Optional[College] = Relationship(back_populates="students")
    is_college_verified: bool = Field(default=False)

    products: List[Product] = Relationship(back_populates="user")

class OTP(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    phone_number: str = Field(index=True)
    code: str
    expires_at: datetime
    is_used: bool = Field(default=False)