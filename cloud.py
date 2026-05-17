"""
Cloudinary upload/delete wrapper.
Requires env var CLOUDINARY_URL = cloudinary://API_KEY:API_SECRET@CLOUD_NAME
"""
import os

CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "").strip()

# Cloudinary library validates CLOUDINARY_URL at import time. If the user set
# CLOUDINARY_URL to the placeholder string from .env.example (which fails
# validation), the bare `import cloudinary` would crash the whole app. To
# survive that, we unset the env var when it doesn't look real, import the lib
# blank, then re-apply config only when the URL really looks valid.
_looks_valid = CLOUDINARY_URL.startswith("cloudinary://") and "API_KEY" not in CLOUDINARY_URL
if CLOUDINARY_URL and not _looks_valid:
    print(f"[cloud] CLOUDINARY_URL is set but looks like a placeholder or invalid format. "
          f"Image upload disabled. Got: {CLOUDINARY_URL[:30]}...")
    # Temporarily hide from cloudinary lib so import doesn't blow up
    os.environ.pop("CLOUDINARY_URL", None)

try:
    import cloudinary
    import cloudinary.uploader
    _CLOUD_LIB_OK = True
except ImportError:
    _CLOUD_LIB_OK = False
except ValueError as e:
    # Defensive: even after our pre-check, just in case
    print(f"[cloud] Cloudinary import failed ({e}). Image upload disabled.")
    _CLOUD_LIB_OK = False

# Restore env var so other code can still read the raw value (informational)
if CLOUDINARY_URL and not _looks_valid:
    os.environ["CLOUDINARY_URL"] = CLOUDINARY_URL

CLOUD_ENABLED = _looks_valid and _CLOUD_LIB_OK
if CLOUD_ENABLED:
    cloudinary.config(secure=True)  # picks up CLOUDINARY_URL automatically

def upload_hero_image(file_storage, hero_id):
    """
    file_storage: Werkzeug FileStorage (request.files['image'])
    hero_id:      e.g. "H042"
    Returns (url, public_id) or (None, None) on failure.
    """
    if not CLOUD_ENABLED:
        return None, None
    res = cloudinary.uploader.upload(
        file_storage,
        folder="mlbb-heroes",
        public_id=hero_id,           # stable id per hero — re-upload overwrites
        overwrite=True,
        resource_type="image",
        transformation=[{"width": 400, "height": 400, "crop": "fill", "gravity": "face"}],
    )
    return res.get("secure_url"), res.get("public_id")

def delete_hero_image(public_id):
    if not CLOUD_ENABLED or not public_id:
        return False
    try:
        cloudinary.uploader.destroy(public_id, resource_type="image")
        return True
    except Exception:
        return False
