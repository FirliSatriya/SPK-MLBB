"""
Script untuk menghitung skor SAW (Simple Additive Weighting)
dengan bobot AHP (Analytical Hierarchy Process) dari data expert.
Menghasilkan Top 10 hero per role/lane.
"""

import csv
import math
import os
from fractions import Fraction

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 1. LOAD DATA HERO
# ============================================================
def load_heroes():
    """Load hero data dari CSV."""
    heroes = {}
    path = os.path.join(BASE_DIR, "AHP-SAW - DATA HERO.csv")
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hid = row["ID_HERO"].strip()
            heroes[hid] = {
                "id": hid,
                "nama": row["NAMA_HERO"].strip(),
                "class": row["CLASS"].strip(),
                "role": [r.strip() for r in row["ROLE"].split(",")],
            }
    return heroes

# ============================================================
# 2. LOAD RATING SUBKRITERIA & HITUNG SKOR KRITERIA UTAMA
# ============================================================
CRITERIA_FILES = {
    "Difficulty":     ("AHP-SAW - DIFFICULTY.csv",     ["COMPLEXITY", "TIMING PRECISSION", "POSITIONING REQUIREMENT", "DECISION COMPLEXITY"]),
    "Crowd Control":  ("AHP-SAW - CROWD CONTROL.csv",  ["TYPE STRENGHT", "RELIABILITY", "AREA COVERAGE", "CHAIN / FREQUENCY"]),
    "Mobility":       ("AHP-SAW - MOBILITY.csv",       ["DASH/BLINK", "ROTATION SPEED", "ESCAPE CAPABILITY", "FLEXIBILITY"]),
    "Utility":        ("AHP-SAW - UTILITY.csv",         ["TEAM SUPPORT", "ZONING / CONTROL", "DISRUPTION", "PROTECTION"]),
    "Durability":     ("AHP-SAW - DURABILITY.csv",      ["BASE TANKINESS", "SUSTAIN/REGEN", "DAMAGE MITIGATION", "SURVIVAL TOOLS"]),
    "Offense":        ("AHP-SAW - OFFENSE.csv",         ["DAMAGE", "KILL THREAT/BURST", "SUSTAINED DPS", "OBJECTIVE PRESSURE"]),
}

CRITERIA_ORDER = ["Difficulty", "Crowd Control", "Mobility", "Utility", "Durability", "Offense"]
ATTRIBUTE_TYPES = {
    "Difficulty": "cost",
    "Crowd Control": "benefit",
    "Mobility": "benefit",
    "Utility": "benefit",
    "Durability": "benefit",
    "Offense": "benefit",
}

def load_criteria_scores():
    """Load rating subkriteria dan hitung skor kriteria utama (rata-rata 4 subkriteria)."""
    scores = {}  # {hero_id: {criteria_name: score}}
    
    for criteria_name, (filename, subcriteria_cols) in CRITERIA_FILES.items():
        path = os.path.join(BASE_DIR, filename)
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hid = row["ID_HERO"].strip()
                if hid not in scores:
                    scores[hid] = {}
                
                vals = []
                for col in subcriteria_cols:
                    v = row.get(col, "").strip()
                    if v:
                        vals.append(float(v))
                
                if vals:
                    scores[hid][criteria_name] = sum(vals) / len(vals)
                else:
                    scores[hid][criteria_name] = 0.0
    
    return scores

# ============================================================
# 3. LOAD & PARSE MATRIKS AHP EXPERT
# ============================================================
def parse_fraction(val):
    """Parse nilai seperti '1/3', '7', '1.5' menjadi float."""
    val = val.strip()
    if not val:
        return None
    if "/" in val:
        parts = val.split("/")
        return float(parts[0]) / float(parts[1])
    return float(val)

