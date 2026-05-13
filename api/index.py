"""
SPK Draft Pick MLBB — AHP-SAW
Vercel Serverless Entry Point
"""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os, csv, math

def find_base_dir():
    d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.exists(os.path.join(d, "AHP-SAW - DATA HERO.csv")):
        return d
    d = os.getcwd()
    if os.path.exists(os.path.join(d, "AHP-SAW - DATA HERO.csv")):
        return d
    d = "/var/task"
    if os.path.exists(os.path.join(d, "AHP-SAW - DATA HERO.csv")):
        return d
    return os.getcwd()

BASE_DIR = find_base_dir()
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR, static_url_path="/static")
app.secret_key = os.environ.get("SECRET_KEY", "spk-mlbb-secret-key-2026")

CRITERIA_ORDER = ["Difficulty", "Crowd Control", "Mobility", "Utility", "Durability", "Offense"]
ATTR_TYPES = {"Difficulty": "cost", "Crowd Control": "benefit", "Mobility": "benefit",
              "Utility": "benefit", "Durability": "benefit", "Offense": "benefit"}
ROLES = ["JUNGLING", "MID LANE", "EXP LANE", "ROAMING", "GOLD LANE"]
EVALUATORS = ["Coach", "Player 1", "Player 2"]
HERO_CLASSES = ["Tank", "Fighter", "Assassin", "Mage", "Marksman", "Support"]

CRITERIA_FILES = {
    "Difficulty": ("AHP-SAW - DIFFICULTY.csv", ["COMPLEXITY", "TIMING PRECISSION", "POSITIONING REQUIREMENT", "DECISION COMPLEXITY"]),
    "Crowd Control": ("AHP-SAW - CROWD CONTROL.csv", ["TYPE STRENGHT", "RELIABILITY", "AREA COVERAGE", "CHAIN / FREQUENCY"]),
    "Mobility": ("AHP-SAW - MOBILITY.csv", ["DASH/BLINK", "ROTATION SPEED", "ESCAPE CAPABILITY", "FLEXIBILITY"]),
    "Utility": ("AHP-SAW - UTILITY.csv", ["TEAM SUPPORT", "ZONING / CONTROL", "DISRUPTION", "PROTECTION"]),
    "Durability": ("AHP-SAW - DURABILITY.csv", ["BASE TANKINESS", "SUSTAIN/REGEN", "DAMAGE MITIGATION", "SURVIVAL TOOLS"]),
    "Offense": ("AHP-SAW - OFFENSE.csv", ["DAMAGE", "KILL THREAT/BURST", "POSITIONING REQUIREMENT", "DECISION COMPLEXITY"]),
}

def load_heroes():
    heroes = []
    with open(os.path.join(BASE_DIR, "AHP-SAW - DATA HERO.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            heroes.append({"id": row["ID_HERO"].strip(), "name": row["NAMA_HERO"].strip(),
                           "class": row["CLASS"].strip(),
                           "roles": [r.strip().upper() for r in row["ROLE"].split(",") if r.strip()]})
    return heroes

def load_scores():
    scores = {}
    for cname, (fname, cols) in CRITERIA_FILES.items():
        with open(os.path.join(BASE_DIR, fname), encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                hid = row["ID_HERO"].strip()
                if hid not in scores: scores[hid] = {}
                vals = [float(row[c].strip()) for c in cols if row.get(c, "").strip()]
                scores[hid][cname] = round(sum(vals)/len(vals), 4) if vals else 0
    return scores

def parse_frac(v):
    v = str(v).strip()
    if not v: return None
    if "/" in v:
        p = v.split("/")
        return float(p[0]) / float(p[1])
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
                ci = col_off + 1 + j
                row.append(parse_frac(lines[start+i][ci]) if start+i < len(lines) and ci < len(lines[start+i]) else None)
            m.append(row)
        for i in range(6):
            for j in range(6):
                if m[i][j] is None and m[j][i] is not None: m[i][j] = 1.0 / m[j][i]
                elif m[i][j] is None and i == j: m[i][j] = 1.0
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
    ci = (lmax - n)/(n - 1)
    cr = ci / 1.24
    return {"weights": [round(x, 6) for x in w], "lambda_max": round(lmax, 4),
            "ci": round(ci, 4), "cr": round(cr, 4), "consistent": cr <= 0.10}

def recompute_role(role):
    mats = AHP_MATS[role]
    if not mats: return
    agg = geo_mean(mats) if len(mats) > 1 else mats[0]
    AHP_RESULTS[role] = calc_ahp(agg)

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
                norm.append(m["values"][j]/max_v[j] if max_v[j] > 0 else 0)
            else:
                norm.append(min_v[j]/m["values"][j] if m["values"][j] > 0 else 0)
        vi = sum(adj_w[j]*norm[j] for j in range(6))
        results.append({**m["hero"], "vi": round(vi, 6), "raw": m["values"], "norm": norm,
                        "scores": scores.get(m["hero"]["id"], {})})
    results.sort(key=lambda x: x["vi"], reverse=True)
    if results:
        mx = results[0]["vi"]
        for i, r in enumerate(results):
            r["rank"] = i + 1
            r["vi_pct"] = round(r["vi"]/mx*100, 2) if mx > 0 else 0
    return results

def next_hero_id():
    nums = []
    for h in HEROES:
        try: nums.append(int(''.join(filter(str.isdigit, h["id"]))))
        except: pass
    n = (max(nums) + 1) if nums else 1
    return f"H{n:03d}"

HEROES = load_heroes()
SCORES = load_scores()
AHP_MATS = load_ahp_matrices()
for r in ROLES:
    while len(AHP_MATS[r]) < 3:
        AHP_MATS[r].append([[1.0]*6 for _ in range(6)])
AHP_RESULTS = {}
for role in ROLES:
    recompute_role(role)

for h in HEROES:
    h["scores"] = SCORES.get(h["id"], {})

@app.context_processor
def inject_admin():
    return {"is_admin": bool(session.get("admin"))}

@app.route("/")
def draft():
    return render_template("draft.html", heroes=HEROES, roles=ROLES)

@app.route("/ahp")
def ahp():
    if not session.get("admin"):
        return redirect(url_for("login"))
    return render_template("ahp.html", ahp=AHP_RESULTS, roles=ROLES, criteria=CRITERIA_ORDER)

@app.route("/heroes")
def heroes():
    if not session.get("admin"):
        return redirect(url_for("login"))
    return render_template("heroes.html", heroes=HEROES, roles=ROLES, criteria=CRITERIA_ORDER)

@app.route("/login", methods=["GET", "POST"])
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
    return redirect(url_for("draft"))

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("login"))
    role_counts = {r: sum(1 for h in HEROES if r in h["roles"]) for r in ROLES}
    return render_template("admin.html", heroes=HEROES, roles=ROLES, criteria=CRITERIA_ORDER,
                           ahp=AHP_RESULTS, ahp_mats=AHP_MATS, evaluators=EVALUATORS,
                           hero_classes=HERO_CLASSES, role_counts=role_counts)

