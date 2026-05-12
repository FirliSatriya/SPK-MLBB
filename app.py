"""
SPK Draft Pick MLBB — AHP-SAW
Flask Application
"""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json, os, csv, math

app = Flask(__name__)
app.secret_key = "spk-mlbb-secret-key-2026"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# DATA LOADING
# ============================================================
CRITERIA_ORDER = ["Difficulty", "Crowd Control", "Mobility", "Utility", "Durability", "Offense"]
ATTR_TYPES = {"Difficulty":"cost","Crowd Control":"benefit","Mobility":"benefit","Utility":"benefit","Durability":"benefit","Offense":"benefit"}
ROLES = ["JUNGLING", "MID LANE", "EXP LANE", "ROAMING", "GOLD LANE"]

CRITERIA_FILES = {
    "Difficulty": ("AHP-SAW - DIFFICULTY.csv", ["COMPLEXITY","TIMING PRECISSION","POSITIONING REQUIREMENT","DECISION COMPLEXITY"]),
    "Crowd Control": ("AHP-SAW - CROWD CONTROL.csv", ["TYPE STRENGHT","RELIABILITY","AREA COVERAGE","CHAIN / FREQUENCY"]),
    "Mobility": ("AHP-SAW - MOBILITY.csv", ["DASH/BLINK","ROTATION SPEED","ESCAPE CAPABILITY","FLEXIBILITY"]),
    "Utility": ("AHP-SAW - UTILITY.csv", ["TEAM SUPPORT","ZONING / CONTROL","DISRUPTION","PROTECTION"]),
    "Durability": ("AHP-SAW - DURABILITY.csv", ["BASE TANKINESS","SUSTAIN/REGEN","DAMAGE MITIGATION","SURVIVAL TOOLS"]),
    "Offense": ("AHP-SAW - OFFENSE.csv", ["DAMAGE","KILL THREAT/BURST","POSITIONING REQUIREMENT","DECISION COMPLEXITY"]),
}

def load_heroes():
    heroes = []
    with open(os.path.join(BASE_DIR, "AHP-SAW - DATA HERO.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            heroes.append({"id": row["ID_HERO"].strip(), "name": row["NAMA_HERO"].strip(),
                           "class": row["CLASS"].strip(), "roles": [r.strip().upper() for r in row["ROLE"].split(",")]})
    return heroes

