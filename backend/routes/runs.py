"""Run management routes for creating and listing experiment runs."""
import json
import uuid
from datetime import datetime
from typing import List, Optional
from itertools import product
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from db import get_db
from db.models import Run, Image, Job, JobStatus, Asset, Config

router = APIRouter(prefix="/api/runs", tags=["runs"])


# ============ Request Schemas ============

class RunCreateRequest(BaseModel):
    """Request body for creating a new run."""
    name: Optional[str] = Field(None, description="Optional run name")
    prompt: str = Field(..., min_length=1, description="Main prompt")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt")
    model_id: str = Field(..., description="SinkIn model ID")
    version: Optional[str] = Field(None, description="Model version")
    
    # Generation parameters (lists for multi-value combinations)
    width: int = Field(512, ge=128, le=896)
    height: int = Field(768, ge=128, le=896)
    steps_list: List[int] = Field(default=[30], description="List of step values to try")
    scale_list: List[float] = Field(default=[7.5], description="List of CFG values to try")
    scheduler_list: List[str] = Field(
        default=["DPMSolverMultistep"],
        description="List of schedulers to try"
    )
    num_images: int = Field(4, ge=1, le=4, description="Images per API call")
    seed: int = Field(-1, description="Seed (-1 for random)")
    
    # Img2Img
    init_image_asset_id: Optional[str] = Field(None, description="Asset ID for img2img")
    image_strength: float = Field(0.75, ge=0, le=1)
    controlnet: Optional[str] = Field(None, description="canny, depth, or openpose")
    
    # LoRA
    lora: Optional[str] = Field(None, description="LoRA model ID")
    lora_scale: float = Field(0.75, ge=0, le=1)
    
    # How many jobs to create
    total_jobs: int = Field(1, ge=1, le=100, description="Number of jobs to create")

    # System settings
    use_default_neg: bool = Field(True, description="Append the default negative prompt")


# ============ Helper Functions ============

def get_next_batch_number(db: Session) -> int:
    """Get the next available batch number."""
    max_batch = db.query(func.max(Run.batch_number)).scalar()
    return (max_batch or 0) + 1


