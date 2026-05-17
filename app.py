"""
SPK Draft Pick MLBB — AHP-SAW
Flask Application
"""
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from markupsafe import Markup
from urllib.parse import quote
import os, csv, math, re

import db as dbmod
from db import Hero, HeroScore, AHPMatrix, get_session, init_db, db_has_data, DB_ENABLED
import cloud

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "spk-mlbb-secret-key-2026")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# CONSTANTS
# ============================================================
CRITERIA_ORDER = ["Difficulty", "Crowd Control", "Mobility", "Utility", "Durability", "Offense"]
ATTR_TYPES = {"Difficulty": "cost", "Crowd Control": "benefit", "Mobility": "benefit",
              "Utility": "benefit", "Durability": "benefit", "Offense": "benefit"}
ROLES = ["JUNGLING", "MID LANE", "EXP LANE", "ROAMING", "GOLD LANE"]
EVALUATORS = ["Coach", "Player 1", "Player 2"]  # 3 penilai per role
HERO_CLASSES = ["Tank", "Fighter", "Assassin", "Mage", "Marksman", "Support"]

CRITERIA_FILES = {
    "Difficulty": ("AHP-SAW - DIFFICULTY.csv", ["COMPLEXITY", "TIMING PRECISSION", "POSITIONING REQUIREMENT", "DECISION COMPLEXITY"]),
    "Crowd Control": ("AHP-SAW - CROWD CONTROL.csv", ["TYPE STRENGHT", "RELIABILITY", "AREA COVERAGE", "CHAIN / FREQUENCY"]),
    "Mobility": ("AHP-SAW - MOBILITY.csv", ["DASH/BLINK", "ROTATION SPEED", "ESCAPE CAPABILITY", "FLEXIBILITY"]),
    "Utility": ("AHP-SAW - UTILITY.csv", ["TEAM SUPPORT", "ZONING / CONTROL", "DISRUPTION", "PROTECTION"]),
    "Durability": ("AHP-SAW - DURABILITY.csv", ["BASE TANKINESS", "SUSTAIN/REGEN", "DAMAGE MITIGATION", "SURVIVAL TOOLS"]),
    "Offense": ("AHP-SAW - OFFENSE.csv", ["DAMAGE", "KILL THREAT/BURST", "SUSTAINED DPS", "OBJECTIVE PRESSURE"]),
}

# ============================================================
# DATA LOADING
# ============================================================
def load_heroes():
    heroes = []
    with open(os.path.join(BASE_DIR, "AHP-SAW - DATA HERO.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            heroes.append({"id": row["ID_HERO"].strip(), "name": row["NAMA_HERO"].strip(),
                           "class": row["CLASS"].strip(),
                           "roles": [r.strip().upper() for r in row["ROLE"].split(",") if r.strip()],
                           "image_url": None, "image_public_id": None})
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

# ============================================================
# DB-BACKED LOADERS (fallback to CSV when DB not configured)
# ============================================================
def load_heroes_from_db():
    """Returns (heroes_list, scores_dict). Both empty if DB not available."""
    s = get_session()
    if s is None:
        return [], {}
    try:
        heroes, scores = [], {}
        for h in s.query(Hero).order_by(Hero.id).all():
            d = h.to_dict()
            heroes.append({"id": d["id"], "name": d["name"], "class": d["class"],
                           "roles": d["roles"], "image_url": d["image_url"],
                           "image_public_id": d["image_public_id"]})
            scores[d["id"]] = d["scores"]
        return heroes, scores
    finally:
        s.close()

def load_ahp_from_db():
    """Returns matrices dict {role: [m1, m2, m3]} from DB, or empty dict."""
    s = get_session()
    if s is None:
        return {}
    try:
        out = {r: [] for r in ROLES}
        rows = s.query(AHPMatrix).order_by(AHPMatrix.role, AHPMatrix.evaluator_idx).all()
        for r in rows:
            if r.role in out:
                while len(out[r.role]) <= r.evaluator_idx:
                    out[r.role].append(None)
                out[r.role][r.evaluator_idx] = r.matrix
        # drop Nones
        return {role: [m for m in mats if m] for role, mats in out.items()}
    finally:
        s.close()

def seed_db_from_csv():
    """One-shot seed when DB is empty. Mirrors migrate.py but in-process."""
    if not DB_ENABLED:
        return
    if db_has_data():
        return
    print("[db] DB empty, seeding from CSV...")
    init_db()
    s = get_session()
    try:
        csv_heroes = load_heroes()
        csv_scores = load_scores()
        csv_mats = load_ahp_matrices()
        for h in csv_heroes:
            s.add(Hero(id=h["id"], name=h["name"], hero_class=h["class"], roles=h["roles"]))
            for c in CRITERIA_ORDER:
                v = float(csv_scores.get(h["id"], {}).get(c, 0))
                s.add(HeroScore(hero_id=h["id"], criterion=c, value=v))
        for role in ROLES:
            for idx, m in enumerate(csv_mats.get(role, [])):
                s.add(AHPMatrix(role=role, evaluator_idx=idx, matrix=m))
        s.commit()
        print(f"[db] Seeded {len(csv_heroes)} heroes.")
    except Exception as e:
        s.rollback()
        print(f"[db] Seed failed: {e}")
    finally:
        s.close()

