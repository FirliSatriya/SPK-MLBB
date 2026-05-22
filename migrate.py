"""
One-time migration: CSV files -> Neon Postgres.

Strategi tahan-banting (Neon bisa cold-start / pooler bisa flaky):
- Cek koneksi dengan retry sebelum mulai
- Commit per-hero (transaksi kecil), bukan satu transaksi besar
- Skip + log hero yang gagal, lanjut hero berikutnya supaya progress tidak hilang
- Tampilkan progress tiap baris

Usage:
    1. Pastikan file CSV (`AHP-SAW - *.csv`) ada di direktori ini.
    2. Set DATABASE_URL di .env
    3. python migrate.py
    4. Re-run aman (UPSERT) -- bisa dipanggil berkali-kali sampai count match.

Catatan: app.py sekarang DB-only dan TIDAK lagi membutuhkan CSV. Script ini
dipanggil manual hanya jika perlu seed / re-seed.
"""
import os, sys, csv, time
from dotenv import load_dotenv
load_dotenv()

if not os.environ.get("DATABASE_URL"):
    print("ERROR: DATABASE_URL is not set. Put it in .env and re-run.")
    sys.exit(1)

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DBAPIError

import db as dbmod
from db import Hero, HeroScore, AHPMatrix, get_engine, get_session, init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ROLES = ["JUNGLING", "MID LANE", "EXP LANE", "ROAMING", "GOLD LANE"]
CRITERIA_ORDER = ["Difficulty", "Crowd Control", "Mobility", "Utility", "Durability", "Offense"]
CRITERIA_FILES = {
    "Difficulty": ("AHP-SAW - DIFFICULTY.csv", ["COMPLEXITY", "TIMING PRECISSION", "POSITIONING REQUIREMENT", "DECISION COMPLEXITY"]),
    "Crowd Control": ("AHP-SAW - CROWD CONTROL.csv", ["TYPE STRENGHT", "RELIABILITY", "AREA COVERAGE", "CHAIN / FREQUENCY"]),
    "Mobility": ("AHP-SAW - MOBILITY.csv", ["DASH/BLINK", "ROTATION SPEED", "ESCAPE CAPABILITY", "FLEXIBILITY"]),
    "Utility": ("AHP-SAW - UTILITY.csv", ["TEAM SUPPORT", "ZONING / CONTROL", "DISRUPTION", "PROTECTION"]),
    "Durability": ("AHP-SAW - DURABILITY.csv", ["BASE TANKINESS", "SUSTAIN/REGEN", "DAMAGE MITIGATION", "SURVIVAL TOOLS"]),
    "Offense": ("AHP-SAW - OFFENSE.csv", ["DAMAGE", "KILL THREAT/BURST", "SUSTAINED DPS", "OBJECTIVE PRESSURE"]),
}


def _require_csv(path):
    if not os.path.exists(path):
        print(f"ERROR: CSV tidak ditemukan: {path}")
        print("Restore CSV dari git history terlebih dulu sebelum re-seed.")
        sys.exit(1)


def load_heroes():
    path = os.path.join(BASE_DIR, "AHP-SAW - DATA HERO.csv")
    _require_csv(path)
    heroes = []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            heroes.append({
                "id": row["ID_HERO"].strip(),
                "name": row["NAMA_HERO"].strip(),
                "class": row["CLASS"].strip(),
                "roles": [r.strip().upper() for r in row["ROLE"].split(",") if r.strip()],
            })
    return heroes


def load_scores():
    scores = {}
    for cname, (fname, cols) in CRITERIA_FILES.items():
        path = os.path.join(BASE_DIR, fname)
        _require_csv(path)
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                hid = row["ID_HERO"].strip()
                if hid not in scores:
                    scores[hid] = {}
                vals = [float(row[c].strip()) for c in cols if row.get(c, "").strip()]
                scores[hid][cname] = round(sum(vals) / len(vals), 4) if vals else 0
    return scores


def parse_frac(v):
    v = str(v).strip()
    if not v:
        return None
    if "/" in v:
        p = v.split("/")
        return float(p[0]) / float(p[1])
    return float(v)


def load_ahp_matrices():
    path = os.path.join(BASE_DIR, "AHP-SAW - DISINI.csv")
    _require_csv(path)
    matrices = {r: [] for r in ROLES}
    with open(path, encoding="utf-8-sig") as f:
        lines = list(csv.reader(f))

    def extract(start, col_off):
        m = []
        for i in range(6):
            row = []
            for j in range(6):
                ci = col_off + 1 + j
                row.append(parse_frac(lines[start + i][ci])
                           if start + i < len(lines) and ci < len(lines[start + i]) else None)
            m.append(row)
        for i in range(6):
            for j in range(6):
                if m[i][j] is None and m[j][i] is not None:
                    m[i][j] = 1.0 / m[j][i]
                elif m[i][j] is None and i == j:
                    m[i][j] = 1.0
        return m

    blocks = [(2, 0, "JUNGLING"), (11, 0, "JUNGLING"), (20, 0, "JUNGLING"),
              (29, 0, "MID LANE"), (38, 0, "MID LANE"), (47, 0, "MID LANE"),
              (56, 0, "GOLD LANE"), (65, 0, "GOLD LANE"), (74, 0, "GOLD LANE"),
              (2, 9, "EXP LANE"), (11, 9, "EXP LANE"), (20, 9, "EXP LANE"),
              (29, 9, "ROAMING"), (38, 9, "ROAMING"), (47, 9, "ROAMING")]
    for s, c, r in blocks:
        m = extract(s, c)
        if all(m[i][j] is not None for i in range(6) for j in range(6)):
            matrices[r].append(m)
    return matrices


