"""
Database layer — Neon Postgres via SQLAlchemy.
Falls back to CSV-loaded in-memory data when DATABASE_URL is not set OR when
SQLAlchemy/psycopg2 packages aren't installed yet, so the app keeps running
before Neon credentials are wired up.
"""
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# Try to import SQLAlchemy. If it's not installed yet, disable DB cleanly.
try:
    from sqlalchemy import (
        create_engine, Column, String, Float, Integer, JSON, DateTime, ForeignKey,
        UniqueConstraint, text, func,
    )
    from sqlalchemy.orm import declarative_base, sessionmaker, relationship
    _SQLA_OK = True
except ImportError:
    _SQLA_OK = False

DB_ENABLED = bool(DATABASE_URL) and _SQLA_OK

# ---------------------------------------------------------------
# Models
# ---------------------------------------------------------------
if _SQLA_OK:
    Base = declarative_base()

    class Hero(Base):
        __tablename__ = "heroes"
        id = Column(String(8), primary_key=True)       # e.g. "H001"
        name = Column(String(64), nullable=False)
        hero_class = Column(String(64), nullable=False)  # "Mage/Tank" allowed
        roles = Column(JSON, nullable=False, default=list)  # ["JUNGLING", ...]
        image_url = Column(String(512), nullable=True)      # Cloudinary URL
        image_public_id = Column(String(255), nullable=True) # for deletion
        created_at = Column(DateTime, server_default=func.now())
        updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

        scores = relationship("HeroScore", back_populates="hero", cascade="all, delete-orphan")

        def to_dict(self):
            return {
                "id": self.id,
                "name": self.name,
                "class": self.hero_class,
                "roles": self.roles or [],
                "image_url": self.image_url,
                "image_public_id": self.image_public_id,
                "scores": {s.criterion: s.value for s in (self.scores or [])},
            }


    class HeroScore(Base):
        __tablename__ = "hero_scores"
        id = Column(Integer, primary_key=True, autoincrement=True)
        hero_id = Column(String(8), ForeignKey("heroes.id", ondelete="CASCADE"), nullable=False)
        criterion = Column(String(32), nullable=False)  # e.g. "Difficulty"
        value = Column(Float, nullable=False, default=0.0)
        hero = relationship("Hero", back_populates="scores")
        __table_args__ = (UniqueConstraint("hero_id", "criterion", name="uq_hero_criterion"),)


    class AHPMatrix(Base):
        """One row per (role, evaluator index). matrix stored as JSON (list of 6 lists of 6 floats)."""
        __tablename__ = "ahp_matrices"
        id = Column(Integer, primary_key=True, autoincrement=True)
        role = Column(String(32), nullable=False)
        evaluator_idx = Column(Integer, nullable=False, default=0)
        matrix = Column(JSON, nullable=False)
        updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
        __table_args__ = (UniqueConstraint("role", "evaluator_idx", name="uq_role_evaluator"),)
else:
    # Stub classes so callers can still `from db import Hero` without ImportError
    class _Stub: pass
    Hero = HeroScore = AHPMatrix = _Stub


# ---------------------------------------------------------------
# Engine / session
# ---------------------------------------------------------------
_engine = None
_Session = None

def get_engine():
    global _engine
    if not DB_ENABLED:
        return None
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300, future=True)
    return _engine

def get_session():
    """Caller is responsible for closing. Returns None when DB is not configured."""
    global _Session
    if not DB_ENABLED:
        return None
    if _Session is None:
        _Session = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    return _Session()

def init_db():
    """Create tables if they don't exist. No-op when DB not configured."""
    if not DB_ENABLED:
        return False
    Base.metadata.create_all(get_engine())
    return True

def db_has_data():
    """True if heroes table has any rows."""
    if not DB_ENABLED:
        return False
    with get_engine().connect() as c:
        return (c.execute(text("SELECT COUNT(*) FROM heroes")).scalar() or 0) > 0
