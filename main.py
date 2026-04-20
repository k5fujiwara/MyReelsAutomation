import asyncio
import os
import re

from dotenv import load_dotenv

from article_sources import fetch_article_detail, pick_random_article
from content_generation import (
    build_page3_note,
    build_page4_data,
    determine_page_count,
    generate_plan_text,
)
from renderer import build_html, capture_image
from settings import CAPTION_FILE, OUTPUT_DIR, ensure_runtime_dirs, get_next_source, get_next_theme, log


async def run_process():
    load_dotenv()
    ensure_runtime_dirs()

    if not os.path.exists("template.html"):
        log("template.html がありません")
        return

    with open("template.html", "r", encoding="utf-8") as f:
        template_str = f.read()

    selected_source = get_next_source()
    article = await asyncio.to_thread(pick_random_article, selected_source)
    article_detail = await asyncio.to_thread(fetch_article_detail, article)
    plan_text = await asyncio.to_thread(generate_plan_text, article_detail)

    def ex(tag):
        match = re.search(fr"\[{tag}\]:(.*?)(?=\n\[|$)", plan_text, re.DOTALL)
        return match.group(1).strip() if match else ""

    theme = get_next_theme()
    page_count = determine_page_count(article_detail)
    log(f"ページ構成: {page_count}枚")

    pages = [
        {"type": "P1", "data": {"title1": ex("P1_T1"), "title2": ex("P1_T2"), "catch": ex("P1_C")}},
        {"type": "P2", "data": {"body": ex("P2_B")}},
        {"type": "P3", "data": {"p3_line1": ex("P3_T1"), "p3_line2": ex("P3_T2"), "note": build_page3_note(article_detail)}},
    ]
    if page_count == 4:
        pages.append({"type": "P4", "data": build_page4_data(article_detail)})

    for i, page in enumerate(pages, start=1):
        final_html = build_html(template_str, page["data"], page["type"], i, page_count, theme)
        await capture_image(final_html, str(OUTPUT_DIR / f"post_{i}.jpg"))

    with open(CAPTION_FILE, "w", encoding="utf-8") as f:
        f.write(ex("CAPTION"))
    log(f"キャプションを {CAPTION_FILE} に保存しました")

if __name__ == "__main__":
    asyncio.run(run_process())