"""
Database layer untuk SPK Draft Pick MLBB.

Backend: Neon Postgres (via DATABASE_URL di .env).
- Coba endpoint pooler dulu (umum pakai `-pooler` di hostname)
- Kalau pooler timeout, otomatis coba endpoint non-pooler (Neon punya dua)
- Connect args sudah tahan cold-start (timeout 30s + TCP keepalive)

App DB-only. Tanpa fallback lokal. Pastikan jaringan Anda bisa reach Neon
di port 5432 (kalau wifi/kampus blok, pakai VPN seperti Cloudflare WARP).
"""
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

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
        id = Column(String(8), primary_key=True)
        name = Column(String(64), nullable=False)
        hero_class = Column(String(64), nullable=False)
        roles = Column(JSON, nullable=False, default=list)
        image_url = Column(String(512), nullable=True)
        image_public_id = Column(String(255), nullable=True)
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
        criterion = Column(String(32), nullable=False)
        value = Column(Float, nullable=False, default=0.0)
        hero = relationship("Hero", back_populates="scores")
        __table_args__ = (UniqueConstraint("hero_id", "criterion", name="uq_hero_criterion"),)


    class AHPMatrix(Base):
        __tablename__ = "ahp_matrices"
        id = Column(Integer, primary_key=True, autoincrement=True)
        role = Column(String(32), nullable=False)
        evaluator_idx = Column(Integer, nullable=False, default=0)
        matrix = Column(JSON, nullable=False)
        updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
        __table_args__ = (UniqueConstraint("role", "evaluator_idx", name="uq_role_evaluator"),)


    class User(Base):
        """Admin user. Password disimpan sebagai bcrypt hash."""
        __tablename__ = "users"
        id = Column(Integer, primary_key=True, autoincrement=True)
        username = Column(String(64), nullable=False, unique=True)
        password_hash = Column(String(255), nullable=False)
        created_at = Column(DateTime, server_default=func.now())
        updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
else:
    class _Stub: pass
    Hero = HeroScore = AHPMatrix = User = _Stub


# ---------------------------------------------------------------
# Engine / session
# ---------------------------------------------------------------
_engine = None
_Session = None

_CONNECT_ARGS = {
    "connect_timeout": 30,
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
}


def _build_engine(url):
    return create_engine(
        url, pool_pre_ping=True, pool_recycle=300, future=True,
        connect_args=_CONNECT_ARGS,
    )


def get_engine():
    """Engine builder dengan auto-fallback pooler -> non-pooler (Neon)."""
    global _engine
    if not DB_ENABLED:
        return None
    if _engine is not None:
        return _engine

    eng = _build_engine(DATABASE_URL)
    try:
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        _engine = eng
        return _engine
    except Exception as e_pooler:
        if "-pooler" not in DATABASE_URL:
            raise
        alt_url = DATABASE_URL.replace("-pooler", "")
        print(f"[db] Pooler timeout ({str(e_pooler)[:80]}...). Coba non-pooler endpoint.")
        eng2 = _build_engine(alt_url)
        with eng2.connect() as c:
            c.execute(text("SELECT 1"))
        print("[db] Non-pooler OK. Pakai endpoint ini.")
        _engine = eng2
        return _engine


def get_session():
    """Caller is responsible for closing. Returns None when DB is not configured."""
    global _Session
    if not DB_ENABLED:
        return None
    if _Session is None:
        _Session = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    return _Session()


def init_db(retries=3, base_delay=3):
    """Create tables if they don't exist. Retry beberapa kali untuk Neon cold-start."""
    if not DB_ENABLED:
        return False
    import time
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(get_engine())
            return True
        except Exception as e:
            last_err = e
            print(f"[db] init_db attempt {attempt}/{retries} failed: {str(e)[:100]}")
            if attempt < retries:
                time.sleep(base_delay * attempt)
    raise last_err


def db_has_data():
    """True if heroes table has any rows."""
    if not DB_ENABLED:
        return False
    with get_engine().connect() as c:
        return (c.execute(text("SELECT COUNT(*) FROM heroes")).scalar() or 0) > 0
