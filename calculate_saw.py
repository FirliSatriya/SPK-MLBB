"""
Script untuk menghitung skor SAW (Simple Additive Weighting)
dengan bobot AHP (Analytical Hierarchy Process) dari data expert.
Menghasilkan Top 10 hero per role/lane.

Sumber data: Neon Postgres (lewat db.py). DATABASE_URL harus diset di .env.
"""

import os
import sys
import math

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from db import Hero, HeroScore, AHPMatrix, get_session, DB_ENABLED


ROLES = ["JUNGLING", "MID LANE", "EXP LANE", "GOLD LANE", "ROAMING"]
CRITERIA_ORDER = ["Difficulty", "Crowd Control", "Mobility", "Utility", "Durability", "Offense"]
ATTRIBUTE_TYPES = {
    "Difficulty": "cost",
    "Crowd Control": "benefit",
    "Mobility": "benefit",
    "Utility": "benefit",
    "Durability": "benefit",
    "Offense": "benefit",
}
RI_TABLE = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


# ============================================================
# DATA LOADING — dari Neon Postgres
# ============================================================
def load_heroes_from_db(session):
    heroes = {}
    for h in session.query(Hero).order_by(Hero.id).all():
        heroes[h.id] = {
            "id": h.id,
            "nama": h.name,
            "class": h.hero_class,
            "role": [r for r in (h.roles or [])],
        }
    return heroes


def load_scores_from_db(session):
    scores = {}
    for row in session.query(HeroScore).all():
        scores.setdefault(row.hero_id, {})[row.criterion] = float(row.value)
    return scores


def load_ahp_matrices_from_db(session):
    matrices = {r: [] for r in ROLES}
    rows = session.query(AHPMatrix).order_by(AHPMatrix.role, AHPMatrix.evaluator_idx).all()
    grouped = {}
    for r in rows:
        if r.role not in matrices:
            continue
        grouped.setdefault(r.role, []).append((r.evaluator_idx, r.matrix))
    for role, items in grouped.items():
        items.sort(key=lambda x: x[0])
        matrices[role] = [m for _, m in items]
    return matrices


# ============================================================
# AHP — agregasi & perhitungan
# ============================================================
def geometric_mean_matrices(matrices):
    n = len(matrices[0])
    k = len(matrices)
    result = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            product = 1.0
            for m in matrices:
                product *= m[i][j]
            result[i][j] = product ** (1.0 / k)
    return result


def calculate_ahp(matrix):
    n = len(matrix)
    col_sums = [sum(matrix[i][j] for i in range(n)) for j in range(n)]
    norm = [[matrix[i][j] / col_sums[j] for j in range(n)] for i in range(n)]
    weights = [sum(norm[i][j] for j in range(n)) / n for i in range(n)]
    aw = [sum(matrix[i][j] * weights[j] for j in range(n)) for i in range(n)]
    lambdas = [aw[i] / weights[i] if weights[i] > 0 else 0 for i in range(n)]
    lambda_max = sum(lambdas) / n
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0
    ri = RI_TABLE.get(n, 1.49)
    cr = ci / ri if ri > 0 else 0
    is_consistent = cr <= 0.10
    return weights, lambda_max, ci, cr, is_consistent


