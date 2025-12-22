"""SQLAlchemy models for the SinkIn Image Experimentation app."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Boolean,
    ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class JobStatus(enum.Enum):
    """Status options for jobs in the queue."""
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class UseAgain(enum.Enum):
    """Options for 'use again' scoring."""
    yes = "yes"
    no = "no"
    test_more = "test_more"
    top_1pct = "top_1pct"


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class Run(Base):
    """A batch experiment run with shared configuration."""
    __tablename__ = "runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    batch_number = Column(Integer, unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    model_id = Column(String(50), nullable=False)
    version = Column(String(50), nullable=True)

    # Relationships
    images = relationship("Image", back_populates="run", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="run", cascade="all, delete-orphan")


class Image(Base):
    """A generated image with metadata and scores."""
    __tablename__ = "images"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False)
    file_path = Column(String(500), nullable=True)
    upscale_url = Column(String(500), nullable=True)
    inf_id = Column(String(100), nullable=True)  # SinkIn inference ID
    batch_index = Column(Integer, nullable=True)  # Index in the batch (0-N)
    is_failed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Legacy scoring fields (kept for historical data but no longer used)
    overall_quality = Column(Integer, nullable=True)  # 1-10
    anatomy_score = Column(Integer, nullable=True)  # 1-10
    prompt_adherence = Column(Integer, nullable=True)  # 1-10
    background_score = Column(Integer, nullable=True)  # 1-10

    # New scoring system (all 1-5)
    score_overall = Column(Integer, nullable=True)
    score_facial_detail_realism = Column(Integer, nullable=True)
    score_body_proportions = Column(Integer, nullable=True)
    score_complexity_artistry = Column(Integer, nullable=True)
    score_composition_framing = Column(Integer, nullable=True)
    score_lighting_color = Column(Integer, nullable=True)
    score_resolution_clarity = Column(Integer, nullable=True)
    score_style_consistency = Column(Integer, nullable=True)
    score_prompt_adherence = Column(Integer, nullable=True)
    score_artifacts = Column(Integer, nullable=True)

    # Additional metadata
    use_again = Column(SQLEnum(UseAgain), nullable=True)
    flaws = Column(Text, nullable=True)  # JSON list of flaws tags
    curation_status = Column(String(20), nullable=True)  # "trash", "use_again", "top_1pct"

    # Relationships
    run = relationship("Run", back_populates="images")
    config = relationship("Config", back_populates="image", uselist=False, cascade="all, delete-orphan")


class Config(Base):
    """Configuration/parameters used to generate an image."""
    __tablename__ = "configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(String(36), ForeignKey("images.id"), unique=True, nullable=False)
    
    # Generation parameters
    steps = Column(Integer, nullable=True)
    scale = Column(Float, nullable=True)  # Guidance scale / CFG
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    seed = Column(Integer, nullable=True)
    scheduler = Column(String(50), nullable=True)
    image_strength = Column(Float, nullable=True)  # For img2img
    controlnet = Column(String(50), nullable=True)  # canny, depth, openpose
    
    # Cost and raw data
    credit_cost = Column(Float, nullable=True)
    raw_payload_json = Column(Text, nullable=True)  # Full request JSON
    raw_response_json = Column(Text, nullable=True)  # Full response JSON

    # Relationships
    image = relationship("Image", back_populates="config")


class Asset(Base):
    """Uploaded files (init images for img2img)."""
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=True)
    file_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    jobs = relationship("Job", back_populates="init_image_asset")


class Job(Base):
    """Queue item for pending image generation."""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.queued, nullable=False)
    config_json = Column(Text, nullable=False)  # Job configuration as JSON
    init_image_asset_id = Column(String(36), ForeignKey("assets.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    run = relationship("Run", back_populates="jobs")
    init_image_asset = relationship("Asset", back_populates="jobs")
