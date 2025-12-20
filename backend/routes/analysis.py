"""Analysis routes for exporting data and cross-run insights."""
import csv
import io
from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db import get_db
from db.models import Image, Run, Config

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/csv")
async def export_csv(db: Session = Depends(get_db)):
    """
    Export all rated and unrated images with their configurations and scores as a CSV.
    Useful for cross-run analysis in Excel or other tools.
    """
    # Join Image, Run, and Config
    query = (
        db.query(Image, Run, Config)
        .join(Run, Image.run_id == Run.id)
        .outerjoin(Config, Image.id == Config.image_id)
        .order_by(desc(Run.batch_number), desc(Image.created_at))
    )
    
    results = query.all()
    
    # Define CSV columns
    fieldnames = [
        "run_id", "batch", "run_name", "created_at", "model_id", 
        "prompt", "negative_prompt", "steps", "scale", "width", 
        "height", "seed", "scheduler", "overall_quality", 
        "anatomy_score", "prompt_adherence", "background_score", 
        "use_again", "image_id", "file_path", "upscale_url", "credit_cost",
        "score_fidelity", "score_alignment", "score_aesthetics", "flaws", "curation_status"
    ]
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for image, run, config in results:
        writer.writerow({
            "run_id": run.id,
            "batch": run.batch_number,
            "run_name": run.name,
            "created_at": image.created_at.isoformat(),
            "model_id": run.model_id,
            "prompt": run.prompt,
            "negative_prompt": run.negative_prompt,
            "steps": config.steps if config else "",
            "scale": config.scale if config else "",
            "width": config.width if config else "",
            "height": config.height if config else "",
            "seed": config.seed if config else "",
            "scheduler": config.scheduler if config else "",
            "overall_quality": image.overall_quality if image.overall_quality is not None else "",
            "anatomy_score": image.anatomy_score if image.anatomy_score is not None else "",
            "prompt_adherence": image.prompt_adherence if image.prompt_adherence is not None else "",
            "background_score": image.background_score if image.background_score is not None else "",
            "use_again": image.use_again.value if image.use_again else "",
            "image_id": image.id,
            "file_path": image.file_path,
            "upscale_url": image.upscale_url,
            "credit_cost": config.credit_cost if config else 0,
            "score_fidelity": image.score_fidelity if image.score_fidelity is not None else "",
            "score_alignment": image.score_alignment if image.score_alignment is not None else "",
            "score_aesthetics": image.score_aesthetics if image.score_aesthetics is not None else "",
            "flaws": image.flaws if image.flaws else "",
            "curation_status": image.curation_status if image.curation_status else ""
        })
    
    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=experiments_export.csv"}
    )
    return response


@router.get("/table")
async def get_analysis_table(db: Session = Depends(get_db)):
    """
    Returns a flat list of all images with their run info and config.
    Used for the frontend analysis table view.
    """
    query = (
        db.query(Image, Run, Config)
        .join(Run, Image.run_id == Run.id)
        .outerjoin(Config, Image.id == Config.image_id)
        .order_by(desc(Run.batch_number), desc(Image.created_at))
    )
    
    results = query.all()
    
    data = []
    for image, run, config in results:
        data.append({
            "id": image.id,
            "run_id": run.id,
            "batch": run.batch_number,
            "run_name": run.name,
            "created_at": image.created_at.isoformat(),
            "prompt": run.prompt,
            "model_id": run.model_id,
            "config": {
                "steps": config.steps if config else None,
                "scale": config.scale if config else None,
                "width": config.width if config else None,
                "height": config.height if config else None,
                "scheduler": config.scheduler if config else None,
                "seed": config.seed if config else None,
                "credit_cost": config.credit_cost if config else 0,
            },
            "scores": {
                "overall_quality": image.overall_quality,
                "anatomy_score": image.anatomy_score,
                "prompt_adherence": image.prompt_adherence,
                "background_score": image.background_score,
                "use_again": image.use_again.value if image.use_again else None,
                "score_fidelity": image.score_fidelity,
                "score_alignment": image.score_alignment,
                "score_aesthetics": image.score_aesthetics,
                "flaws": image.flaws,
                "curation_status": image.curation_status
            },
            "image": {
                "file_path": image.file_path,
                "upscale_url": image.upscale_url,
                "is_rated": image.overall_quality is not None,
            }
        })
        
    return data
