import os
from PIL import Image
from fastapi import UploadFile, HTTPException
import uuid
import shutil

# Configure where to save local images
UPLOAD_DIR = "static/uploads/products"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ImageManager:
    @staticmethod
    def validate_image(file: UploadFile):
        # 1. Check content type
        if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(status_code=400, detail="Invalid image format. Use JPEG, PNG, or WebP.")
        
        # 2. Check File Size (Limit to 5MB)
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        if size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large. Max 5MB.")

    @staticmethod
    def is_nsfw(image: Image.Image) -> bool:
        # Placeholder for NSFW logic.
        # In future, call an external API or use a library like 'nsfw-detector'
        return False 

    @staticmethod
    async def save_image(file: UploadFile, is_local: bool = True) -> str:
        # 1. Open Image with Pillow
        try:
            img = Image.open(file.file)
            img.verify() # Verify it's not corrupt
            file.file.seek(0)
            img = Image.open(file.file) # Re-open for processing
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image file.")

        # 2. Check NSFW
        if ImageManager.is_nsfw(img):
            raise HTTPException(status_code=400, detail="Inappropriate image detected.")

        # 3. Compress / Resize
        # Convert to RGB (handles PNG transparency issues)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Resize if massive (e.g., max width 1200px)
        img.thumbnail((1200, 1200)) 

        # 4. Generate Filename
        filename = f"{uuid.uuid4()}.webp"
        
        if is_local:
            file_path = os.path.join(UPLOAD_DIR, filename)
            # Save as optimized WebP
            img.save(file_path, "WEBP", quality=80)
            
            # Return URL (Assuming you mount /static in main.py)
            return f"/static/uploads/products/{filename}"
        else:
            # AWS S3 Logic would go here
            return "https://s3.aws.com/..."