def load_scores():
    scores = {}
    for cname, (fname, cols) in CRITERIA_FILES.items():
        with open(os.path.join(BASE_DIR, fname), encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                hid = row["ID_HERO"].strip()
                if hid not in scores: scores[hid] = {}
                vals = [float(row[c].strip()) for c in cols if row.get(c,"").strip()]
                scores[hid][cname] = round(sum(vals)/len(vals), 4) if vals else 0
    return scores

def parse_frac(v):
    v = v.strip()
    if not v: return None
    if "/" in v: p = v.split("/"); return float(p[0])/float(p[1])
    return float(v)

def load_ahp_matrices():
    matrices = {r: [] for r in ROLES}
    with open(os.path.join(BASE_DIR, "AHP-SAW - DISINI.csv"), encoding="utf-8-sig") as f:
        lines = list(csv.reader(f))
    def extract(start, col_off):
        m = []
        for i in range(6):
            row = []
            for j in range(6):
                ci = col_off+1+j
                row.append(parse_frac(lines[start+i][ci]) if start+i<len(lines) and ci<len(lines[start+i]) else None)
            m.append(row)
        for i in range(6):
            for j in range(6):
                if m[i][j] is None and m[j][i] is not None: m[i][j]=1.0/m[j][i]
                elif m[i][j] is None and i==j: m[i][j]=1.0
        return m
    blocks = [(2,0,"JUNGLING"),(11,0,"JUNGLING"),(20,0,"JUNGLING"),
              (29,0,"MID LANE"),(38,0,"MID LANE"),(47,0,"MID LANE"),
              (56,0,"GOLD LANE"),(65,0,"GOLD LANE"),(74,0,"GOLD LANE"),
              (2,9,"EXP LANE"),(11,9,"EXP LANE"),(20,9,"EXP LANE"),
              (29,9,"ROAMING"),(38,9,"ROAMING"),(47,9,"ROAMING")]
    for s,c,r in blocks:
        m = extract(s,c)
        if all(m[i][j] is not None for i in range(6) for j in range(6)):
            matrices[r].append(m)
    return matrices

def geo_mean(mats):
    n, k = 6, len(mats)
    return [[math.prod(m[i][j] for m in mats)**(1/k) for j in range(n)] for i in range(n)]

def calc_ahp(mat):
    n = len(mat)
    cs = [sum(mat[i][j] for i in range(n)) for j in range(n)]
    norm = [[mat[i][j]/cs[j] for j in range(n)] for i in range(n)]
    w = [sum(norm[i][j] for j in range(n))/n for i in range(n)]
    aw = [sum(mat[i][j]*w[j] for j in range(n)) for i in range(n)]
    lams = [aw[i]/w[i] for i in range(n)]
    lmax = sum(lams)/n
    ci = (lmax-n)/(n-1)
    cr = ci/1.24
    return {"weights":[round(x,6) for x in w], "lambda_max":round(lmax,4), "ci":round(ci,4), "cr":round(cr,4), "consistent":cr<=0.10}

def calc_saw(candidates, scores, weights, exclude_ids=None, scenario="default"):
    exclude_ids = exclude_ids or []
    heroes = [h for h in candidates if h["id"] not in exclude_ids]
    if not heroes: return []
    
    adj_w = list(weights)
    if scenario == "safe":
        adj_w[4] *= 1.5; adj_w[3] *= 1.5; adj_w[5] *= 0.7; adj_w[2] *= 0.8
    elif scenario == "aggressive":
        adj_w[5] *= 1.5; adj_w[2] *= 1.5; adj_w[4] *= 0.7; adj_w[3] *= 0.8
    ws = sum(adj_w)
    adj_w = [x/ws for x in adj_w]
    
    matrix = []
    for h in heroes:
        vals = [scores.get(h["id"], {}).get(c, 0) for c in CRITERIA_ORDER]
        matrix.append({"hero": h, "values": vals})
    
    max_v = [max(m["values"][j] for m in matrix) for j in range(6)]
    min_v = [min(m["values"][j] for m in matrix) for j in range(6)]
    
    results = []
    for m in matrix:
        norm = []
        for j in range(6):
            if ATTR_TYPES[CRITERIA_ORDER[j]] == "benefit":
                norm.append(m["values"][j]/max_v[j] if max_v[j]>0 else 0)
            else:
                norm.append(min_v[j]/m["values"][j] if m["values"][j]>0 else 0)
        vi = sum(adj_w[j]*norm[j] for j in range(6))
        results.append({**m["hero"], "vi": round(vi,6), "raw": m["values"], "norm": norm,
                        "scores": scores.get(m["hero"]["id"], {})})
    results.sort(key=lambda x: x["vi"], reverse=True)
    if results:
        mx = results[0]["vi"]
        for i,r in enumerate(results):
            r["rank"] = i+1
            r["vi_pct"] = round(r["vi"]/mx*100, 2) if mx > 0 else 0
    return results

# Load data at startup
HEROES = load_heroes()
SCORES = load_scores()
AHP_MATS = load_ahp_matrices()
AHP_RESULTS = {}
for role in ROLES:
    mats = AHP_MATS[role]
    agg = geo_mean(mats) if len(mats) > 1 else mats[0]
    AHP_RESULTS[role] = calc_ahp(agg)

# Attach scores to heroes
for h in HEROES:
    h["scores"] = SCORES.get(h["id"], {})

# ============================================================
# ROUTES
# ============================================================
@app.route("/")
def draft():
    return render_template("draft.html", heroes=HEROES, roles=ROLES)

@app.route("/ahp")
def ahp():
    return render_template("ahp.html", ahp=AHP_RESULTS, roles=ROLES, criteria=CRITERIA_ORDER)

@app.route("/heroes")
def heroes():
    return render_template("heroes.html", heroes=HEROES, roles=ROLES, criteria=CRITERIA_ORDER)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == "admin" and request.form.get("password") == "admin123":
            session["admin"] = True
            return redirect(url_for("admin"))
        return render_template("login.html", error="Username atau password salah")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("login"))
    role_counts = {r: sum(1 for h in HEROES if r in h["roles"]) for r in ROLES}
    return render_template("admin.html", heroes=HEROES, roles=ROLES, criteria=CRITERIA_ORDER, ahp=AHP_RESULTS, role_counts=role_counts)

@app.route("/admin/update_hero", methods=["POST"])
def update_hero():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json()
    hid = data.get("id")
    for h in HEROES:
        if h["id"] == hid:
            h["name"] = data.get("name", h["name"])
            h["class"] = data.get("class", h["class"])
            for c in CRITERIA_ORDER:
                if c in data:
                    h["scores"][c] = float(data[c])
                    SCORES[hid][c] = float(data[c])
            break
    return jsonify({"ok": True})

# API for draft pick JS
@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    data = request.get_json()
    exclude = data.get("exclude", [])
    scenario = data.get("scenario", "default")
    results = {}
    for role in ROLES:
        w = AHP_RESULTS[role]["weights"]
        cands = [h for h in HEROES if role in h["roles"]]
        ranked = calc_saw(cands, SCORES, w, exclude, scenario)
        results[role] = ranked[:5]
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