def load_ahp_matrices():
    """Parse matriks AHP dari DISINI.csv. Return dict {role: [matrix1, matrix2, matrix3]}."""
    path = os.path.join(BASE_DIR, "AHP-SAW - DISINI.csv")
    
    matrices = {
        "JUNGLING": [],
        "MID LANE": [],
        "EXP LANE": [],
        "GOLD LANE": [],
        "ROAMING": [],
    }
    
    with open(path, encoding="utf-8-sig") as f:
        lines = list(csv.reader(f))
    
    # Parse structure: each matrix block has a header row (role, expert name)
    # then a criteria header row, then 6 data rows
    
    # We need to find all matrix blocks. They appear in pairs (left/right columns)
    # Left columns: 0-6, Right columns: 9-15
    
    def extract_matrix(lines, start_row, col_offset):
        """Extract a 6x6 matrix from given position."""
        matrix = []
        for i in range(6):
            row_idx = start_row + i
            if row_idx >= len(lines):
                return None
            row = []
            for j in range(6):
                cell_idx = col_offset + 1 + j  # +1 to skip criteria label
                if cell_idx < len(lines[row_idx]):
                    val = parse_fraction(lines[row_idx][cell_idx])
                    row.append(val)
                else:
                    row.append(None)
            matrix.append(row)
        return matrix
    
    def fill_matrix(matrix):
        """Fill in missing values using reciprocal property: a[j][i] = 1/a[i][j]."""
        n = len(matrix)
        for i in range(n):
            for j in range(n):
                if matrix[i][j] is None and matrix[j][i] is not None:
                    matrix[i][j] = 1.0 / matrix[j][i]
                elif matrix[i][j] is None and i == j:
                    matrix[i][j] = 1.0
        return matrix
    
    # Parse left-side matrices (columns 0-6)
    # Row 0: header (expert name) -> "adrin"
    # Row 1: criteria header
    # Rows 2-7: matrix data
    
    # LEFT SIDE blocks (col_offset=0):
    # Block 1: row 2-7 -> Adrin (Jungling) - but header says just "adrin"
    # Block 2: row 11-16 -> Lazim (Jungling) - header "JUNGLING, lazim"
    # Block 3: row 20-25 -> Coach Reno (Jungling) - header "JUNGLING, coach reno"
    # Block 4: row 29-34 -> Dzaki (Midlane)
    # Block 5: row 38-43 -> Alfarisi (Midlane)
    # Block 6: row 47-52 -> Coach Reno (Midlane)
    # Block 7: row 56-61 -> Minulz (Gold Lane)
    # Block 8: row 65-70 -> Abdil (Gold Lane)
    # Block 9: row 74-79 -> Coach Reno (Gold Lane)
    
    # RIGHT SIDE blocks (col_offset=9):
    # Block 1: row 2-7 -> Fikri (Exp Lane)
    # Block 2: row 11-16 -> Alfarosi (Exp Lane)
    # Block 3: row 20-25 -> Coach Reno (Exp Lane)
    # Block 4: row 29-34 -> Irvan (Roaming)
    # Block 5: row 38-43 -> Reynaldi (Roaming)
    # Block 6: row 47-52 -> Coach Reno (Roaming)
    
    # Define block positions: (start_data_row, col_offset, role)
    blocks = [
        # Left side
        (2, 0, "JUNGLING"),    # Adrin
        (11, 0, "JUNGLING"),   # Lazim
        (20, 0, "JUNGLING"),   # Coach Reno
        (29, 0, "MID LANE"),   # Dzaki
        (38, 0, "MID LANE"),   # Alfarisi
        (47, 0, "MID LANE"),   # Coach Reno
        (56, 0, "GOLD LANE"),  # Minulz
        (65, 0, "GOLD LANE"),  # Abdil
        (74, 0, "GOLD LANE"),  # Coach Reno
        # Right side
        (2, 9, "EXP LANE"),    # Fikri
        (11, 9, "EXP LANE"),   # Alfarosi
        (20, 9, "EXP LANE"),   # Coach Reno
        (29, 9, "ROAMING"),    # Irvan
        (38, 9, "ROAMING"),    # Reynaldi
        (47, 9, "ROAMING"),    # Coach Reno
    ]
    
    for start_row, col_offset, role in blocks:
        matrix = extract_matrix(lines, start_row, col_offset)
        if matrix:
            matrix = fill_matrix(matrix)
            # Verify matrix is complete
            complete = all(matrix[i][j] is not None for i in range(6) for j in range(6))
            if complete:
                matrices[role].append(matrix)
            else:
                print(f"  WARNING: Incomplete matrix for {role} at row {start_row}, col {col_offset}")
                # Print what we got
                for i in range(6):
                    print(f"    {matrix[i]}")
    
    return matrices

