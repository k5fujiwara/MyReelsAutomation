import os
from pathlib import Path


THEMES = ["dark", "clean", "energetic"]
OUTPUT_DIR = Path("output")
STATE_DIR = Path("state")
LOG_FILE = STATE_DIR / "theme_pos.txt"
LAST_SOURCE_FILE = STATE_DIR / "last_source.txt"
SELECTED_ARTICLE_FILE = OUTPUT_DIR / "selected_article.txt"
CAPTION_FILE = OUTPUT_DIR / "caption.txt"
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


def get_next_source():
    current = ""
    if os.path.exists(LAST_SOURCE_FILE):
        with open(LAST_SOURCE_FILE, "r", encoding="utf-8") as f:
            current = f.read().strip().upper()

    next_source = "NOTE" if current == "HP" else "HP"
    with open(LAST_SOURCE_FILE, "w", encoding="utf-8") as f:
        f.write(next_source)
    return next_source


def get_next_theme():
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
