from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List

# --- Database Tables ---
class College(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    domain: str | None = Field(unique=True, index=True)
    logo_url: str | None = None
    address: str | None = None
    
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