def create_job_configs(request: RunCreateRequest) -> List[dict]:
    """
    Generate job configurations from run parameters.
    Creates combinations from multi-value parameters.
    """
    # Create all combinations of multi-value parameters
    combinations = list(product(
        request.steps_list,
        request.scale_list,
        request.scheduler_list,
    ))
    
    configs = []
    jobs_per_combo = max(1, request.total_jobs // len(combinations))
    
    for steps, scale, scheduler in combinations:
        for _ in range(jobs_per_combo):
            config = {
                "width": request.width,
                "height": request.height,
                "steps": steps,
                "scale": scale,
                "scheduler": scheduler,
                "num_images": request.num_images,
                "seed": request.seed,
                "image_strength": request.image_strength,
                "use_default_neg": request.use_default_neg,
            }
            
            if request.controlnet:
                config["controlnet"] = request.controlnet
            
            if request.lora:
                config["lora"] = request.lora
                config["lora_scale"] = request.lora_scale
            
            configs.append(config)
    
    # Limit to requested total
    return configs[:request.total_jobs]


# ============ Routes ============

@router.post("")
async def create_run(request: RunCreateRequest, db: Session = Depends(get_db)):
    """
    Create a new experiment run and enqueue jobs.
    
    Generates job configurations based on multi-value parameters
    (steps_list, scale_list, scheduler_list) and creates jobs in the queue.
    """
    # Validate init_image_asset if provided
    if request.init_image_asset_id:
        asset = db.query(Asset).filter(Asset.id == request.init_image_asset_id).first()
        if not asset:
            raise HTTPException(status_code=400, detail="Init image asset not found")
    
    # Create the run
    batch_number = get_next_batch_number(db)
    run = Run(
        id=str(uuid.uuid4()),
        batch_number=batch_number,
        name=request.name or f"Batch {batch_number}",
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        model_id=request.model_id,
        version=request.version,
    )
    db.add(run)
    db.flush()  # Get the run ID
    
    # Generate job configurations
    job_configs = create_job_configs(request)
    
    # Create jobs
    jobs_created = []
    for config in job_configs:
        job = Job(
            run_id=run.id,
            status=JobStatus.queued,
            config_json=json.dumps(config),
            init_image_asset_id=request.init_image_asset_id,
        )
        db.add(job)
        db.flush()
        jobs_created.append({
            "id": job.id,
            "config": config,
        })
    
    db.commit()
    
    return {
        "success": True,
        "run": {
            "id": run.id,
            "batch_number": run.batch_number,
            "name": run.name,
            "prompt": run.prompt,
            "model_id": run.model_id,
        },
        "jobs_created": len(jobs_created),
        "jobs": jobs_created,
    }


@router.get("")
async def list_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List all runs with summary counts.
    
    Returns total images, unrated count, and upscaled count for each run.
    """
    # Get runs with pagination
    runs = db.query(Run).order_by(Run.created_at.desc()).offset(offset).limit(limit).all()
    total = db.query(Run).count()
    
    results = []
    for run in runs:
        # Count images for this run
        total_images = db.query(Image).filter(Image.run_id == run.id).count()
        
        # Count unrated images (no overall score)
        unrated_count = db.query(Image).filter(
            Image.run_id == run.id,
            Image.score_overall.is_(None)
        ).count()
        
        # Count upscaled images (has upscale_url)
        upscaled_count = db.query(Image).filter(
            Image.run_id == run.id,
            Image.upscale_url.isnot(None)
        ).count()
        
        # Get queued jobs count
        queued_jobs = db.query(Job).filter(
            Job.run_id == run.id,
            Job.status == JobStatus.queued
        ).count()
        
        # Calculate total cost from Configs
        total_cost = db.query(func.sum(Config.credit_cost)).join(Image).filter(Image.run_id == run.id).scalar() or 0.0
        
        results.append({
            "id": run.id,
            "batch_number": run.batch_number,
            "name": run.name,
            "created_at": run.created_at.isoformat(),
            "prompt": run.prompt[:100] + "..." if len(run.prompt) > 100 else run.prompt,
            "model_id": run.model_id,
            "total_images": total_images,
            "unrated_count": unrated_count,
            "upscaled_count": upscaled_count,
            "queued_jobs": queued_jobs,
            "total_cost": round(total_cost, 2),
        })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "runs": results,
    }


@router.get("/{run_id}")
async def get_run(run_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific run."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Get counts
    total_images = db.query(Image).filter(Image.run_id == run.id).count()
    unrated_count = db.query(Image).filter(
        Image.run_id == run.id,
        Image.score_overall.is_(None)
    ).count()
    upscaled_count = db.query(Image).filter(
        Image.run_id == run.id,
        Image.upscale_url.isnot(None)
    ).count()
    
    # Get job counts
    jobs_by_status = {}
    for status in JobStatus:
        count = db.query(Job).filter(
            Job.run_id == run.id,
            Job.status == status
        ).count()
        jobs_by_status[status.value] = count
    
    # Calculate total cost from Configs
    total_cost = db.query(func.sum(Config.credit_cost)).join(Image).filter(Image.run_id == run.id).scalar() or 0.0
    
    return {
        "id": run.id,
        "batch_number": run.batch_number,
        "name": run.name,
        "created_at": run.created_at.isoformat(),
        "prompt": run.prompt,
        "negative_prompt": run.negative_prompt,
        "model_id": run.model_id,
        "version": run.version,
        "counts": {
            "total_images": total_images,
            "unrated": unrated_count,
            "upscaled": upscaled_count,
        },
        "jobs": jobs_by_status,
        "total_cost": round(total_cost, 2),
    }


@router.delete("/{run_id}")
async def delete_run(run_id: str, db: Session = Depends(get_db)):
    """Delete a run and all associated images/jobs."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # SQLAlchemy will cascade delete images, configs, and jobs
    db.delete(run)
    db.commit()
    
    return {"success": True, "message": f"Run {run_id} deleted"}