@app.route("/admin/create_hero", methods=["POST"])
def create_hero():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json() or {}
    new_id = next_hero_id()
    roles = data.get("roles", [])
    if isinstance(roles, str):
        roles = [r.strip().upper() for r in roles.split(",") if r.strip()]
    hero = {"id": new_id,
            "name": (data.get("name") or "Unnamed").strip(),
            "class": (data.get("class") or "Fighter").strip(),
            "roles": [r.upper() for r in roles] or ["JUNGLING"],
            "scores": {}}
    for c in CRITERIA_ORDER:
        v = float(data.get(c, 2.5) or 2.5)
        hero["scores"][c] = v
    HEROES.append(hero)
    SCORES[new_id] = dict(hero["scores"])
    return jsonify({"ok": True, "hero": hero})

@app.route("/admin/update_hero", methods=["POST"])
def update_hero():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json() or {}
    hid = data.get("id")
    for h in HEROES:
        if h["id"] == hid:
            h["name"] = (data.get("name") or h["name"]).strip()
            h["class"] = (data.get("class") or h["class"]).strip()
            if "roles" in data:
                rs = data["roles"]
                if isinstance(rs, str):
                    rs = [r.strip().upper() for r in rs.split(",") if r.strip()]
                h["roles"] = [r.upper() for r in rs]
            for c in CRITERIA_ORDER:
                if c in data and data[c] != "":
                    h["scores"][c] = float(data[c])
                    SCORES.setdefault(hid, {})[c] = float(data[c])
            return jsonify({"ok": True, "hero": h})
    return jsonify({"error": "not_found"}), 404

@app.route("/admin/delete_hero", methods=["POST"])
def delete_hero():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401
    hid = (request.get_json() or {}).get("id")
    for i, h in enumerate(HEROES):
        if h["id"] == hid:
            HEROES.pop(i)
            SCORES.pop(hid, None)
            return jsonify({"ok": True})
    return jsonify({"error": "not_found"}), 404

@app.route("/admin/update_ahp", methods=["POST"])
def update_ahp():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json() or {}
    role = data.get("role")
    idx = int(data.get("idx", 0))
    matrix = data.get("matrix")
    if role not in ROLES or not matrix or len(matrix) != 6:
        return jsonify({"error": "invalid_input"}), 400
    parsed = []
    for i in range(6):
        row = []
        for j in range(6):
            try:
                row.append(parse_frac(matrix[i][j]) or 1.0)
            except Exception:
                row.append(1.0)
        parsed.append(row)
    for i in range(6):
        parsed[i][i] = 1.0
        for j in range(i+1, 6):
            parsed[j][i] = 1.0 / parsed[i][j] if parsed[i][j] else 1.0
    AHP_MATS[role][idx] = parsed
    recompute_role(role)
    return jsonify({"ok": True, "ahp": AHP_RESULTS[role]})

@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    data = request.get_json() or {}
    exclude = data.get("exclude", [])
    scenario = data.get("scenario", "default")
    results = {}
    for role in ROLES:
        w = AHP_RESULTS[role]["weights"]
        cands = [h for h in HEROES if role in h["roles"]]
        ranked = calc_saw(cands, SCORES, w, exclude, scenario)
        results[role] = ranked[:5]
    return jsonify(results)

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "base_dir": BASE_DIR,
        "heroes_count": len(HEROES),
        "template_dir": TEMPLATE_DIR,
        "templates_exist": os.path.exists(TEMPLATE_DIR),
        "csv_exist": os.path.exists(os.path.join(BASE_DIR, "AHP-SAW - DATA HERO.csv")),
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
