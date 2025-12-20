"""Job processing routes for SinkIn inference."""
import json
import os
import uuid
import requests
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from db.models import Job, JobStatus, Image, Config, Run
from schemas import InferenceResult, JobRunRequest
from services.sinkin import sinkin_service
from config import get_settings

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def download_image(url: str, save_dir: Path, filename: str) -> str:
    """Download image from URL and save locally."""
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / filename
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(response.content)
        return str(file_path)
    except Exception as e:
        print(f"Error downloading image: {e}")
        return ""


@router.post("/run", response_model=InferenceResult)
async def run_job(request: JobRunRequest, db: Session = Depends(get_db)):
    """
    Process a single job from the queue by calling SinkIn /inference API.
    Stores generated images and their configs in the database.
    """
    settings = get_settings()
    
    # Get the job
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.queued:
        raise HTTPException(status_code=400, detail=f"Job is not queued (status: {job.status.value})")
    
    # Get the associated run
    run = db.query(Run).filter(Run.id == job.run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Parse job config
    try:
        config = json.loads(job.config_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid job config JSON")
    
    # Update job status to running
    job.status = JobStatus.running
    db.commit()
    
    # Get init image path if present
    init_image_path = None
    if job.init_image_asset_id:
        from db.models import Asset
        asset = db.query(Asset).filter(Asset.id == job.init_image_asset_id).first()
        if asset:
            init_image_path = asset.file_path
    
    # Call SinkIn API
    try:
        payload, response = sinkin_service.inference(
            model_id=run.model_id,
            prompt=run.prompt,
            negative_prompt=run.negative_prompt,
            width=config.get("width", 512),
            height=config.get("height", 768),
            steps=config.get("steps", 30),
            scale=config.get("scale", 7.5),
            num_images=config.get("num_images", 4),
            seed=config.get("seed", -1),
            scheduler=config.get("scheduler", "DPMSolverMultistep"),
            lora=config.get("lora"),
            lora_scale=config.get("lora_scale", 0.75),
            init_image_path=init_image_path,
            image_strength=config.get("image_strength", 0.75),
            controlnet=config.get("controlnet"),
            use_default_neg=config.get("use_default_neg", True),
        )
        
        # Check for API error and handle fallback if img2img
        if response.get("error_code", 0) != 0:
            if init_image_path:
                print(f"Img2Img failed, falling back to text2img for job {job.id}")
                # Retry without init image
                payload, response = sinkin_service.inference(
                    model_id=run.model_id,
                    prompt=run.prompt,
                    negative_prompt=run.negative_prompt,
                    width=config.get("width", 512),
                    height=config.get("height", 768),
                    steps=config.get("steps", 30),
                    scale=config.get("scale", 7.5),
                    num_images=config.get("num_images", 4),
                    seed=config.get("seed", -1),
                    scheduler=config.get("scheduler", "DPMSolverMultistep"),
                    lora=config.get("lora"),
                    lora_scale=config.get("lora_scale", 0.75),
                    init_image_path=None, # Fallback
                    use_default_neg=config.get("use_default_neg", True),
                )
            
            # If still error (or not img2img)
            if response.get("error_code", 0) != 0:
                job.status = JobStatus.failed
                job.error_message = response.get("message", "Unknown API error")
                job.completed_at = datetime.utcnow()
                db.commit()
                return InferenceResult(
                    success=False,
                    error_message=job.error_message
                )
        
        # Process successful response
        image_urls = response.get("images", [])
        inf_id = response.get("inf_id", "")
        credit_cost = response.get("credit_cost", 0)
        
        # Set up image storage directory
        images_dir = Path(settings.images_dir)
        
        saved_images = []
        for i, img_url in enumerate(image_urls):
            # Generate unique filename
            image_id = str(uuid.uuid4())
            filename = f"{image_id}.png"
            
            # Download and save image
            file_path = download_image(img_url, images_dir, filename)
            
            # Create image record
            image = Image(
                id=image_id,
                run_id=run.id,
                file_path=file_path if file_path else None,
                inf_id=inf_id,
                batch_index=i,
            )
            db.add(image)
            db.flush()  # Get the image ID
            
            # Create config record
            image_config = Config(
                image_id=image.id,
                steps=config.get("steps", 30),
                scale=config.get("scale", 7.5),
                width=config.get("width", 512),
                height=config.get("height", 768),
                seed=response.get("seed", config.get("seed", -1)),
                scheduler=config.get("scheduler", "DPMSolverMultistep"),
                image_strength=config.get("image_strength") if init_image_path else None,
                controlnet=config.get("controlnet"),
                credit_cost=credit_cost / len(image_urls) if image_urls else credit_cost,
                raw_payload_json=json.dumps(payload),
                raw_response_json=json.dumps(response),
            )
            db.add(image_config)
            
            saved_images.append(img_url)
        
        # Update job status
        job.status = JobStatus.completed
        job.completed_at = datetime.utcnow()
        db.commit()
        
        return InferenceResult(
            success=True,
            images=saved_images,
            inf_id=inf_id,
            credit_cost=credit_cost
        )
        
    except ValueError as e:
        # API key not configured
        job.status = JobStatus.failed
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Unexpected error
        job.status = JobStatus.failed
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")


@router.get("")
async def list_jobs(
    status: str = None,
    run_id: str = None,
    db: Session = Depends(get_db)
):
    """List jobs with optional filters and associated run info."""
    query = db.query(Job)
    
    if status:
        try:
            job_status = JobStatus(status)
            query = query.filter(Job.status == job_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    if run_id:
        query = query.filter(Job.run_id == run_id)
    
    jobs = query.order_by(Job.created_at.desc()).all()
    
    return [
        {
            "id": job.id,
            "run_id": job.run_id,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "run_name": job.run.name,
            "run_batch": job.run.batch_number,
            "config": json.loads(job.config_json)
        }
        for job in jobs
    ]


@router.get("/next")
async def get_next_job(db: Session = Depends(get_db)):
    """Get the next pending job in the queue."""
    job = (
        db.query(Job)
        .filter(Job.status == JobStatus.queued)
        .order_by(Job.created_at.asc())
        .first()
    )
    
    if not job:
        return {"job_id": None}
    
    return {
        "job_id": job.id,
        "run_name": job.run.name,
        "run_batch": job.run.batch_number
    }


@router.delete("/{job_id}")
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    """Cancel and delete a job from the queue."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status == JobStatus.running:
        raise HTTPException(status_code=400, detail="Cannot delete a running job")
    
    db.delete(job)
    db.commit()
    
    return {"success": True, "message": f"Job {job_id} deleted"}


@router.post("/cancel-all")
async def cancel_all_jobs(run_id: str = None, db: Session = Depends(get_db)):
    """Cancel all queued jobs, optionally filtered by run."""
    query = db.query(Job).filter(Job.status == JobStatus.queued)
    if run_id:
        query = query.filter(Job.run_id == run_id)
    
    count = query.delete()
    db.commit()
    
    return {"success": True, "deleted_count": count}
