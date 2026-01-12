from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models import Product, ProductImage, Category, User, ProductStatus, ProductType, ProductVisibility
from app.auth import get_current_user
from app.services.image_manager import ImageManager
from app.utils import generate_slug
import json
import random

router = APIRouter(prefix="/api/products", tags=["products"])

@router.post("/", response_model=dict)
async def create_product(
    title: str = Form(...),
    description: str = Form(...),
    product_type: ProductType = Form(...),
    
    # Price is optional form field now
    price: float = Form(None),
    
    # Visibility
    visibility: ProductVisibility = Form(ProductVisibility.public),
    
    is_digital: bool = Form(False),
    city: str = Form(None),
    
    category_id: int = Form(None),
    new_category_name: str = Form(None),
    
    files: List[UploadFile] = File(None),
    
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # 1. Logic for Lost/Found
    if product_type in [ProductType.lost, ProductType.found]:
        price = 0.0  # Force price to 0 for lost/found items
    elif price is None:
        raise HTTPException(status_code=400, detail="Price is required for Buy/Sell/Rent.")

    # 2. Handle Category (Same as before)
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

    # 3. Create Slug
    product_slug = generate_slug(title)
    while session.exec(select(Product).where(Product.slug == product_slug)).first():
        product_slug += f"-{json.dumps(random.randint(10,99))}"

    # 4. Create Product
    new_product = Product(
        title=title,
        slug=product_slug,
        description=description,
        price=price,
        product_type=product_type,
        visibility=visibility, # <--- Storing visibility
        is_digital=is_digital,
        city=city if not is_digital else None,
        category_id=final_cat_id,
        user_id=current_user.id,
        status=ProductStatus.active 
    )
    session.add(new_product)
    session.commit()
    session.refresh(new_product)

    # 5. Handle Images
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

# (Snippet for future use in GET /api/products)
@router.get("/")
def get_products(
    current_user: User = Depends(get_current_user), # The viewer
    session: Session = Depends(get_session)
):
    query = select(Product).where(Product.status == ProductStatus.active)
    
    # Retrieve all items
    results = session.exec(query).all()
    
    visible_products = []
    for product in results:
        # 1. Public? Everyone sees it.
        if product.visibility == ProductVisibility.public:
            visible_products.append(product)
            continue
            
        # 2. College? Check IDs.
        if product.visibility == ProductVisibility.college:
            if current_user.college_id == product.user.college_id:
                visible_products.append(product)
            continue

        # 3. Gender? Check genders.
        if product.visibility == ProductVisibility.gender:
            if current_user.gender == product.user.gender:
                visible_products.append(product)
            continue
            
    return visible_products