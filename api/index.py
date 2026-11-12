"""
Vercel serverless entry — re-exports the Flask app from the root app.py
so there is a single source of truth. (Previously this file was a full
duplicate which drifted from app.py.)
"""
import os, sys, traceback

# Make the project root importable from inside /api/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _startup_error_body(err: BaseException) -> bytes:
    env_keys = ["DATABASE_URL", "FLASK_SECRET_KEY", "JWT_SECRET_KEY",
                "CLOUDINARY_URL", "ADMIN_USERNAME", "ADMIN_PASSWORD"]
    env_report = "\n".join(
        f"  - {k}: {'SET' if os.environ.get(k) else 'MISSING'}" for k in env_keys
    )
    return (
        "Aplikasi gagal start di Vercel.\n"
        "\n"
        f"{type(err).__name__}: {err}\n"
        "\n"
        f"Python: {sys.version.split()[0]}\n"
        "Environment variables:\n"
        f"{env_report}\n"
        "\n"
        "Cek detail di Vercel -> Deployments -> Functions -> Logs.\n"
        "DATABASE_URL wajib diisi (connection string Neon, mode pooled).\n"
    ).encode("utf-8")


try:
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

except BaseException as _exc:  # SystemExit / ImportError / DB error, dll.
    # Jangan biarkan function mati tanpa pesan — tampilkan penyebabnya.
    traceback.print_exc()
    _body = _startup_error_body(_exc)

    def app(environ, start_response):
        start_response(
            "500 Internal Server Error",
            [("Content-Type", "text/plain; charset=utf-8")],
        )
        return [_body]


if __name__ == "__main__":
    app.run(debug=True, port=5000)
