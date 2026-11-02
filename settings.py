import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


THEMES = ["dark", "clean", "energetic"]
OUTPUT_DIR = Path("output")
STATE_DIR = Path("state")
LOG_FILE = STATE_DIR / "theme_pos.txt"
LAST_SOURCE_FILE = STATE_DIR / "last_source.txt"
SELECTED_ARTICLE_FILE = OUTPUT_DIR / "selected_article.txt"
CAPTION_FILE = OUTPUT_DIR / "caption.txt"
PUBLISH_RESULT_FILE = OUTPUT_DIR / "publish_result.json"
REQUIRED_TAGS = ["P1_T1", "P1_T2", "P1_C", "P2_B", "P3_T1", "P3_T2", "CAPTION"]
DEFAULT_HASHTAGS = ["#学び", "#自己成長", "#情報発信", "#思考整理"]


def log(message):
    print(message)


def get_configured_models():
    models = os.getenv("GEMINI_MODELS", "")
    return [model.strip() for model in models.split(",") if model.strip()]


def ensure_runtime_dirs():
    OUTPUT_DIR.mkdir(exist_ok=True)
    STATE_DIR.mkdir(exist_ok=True)


def is_running_in_github_actions():
    return os.getenv("GITHUB_ACTIONS", "").strip().lower() == "true"


def _get_rotation_seed():
    manual_seed = os.getenv("ROTATION_SEED", "").strip()
    if manual_seed:
        try:
            return int(manual_seed)
        except ValueError:
            pass

    if is_running_in_github_actions():
        return datetime.now(ZoneInfo("Asia/Tokyo")).date().toordinal()

    return None


def get_next_source():
    forced_source = os.getenv("FORCE_SOURCE", "").strip().upper()
    if forced_source in {"HP", "NOTE"}:
        return forced_source

    rotation_seed = _get_rotation_seed()
    if rotation_seed is not None:
        return "HP" if rotation_seed % 2 == 0 else "NOTE"

    current = ""
    if os.path.exists(LAST_SOURCE_FILE):
        with open(LAST_SOURCE_FILE, "r", encoding="utf-8") as f:
            current = f.read().strip().upper()

    next_source = "NOTE" if current == "HP" else "HP"
    with open(LAST_SOURCE_FILE, "w", encoding="utf-8") as f:
        f.write(next_source)
    return next_source


def get_next_theme():
    forced_theme = os.getenv("FORCE_THEME", "").strip()
    if forced_theme in THEMES:
        return forced_theme

    rotation_seed = _get_rotation_seed()
    if rotation_seed is not None:
        return THEMES[rotation_seed % len(THEMES)]

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("0")
        return THEMES[0]

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        try:
            current_index = int(f.read().strip())
        except ValueError:
            current_index = 0

    next_index = (current_index + 1) % len(THEMES)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(str(next_index))
    return THEMES[next_index]


def is_instagram_publish_enabled():
    value = os.getenv("INSTAGRAM_PUBLISH_ENABLED", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_instagram_publish_config():
    return {
        "business_id": os.getenv("INSTAGRAM_BUSINESS_ID", "").strip(),
        "access_token": os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip(),
        "api_version": os.getenv("INSTAGRAM_GRAPH_API_VERSION", "v22.0").strip() or "v22.0",
        "cloudinary_cloud_name": os.getenv("CLOUDINARY_CLOUD_NAME", "").strip(),
        "cloudinary_api_key": os.getenv("CLOUDINARY_API_KEY", "").strip(),
        "cloudinary_api_secret": os.getenv("CLOUDINARY_API_SECRET", "").strip(),
        "cloudinary_folder": os.getenv("CLOUDINARY_FOLDER", "myreelsautomation").strip() or "myreelsautomation",
    }
