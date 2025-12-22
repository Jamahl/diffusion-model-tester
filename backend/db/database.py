"""SQLite database connection and session management."""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# Database file path (relative to backend directory)
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "experiments.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine with SQLite-specific settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite with FastAPI
    echo=False,  # Set to True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI routes to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_images_columns() -> None:
    """Add newly introduced columns to existing SQLite databases when missing."""
    columns_to_add = [
        ("score_overall", "INTEGER"),
        ("score_facial_detail_realism", "INTEGER"),
        ("score_body_proportions", "INTEGER"),
        ("score_complexity_artistry", "INTEGER"),
        ("score_composition_framing", "INTEGER"),
        ("score_lighting_color", "INTEGER"),
        ("score_resolution_clarity", "INTEGER"),
        ("score_style_consistency", "INTEGER"),
        ("score_prompt_adherence", "INTEGER"),
        ("score_artifacts", "INTEGER"),
        ("use_again", "TEXT"),
        ("flaws", "TEXT"),
        ("curation_status", "VARCHAR(20)"),
        ("is_failed", "BOOLEAN NOT NULL DEFAULT 0"),
        ("batch_index", "INTEGER"),
    ]

    with engine.begin() as conn:
        result = conn.execute(text("PRAGMA table_info('images')"))
        existing_columns = {row[1] for row in result.fetchall()}

        for name, ddl in columns_to_add:
            if name not in existing_columns:
                conn.execute(text(f"ALTER TABLE images ADD COLUMN {name} {ddl}"))
                print(f"🛠️ Added missing column to images table: {name}")


def init_db() -> None:
    """Initialize the database by creating all tables."""
    from .models import Base
    Base.metadata.create_all(bind=engine)
    _ensure_images_columns()
    print(f"✅ Database initialized at: {DATABASE_PATH}")
