"""File upload validation (doc #67/#80). Verification documents are stored
under a path that is never served by the public /static/uploads/... route
for shop/product images; they are only served through an admin-authenticated
route (see admin_controller.document)."""
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

VERIFICATION_SUBDIR = "verification"
SHOP_SUBDIR = "shops"
PRODUCT_SUBDIR = "products"
PROFILE_SUBDIR = "profiles"


class InvalidFile(Exception):
    pass


def _ext(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def save_image(file_storage, subdir):
    if not file_storage or not file_storage.filename:
        return None
    ext = _ext(file_storage.filename)
    if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        raise InvalidFile("Unsupported image type. Use PNG, JPG or WEBP.")
    return _save(file_storage, subdir, ext)


def save_document(file_storage, subdir=VERIFICATION_SUBDIR):
    """Saves to PRIVATE_UPLOAD_FOLDER (never under static/), so the file is
    not publicly reachable by URL guessing."""
    if not file_storage or not file_storage.filename:
        return None
    ext = _ext(file_storage.filename)
    if ext not in current_app.config["ALLOWED_DOCUMENT_EXTENSIONS"]:
        raise InvalidFile("Unsupported document type. Use PDF, PNG or JPG.")
    safe_name = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    folder = os.path.join(current_app.config["PRIVATE_UPLOAD_FOLDER"], subdir)
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, safe_name))
    return f"{subdir}/{safe_name}"


def _save(file_storage, subdir, ext):
    safe_name = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subdir)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, safe_name)
    file_storage.save(path)
    return f"{subdir}/{safe_name}"
