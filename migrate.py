"""
One-time migration: CSV files → Neon Postgres.
Usage:
    1. Set DATABASE_URL in .env
    2. python migrate.py
    3. Re-run is idempotent: existing heroes/scores/matrices are UPSERTed.
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()

if not os.environ.get("DATABASE_URL"):
    print("ERROR: DATABASE_URL is not set. Put it in .env and re-run.")
    sys.exit(1)

import db as dbmod
from db import Hero, HeroScore, AHPMatrix, get_session, init_db
from app import load_heroes, load_scores, load_ahp_matrices, ROLES, CRITERIA_ORDER

def main():
    print("[migrate] Creating tables...")
    init_db()

    heroes = load_heroes()
    scores = load_scores()
    matrices = load_ahp_matrices()

    s = get_session()
    try:
        # Heroes + Scores
        print(f"[migrate] Upserting {len(heroes)} heroes...")
        for h in heroes:
            existing = s.get(Hero, h["id"])
            if existing:
                existing.name = h["name"]
                existing.hero_class = h["class"]
                existing.roles = h["roles"]
            else:
                s.add(Hero(id=h["id"], name=h["name"], hero_class=h["class"], roles=h["roles"]))

            for c in CRITERIA_ORDER:
                v = float(scores.get(h["id"], {}).get(c, 0))
                row = (s.query(HeroScore)
                       .filter_by(hero_id=h["id"], criterion=c).one_or_none())
                if row:
                    row.value = v
                else:
                    s.add(HeroScore(hero_id=h["id"], criterion=c, value=v))

        # AHP matrices (up to 3 per role)
        print("[migrate] Upserting AHP matrices...")
        for role in ROLES:
            mats = matrices.get(role, [])
            for idx, m in enumerate(mats):
                row = (s.query(AHPMatrix)
                       .filter_by(role=role, evaluator_idx=idx).one_or_none())
                if row:
                    row.matrix = m
                else:
                    s.add(AHPMatrix(role=role, evaluator_idx=idx, matrix=m))

        s.commit()
        print("[migrate] Migration complete.")
    except Exception as e:
        s.rollback()
        print(f"[migrate] Migration failed: {e}")
        raise
    finally:
        s.close()

if __name__ == "__main__":
    main()