# Load data at startup
if DB_ENABLED:
    try:
        init_db()
        seed_db_from_csv()
        HEROES, SCORES = load_heroes_from_db()
        db_mats = load_ahp_from_db()
        AHP_MATS = {r: db_mats.get(r, []) for r in ROLES}
        if not HEROES:  # DB connection failed silently — fall back to CSV
            raise RuntimeError("DB returned empty heroes")
    except Exception as e:
        print(f"[db] DB unavailable ({e}). Falling back to CSV-only mode.")
        HEROES = load_heroes()
        SCORES = load_scores()
        AHP_MATS = load_ahp_matrices()
else:
    HEROES = load_heroes()
    SCORES = load_scores()
    AHP_MATS = load_ahp_matrices()

# Pad any role with fewer than 3 matrices using identity-ish fallback
for r in ROLES:
    while len(AHP_MATS[r]) < 3:
        AHP_MATS[r].append([[1.0]*6 for _ in range(6)])
AHP_RESULTS = {}
for role in ROLES:
    recompute_role(role)

for h in HEROES:
    h["scores"] = SCORES.get(h["id"], {})

# ============================================================
# DB PERSISTENCE HELPERS
# ============================================================
def db_upsert_hero(hero_dict, scores_dict, image_url=None, image_public_id=None):
    """hero_dict: {id, name, class, roles}.  scores_dict: {criterion: value}."""
    s = get_session()
    if s is None:
        return
    try:
        h = s.get(Hero, hero_dict["id"])
        if h is None:
            h = Hero(id=hero_dict["id"])
            s.add(h)
        h.name = hero_dict["name"]
        h.hero_class = hero_dict["class"]
        h.roles = hero_dict["roles"]
        if image_url is not None:
            h.image_url = image_url
        if image_public_id is not None:
            h.image_public_id = image_public_id
        for c, v in scores_dict.items():
            row = (s.query(HeroScore).filter_by(hero_id=hero_dict["id"], criterion=c).one_or_none())
            if row:
                row.value = float(v)
            else:
                s.add(HeroScore(hero_id=hero_dict["id"], criterion=c, value=float(v)))
        s.commit()
    except Exception as e:
        s.rollback(); print(f"db_upsert_hero error: {e}")
    finally:
        s.close()

def db_delete_hero(hero_id):
    s = get_session()
    if s is None:
        return
    try:
        h = s.get(Hero, hero_id)
        if h:
            s.delete(h)
            s.commit()
    except Exception as e:
        s.rollback(); print(f"db_delete_hero error: {e}")
    finally:
        s.close()

def db_upsert_matrix(role, idx, matrix):
    s = get_session()
    if s is None:
        return
    try:
        row = s.query(AHPMatrix).filter_by(role=role, evaluator_idx=idx).one_or_none()
        if row:
            row.matrix = matrix
        else:
            s.add(AHPMatrix(role=role, evaluator_idx=idx, matrix=matrix))
        s.commit()
    except Exception as e:
        s.rollback(); print(f"db_upsert_matrix error: {e}")
    finally:
        s.close()

# ============================================================
# HERO AVATAR / PORTRAIT HELPERS (exposed to Jinja)
# ============================================================
HERO_AVATAR_COLORS = ['#5b8fc7', '#c25c5c', '#6fa886', '#8a78c0', '#b08842',
                     '#5fa7b8', '#c2845c', '#7c6ec0', '#a08947', '#6b8aa5']

def hero_color(name):
    h = 0
    for c in str(name):
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return HERO_AVATAR_COLORS[h % len(HERO_AVATAR_COLORS)]

def hero_initials(name):
    words = [w for w in re.split(r'[^A-Za-z0-9]+', str(name)) if w]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return (words[0] if words else str(name))[:2].upper()

