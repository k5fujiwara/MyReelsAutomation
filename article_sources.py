import html
import os
import random
import re
from pathlib import Path

import feedparser
import requests

from settings import SELECTED_ARTICLE_FILE, log


def get_source_config(source_name):
    configs = {
        "NOTE": {
            "label": "note",
            "rss_url": os.getenv("NOTE_RSS_URL", "").strip(),
            "base_url": os.getenv("NOTE_URL", "").strip(),
        },
        "HP": {
            "label": "HP",
            "rss_url": os.getenv("HP_RSS_URL", "").strip(),
            "base_url": os.getenv("HP_URL", "").strip(),
        },
    }
    return configs[source_name]


def load_target_links():
    path = Path("target_links.txt")
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def pick_random_article(source_name):
    config = get_source_config(source_name)
    entries = []

    if config["rss_url"]:
        feed = feedparser.parse(config["rss_url"])
        for entry in feed.entries:
            link = (getattr(entry, "link", "") or "").strip()
            if not link:
                continue
            if config["base_url"] and config["base_url"] not in link:
                continue
            entries.append(
                {
                    "title": (getattr(entry, "title", "") or "").strip(),
                    "link": link,
                    "summary": html.unescape((getattr(entry, "summary", "") or "").strip()),
                    "source": config["label"],
                }
            )

    if not entries:
        for link in load_target_links():
            if config["base_url"] and config["base_url"] in link:
                entries.append({"title": "", "link": link, "summary": "", "source": config["label"]})

    if not entries:
        raise RuntimeError(f"{config['label']} の候補記事を取得できませんでした")

    article = random.choice(entries)
    log(f"取得元: {config['label']}")
    log(f"対象記事: {article['link']}")
    return article


def strip_html_tags(raw_html):
    cleaned = re.sub(r"(?is)<(script|style|noscript|svg).*?>.*?</\1>", " ", raw_html)
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</p>|</div>|</li>|</section>|</article>|</h[1-6]>", "\n", cleaned)
    cleaned = re.sub(r"(?s)<.*?>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = cleaned.replace("\u3000", " ")
    lines = [re.sub(r"\s+", " ", line).strip() for line in cleaned.splitlines()]
    return "\n".join(line for line in lines if len(line) >= 8)


def extract_article_text(page_html):
    patterns = [
        r"(?is)<article\b.*?>(.*?)</article>",
        r"(?is)<main\b.*?>(.*?)</main>",
        r'(?is)<div[^>]+class="[^"]*(?:post|article|entry-content|content-body|note-common-styles__textnote-body)[^"]*"[^>]*>(.*?)</div>',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, page_html)
        for match in matches:
            text = strip_html_tags(match)
            if len(text) >= 400:
                return text

    return strip_html_tags(page_html)


def fetch_article_detail(article):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    }
    response = requests.get(article["link"], headers=headers, timeout=20)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    page_html = response.text

    title_match = re.search(r'(?is)<meta[^>]+property="og:title"[^>]+content="(.*?)"', page_html)
    page_title = html.unescape(title_match.group(1)).strip() if title_match else article["title"]
    article_text = extract_article_text(page_html)

    detail = {
        "source": article["source"],
        "title": page_title or "タイトル未取得",
        "url": article["link"],
        "summary": article["summary"],
        "body": article_text[:5000],
    }

    with open(SELECTED_ARTICLE_FILE, "w", encoding="utf-8") as f:
        f.write(
            f"source: {detail['source']}\n"
            f"title: {detail['title']}\n"
            f"url: {detail['url']}\n\n"
            f"{detail['body']}"
        )

    return detail
