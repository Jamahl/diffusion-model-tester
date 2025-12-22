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
        "height", "seed", "scheduler",
        "score_overall",
        "score_facial_detail_realism",
        "score_body_proportions",
        "score_complexity_artistry",
        "score_composition_framing",
        "score_lighting_color",
        "score_resolution_clarity",
        "score_style_consistency",
        "score_prompt_adherence",
        "score_artifacts",
        "use_again",
        "curation_status",
        "image_id", "file_path", "upscale_url", "credit_cost",
        "flaws"
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
            "score_overall": image.score_overall if image.score_overall is not None else "",
            "score_facial_detail_realism": image.score_facial_detail_realism if image.score_facial_detail_realism is not None else "",
            "score_body_proportions": image.score_body_proportions if image.score_body_proportions is not None else "",
            "score_complexity_artistry": image.score_complexity_artistry if image.score_complexity_artistry is not None else "",
            "score_composition_framing": image.score_composition_framing if image.score_composition_framing is not None else "",
            "score_lighting_color": image.score_lighting_color if image.score_lighting_color is not None else "",
            "score_resolution_clarity": image.score_resolution_clarity if image.score_resolution_clarity is not None else "",
            "score_style_consistency": image.score_style_consistency if image.score_style_consistency is not None else "",
            "score_prompt_adherence": image.score_prompt_adherence if image.score_prompt_adherence is not None else "",
            "score_artifacts": image.score_artifacts if image.score_artifacts is not None else "",
            "use_again": image.use_again.value if image.use_again else "",
            "curation_status": image.curation_status if image.curation_status else "",
            "image_id": image.id,
            "file_path": image.file_path,
            "upscale_url": image.upscale_url,
            "credit_cost": config.credit_cost if config else 0,
            "flaws": image.flaws if image.flaws else "",
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
                "curation_status": image.curation_status
            },
            "image": {
                "file_path": image.file_path,
                "upscale_url": image.upscale_url,
                "is_rated": image.score_overall is not None,
                "is_failed": image.is_failed,
            }
        })
        
    return data