# ---------------------------------------------------------------
# Resilient DB helpers
# ---------------------------------------------------------------
def wait_for_db(max_attempts=5, base_delay=3):
    """Ping DB sampai sukses. Neon cold-start bisa makan 5-15 detik."""
    eng = get_engine()
    if eng is None:
        print("ERROR: get_engine() return None (SQLAlchemy belum terpasang?).")
        sys.exit(1)
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"[connect] Attempt {attempt}/{max_attempts}...", end=" ", flush=True)
            with eng.connect() as c:
                c.execute(text("SELECT 1"))
            print("OK")
            return True
        except (OperationalError, DBAPIError) as e:
            msg = str(e).split("\n", 1)[0]
            print(f"FAILED: {msg[:120]}")
            if attempt < max_attempts:
                delay = base_delay * attempt
                print(f"[connect] Wait {delay}s before retry...")
                time.sleep(delay)
            else:
                print("[connect] Semua attempt habis. Cek DATABASE_URL & jaringan.")
                return False


def upsert_one_hero(session, h, scores):
    """Commit per-hero supaya kalau ada error, hero lain tetap masuk."""
    existing = session.get(Hero, h["id"])
    if existing:
        existing.name = h["name"]
        existing.hero_class = h["class"]
        existing.roles = h["roles"]
    else:
        session.add(Hero(id=h["id"], name=h["name"], hero_class=h["class"], roles=h["roles"]))
    for c in CRITERIA_ORDER:
        v = float(scores.get(h["id"], {}).get(c, 0))
        row = (session.query(HeroScore)
               .filter_by(hero_id=h["id"], criterion=c).one_or_none())
        if row:
            row.value = v
        else:
            session.add(HeroScore(hero_id=h["id"], criterion=c, value=v))
    session.commit()


def upsert_one_matrix(session, role, idx, matrix):
    row = (session.query(AHPMatrix)
           .filter_by(role=role, evaluator_idx=idx).one_or_none())
    if row:
        row.matrix = matrix
    else:
        session.add(AHPMatrix(role=role, evaluator_idx=idx, matrix=matrix))
    session.commit()


def main():
    print("=" * 70)
    print(" MIGRATE CSV -> NEON POSTGRES")
    print("=" * 70)

    if not wait_for_db():
        sys.exit(1)

    print("[init] Creating tables (jika belum ada)...")
    try:
        init_db()
    except Exception as e:
        print(f"[init] init_db() FAILED: {e}")
        sys.exit(1)

    heroes = load_heroes()
    scores = load_scores()
    matrices = load_ahp_matrices()
    print(f"[load] CSV: {len(heroes)} heroes, "
          f"{sum(len(v) for v in scores.values())} score rows, "
          f"{sum(len(v) for v in matrices.values())} AHP matrices")

    # --- Heroes + Scores (commit per hero) ---
    print(f"\n[heroes] Upserting {len(heroes)} heroes (commit per row)...")
    ok, fail = 0, 0
    failed_ids = []
    for i, h in enumerate(heroes, 1):
        s = get_session()
        try:
            upsert_one_hero(s, h, scores)
            ok += 1
            if i % 10 == 0 or i == len(heroes):
                print(f"  [{i:>3}/{len(heroes)}] OK={ok} FAIL={fail}")
        except Exception as e:
            s.rollback()
            fail += 1
            failed_ids.append(h["id"])
            print(f"  [{i:>3}/{len(heroes)}] FAIL {h['id']} ({h['name']}): {str(e)[:100]}")
        finally:
            s.close()

    # --- AHP matrices ---
    print(f"\n[ahp] Upserting AHP matrices per role...")
    mat_ok, mat_fail = 0, 0
    for role in ROLES:
        mats = matrices.get(role, [])
        for idx, m in enumerate(mats):
            s = get_session()
            try:
                upsert_one_matrix(s, role, idx, m)
                mat_ok += 1
                print(f"  {role} [{idx}] OK")
            except Exception as e:
                s.rollback()
                mat_fail += 1
                print(f"  {role} [{idx}] FAIL: {str(e)[:100]}")
            finally:
                s.close()

    # --- Final counts ---
    s = get_session()
    try:
        h_total = s.query(Hero).count()
        sc_total = s.query(HeroScore).count()
        a_total = s.query(AHPMatrix).count()
    finally:
        s.close()

    print("\n" + "=" * 70)
    print(" RESULT")
    print("=" * 70)
    print(f" Heroes        : OK={ok}  FAIL={fail}  -> DB total now: {h_total}")
    print(f" AHP matrices  : OK={mat_ok}  FAIL={mat_fail}  -> DB total now: {a_total}")
    print(f" Score rows    : DB total now: {sc_total}")
    if failed_ids:
        print(f" Failed hero IDs: {failed_ids}")
        print(" -> Re-run `python migrate.py` untuk retry yang gagal.")
        sys.exit(2)
    if h_total < len(heroes):
        print(f" WARNING: DB punya {h_total} hero, CSV {len(heroes)}. Re-run migrate.py.")
        sys.exit(2)
    print(" Migration complete. DB sudah sinkron dengan CSV.")


if __name__ == "__main__":
    main()