# ============================================================
# 4. AGGREGATE MATRIKS AHP (GEOMETRIC MEAN)
# ============================================================
def geometric_mean_matrices(matrices):
    """Aggregate multiple pairwise comparison matrices using geometric mean."""
    n = len(matrices[0])
    k = len(matrices)
    result = [[0.0]*n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            product = 1.0
            for m in matrices:
                product *= m[i][j]
            result[i][j] = product ** (1.0 / k)
    
    return result

# ============================================================
# 5. PERHITUNGAN AHP
# ============================================================
RI_TABLE = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}

def calculate_ahp(matrix):
    """
    Hitung bobot AHP dari matriks perbandingan berpasangan.
    Return: (weights, lambda_max, CI, CR, is_consistent)
    """
    n = len(matrix)
    
    # 1. Jumlah setiap kolom
    col_sums = [sum(matrix[i][j] for i in range(n)) for j in range(n)]
    
    # 2. Normalisasi matriks
    norm = [[matrix[i][j] / col_sums[j] for j in range(n)] for i in range(n)]
    
    # 3. Bobot prioritas (rata-rata baris dari matriks normalisasi)
    weights = [sum(norm[i][j] for j in range(n)) / n for i in range(n)]
    
    # 4. Hitung lambda_max
    # AW = A × W
    aw = [sum(matrix[i][j] * weights[j] for j in range(n)) for i in range(n)]
    # lambda_i = (AW)_i / w_i
    lambdas = [aw[i] / weights[i] if weights[i] > 0 else 0 for i in range(n)]
    lambda_max = sum(lambdas) / n
    
    # 5. CI & CR
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0
    ri = RI_TABLE.get(n, 1.49)
    cr = ci / ri if ri > 0 else 0
    
    is_consistent = cr <= 0.10
    
    return weights, lambda_max, ci, cr, is_consistent

# ============================================================
# 6. PERHITUNGAN SAW
# ============================================================
def calculate_saw(hero_ids, scores, weights, attribute_types):
    """
    Hitung SAW.
    - hero_ids: list of hero IDs to rank
    - scores: {hero_id: {criteria: score}}
    - weights: list of weights for each criteria (same order as CRITERIA_ORDER)
    - attribute_types: {criteria: 'benefit'/'cost'}
    
    Return: list of (hero_id, Vi, normalized_scores)
    """
    criteria = CRITERIA_ORDER
    
    # Build decision matrix
    decision_matrix = {}
    for hid in hero_ids:
        if hid in scores:
            decision_matrix[hid] = [scores[hid].get(c, 0) for c in criteria]
    
    if not decision_matrix:
        return []
    
    hero_list = list(decision_matrix.keys())
    n_criteria = len(criteria)
    
    # Find max and min per criteria
    max_vals = [max(decision_matrix[hid][j] for hid in hero_list) for j in range(n_criteria)]
    min_vals = [min(decision_matrix[hid][j] for hid in hero_list) for j in range(n_criteria)]
    
    # Normalize
    normalized = {}
    for hid in hero_list:
        norm_row = []
        for j in range(n_criteria):
            c = criteria[j]
            x = decision_matrix[hid][j]
            if attribute_types[c] == "benefit":
                r = x / max_vals[j] if max_vals[j] > 0 else 0
            else:  # cost
                r = min_vals[j] / x if x > 0 else 0
            norm_row.append(r)
        normalized[hid] = norm_row
    
    # Calculate Vi
    results = []
    for hid in hero_list:
        vi = sum(weights[j] * normalized[hid][j] for j in range(n_criteria))
        results.append((hid, vi, normalized[hid], decision_matrix[hid]))
    
    # Sort by Vi descending
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results

