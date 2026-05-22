"""
SPK Draft Pick MLBB — AHP-SAW
Flask Application
"""
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
from markupsafe import Markup
from urllib.parse import quote
import os, sys, math, re
import datetime as dt
from functools import wraps

import bcrypt
import jwt

import db as dbmod
from db import Hero, HeroScore, AHPMatrix, User, get_session, init_db, DB_ENABLED
import cloud

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "spk-mlbb-secret-key-2026")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# AUTH — JWT in HttpOnly cookie + bcrypt password hashing
# ============================================================
JWT_SECRET = os.environ.get("JWT_SECRET_KEY", app.secret_key)
JWT_ALGO = "HS256"
JWT_TTL_HOURS = 12
JWT_COOKIE_NAME = "spk_auth"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "spkmlbb"


def hash_password(plain: str) -> str:
    """bcrypt hash, simpan sebagai utf-8 string supaya cocok dengan kolom String DB."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_jwt(username: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": username,
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(hours=JWT_TTL_HOURS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_jwt(token: str):
    """Return payload dict kalau valid, None kalau invalid/expired."""
    if not token:
        return None
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        return None


def current_user():
    """Username dari JWT cookie, atau None. Tidak query DB tiap request."""
    payload = decode_jwt(request.cookies.get(JWT_COOKIE_NAME))
    return payload.get("sub") if payload else None


def login_required(fn):
    """Decorator: redirect ke /login untuk HTML, 401 JSON untuk API."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            if request.path.startswith("/admin/") or request.path.startswith("/api/"):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def set_auth_cookie(resp, token: str):
    resp.set_cookie(
        JWT_COOKIE_NAME,
        token,
        max_age=JWT_TTL_HOURS * 3600,
        httponly=True,
        secure=request.is_secure,
        samesite="Lax",
    )
    return resp


def clear_auth_cookie(resp):
    resp.delete_cookie(JWT_COOKIE_NAME)
    return resp


def seed_default_admin():
    """Buat user admin default kalau tabel users kosong."""
    if not DB_ENABLED:
        return
    s = get_session()
    if s is None:
        return
    try:
        if s.query(User).count() == 0:
            s.add(User(
                username=DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            ))
            s.commit()
            print(f"[auth] Seeded default admin: {DEFAULT_ADMIN_USERNAME}/{DEFAULT_ADMIN_PASSWORD}")
    except Exception as e:
        s.rollback()
        print(f"[auth] Seed admin failed: {e}")
    finally:
        s.close()

# ============================================================
# CONSTANTS
# ============================================================
CRITERIA_ORDER = ["Difficulty", "Crowd Control", "Mobility", "Utility", "Durability", "Offense"]
ATTR_TYPES = {"Difficulty": "cost", "Crowd Control": "benefit", "Mobility": "benefit",
              "Utility": "benefit", "Durability": "benefit", "Offense": "benefit"}
ROLES = ["JUNGLING", "MID LANE", "EXP LANE", "ROAMING", "GOLD LANE"]
EVALUATORS = ["Coach", "Player 1", "Player 2"]  # 3 penilai per role
HERO_CLASSES = ["Tank", "Fighter", "Assassin", "Mage", "Marksman", "Support"]

# ============================================================
# UTILITIES
# ============================================================
def parse_frac(v):
    v = str(v).strip()
    if not v: return None
    if "/" in v:
        p = v.split("/")
        return float(p[0]) / float(p[1])
    return float(v)

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
# DB-BACKED LOADERS
# ============================================================
def load_heroes_from_db():
    """Returns (heroes_list, scores_dict)."""
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

def refresh_hero_images_from_db():
    """Refresh image_url & image_public_id pada HEROES in-memory dari DB.
       Dipanggil sebelum render draft page supaya hero baru / image baru langsung
       tampil walau upload terjadi di serverless instance lain (Vercel)."""
    s = get_session()
    if s is None:
        return
    try:
        rows = s.query(Hero.id, Hero.image_url, Hero.image_public_id).all()
        url_by_id = {r[0]: (r[1], r[2]) for r in rows}
        for h in HEROES:
            t = url_by_id.get(h["id"])
            if t:
                h["image_url"] = t[0]
                h["image_public_id"] = t[1]
    except Exception as e:
        print(f"refresh_hero_images_from_db error: {e}")
    finally:
        s.close()


