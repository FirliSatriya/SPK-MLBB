"""
Vercel serverless entry — re-exports the Flask app from the root app.py
so there is a single source of truth. (Previously this file was a full
duplicate which drifted from app.py.)
"""
import os, sys

# Make the project root importable from inside /api/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app  # noqa: E402,F401   (Vercel expects `app` in this module)

# Health endpoint kept here for parity with the previous /health route
from flask import jsonify

@app.route("/health")
def _health():
    from app import HEROES, BASE_DIR
    return jsonify({
        "status": "ok",
        "base_dir": BASE_DIR,
        "heroes_count": len(HEROES),
        "db_enabled": bool(os.environ.get("DATABASE_URL")),
        "cloud_enabled": bool(os.environ.get("CLOUDINARY_URL")),
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
