"""
update_saw_scores.py — Update HANYA skor kriteria (tabel hero_scores) dari CSV baru.

Aman: TIDAK menyentuh tabel `heroes` maupun `ahp_matrices`.
Skor tiap kriteria = rata-rata 4 sub-kolom (kolom ke-5..8, diambil BY POSITION,
bukan by nama header — supaya tahan terhadap beda nama kolom seperti
"SUSTAIN DPS" vs "SUSTAINED DPS"), dibulatkan 4 desimal.

Usage:
    python update_saw_scores.py            # DRY-RUN: hanya tampilkan preview perubahan
    python update_saw_scores.py --commit   # Tulis perubahan ke DB Neon
"""
import os, sys, csv

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from db import Hero, HeroScore, get_session, DB_ENABLED

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# criterion (sesuai CRITERIA_ORDER di app.py) -> nama file CSV di folder ini
CSV_FILES = {
    "Difficulty":    "AHP-SAW - DIFFICULTY.csv",
    "Crowd Control": "AHP-SAW - CROWD CONTROL.csv",
    "Mobility":      "AHP-SAW - MOBILITY.csv",
    "Utility":       "AHP-SAW - UTILITY.csv",
    "Durability":    "AHP-SAW - DURABILITY.csv",
    "Offense":       "AHP-SAW - OFFENSE.csv",
}

SUB_COL_START = 4   # kolom 0..3 = ID_HERO, NAMA_HERO, CLASS, ROLE
SUB_COL_COUNT = 4   # 4 sub-kriteria setelah ROLE


def read_criterion_csv(path):
    """Return {hero_id: avg_score} dari 4 sub-kolom (by position)."""
    out = {}
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    for r in rows[1:]:  # skip header
        if not r or not r[0].strip():
            continue
        hid = r[0].strip()
        vals = []
        for j in range(SUB_COL_START, SUB_COL_START + SUB_COL_COUNT):
            if j < len(r) and str(r[j]).strip():
                vals.append(float(r[j]))
        if vals:
            out[hid] = round(sum(vals) / len(vals), 4)
    return out


def load_new_scores():
    new_scores = {}
    for crit, fname in CSV_FILES.items():
        path = os.path.join(BASE_DIR, fname)
        if not os.path.exists(path):
            print(f"ERROR: file CSV tidak ditemukan: {fname}")
            sys.exit(1)
        for hid, val in read_criterion_csv(path).items():
            new_scores.setdefault(hid, {})[crit] = val
    return new_scores


def main():
    commit = "--commit" in sys.argv
    if not DB_ENABLED:
        print("ERROR: DATABASE_URL tidak diset / SQLAlchemy belum terpasang.")
        sys.exit(1)

    new_scores = load_new_scores()
    print(f"[load] {len(new_scores)} hero dibaca dari CSV, {len(CSV_FILES)} kriteria.\n")

    s = get_session()
    if s is None:
        print("ERROR: tidak bisa membuka session DB.")
        sys.exit(1)
    try:
        db_hero_ids = {h.id for h in s.query(Hero.id).all()}
        existing = {}
        for row in s.query(HeroScore).all():
            existing.setdefault(row.hero_id, {})[row.criterion] = row.value

        changes = []   # (hid, crit, old, new)
        unknown = []   # hero id di CSV tapi tidak ada di DB
        for hid, crits in new_scores.items():
            if hid not in db_hero_ids:
                unknown.append(hid)
                continue
            for crit, newv in crits.items():
                oldv = existing.get(hid, {}).get(crit)
                if oldv is None or abs(oldv - newv) > 1e-9:
                    changes.append((hid, crit, oldv, newv))

        print("=" * 78)
        print(f" PREVIEW PERUBAHAN SKOR  ({len(changes)} nilai berubah)")
        print("=" * 78)
        if changes:
            print(f" {'HERO':<8} {'KRITERIA':<16} {'LAMA':>8}  ->  {'BARU':>8}")
            print(" " + "-" * 74)
            for hid, crit, oldv, newv in changes:
                olds = f"{oldv:.4f}" if oldv is not None else "(baru)"
                print(f" {hid:<8} {crit:<16} {olds:>8}  ->  {newv:>8.4f}")
        else:
            print(" Tidak ada perubahan — skor di DB sudah sama dengan CSV.")
        if unknown:
            print(f"\n WARNING: {len(unknown)} hero di CSV tidak ada di DB (dilewati): {unknown}")

        heroes_changed = len({c[0] for c in changes})
        print("\n" + "-" * 78)
        print(f" Ringkasan: {len(changes)} nilai berubah pada {heroes_changed} hero.")

        if not commit:
            print("\n[DRY-RUN] Tidak ada yang ditulis ke DB.")
            print("Jalankan ulang dengan --commit untuk menyimpan perubahan.")
            return

        if not changes:
            print("\nTidak ada yang perlu di-commit.")
            return

        print("\n[COMMIT] Menulis perubahan ke DB...")
        n = 0
        for hid, crit, oldv, newv in changes:
            row = s.query(HeroScore).filter_by(hero_id=hid, criterion=crit).one_or_none()
            if row:
                row.value = float(newv)
            else:
                s.add(HeroScore(hero_id=hid, criterion=crit, value=float(newv)))
            n += 1
        s.commit()
        print(f"[OK] {n} skor ter-update di DB.")
    except Exception as e:
        s.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        s.close()


if __name__ == "__main__":
    main()
