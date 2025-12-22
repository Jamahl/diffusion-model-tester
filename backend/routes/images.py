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
    
    # Exclude failed images from gallery listings
    query = query.filter(Image.is_failed.is_(False))
    
    if run_id:
        query = query.filter(Image.run_id == run_id)
    
    if unrated_only:
        query = query.filter(Image.score_overall.is_(None))
    
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
                "score_overall": img.score_overall,
                "is_rated": img.score_overall is not None,
                "scores": {
                    "score_overall": img.score_overall,
                    "facial_detail_realism": img.score_facial_detail_realism,
                    "body_proportions": img.score_body_proportions,
                    "complexity_artistry": img.score_complexity_artistry,
                    "composition_framing": img.score_composition_framing,
                    "lighting_color": img.score_lighting_color,
                    "resolution_clarity": img.score_resolution_clarity,
                    "style_consistency": img.score_style_consistency,
                    "prompt_adherence": img.score_prompt_adherence,
                    "artifacts": img.score_artifacts,
                },
                "curation_status": img.curation_status,
                "use_again": img.use_again.value if img.use_again else None,
                "flaws": img.flaws,
                "config": {
                    "steps": img.config.steps if img.config else None,
                    "scale": img.config.scale if img.config else None,
                    "width": img.config.width if img.config else None,
                    "height": img.config.height if img.config else None,
                    "seed": img.config.seed if img.config else None,
                    "scheduler": img.config.scheduler if img.config else None,
                    "credit_cost": img.config.credit_cost if img.config else None,
                }
            }
            for img in images
        ],
    }


@router.get("/ids")
async def list_image_ids(
    run_id: str = Query(..., description="Run ID to fetch image IDs for"),
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Fetch only the IDs for images in a run (lightweight navigation helper).
    """
    images = (
        db.query(Image.id)
        .filter(Image.run_id == run_id)
        .filter(Image.is_failed.is_(False))
        .order_by(Image.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "run_id": run_id,
        "limit": limit,
        "offset": offset,
        "image_ids": [row[0] for row in images],
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
        "is_failed": image.is_failed,
        "created_at": image.created_at.isoformat(),
        "scores": {
            "score_overall": image.score_overall,
            "facial_detail_realism": image.score_facial_detail_realism,
            "body_proportions": image.score_body_proportions,
            "complexity_artistry": image.score_complexity_artistry,
            "composition_framing": image.score_composition_framing,
            "lighting_color": image.score_lighting_color,
            "resolution_clarity": image.score_resolution_clarity,
            "style_consistency": image.score_style_consistency,
            "prompt_adherence": image.score_prompt_adherence,
            "artifacts": image.score_artifacts,
            "use_again": image.use_again.value if image.use_again else None,
            "curation_status": image.curation_status,
            "flaws": image.flaws,
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
    if request.score_overall is not None:
        image.score_overall = request.score_overall
    if request.score_facial_detail_realism is not None:
        image.score_facial_detail_realism = request.score_facial_detail_realism
    if request.score_body_proportions is not None:
        image.score_body_proportions = request.score_body_proportions
    if request.score_complexity_artistry is not None:
        image.score_complexity_artistry = request.score_complexity_artistry
    if request.score_composition_framing is not None:
        image.score_composition_framing = request.score_composition_framing
    if request.score_lighting_color is not None:
        image.score_lighting_color = request.score_lighting_color
    if request.score_resolution_clarity is not None:
        image.score_resolution_clarity = request.score_resolution_clarity
    if request.score_style_consistency is not None:
        image.score_style_consistency = request.score_style_consistency
    if request.score_prompt_adherence is not None:
        image.score_prompt_adherence = request.score_prompt_adherence
    if request.score_artifacts is not None:
        image.score_artifacts = request.score_artifacts
    if request.use_again is not None:
        from db.models import UseAgain
        image.use_again = UseAgain(request.use_again)
    if request.is_failed is not None:
        image.is_failed = request.is_failed
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
            "overall": image.score_overall,
            "facial_detail_realism": image.score_facial_detail_realism,
            "body_proportions": image.score_body_proportions,
            "complexity_artistry": image.score_complexity_artistry,
            "composition_framing": image.score_composition_framing,
            "lighting_color": image.score_lighting_color,
            "resolution_clarity": image.score_resolution_clarity,
            "style_consistency": image.score_style_consistency,
            "prompt_adherence": image.score_prompt_adherence,
            "artifacts": image.score_artifacts,
            "use_again": image.use_again.value if image.use_again else None,
            "flaws": image.flaws,
            "curation_status": image.curation_status,
        },
        "is_failed": image.is_failed,
    }
