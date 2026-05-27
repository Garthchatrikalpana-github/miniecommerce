from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # detect stale connections
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """
    Dependency that yields a DB session and guarantees it is closed.
    BUG FIX: original code used SessionLocal() directly with no cleanup,
    causing connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
