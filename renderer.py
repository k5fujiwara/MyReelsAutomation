import asyncio
import html
import os
import re
from pathlib import Path

from playwright.async_api import async_playwright

from settings import log


async def capture_image(html_content, output_name):
    temp_file = Path(os.getcwd()) / "temp_render.html"
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1080, "height": 1080})
            await page.goto(temp_file.as_uri())
            await page.evaluate("document.fonts.ready")
            await asyncio.sleep(2)
            await page.screenshot(path=output_name, type="jpeg", quality=95)
            log(f"画像生成完了: {output_name}")
            await browser.close()
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def _weighted_text_length(text):
    score = 0.0
    for char in text:
        if re.match(r"[A-Za-z0-9]", char):
            score += 0.65
        elif char in " ・/":
            score += 0.4
        else:
            score += 1.0
    return score


def _format_p1_title(text):
    normalized = re.sub(r"\s+", "", text or "")
    if not normalized:
        return ""

    if _weighted_text_length(normalized) <= 13.5:
        return html.escape(normalized)

    preferred_chars = "でがをはにへと"
    fallback_chars = "のアイデア力戦略術法学"
    candidates = []

    for index in range(2, len(normalized) - 2):
        left = normalized[:index]
        right = normalized[index:]
        balance_penalty = abs(_weighted_text_length(left) - _weighted_text_length(right))
        score = balance_penalty

        prev_char = normalized[index - 1]
        if prev_char in preferred_chars:
            score -= 1.2
        elif prev_char in fallback_chars:
            score += 0.5

        if len(left) < 4 or len(right) < 4:
            score += 2

        candidates.append((score, index))

    if not candidates:
        return html.escape(normalized)

    _, split_at = min(candidates, key=lambda item: item[0])
    return f"{html.escape(normalized[:split_at])}<br>{html.escape(normalized[split_at:])}"


def build_html(template, data, page_type, page_num, total_pages, theme):
    if page_type == "P1":
        formatted_title = _format_p1_title(data["title2"])
        content_html = f"""
        <div class="page1">
            <div class="hero-kicker fit-text" data-fit-lines="1" data-min-size="28">{data["title1"]}</div>
            <div class="title-group">
                <div class="title-line2 fit-text" data-fit-lines="2" data-min-size="112">{formatted_title}</div>
            </div>
            <div class="accent-line"></div>
            <div class="catch fit-text" data-fit-lines="2" data-min-size="34">{data["catch"]}</div>
        </div>"""
    elif page_type == "P2":
        items = data["body"].split("\n")
        dense_class = " dense" if any(len(line.strip()) >= 18 for line in items if line.strip()) else ""
        item_list = [
            f'<div class="content-item"><div class="icon-wrap"><div class="icon-border"></div></div><div class="content-text fit-text" data-fit-lines="2" data-min-size="50">{line}</div></div>'
            for line in items
            if line.strip()
        ]
        content_html = f'<div class="page2{dense_class}">{"".join(item_list)}</div>'
    elif page_type == "P3":
        content_html = f"""
        <div class="page3">
            <div class="p3-main fit-text" data-fit-lines="2" data-min-size="88">{data["p3_line1"]}</div>
            <div class="p3-accent-line"></div>
            <div class="p3-support fit-text" data-fit-lines="2" data-min-size="46">{data["p3_line2"]}</div>
            <div class="p3-note">{data["note"]}</div>
        </div>"""
    else:
        points_html = "".join(
            f'<div class="p4-point"><span class="p4-point-num">{index:02d}</span><span class="p4-point-text">{point}</span></div>'
            for index, point in enumerate(data["points"], start=1)
        )
        content_html = f"""
        <div class="page4">
            <div class="p4-main fit-text" data-fit-lines="2" data-min-size="66">{data["main"]}</div>
            <div class="p4-sub fit-text" data-fit-lines="2" data-min-size="52">{data["sub"]}</div>
            <div class="p4-accent-line"></div>
            <div class="p4-label">{data["label"]}</div>
            <div class="p4-points">{points_html}</div>
        </div>"""

    return (
        template.replace("{{CONTENT}}", content_html)
        .replace("{{PAGE_NUM}}", str(page_num))
        .replace("{{PAGE_TOTAL}}", str(total_pages))
        .replace("{{THEME_CLASS}}", f"theme-{theme}")
    )