# ============================================================
# 7. LOAD HERO-ROLE MAPPING
# ============================================================
def get_heroes_by_role(heroes):
    """Group heroes by their role/lane."""
    role_heroes = {
        "JUNGLING": [],
        "MID LANE": [],
        "EXP LANE": [],
        "GOLD LANE": [],
        "ROAMING": [],
    }
    
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
    
    # 1. Load data
    print("\n[1] Loading data hero...")
    heroes = load_heroes()
    print(f"    Total hero: {len(heroes)}")
    
    print("\n[2] Loading & menghitung skor kriteria utama...")
    scores = load_criteria_scores()
    # Print sample
    sample_id = "H001"
    print(f"    Sample — {heroes[sample_id]['nama']}:")
    for c in CRITERIA_ORDER:
        print(f"      {c}: {scores[sample_id][c]:.2f}")
    
    print("\n[3] Loading matriks AHP expert...")
    ahp_matrices = load_ahp_matrices()
    for role, mats in ahp_matrices.items():
        print(f"    {role}: {len(mats)} expert matrices")
    
    # 2. Aggregate & Calculate AHP per role
    print("\n[4] Aggregasi & perhitungan AHP per role...")
    print("-" * 80)
    
    role_weights = {}
    
    for role in ["JUNGLING", "MID LANE", "EXP LANE", "ROAMING", "GOLD LANE"]:
        mats = ahp_matrices[role]
        if not mats:
            print(f"\n  {role}: Tidak ada matriks!")
            continue
        
        # Aggregate
        if len(mats) > 1:
            agg_matrix = geometric_mean_matrices(mats)
        else:
            agg_matrix = mats[0]
        
        # Calculate AHP
        weights, lambda_max, ci, cr, is_consistent = calculate_ahp(agg_matrix)
        role_weights[role] = weights
        
        status = "[OK] KONSISTEN" if is_consistent else "[X] TIDAK KONSISTEN"
        print(f"\n  {'=' * 60}")
        print(f"  ROLE: {role} ({len(mats)} expert) — {status}")
        print(f"  {'=' * 60}")
        print(f"  λmax = {lambda_max:.4f}")
        print(f"  CI   = {ci:.4f}")
        print(f"  CR   = {cr:.4f} (threshold ≤ 0.10)")
        print(f"  {'─' * 60}")
        print(f"  {'Kriteria':<20} {'Bobot':>10} {'Persentase':>12}")
        print(f"  {'─' * 60}")
        for i, c in enumerate(CRITERIA_ORDER):
            print(f"  {c:<20} {weights[i]:>10.6f} {weights[i]*100:>11.2f}%")
        print(f"  {'─' * 60}")
        print(f"  Total: {sum(weights):>29.6f}")
    
    # 3. Group heroes by role
    role_heroes = get_heroes_by_role(heroes)
    
    # 4. Calculate SAW per role
    print("\n\n" + "=" * 80)
    print("  HASIL PERANGKINGAN SAW — TOP 10 PER ROLE")
    print("=" * 80)
    
    for role in ["JUNGLING", "MID LANE", "EXP LANE", "ROAMING", "GOLD LANE"]:
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
        
        print(f"  {'─' * 76}")
        
        # Also show Vi as percentage (relative to max)
        if results:
            max_vi = results[0][1]
            print(f"\n  Vi sebagai persentase (relatif terhadap Vi tertinggi):")
            print(f"  {'Rank':<6} {'Hero':<18} {'Vi':>10} {'Vi %':>8}")
            print(f"  {'─' * 45}")
            for rank, (hid, vi, _, _) in enumerate(results[:10], 1):
                pct = (vi / max_vi * 100) if max_vi > 0 else 0
                print(f"  {rank:<6} {heroes[hid]['nama']:<18} {vi:>10.6f} {pct:>7.2f}%")
    
    print("\n" + "=" * 80)
    print("  PERHITUNGAN SELESAI")
    print("=" * 80)

if __name__ == "__main__":
    main()