def load_ahp_from_db():
    """Returns matrices dict {role: [m1, m2, m3]} from DB."""
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
        return {role: [m for m in mats if m] for role, mats in out.items()}
    finally:
        s.close()

# Load data at startup — DB-only.
def _startup_or_die():
    if not DB_ENABLED:
        print("\n" + "=" * 70)
        print(" STARTUP GAGAL: DATABASE_URL tidak diset.")
        print(" Set DATABASE_URL di .env, lalu jalankan ulang.")
        print("=" * 70)
        sys.exit(1)
    try:
        init_db()
        seed_default_admin()
        heroes, scores = load_heroes_from_db()
        if not heroes:
            print("\n" + "=" * 70)
            print(" STARTUP GAGAL: DB tersambung tapi tabel heroes kosong.")
            print(" Restore CSV dari git history lalu jalankan `python migrate.py`.")
            print("=" * 70)
            sys.exit(1)
        db_mats_ = load_ahp_from_db()
        return heroes, scores, {r: db_mats_.get(r, []) for r in ROLES}
    except Exception as e:
        print("\n" + "=" * 70)
        print(" STARTUP GAGAL: tidak bisa connect ke Neon Postgres.")
        print(f" Error: {str(e)[:200]}")
        print("")
        print(" Kemungkinan penyebab:")
        print(" 1. ISP/wifi/kampus memblok port 5432 outbound (paling sering).")
        print("    -> Test dengan tethering data HP: kalau jalan = network kantor/kampus block.")
        print(" 2. Firewall Windows / antivirus blok psycopg2.")
        print("    -> Cek Windows Defender > Allow app through firewall.")
        print(" 3. Neon instance suspended atau jaringan Neon down.")
        print("    -> Cek https://console.neon.tech untuk status project Anda.")
        print(" 4. DATABASE_URL salah / password expired.")
        print("    -> Generate ulang connection string di Neon dashboard.")
        print("=" * 70)
        sys.exit(1)


HEROES, SCORES, AHP_MATS = _startup_or_die()

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
    return {"is_admin": current_user() is not None}

app.jinja_env.globals['hero_color'] = hero_color
app.jinja_env.globals['hero_initials'] = hero_initials
app.jinja_env.globals['portrait_html'] = portrait_html

# ============================================================
# ROUTES
# ============================================================
@app.route("/")
def draft():
    refresh_hero_images_from_db()
    return render_template("draft.html", heroes=HEROES, roles=ROLES)

@app.route("/ahp")
@login_required
def ahp():
    return render_template("ahp.html", ahp=AHP_RESULTS, roles=ROLES, criteria=CRITERIA_ORDER)

@app.route("/heroes")
@login_required
def heroes():
    return render_template("heroes.html", heroes=HEROES, roles=ROLES, criteria=CRITERIA_ORDER)

@app.route("/login", methods=["GET", "POST"])
def login():
    # Sudah login? langsung ke admin.
    if current_user() and request.method == "GET":
        return redirect(url_for("admin"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        s = get_session()
        try:
            user = s.query(User).filter_by(username=username).one_or_none() if s else None
            if user and verify_password(password, user.password_hash):
                token = create_jwt(user.username)
                resp = make_response(redirect(url_for("admin")))
                return set_auth_cookie(resp, token)
        finally:
            if s is not None:
                s.close()
        return render_template("login.html", error="Username atau password salah")
    return render_template("login.html")

@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for("draft")))
    return clear_auth_cookie(resp)

@app.route("/admin")
@login_required
def admin():
    role_counts = {r: sum(1 for h in HEROES if r in h["roles"]) for r in ROLES}
    return render_template("admin.html", heroes=HEROES, roles=ROLES, criteria=CRITERIA_ORDER,
                           ahp=AHP_RESULTS, ahp_mats=AHP_MATS, evaluators=EVALUATORS,
                           hero_classes=HERO_CLASSES, role_counts=role_counts)

# --- Hero CRUD ---
@app.route("/admin/create_hero", methods=["POST"])
@login_required
def create_hero():
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
@login_required
def update_hero():
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
@login_required
def delete_hero():
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
@login_required
def upload_hero_image():
    """Multipart POST: form field 'image' (file) + 'id' (hero id).
       Uploads to Cloudinary, persists URL on hero row."""
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
@login_required
def delete_hero_image():
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
@login_required
def update_ahp():
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
