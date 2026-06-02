"""
update_hero_roles.py — Update HANYA kolom name/class/roles di tabel `heroes`
dari CSV `AHP-SAW - DATA HERO.csv` (sumber data baru).

Aman: TIDAK menyentuh tabel `hero_scores`, `ahp_matrices`, atau `users`.
Aman: TIDAK menyentuh image_url / image_public_id (kolom hero tetap utuh).

Tujuan: memperbaiki kasus seperti Guinevere yang tercatat memiliki role
`EXP LANE, JUNGLING, ROAMING` padahal seharusnya hanya `EXP LANE, JUNGLING`,
sehingga saat coach ingin pick Guin sebagai JUNGLING tidak salah-deteksi.

Usage:
    python update_hero_roles.py            # DRY-RUN: tampilkan diff saja
    python update_hero_roles.py --commit   # Tulis perubahan ke DB Neon
"""
import os, sys, csv

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from db import Hero, get_session, DB_ENABLED

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "AHP-SAW - DATA HERO.csv")


def load_csv():
    rows = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            hid = row["ID_HERO"].strip()
            name = row["NAMA_HERO"].strip()
            cls = row["CLASS"].strip()
            roles = [r.strip().upper() for r in row["ROLE"].split(",") if r.strip()]
            rows.append({"id": hid, "name": name, "class": cls, "roles": roles})
    return rows


def diff_one(db_hero, csv_row):
    changes = {}
    if (db_hero.name or "").strip() != csv_row["name"]:
        changes["name"] = (db_hero.name, csv_row["name"])
    if (db_hero.hero_class or "").strip() != csv_row["class"]:
        changes["class"] = (db_hero.hero_class, csv_row["class"])
    db_roles = [r.strip().upper() for r in (db_hero.roles or [])]
    if db_roles != csv_row["roles"]:
        changes["roles"] = (db_roles, csv_row["roles"])
    return changes


def main():
    if not DB_ENABLED:
        print("ERROR: DATABASE_URL belum diset. Set di .env dulu.")
        sys.exit(1)
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: CSV tidak ditemukan: {CSV_PATH}")
        sys.exit(1)

    commit = "--commit" in sys.argv
    csv_rows = load_csv()
    print(f"[load] CSV: {len(csv_rows)} hero")

    s = get_session()
    if s is None:
        print("ERROR: get_session() return None.")
        sys.exit(1)

    try:
        db_by_id = {h.id: h for h in s.query(Hero).all()}
        print(f"[load] DB: {len(db_by_id)} hero")

        updated, added, unchanged, missing_in_csv = 0, 0, 0, []
        diffs_log = []

        for row in csv_rows:
            h = db_by_id.get(row["id"])
            if h is None:
                added += 1
                diffs_log.append(f"  + NEW    {row['id']}  {row['name']}  ({row['class']}, {row['roles']})")
                if commit:
                    s.add(Hero(id=row["id"], name=row["name"],
                               hero_class=row["class"], roles=row["roles"]))
                continue
            ch = diff_one(h, row)
            if not ch:
                unchanged += 1
                continue
            updated += 1
            line = f"  ~ UPDATE {row['id']:<6} {row['name']}"
            for k, (old, new) in ch.items():
                line += f"\n      {k:<6}: {old!r}  ->  {new!r}"
            diffs_log.append(line)
            if commit:
                if "name" in ch:
                    h.name = row["name"]
                if "class" in ch:
                    h.hero_class = row["class"]
                if "roles" in ch:
                    h.roles = row["roles"]

        csv_ids = {r["id"] for r in csv_rows}
        for hid in db_by_id:
            if hid not in csv_ids:
                missing_in_csv.append(hid)

        print()
        print("=" * 70)
        print(" PREVIEW PERUBAHAN" if not commit else " COMMITTED CHANGES")
        print("=" * 70)
        for line in diffs_log:
            print(line)
        if missing_in_csv:
            print()
            print(f"[warn] {len(missing_in_csv)} hero ada di DB tapi tidak ada di CSV "
                  f"(TIDAK dihapus): {missing_in_csv}")
        print()
        print(f"  Total update    : {updated}")
        print(f"  Total tambah    : {added}")
        print(f"  Tidak berubah   : {unchanged}")

        if commit:
            s.commit()
            print("\n[ok] Perubahan sudah ditulis ke DB Neon.")
        else:
            print("\n[dry-run] Tidak ada perubahan ditulis ke DB.")
            print("          Jalankan ulang dengan `--commit` untuk apply.")
    except Exception as e:
        s.rollback()
        print(f"\nERROR: {e}")
        sys.exit(2)
    finally:
        s.close()


if __name__ == "__main__":
    main()
