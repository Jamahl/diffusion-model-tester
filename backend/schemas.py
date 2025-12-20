"""Pydantic schemas for API request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class SchedulerType(str, Enum):
    """Valid scheduler options for SinkIn API."""
    DPMSolverMultistep = "DPMSolverMultistep"
    K_EULER_ANCESTRAL = "K_EULER_ANCESTRAL"
    DDIM = "DDIM"
    K_EULER = "K_EULER"
    PNDM = "PNDM"
    KLMS = "KLMS"


class ControlNetType(str, Enum):
    """Valid ControlNet options."""
    canny = "canny"
    depth = "depth"
    openpose = "openpose"


class UpscaleType(str, Enum):
    """Valid upscale types."""
    esrgan = "esrgan"
    hires_fix = "hires_fix"


# ============ Request Schemas ============

class InferenceRequest(BaseModel):
    """Request body for triggering inference."""
    model_id: str = Field(..., description="Model ID from SinkIn")
    prompt: str = Field(..., min_length=1, description="Text prompt for generation")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt")
    use_default_neg: Optional[bool] = Field(True, description="Use default negative prompt")
    
    # Dimensions
    width: Optional[int] = Field(512, ge=128, le=896, description="Image width (128-896, increment of 8)")
    height: Optional[int] = Field(768, ge=128, le=896, description="Image height (128-896, increment of 8)")
    
    # Generation parameters
    steps: Optional[int] = Field(30, ge=1, le=50, description="Inference steps (1-50)")
    scale: Optional[float] = Field(7.5, ge=1, le=20, description="Guidance scale (1-20)")
    num_images: Optional[int] = Field(4, ge=1, le=4, description="Number of images per call")
    seed: Optional[int] = Field(-1, description="Seed (-1 for random)")
    scheduler: Optional[SchedulerType] = Field(SchedulerType.DPMSolverMultistep)
    
    # LoRA
    lora: Optional[str] = Field(None, description="LoRA model ID")
    lora_scale: Optional[float] = Field(0.75, ge=0, le=1, description="LoRA strength")
    
    # Img2Img parameters
    image_strength: Optional[float] = Field(0.75, ge=0, le=1, description="Img2img strength")
    controlnet: Optional[ControlNetType] = Field(None, description="ControlNet type")


class JobRunRequest(BaseModel):
    """Request body for running a job from the queue."""
    job_id: int = Field(..., description="Job ID to process")


class UpscaleRequest(BaseModel):
    """Request body for upscaling an image."""
    type: UpscaleType = Field(UpscaleType.esrgan, description="Upscale type")
    scale: Optional[float] = Field(2, ge=2, le=4, description="Scale factor (ESRGAN only)")
    strength: Optional[float] = Field(0.6, ge=0, le=1, description="Strength (Hires Fix only)")


class ScoreRequest(BaseModel):
    """Request body for scoring an image."""
    overall_quality: Optional[int] = Field(None, ge=1, le=10)
    anatomy_score: Optional[int] = Field(None, ge=1, le=10)
    use_again: Optional[str] = Field(None, pattern="^(yes|no|test_more)$")
    prompt_adherence: Optional[int] = Field(None, ge=1, le=10)
    background_score: Optional[int] = Field(None, ge=1, le=10)
    is_failed: Optional[bool] = Field(None, description="Mark as failed generation")


# ============ Response Schemas ============

class InferenceResult(BaseModel):
    """Result from a single inference call."""
    success: bool
    images: List[str] = Field(default_factory=list, description="Generated image URLs")
    inf_id: Optional[str] = None
    credit_cost: Optional[float] = None
    error_message: Optional[str] = None


class ImageResponse(BaseModel):
    """Single image data for API responses."""
    id: str
    run_id: str
    file_path: Optional[str] = None
    upscale_url: Optional[str] = None
    inf_id: Optional[str] = None
    overall_quality: Optional[int] = None
    is_rated: bool = False
    is_failed: bool = False

    class Config:
        from_attributes = True


class RunResponse(BaseModel):
    """Run data for API responses."""
    id: str
    batch_number: int
    name: Optional[str] = None
    prompt: str
    model_id: str
    total_images: int = 0
    unrated_count: int = 0
    upscaled_count: int = 0

    class Config:
        from_attributes = True
