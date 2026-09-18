import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load .env before any os.environ.get() calls below so DATABASE_URL / SECRET_KEY /
# MAP_* / AI_* vars set there are actually picked up (doc: "working .env loading").
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Prototype uses SQLite so the app runs with zero external setup.
    # Models are plain SQLAlchemy (no SQLite-only features) so swapping
    # DATABASE_URL to a mysql+pymysql:// URL later requires no code changes.
    # MySQL is the intended configured database; set DATABASE_URL in .env to
    # something like mysql+pymysql://user:pass@host:3306/nearcart to use it.
    # Falls back to a local SQLite file with zero setup when unset.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "nearcart.db")
    )
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"pool_pre_ping": True, "pool_recycle": 280}
        if SQLALCHEMY_DATABASE_URI.startswith("mysql")
        else {}
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Public images (shop/product/profile photos) live under static/ so
    # Flask serves them directly. Verification documents (PAN/GST/etc.) are
    # kept OUTSIDE static/ and are only ever served through the admin
    # blueprint's authenticated document route (doc #67/#80).
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    PRIVATE_UPLOAD_FOLDER = os.path.join(BASE_DIR, "private_uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB per request

    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

    # Map: prototype uses Leaflet + OpenStreetMap tiles (no API key required).
    # Provider-specific logic is isolated in app/services/map_service.py so
    # this can be swapped for Google Maps / Mapbox without touching routes.
    MAP_PROVIDER = os.environ.get("MAP_PROVIDER", "leaflet")
    MAP_API_KEY = os.environ.get("MAP_API_KEY", "")

    AI_API_KEY = os.environ.get("AI_API_KEY", "")
    AI_ENABLED = bool(AI_API_KEY)

    DEFAULT_SEARCH_RADIUS_KM = 5.0

    WTF_CSRF_TIME_LIMIT = None