def portrait_html(name, size="", image_url=None):
    """Render hero avatar. If image_url provided (Cloudinary), use it; else fall back to
    a colored initial + DiceBear cartoon placeholder."""
    bg = hero_color(name)
    init = hero_initials(name)
    if image_url:
        return Markup(
            f'<div class="hero-avatar {size}" style="background:{bg}">'
            f'<span class="initials">{init}</span>'
            f'<img src="{image_url}" alt="{name}" loading="lazy" onerror="this.remove()">'
            f'</div>'
        )
    seed = quote(str(name))
    src = f"https://api.dicebear.com/7.x/adventurer-neutral/svg?seed={seed}"
    return Markup(
        f'<div class="hero-avatar {size}" style="background:{bg}">'
        f'<span class="initials">{init}</span>'
        f'<img src="{src}" alt="" loading="lazy" onerror="this.remove()">'
        f'</div>'
    )

# ============================================================
# CONTEXT PROCESSOR — make `is_admin` available in all templates
# ============================================================
@app.context_processor
def inject_admin():
    return {"is_admin": bool(session.get("admin"))}

app.jinja_env.globals['hero_color'] = hero_color
app.jinja_env.globals['hero_initials'] = hero_initials
app.jinja_env.globals['portrait_html'] = portrait_html

# ============================================================
# ROUTES
# ============================================================
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

# --- Hero CRUD ---
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
            "image_url": (data.get("image_url") or "").strip() or None,
            "image_public_id": None,
            "scores": {}}
    for c in CRITERIA_ORDER:
        v = float(data.get(c, 2.5) or 2.5)
        hero["scores"][c] = v
    HEROES.append(hero)
    SCORES[new_id] = dict(hero["scores"])
    db_upsert_hero(hero, hero["scores"], image_url=hero["image_url"])
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
            if "image_url" in data:
                h["image_url"] = (data.get("image_url") or "").strip() or None
            for c in CRITERIA_ORDER:
                if c in data and data[c] != "":
                    h["scores"][c] = float(data[c])
                    SCORES.setdefault(hid, {})[c] = float(data[c])
            db_upsert_hero(h, h["scores"], image_url=h.get("image_url"))
            return jsonify({"ok": True, "hero": h})
    return jsonify({"error": "not_found"}), 404

@app.route("/admin/delete_hero", methods=["POST"])
def delete_hero():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401
    hid = (request.get_json() or {}).get("id")
    for i, h in enumerate(HEROES):
        if h["id"] == hid:
            # Best-effort image cleanup before DB cascade-delete
            if cloud.CLOUD_ENABLED and h.get("image_public_id"):
                cloud.delete_hero_image(h["image_public_id"])
            HEROES.pop(i)
            SCORES.pop(hid, None)
            db_delete_hero(hid)
            return jsonify({"ok": True})
    return jsonify({"error": "not_found"}), 404

@app.route("/admin/upload_hero_image", methods=["POST"])
def upload_hero_image():
    """Multipart POST: form field 'image' (file) + 'id' (hero id).
       Uploads to Cloudinary, persists URL on hero row."""
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401
    if not cloud.CLOUD_ENABLED:
        return jsonify({"error": "cloudinary_not_configured"}), 503
    hid = request.form.get("id")
    f = request.files.get("image")
    if not hid or not f:
        return jsonify({"error": "missing_id_or_image"}), 400
    hero = next((h for h in HEROES if h["id"] == hid), None)
    if not hero:
        return jsonify({"error": "hero_not_found"}), 404
    try:
        url, public_id = cloud.upload_hero_image(f, hid)
    except Exception as e:
        return jsonify({"error": f"upload_failed: {e}"}), 500
    if not url:
        return jsonify({"error": "upload_failed"}), 500
    hero["image_url"] = url
    hero["image_public_id"] = public_id
    db_upsert_hero(hero, hero.get("scores", {}), image_url=url, image_public_id=public_id)
    return jsonify({"ok": True, "image_url": url, "image_public_id": public_id})

@app.route("/admin/delete_hero_image", methods=["POST"])
def delete_hero_image():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401
    hid = (request.get_json() or {}).get("id")
    hero = next((h for h in HEROES if h["id"] == hid), None)
    if not hero:
        return jsonify({"error": "hero_not_found"}), 404
    if cloud.CLOUD_ENABLED and hero.get("image_public_id"):
        cloud.delete_hero_image(hero["image_public_id"])
    hero["image_url"] = None
    hero["image_public_id"] = None
    db_upsert_hero(hero, hero.get("scores", {}), image_url=None, image_public_id=None)
    return jsonify({"ok": True})

# --- AHP Matrix update ---
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
    # enforce reciprocal + diagonal=1
    for i in range(6):
        parsed[i][i] = 1.0
        for j in range(i+1, 6):
            parsed[j][i] = 1.0 / parsed[i][j] if parsed[i][j] else 1.0
    AHP_MATS[role][idx] = parsed
    recompute_role(role)
    db_upsert_matrix(role, idx, parsed)
    return jsonify({"ok": True, "ahp": AHP_RESULTS[role]})

# --- API recommend ---
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

if __name__ == "__main__":
    app.run(debug=True, port=5000)
