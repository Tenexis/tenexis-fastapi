from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlmodel import Session, select, SQLModel
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
from jose import jwt, JWTError
import json
import random

from app.database import get_session
from app.models import Product, ProductImage, Category, User, ProductStatus, ProductType, ProductVisibility
from app.auth import get_current_user, SECRET_KEY, ALGORITHM
from app.services.image_manager import ImageManager
from app.utils import generate_slug

router = APIRouter(prefix="/api/products", tags=["products"])

# ==========================================
# 1. RESPONSE SCHEMAS (Fixes Pydantic Error)
# ==========================================

# Simple Read Models for Nested Data
class ProductImageRead(SQLModel):
    id: int
    url: str

class CategoryRead(SQLModel):
    id: int
    name: str
    slug: str

class CollegeRead(SQLModel):
    name: str
    city: Optional[str] = None

class UserRead(SQLModel):
    id: int
    name: Optional[str] = None
    username: str
    picture: Optional[str] = None
    college: Optional[CollegeRead] = None

# Main Product Response Model
class ProductRead(SQLModel):
    id: int
    title: str
    slug: str
    description: str
    price: Optional[float] = None
    product_type: ProductType
    status: ProductStatus
    visibility: ProductVisibility
    created_at: datetime
    is_digital: bool
    city: Optional[str] = None
    
    # Relationships (Explicitly defined)
    images: List[ProductImageRead] = []
    category: Optional[CategoryRead] = None
    user: Optional[UserRead] = None

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

async def get_optional_user(
    request: Request,
    session: Session = Depends(get_session)
) -> Optional[User]:
    """
    Checks for a token in the header. 
    If present and valid, returns User.
    If missing or invalid, returns None (Guest).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    try:
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            return None
            
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        
        if user_id is None:
            return None
            
        user = session.get(User, user_id)
        return user
        
    except (JWTError, ValueError):
        return None


def check_visibility(product: Product, user: Optional[User]) -> bool:
    # 1. Owner always sees their product
    if user and product.user_id == user.id:
        return True

    # 2. Public: Everyone sees it
    if product.visibility == ProductVisibility.public:
        return True

    # 3. If not public and user is not logged in -> Hidden
    if not user:
        return False

    # 4. College Visibility
    if product.visibility == ProductVisibility.college:
        if user.college_slug and product.user.college_slug == user.college_slug:
            return True
        return False

    # 5. Gender Visibility
    if product.visibility == ProductVisibility.gender:
        if user.gender and product.user.gender == user.gender:
            return True
        return False
        
    # 6. City Visibility
    if product.visibility == ProductVisibility.city:
        user_city = user.college.city if user.college else None
        target_city = product.city or (product.user.college.city if product.user.college else None)
        
        if user_city and target_city and user_city.lower() == target_city.lower():
            return True
        return False

    return False


# ==========================================
# 3. ENDPOINTS
# ==========================================

@router.post("/", response_model=dict)
async def create_product(
    title: str = Form(...),
    description: str = Form(...),
    product_type: ProductType = Form(...),
    price: float = Form(None),
    visibility: ProductVisibility = Form(ProductVisibility.public),
    is_digital: bool = Form(False),
    city: str = Form(None),
    category_id: int = Form(None),
    new_category_name: str = Form(None),
    files: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if product_type in [ProductType.lost, ProductType.found]:
        price = 0.0
    elif price is None:
        raise HTTPException(status_code=400, detail="Price is required for Buy/Sell/Rent.")

    final_cat_id = category_id
    if new_category_name:
        cat_slug = generate_slug(new_category_name)
        existing_cat = session.exec(select(Category).where(Category.slug == cat_slug)).first()
        if existing_cat:
            final_cat_id = existing_cat.id
        else:
            new_cat = Category(name=new_category_name, slug=cat_slug, is_verified=False)
            session.add(new_cat)
            session.commit()
            session.refresh(new_cat)
            final_cat_id = new_cat.id

    product_slug = generate_slug(title)
    while session.exec(select(Product).where(Product.slug == product_slug)).first():
        product_slug += f"-{json.dumps(random.randint(10,99))}"

    new_product = Product(
        title=title,
        slug=product_slug,
        description=description,
        price=price,
        product_type=product_type,
        visibility=visibility, 
        is_digital=is_digital,
        city=city if not is_digital else None,
        category_id=final_cat_id,
        user_id=current_user.id,
        status=ProductStatus.active 
    )
    session.add(new_product)
    session.commit()
    session.refresh(new_product)

    if files:
        if len(files) > 5:
            raise HTTPException(status_code=400, detail="Max 5 images allowed")
        for file in files:
            ImageManager.validate_image(file)
            image_url = await ImageManager.save_image(file, is_local=True)
            p_img = ProductImage(url=image_url, product_id=new_product.id)
            session.add(p_img)
        session.commit()

    return {"slug": new_product.slug, "status": new_product.status}


@router.get("/", response_model=List[ProductRead])
def get_products(
    current_user: Optional[User] = Depends(get_optional_user),
    session: Session = Depends(get_session)
):
    query = (
        select(Product)
        .where(Product.status == ProductStatus.active)
        .options(
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.user).selectinload(User.college)
        )
    )
    
    results = session.exec(query).all()
    
    visible_products = []
    
    for product in results:
        if check_visibility(product, current_user):
            # Privacy Scrubbing
            if not current_user:
                # We can't modify the ORM object directly if we are strict about types
                # but SQLModel is flexible.
                product.user = None 
            
            visible_products.append(product)
            
    return visible_products


@router.get("/{slug}", response_model=ProductRead)
def get_product_by_slug(
    slug: str,
    current_user: Optional[User] = Depends(get_optional_user),
    session: Session = Depends(get_session)
):
    query = (
        select(Product)
        .where(Product.slug == slug)
        .options(
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.user).selectinload(User.college)
        )
    )
    
    product = session.exec(query).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not check_visibility(product, current_user):
        if current_user:
            raise HTTPException(
                status_code=403, 
                detail=f"This product is restricted to {product.visibility} only."
            )
        raise HTTPException(status_code=404, detail="Product not found")

    if not current_user:
        product.user = None 

    return product