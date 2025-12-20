"""Routes for handling asset uploads (init images)."""
import os
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from db.models import Asset
from config import get_settings

router = APIRouter(prefix="/api/assets", tags=["assets"])

@router.post("")
async def upload_asset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload an image to be used as an init_image for img2img."""
    settings = get_settings()
    
    # Ensure directory exists
    assets_dir = Path(settings.assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    asset_id = str(uuid.uuid4())
    extension = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    filename = f"{asset_id}.{extension}"
    file_path = assets_dir / filename
    
    try:
        # Save file locally
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Create DB record
        asset = Asset(
            id=asset_id,
            original_filename=file.filename,
            mime_type=file.content_type,
            file_path=str(file_path)
        )
        db.add(asset)
        db.commit()
        
        return {
            "id": asset.id,
            "filename": file.filename,
            "status": "uploaded"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload asset: {str(e)}")
