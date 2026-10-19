"""장소 사진 저장소. CLOUDINARY_URL이 있으면 Cloudinary(배포용 무료 이미지 저장소)에,
없으면 로컬 app/static/uploads/places/ 에 저장합니다."""
import os
import pathlib

CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL")
CLOUDINARY_FOLDER = "prague/places"
LOCAL_PREFIX = "/static/uploads/places/"
UPLOAD_DIR = pathlib.Path(__file__).resolve().parent / "static" / "uploads" / "places"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

if CLOUDINARY_URL:
    import cloudinary  # reads CLOUDINARY_URL from the environment on import
    import cloudinary.uploader


def save_photo(content: bytes, fname: str) -> str:
    """Store a photo and return the path/URL to put in places.photo_path."""
    if CLOUDINARY_URL:
        result = cloudinary.uploader.upload(
            content, folder=CLOUDINARY_FOLDER, public_id=pathlib.Path(fname).stem, overwrite=True,
        )
        return result["secure_url"]
    (UPLOAD_DIR / fname).write_bytes(content)
    return LOCAL_PREFIX + fname


def publish_pending(fname: str) -> str:
    """A photo kept in UPLOAD_DIR while the visitor finishes the form becomes the place photo."""
    if not CLOUDINARY_URL:
        return LOCAL_PREFIX + fname
    pending = UPLOAD_DIR / fname
    url = save_photo(pending.read_bytes(), fname)
    pending.unlink(missing_ok=True)
    return url


def delete_photo(photo_path):
    # Only user uploads are removed; journal media stays (the journal still uses it)
    path = photo_path or ""
    if path.startswith(LOCAL_PREFIX):
        (UPLOAD_DIR / path.rsplit("/", 1)[1]).unlink(missing_ok=True)
    elif CLOUDINARY_URL and "res.cloudinary.com" in path and f"/{CLOUDINARY_FOLDER}/" in path:
        stem = path.rsplit("/", 1)[1].rsplit(".", 1)[0]
        cloudinary.uploader.destroy(f"{CLOUDINARY_FOLDER}/{stem}")
