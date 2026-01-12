from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.database import get_session
from app.models import College
from app.schemas import CollegeRead, CollegeCreateRequest
from app.utils import generate_slug

router = APIRouter(prefix="/api/colleges", tags=["colleges"])

@router.post("/", response_model=CollegeRead)
def create_college(
    data: CollegeCreateRequest,
    session: Session = Depends(get_session)
):
    slug = generate_slug(data.name)
    if session.exec(select(College).where(College.slug == slug)).first():
        raise HTTPException(status_code=400, detail="College already exists")

    new_college = College(
        name=data.name,
        slug=slug,
        domain=data.domain,
        city=data.city,
        # Default logo or None
        logo_url="https://via.placeholder.com/100" 
    )
    session.add(new_college)
    session.commit()
    session.refresh(new_college)
    return new_college

@router.get("/search", response_model=list[CollegeRead])
def search_colleges(
    q: str = Query(None, min_length=2),
    session: Session = Depends(get_session)
):
    if not q:
        return []
        
    # Case insensitive search on Name or City
    statement = select(College).where(
        (College.name.ilike(f"%{q}%")) | 
        (College.city.ilike(f"%{q}%"))
    ).limit(10)
    
    colleges = session.exec(statement).all()
    return colleges


@router.get("/{college_slug}", response_model=CollegeRead)
def get_college_public(college_slug: str, session: Session = Depends(get_session)):
    college = session.exec(select(College).where(College.slug == college_slug)).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    return college