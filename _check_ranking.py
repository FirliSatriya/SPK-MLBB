"""Verifikasi Tabel ranking SAW Jungling (Vi top-10) vs project."""
from dotenv import load_dotenv
load_dotenv()
import numpy as np
from db import get_session, Hero, AHPMatrix

CRIT = ["Difficulty","Crowd Control","Mobility","Utility","Durability","Offense"]
ATTR = {"Difficulty":"cost","Crowd Control":"benefit","Mobility":"benefit",
        "Utility":"benefit","Durability":"benefit","Offense":"benefit"}

SKRIPSI = [
    ("Fredrinn",   0.8830, "Sangat direkomendasikan"),
    ("Helcurt",    0.8190, "Sangat direkomendasikan"),
    ("Freya",      0.8100, "Sangat direkomendasikan"),
    ("Yi Sun-shin",0.7982, "Direkomendasikan"),
    ("Nolan",      0.7829, "Direkomendasikan"),
    ("Julian",     0.7803, "Direkomendasikan"),
    ("Harley",     0.7671, "Direkomendasikan"),
    ("Leomord",    0.7625, "Direkomendasikan"),
    ("Alice",      0.7538, "Direkomendasikan"),
    ("Baxia",      0.7437, "Direkomendasikan"),
]

s = get_session()
try:
    # Ambil semua kandidat JUNGLING (pool normalisasi)
    all_h = s.query(Hero).all()
    jung = [h for h in all_h if "JUNGLING" in (h.roles or [])]

    # Ambil 3 matriks AHP Jungling, hitung bobot via Saaty PRD method
    rows = (s.query(AHPMatrix).filter(AHPMatrix.role == "JUNGLING")
              .order_by(AHPMatrix.evaluator_idx).all())
    mats = [np.array(r.matrix, dtype=float) for r in rows]
    agg = np.prod(np.array(mats), axis=0) ** (1.0/len(mats))
    norm = agg / agg.sum(axis=0)
    w = norm.mean(axis=1)  # bobot 6 kriteria
    print("Bobot AHP Jungling:", [f"{x:.4f}" for x in w])
    print(f"Pool kandidat JUNGLING: {len(jung)} hero\n")

    # Bangun matrix nilai semua kandidat → max/min per kriteria
    cand_vals = []
    for h in jung:
        sc = {x.criterion: x.value for x in h.scores}
        cand_vals.append({"name": h.name, "vals": [sc.get(c, 0) for c in CRIT]})
    max_v = [max(c["vals"][j] for c in cand_vals) for j in range(6)]
    min_v = [min(c["vals"][j] for c in cand_vals) for j in range(6)]
    print(f"Max per kriteria: {max_v}")
    print(f"Min per kriteria: {min_v}\n")

    # Hitung Vi untuk semua kandidat lalu ranking
    results = []
    for c in cand_vals:
        nrm = []
        for j in range(6):
            if ATTR[CRIT[j]] == "benefit":
                nrm.append(c["vals"][j] / max_v[j] if max_v[j] > 0 else 0)
            else:
                nrm.append(min_v[j] / c["vals"][j] if c["vals"][j] > 0 else 0)
        vi = sum(w[j] * nrm[j] for j in range(6))
        results.append({"name": c["name"], "vi": vi})
    results.sort(key=lambda x: x["vi"], reverse=True)

    print(f"{'Rk':>3} {'Hero':18s} {'Vi(proj)':>9s} {'Vi(sk)':>8s} {'diff':>8s}")
    print("-"*60)
    for i, (sk_name, sk_vi, _) in enumerate(SKRIPSI, 1):
        # cari di hasil
        lookup = sk_name.lower().replace("-","").replace(" ","")
        hit = None
        for r in results:
            if r["name"].lower().replace("-","").replace(" ","") == lookup:
                hit = r
                break
        if not hit:
            print(f"  ! {sk_name} tidak ketemu")
            continue
        # cari rank-nya
        rank = next(idx for idx, r in enumerate(results, 1) if r["name"] == hit["name"])
        diff = hit["vi"] - sk_vi
        tag = "OK" if abs(diff) < 0.002 else "BEDA"
        print(f"  {rank:>2} {sk_name:18s} {hit['vi']:>9.4f} {sk_vi:>8.4f} {diff:>+8.4f}  [{tag}]")

    print("\n=== Top-10 hasil project ===")
    for i, r in enumerate(results[:10], 1):
        print(f"  {i:>2}. {r['name']:18s} Vi={r['vi']:.4f}")
finally:
    s.close()
