"""
Diagnostik DB step-by-step. Tunjukkan tepat di mana titik kegagalannya
dan otomatis test alternatif (non-pooler URL Neon).

Usage:
    python diagnose.py
"""
import os, sys, time, traceback

print("=" * 70)
print(" DIAGNOSTIK DB SPK MLBB")
print("=" * 70)

# 1. dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[1] dotenv loaded OK")
except Exception as e:
    print(f"[1] dotenv error: {e}")

# 2. URL
url = os.environ.get("DATABASE_URL", "")
print(f"[2] DATABASE_URL set? {'YES' if url else 'NO'}")
if not url:
    print("    -> Stop. Set DATABASE_URL di .env dulu.")
    sys.exit(1)
safe = url[:35] + "..." + url[-40:] if len(url) > 80 else url
print(f"    URL preview: {safe}")
is_pooler = "-pooler" in url
print(f"    Pakai pooler? {'YES' if is_pooler else 'NO'}")

# 3. Libs
try:
    import sqlalchemy, psycopg2
    print(f"[3] sqlalchemy {sqlalchemy.__version__}, psycopg2 {psycopg2.__version__}")
except ImportError as e:
    print(f"[3] Import error: {e}")
    print("    -> pip install sqlalchemy psycopg2-binary python-dotenv")
    sys.exit(1)

# 4. Connect via db.get_engine (yang sudah pakai connect_args resilient)
from sqlalchemy import text, create_engine
from sqlalchemy.exc import OperationalError, DBAPIError
from db import get_engine, get_session, init_db, Hero, HeroScore, AHPMatrix


def try_connect(eng, label):
    for attempt in range(1, 4):
        try:
            print(f"[connect/{label}] attempt {attempt}/3...", end=" ", flush=True)
            with eng.connect() as c:
                ver = c.execute(text("SELECT version()")).scalar()
            print("OK")
            print(f"    Postgres: {ver[:70]}")
            return True
        except (OperationalError, DBAPIError) as e:
            msg = str(e).split("\n", 1)[0]
            print(f"FAIL: {msg[:140]}")
            time.sleep(3 * attempt)
    return False


print("[4] Test koneksi primary (lewat db.get_engine)...")
eng = get_engine()
ok = try_connect(eng, "primary")

if not ok and is_pooler:
    print("[4b] Pooler gagal. Coba non-pooler URL otomatis...")
    alt_url = url.replace("-pooler", "")
    alt_eng = create_engine(
        alt_url, pool_pre_ping=True, future=True,
        connect_args={
            "connect_timeout": 30, "keepalives": 1,
            "keepalives_idle": 30, "keepalives_interval": 10, "keepalives_count": 5,
        },
    )
    if try_connect(alt_eng, "non-pooler"):
        print()
        print("    !!! Non-pooler URL berhasil. Pooler-nya yang bermasalah.")
        print("    !!! Edit .env, ganti DATABASE_URL dengan versi tanpa '-pooler':")
        print(f"    DATABASE_URL={alt_url}")
        sys.exit(0)
    print("[4c] Non-pooler juga gagal. Cek: jaringan/firewall, kredensial, status Neon.")
    sys.exit(1)
elif not ok:
    print("    Cek: jaringan/firewall, kredensial, status Neon (https://console.neon.tech).")
    sys.exit(1)

# 5. Tables
print("[5] init_db() ...")
try:
    init_db()
    print("    OK (tabel sudah ada / dibuat)")
except Exception as e:
    print(f"    FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

# 6. Counts
print("[6] Hitung baris di tiap tabel...")
s = get_session()
try:
    h = s.query(Hero).count()
    sc = s.query(HeroScore).count()
    a = s.query(AHPMatrix).count()
    print(f"    heroes={h}, hero_scores={sc}, ahp_matrices={a}")
    last = s.query(Hero).order_by(Hero.id.desc()).limit(5).all()
    print(f"    Last 5 hero IDs: {[x.id for x in last]}")
finally:
    s.close()

print()
print("=" * 70)
print(" DIAGNOSIS OK. Sekarang jalankan: python migrate.py")
print("=" * 70)
