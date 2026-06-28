import os
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./grants.db")

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _migrate()


def _migrate():
    """Add columns that did not exist in earlier schema versions."""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE searchjob ADD COLUMN search_type TEXT DEFAULT 'full'"))
            conn.commit()
        except Exception:
            pass  # Column already exists


def get_session():
    with Session(engine) as session:
        yield session
