from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models import College
from app.schemas import CollegeRead

router = APIRouter(prefix="/api/colleges", tags=["colleges"])

@router.get("/{college_slug}", response_model=CollegeRead)
def get_college_public(college_slug: str, session: Session = Depends(get_session)):
    college = session.exec(select(College).where(College.slug == college_slug)).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    return college