# ============================================================
# SAW
# ============================================================
def calculate_saw(hero_ids, scores, weights, attribute_types):
    criteria = CRITERIA_ORDER
    decision_matrix = {}
    for hid in hero_ids:
        if hid in scores:
            decision_matrix[hid] = [scores[hid].get(c, 0) for c in criteria]
    if not decision_matrix:
        return []
    hero_list = list(decision_matrix.keys())
    n_criteria = len(criteria)
    max_vals = [max(decision_matrix[hid][j] for hid in hero_list) for j in range(n_criteria)]
    min_vals = [min(decision_matrix[hid][j] for hid in hero_list) for j in range(n_criteria)]
    normalized = {}
    for hid in hero_list:
        norm_row = []
        for j in range(n_criteria):
            c = criteria[j]
            x = decision_matrix[hid][j]
            if attribute_types[c] == "benefit":
                r = x / max_vals[j] if max_vals[j] > 0 else 0
            else:
                r = min_vals[j] / x if x > 0 else 0
            norm_row.append(r)
        normalized[hid] = norm_row
    results = []
    for hid in hero_list:
        vi = sum(weights[j] * normalized[hid][j] for j in range(n_criteria))
        results.append((hid, vi, normalized[hid], decision_matrix[hid]))
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def get_heroes_by_role(heroes):
    role_heroes = {r: [] for r in ROLES}
    for hid, hero in heroes.items():
        for role in hero["role"]:
            role_upper = role.upper().strip()
            if role_upper in role_heroes:
                role_heroes[role_upper].append(hid)
    return role_heroes


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 80)
    print("  PERHITUNGAN SPK DRAFT PICK MLBB — AHP-SAW")
    print("=" * 80)

    if not DB_ENABLED:
        print("\nERROR: DATABASE_URL tidak diset atau SQLAlchemy/psycopg2 belum terpasang.")
        print("Set DATABASE_URL di .env lalu jalankan ulang.")
        sys.exit(1)

    session = get_session()
    if session is None:
        print("\nERROR: Tidak bisa membuka session DB.")
        sys.exit(1)

    try:
        print("\n[1] Loading data hero dari DB...")
        heroes = load_heroes_from_db(session)
        print(f"    Total hero: {len(heroes)}")
        if not heroes:
            print("    DB kosong. Jalankan `python migrate.py` dulu (perlu CSV).")
            sys.exit(1)

        print("\n[2] Loading skor kriteria dari DB...")
        scores = load_scores_from_db(session)
        sample_id = next(iter(heroes))
        print(f"    Sample — {heroes[sample_id]['nama']}:")
        for c in CRITERIA_ORDER:
            print(f"      {c}: {scores.get(sample_id, {}).get(c, 0):.2f}")

        print("\n[3] Loading matriks AHP dari DB...")
        ahp_matrices = load_ahp_matrices_from_db(session)
        for role, mats in ahp_matrices.items():
            print(f"    {role}: {len(mats)} expert matrices")
    finally:
        session.close()

    print("\n[4] Aggregasi & perhitungan AHP per role...")
    print("-" * 80)

    role_weights = {}
    for role in ROLES:
        mats = ahp_matrices[role]
        if not mats:
            print(f"\n  {role}: Tidak ada matriks!")
            continue
        agg_matrix = geometric_mean_matrices(mats) if len(mats) > 1 else mats[0]
        weights, lambda_max, ci, cr, is_consistent = calculate_ahp(agg_matrix)
        role_weights[role] = weights

        status = "[OK] KONSISTEN" if is_consistent else "[X] TIDAK KONSISTEN"
        print(f"\n  {'=' * 60}")
        print(f"  ROLE: {role} ({len(mats)} expert) — {status}")
        print(f"  {'=' * 60}")
        print(f"  lambda_max = {lambda_max:.4f}")
        print(f"  CI   = {ci:.4f}")
        print(f"  CR   = {cr:.4f} (threshold <= 0.10)")
        print(f"  {'-' * 60}")
        print(f"  {'Kriteria':<20} {'Bobot':>10} {'Persentase':>12}")
        print(f"  {'-' * 60}")
        for i, c in enumerate(CRITERIA_ORDER):
            print(f"  {c:<20} {weights[i]:>10.6f} {weights[i] * 100:>11.2f}%")
        print(f"  {'-' * 60}")
        print(f"  Total: {sum(weights):>29.6f}")

    role_heroes = get_heroes_by_role(heroes)

    print("\n\n" + "=" * 80)
    print("  HASIL PERANGKINGAN SAW — TOP 10 PER ROLE")
    print("=" * 80)

    for role in ROLES:
        if role not in role_weights:
            continue
        weights = role_weights[role]
        hero_ids = role_heroes[role]
        results = calculate_saw(hero_ids, scores, weights, ATTRIBUTE_TYPES)

        print(f"\n  {'=' * 76}")
        print(f"  >> TOP 10 -- {role} ({len(hero_ids)} hero kandidat)")
        print(f"  {'=' * 76}")
        print(f"  {'Rank':<6} {'Hero':<18} {'Class':<22} {'Vi':>8} {'Diff':>6} {'CC':>6} {'Mob':>6} {'Util':>6} {'Dur':>6} {'Off':>6}")
        print(f"  {'-' * 76}")

        for rank, (hid, vi, norm_scores, raw_scores) in enumerate(results[:10], 1):
            hero = heroes[hid]
            print(f"  {rank:<6} {hero['nama']:<18} {hero['class']:<22} {vi:>7.4f}"
                  f" {raw_scores[0]:>5.2f} {raw_scores[1]:>5.2f} {raw_scores[2]:>5.2f}"
                  f" {raw_scores[3]:>5.2f} {raw_scores[4]:>5.2f} {raw_scores[5]:>5.2f}")

        print(f"  {'-' * 76}")

        if results:
            max_vi = results[0][1]
            print(f"\n  Vi sebagai persentase (relatif terhadap Vi tertinggi):")
            print(f"  {'Rank':<6} {'Hero':<18} {'Vi':>10} {'Vi %':>8}")
            print(f"  {'-' * 45}")
            for rank, (hid, vi, _, _) in enumerate(results[:10], 1):
                pct = (vi / max_vi * 100) if max_vi > 0 else 0
                print(f"  {rank:<6} {heroes[hid]['nama']:<18} {vi:>10.6f} {pct:>7.2f}%")

    print("\n" + "=" * 80)
    print("  PERHITUNGAN SELESAI")
    print("=" * 80)


if __name__ == "__main__":
    main()
