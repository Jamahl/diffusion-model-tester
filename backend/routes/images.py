"""Image routes for viewing, scoring, and upscaling images."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from db import get_db
from db.models import Image, Config, Run
from schemas import UpscaleRequest, ScoreRequest
from services.sinkin import sinkin_service

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("")
async def list_images(
    run_id: Optional[str] = Query(None, description="Filter by run ID"),
    unrated_only: bool = Query(False, description="Only show unrated images"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of images with optional filters.
    """
    query = db.query(Image)
    
    if run_id:
        query = query.filter(Image.run_id == run_id)
    
    if unrated_only:
        query = query.filter(Image.overall_quality.is_(None))
    
    total = query.count()
    images = query.order_by(Image.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "images": [
            {
                "id": img.id,
                "run_id": img.run_id,
                "file_path": img.file_path,
                "upscale_url": img.upscale_url,
                "inf_id": img.inf_id,
                "created_at": img.created_at.isoformat(),
                "overall_quality": img.overall_quality,
                "is_rated": img.overall_quality is not None,
                # RLHF + extended scoring context
                "score_fidelity": img.score_fidelity,
                "score_alignment": img.score_alignment,
                "score_aesthetics": img.score_aesthetics,
                "curation_status": img.curation_status,
                "flaws": img.flaws,
            }
            for img in images
        ],
    }


@router.get("/{image_id}")
async def get_image(image_id: str, db: Session = Depends(get_db)):
    """Get a single image with its config."""
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Get associated config
    config = db.query(Config).filter(Config.image_id == image_id).first()
    
    # Get run info
    run = db.query(Run).filter(Run.id == image.run_id).first()
    
    return {
        "id": image.id,
        "run_id": image.run_id,
        "file_path": image.file_path,
        "upscale_url": image.upscale_url,
        "inf_id": image.inf_id,
        "created_at": image.created_at.isoformat(),
        "scores": {
            "overall_quality": image.overall_quality,
            "anatomy_score": image.anatomy_score,
            "use_again": image.use_again.value if image.use_again else None,
            "prompt_adherence": image.prompt_adherence,
            "background_score": image.background_score,
        },
        "config": {
            "steps": config.steps if config else None,
            "scale": config.scale if config else None,
            "width": config.width if config else None,
            "height": config.height if config else None,
            "seed": config.seed if config else None,
            "scheduler": config.scheduler if config else None,
            "image_strength": config.image_strength if config else None,
            "controlnet": config.controlnet if config else None,
            "credit_cost": config.credit_cost if config else None,
        } if config else None,
        "run": {
            "prompt": run.prompt if run else None,
            "negative_prompt": run.negative_prompt if run else None,
            "model_id": run.model_id if run else None,
        } if run else None,
    }


@router.post("/{image_id}/upscale")
async def upscale_image(
    image_id: str,
    request: UpscaleRequest,
    db: Session = Depends(get_db),
):
    """
    Upscale an image using SinkIn /upscale API.
    Updates the image record with the upscale_url.
    """
    # Get the image
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Need inf_id and a URL to upscale
    if not image.inf_id:
        raise HTTPException(status_code=400, detail="Image has no inf_id - cannot upscale")
    
    # Get the config to find the original image URL from raw_response
    config = db.query(Config).filter(Config.image_id == image_id).first()
    if not config or not config.raw_response_json:
        raise HTTPException(status_code=400, detail="Image has no config data - cannot determine original URL")
    
    # Parse raw response to get the correct original image URL
    try:
        if not config.raw_response_json:
             raise HTTPException(status_code=400, detail="Image has no raw response data - cannot upscale")
             
        raw_response = json.loads(config.raw_response_json)
        image_urls = raw_response.get("images", [])
        
        if not image_urls:
            raise HTTPException(status_code=400, detail="No source image URLs found in generation records")
            
        # Use stored batch_index to pick the correct URL from the original batch
        index = image.batch_index if image.batch_index is not None else 0
        if index >= len(image_urls):
            index = 0 # Fallback
            
        image_url = image_urls[index]
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid generation record data")
    
    try:
        # Call SinkIn upscale API
        result = sinkin_service.upscale(
            inf_id=image.inf_id,
            image_url=image_url,
            upscale_type=request.type.value,
            scale=request.scale,
            strength=request.strength,
        )
        
        # Check for error
        if result.get("error_code", 0) != 0:
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Upscale failed")
            )
        
        # Get upscaled image URL
        upscale_url = result.get("output")
        credit_cost = result.get("credit_cost", 0)
        
        # Update image record
        image.upscale_url = upscale_url
        
        # Update config with upscale credit cost (add to existing)
        if config:
            existing_cost = config.credit_cost or 0
            config.credit_cost = existing_cost + credit_cost
        
        db.commit()
        
        return {
            "success": True,
            "upscale_url": upscale_url,
            "credit_cost": credit_cost,
            "type": request.type.value,
        }
        
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{image_id}/score")
async def score_image(
    image_id: str,
    request: ScoreRequest,
    db: Session = Depends(get_db),
):
    """
    Update scores for an image.
    """
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Update only provided scores
    if request.overall_quality is not None:
        image.overall_quality = request.overall_quality
    if request.anatomy_score is not None:
        image.anatomy_score = request.anatomy_score
    if request.use_again is not None:
        from db.models import UseAgain
        image.use_again = UseAgain(request.use_again)
    if request.prompt_adherence is not None:
        image.prompt_adherence = request.prompt_adherence
    if request.background_score is not None:
        image.background_score = request.background_score
    if request.is_failed is not None:
        image.is_failed = request.is_failed
    
    # New RLHF Scoring
    if request.score_fidelity is not None:
        image.score_fidelity = request.score_fidelity
    if request.score_alignment is not None:
        image.score_alignment = request.score_alignment
    if request.score_aesthetics is not None:
        image.score_aesthetics = request.score_aesthetics
    if request.flaws is not None:
        # Store as JSON string if list, else string
        image.flaws = json.dumps(request.flaws) if isinstance(request.flaws, list) else request.flaws
    if request.curation_status is not None:
        image.curation_status = request.curation_status
    
    db.commit()
    
    return {
        "success": True,
        "image_id": image_id,
        "scores": {
            "overall_quality": image.overall_quality,
            "anatomy_score": image.anatomy_score,
            "use_again": image.use_again.value if image.use_again else None,
            "prompt_adherence": image.prompt_adherence,
            "background_score": image.background_score,
            # New fields
            "score_fidelity": image.score_fidelity,
            "score_alignment": image.score_alignment,
            "score_aesthetics": image.score_aesthetics,
            "flaws": image.flaws,
            "curation_status": image.curation_status,
        },
    }
