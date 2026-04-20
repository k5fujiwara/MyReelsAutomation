import os
import re

from settings import DEFAULT_HASHTAGS, REQUIRED_TAGS, get_configured_models, log

try:
    import google.generativeai as genai
except ImportError:
    genai = None


def clean_article_title(title):
    cleaned = re.sub(r"\s+", " ", title).strip()
    cleaned = re.sub(r"\s*[|｜]\s*塾講師K5.*$", "", cleaned)
    cleaned = re.sub(r"\s*[|｜]\s*.*学習準備室.*$", "", cleaned)
    return cleaned.strip()


def build_prompt(article_detail):
    return f"""
Instagramのカルーセル投稿用に、以下のタグ形式だけで日本語の出力を返してください。
説明文や前置きは不要です。

[P1_T1]: 1ページ目の1行目タイトル
[P1_T2]: 1ページ目の2行目タイトル
[P1_C]: 1ページ目のキャッチコピー
[P2_B]: 2ページ目の本文。改行区切りで3行
[P3_T1]: 3ページ目の1行目
[P3_T2]: 3ページ目の2行目
[CAPTION]:
キャプション本文

元記事媒体: {article_detail["source"]}
元記事タイトル: {article_detail["title"]}
元記事URL: {article_detail["url"]}
元記事要約候補:
{article_detail["summary"] or "なし"}

記事本文:
{article_detail["body"]}

条件:
- 3ページ構成のカルーセル
- 記事の内容をそのまま縮めるのではなく、ブランド感のある短いコピーに再編集する
- 読み手が一瞬で意味を理解できる、強くて短い表現にする
- 日本語として自然で簡潔
- P1_T1 は導入ラベルとして3文字から8文字程度
- P1_T2 は表紙の主見出しとして6文字から16文字程度
- P1_C は補助文として14文字から28文字程度で、1文に収める
- P1 ではスクロールを止めるフックを作る
- P3_T1 は結論の主見出しとして6文字から14文字程度
- P3_T2 は行動や締めの一言として10文字から24文字程度
- P3 では結論や次の行動を明確にする
- P2_B は改行区切りで3行
- P2_B の各行は20文字前後で、学びが一目で分かる文にする
- CAPTION では元記事に触れる
- メンションは入れない
- CAPTION は可読性を最優先し、2から4個の短い段落で構成する
- CAPTION の途中に URL を混ぜず、最後に「URL（コピペ用）」として別行で置く
- ハッシュタグは最後に3個から4個だけ入れる
""".strip()


def is_valid_plan_text(plan_text):
    return all(f"[{tag}]:" in plan_text for tag in REQUIRED_TAGS)


def is_noise_chunk(text):
    stripped = text.strip()
    if not stripped:
        return True
    if re.search(r"https?://", stripped):
        return True
    if re.fullmatch(r"\d{4}年\d{1,2}月\d{1,2}日.*", stripped):
        return True
    if re.fullmatch(r"\d{1,2}:\d{2}", stripped):
        return True
    if "塾講師K5" in stripped and len(stripped) < 40:
        return True
    if len(re.findall(r"[「」【】|｜:：]", stripped)) >= 4 and len(stripped) > 35:
        return True
    return False


def make_sentence_chunks(text, limit=3):
    pieces = re.split(r"[。！？\n]+", text)
    chunks = []
    for piece in pieces:
        piece = re.sub(r"\s+", " ", piece).strip(" ・-")
        if len(piece) >= 12 and not is_noise_chunk(piece):
            chunks.append(piece)
        if len(chunks) == limit:
            break
    return chunks


def determine_page_count(article_detail):
    sentence_chunks = make_sentence_chunks(article_detail["body"], limit=8)
    summary_text = f"{clean_article_title(article_detail['title'])} {article_detail['summary']}".strip()
    score = 0

    if len(article_detail["body"]) >= 1400:
        score += 2
    elif len(article_detail["body"]) >= 800:
        score += 1

    if len(sentence_chunks) >= 5:
        score += 1
    if len(summary_text) >= 70:
        score += 1
    if article_detail["source"] == "HP":
        score += 1

    return 4 if score >= 2 else 3


def classify_article_topic(article_detail):
    text = f"{clean_article_title(article_detail['title'])} {article_detail['summary']}".strip()
    topic_rules = [
        ("education", ["内申", "高校入試", "受験", "中学生", "授業態度", "勉強", "学習", "教育"]),
        ("communication", ["コミュニケーション", "人間関係", "信頼", "誤解", "対話", "傾聴", "自己開示"]),
        ("automation", ["GitHub Actions", "workflow", "ワークフロー", "自動化", "AI", "プログラミング", "SNS投稿"]),
        ("leadership", ["リーダー", "チーム", "マネジメント", "組織"]),
        ("habit", ["継続", "習慣", "積み上げ", "努力", "発信", "PV"]),
        ("money", ["投資", "資産", "お金", "複利", "資産形成"]),
        ("career", ["仕事術", "仕事", "成果", "キャリア", "生産性"]),
    ]

    best_topic = "general"
    best_score = 0
    for topic, keywords in topic_rules:
        score = sum(1 for keyword in keywords if keyword in text)
        if score > best_score:
            best_score = score
            best_topic = topic
    return best_topic


def pick_brand_template(article_detail):
    text = f"{article_detail['title']} {article_detail['summary']} {article_detail['body']}"
    topic = classify_article_topic(article_detail)
    templates = [
        {
            "keywords": ["内申", "高校入試", "受験", "中学生", "授業態度"],
            "p1_t1": "高校入試は",
            "p1_t2": "内申で差がつく",
            "p1_c": "テストだけでは、合否は決まらない。",
            "p3_t1": "今日から変える",
            "p3_t2": "授業態度と質問の質",
        },
        {
            "keywords": ["GitHub Actions", "workflow", "ワークフロー", "自動化", "SNS投稿"],
            "p1_t1": "発信は",
            "p1_t2": "仕組みで伸ばす",
            "p1_c": "続く発信は、気合いより設計で決まる。",
            "p3_t1": "回る仕組みが",
            "p3_t2": "発信の質を上げる",
        },
        {
            "keywords": ["継続", "積み上げ", "PV", "毎月", "発信"],
            "p1_t1": "結局は",
            "p1_t2": "積み上げが勝つ",
            "p1_c": "派手さより、継続が後から効いてくる。",
            "p3_t1": "伸びる人ほど",
            "p3_t2": "淡々と続けている",
        },
        {
            "keywords": ["投資", "資産形成", "お金", "複利"],
            "p1_t1": "資産形成は",
            "p1_t2": "仕組みで決まる",
            "p1_c": "お金は、一発より積み上げで増えていく。",
            "p3_t1": "増やす力は",
            "p3_t2": "習慣の中で育つ",
        },
    ]

    topic_fallbacks = {
        "education": {
            "p1_t1": "進路は",
            "p1_t2": "日々で決まる",
            "p1_c": "本番の前に、差は日常で生まれている。",
            "p3_t1": "今日の行動が",
            "p3_t2": "次の結果を変える",
        },
        "communication": {
            "p1_t1": "信頼構築",
            "p1_t2": "心を掴む秘訣",
            "p1_c": "関係は、伝え方より向き合い方で変わる。",
            "p3_t1": "関係を深める",
            "p3_t2": "小さな行動から始める",
        },
        "automation": {
            "p1_t1": "仕組み化",
            "p1_t2": "人の時間を増やす",
            "p1_c": "単純作業は、仕組みに任せて前へ進む。",
            "p3_t1": "自動化で",
            "p3_t2": "本当に大事な仕事へ",
        },
        "leadership": {
            "p1_t1": "組織づくり",
            "p1_t2": "人で差がつく",
            "p1_c": "成果は、個人技よりチーム設計で決まる。",
            "p3_t1": "強い組織は",
            "p3_t2": "任せ方で育つ",
        },
        "habit": {
            "p1_t1": "積み上げは",
            "p1_t2": "静かに効く",
            "p1_c": "目立たなくても、続けた人が最後に勝つ。",
            "p3_t1": "次を変えるのは",
            "p3_t2": "今日の継続",
        },
        "money": {
            "p1_t1": "お金は",
            "p1_t2": "仕組みで守る",
            "p1_c": "増やす前に、整える力が差を生む。",
            "p3_t1": "資産形成は",
            "p3_t2": "習慣で前に進む",
        },
        "career": {
            "p1_t1": "仕事術",
            "p1_t2": "成果は待たない",
            "p1_c": "苦しい時期ほど、動き方の質が試される。",
            "p3_t1": "耐える時間も",
            "p3_t2": "次の成果に変えられる",
        },
    }

    for template in templates:
        if any(keyword in text for keyword in template["keywords"]):
            return template
    if topic in topic_fallbacks:
        return topic_fallbacks[topic]

    return {
        "p1_t1": "要点だけで",
        "p1_t2": "価値は伝わる",
        "p1_c": "長く語るより、刺さる一言が記憶に残る。",
        "p3_t1": "最後は",
        "p3_t2": "行動に変えて終わる",
    }


def infer_hashtags(article_detail):
    text = f"{clean_article_title(article_detail['title'])} {article_detail['summary']}"
    hashtag_sets = [
        (["内申", "高校入試", "受験", "中学生", "授業態度"], ["#高校受験", "#内申点", "#勉強法", "#中学生"]),
        (["コミュニケーション", "人間関係", "信頼", "誤解", "対話"], ["#コミュニケーション", "#人間関係", "#信頼関係", "#対話力"]),
        (["GitHub Actions", "workflow", "自動化", "AI", "プログラミング"], ["#AI", "#プログラミング", "#業務効率化", "#自動化"]),
        (["リーダー", "チーム", "マネジメント", "組織"], ["#リーダーシップ", "#チームビルディング", "#マネジメント", "#組織づくり"]),
        (["継続", "習慣", "積み上げ", "努力"], ["#継続力", "#習慣化", "#自己成長", "#積み上げ"]),
        (["投資", "資産", "お金", "複利"], ["#資産形成", "#投資", "#お金の勉強", "#複利"]),
        (["勉強", "学習", "教育", "受験"], ["#学習法", "#教育", "#勉強法", "#成長"]),
        (["仕事術", "仕事", "成果", "キャリア", "生産性"], ["#仕事術", "#キャリア", "#自己成長", "#思考整理"]),
    ]

    best_tags = DEFAULT_HASHTAGS
    best_score = 0
    for keywords, tags in hashtag_sets:
        score = sum(1 for keyword in keywords if keyword in text)
        if score > best_score:
            best_score = score
            best_tags = tags

    if best_score > 0:
        return best_tags
    return DEFAULT_HASHTAGS


def build_page4_data(article_detail):
    topic = classify_article_topic(article_detail)
    cta_map = {
        "education": {
            "main": "明日から",
            "sub": "差がつく行動へ",
            "label": "見返しポイント",
            "points": ["授業態度を整える", "質問を1つ増やす", "提出を先回りする"],
        },
        "communication": {
            "main": "次の会話で",
            "sub": "1つ試す",
            "label": "見返しポイント",
            "points": ["最後まで聴く", "先に与える", "弱みを少し見せる"],
        },
        "automation": {
            "main": "次の改善を",
            "sub": "1つ決める",
            "label": "見返しポイント",
            "points": ["繰り返し作業を探す", "自動化候補を書き出す", "仕組みに任せる"],
        },
        "leadership": {
            "main": "強い組織は",
            "sub": "任せ方で育つ",
            "label": "見返しポイント",
            "points": ["役割を明確にする", "期待値をそろえる", "任せた後も観察する"],
        },
        "habit": {
            "main": "続ける人が",
            "sub": "最後に勝つ",
            "label": "見返しポイント",
            "points": ["今日の1回を止めない", "完璧より継続を選ぶ", "積み上げを見える化する"],
        },
        "money": {
            "main": "迷った時ほど",
            "sub": "仕組みで決める",
            "label": "見返しポイント",
            "points": ["感情で動かない", "基準を先に決める", "小さく整えて続ける"],
        },
        "career": {
            "main": "待つ間も",
            "sub": "前に進める",
            "label": "見返しポイント",
            "points": ["状況を観察する", "動き方を修正する", "次の一手を準備する"],
        },
    }
    return cta_map.get(
        topic,
        {
            "main": "明日から",
            "sub": "動きを変える",
            "label": "見返しポイント",
            "points": ["要点を1つ残す", "行動を1つ決める", "次の改善へつなげる"],
        },
    )


def build_page3_note(article_detail):
    topic = classify_article_topic(article_detail)
    note_map = {
        "education": "明日の行動を1つ決める",
        "communication": "次の会話で1つ試す",
        "automation": "次の改善案を書き出す",
        "leadership": "任せ方を1つ見直す",
        "habit": "今日の継続を止めない",
        "money": "次の判断基準にする",
        "career": "次の一手を言葉にする",
    }
    return note_map.get(topic, "大事な視点を残しておく")


def build_fallback_p2_lines(article_detail):
    topic = classify_article_topic(article_detail)
    topic_lines = {
        "education": [
            "定期テストで実力を示す",
            "提出物は質と期限で差がつく",
            "授業中の積極性が評価を分ける",
        ],
        "communication": [
            "相手を最後まで聴く",
            "先に与えて信頼をつくる",
            "本音を少しだけ開く",
        ],
        "automation": [
            "手作業を洗い出す",
            "繰り返しは仕組みに任せる",
            "浮いた時間を価値に変える",
        ],
        "leadership": [
            "自分で抱え込まない",
            "期待値を先にそろえる",
            "任せた後こそ観察する",
        ],
        "habit": [
            "今日の1回を止めない",
            "完璧より継続を選ぶ",
            "積み上げを見える化する",
        ],
        "money": [
            "感情より基準で決める",
            "小さく積んで守り続ける",
            "増やす前に整える",
        ],
        "career": [
            "待つ時間も準備に変える",
            "結果より動き方を磨く",
            "次の一手を言葉にする",
        ],
        "general": [
            "要点を短くつかむ",
            "行動を1つ決める",
            "次の改善へつなげる",
        ],
    }
    return topic_lines.get(topic, topic_lines["general"])


def build_local_fallback_plan(article_detail):
    body_lines = build_fallback_p2_lines(article_detail)

    template = pick_brand_template(article_detail)
    hashtags = infer_hashtags(article_detail)
    caption_lines = [
        "今回の学びを、短く整理します。",
        "",
        "【今回のポイント】",
        f"・{body_lines[0]}",
        f"・{body_lines[1]}",
        f"・{body_lines[2]}",
        "",
        "詳しい背景は元記事もあわせてどうぞ。",
        "",
        f"元記事: {article_detail['title']}",
        f"URL（コピペ用）: {article_detail['url']}",
        "",
        " ".join(hashtags),
    ]

    return "\n".join(
        [
            f"[P1_T1]: {template['p1_t1']}",
            f"[P1_T2]: {template['p1_t2']}",
            f"[P1_C]: {template['p1_c']}",
            f"[P2_B]: " + "\n".join(body_lines[:3]),
            f"[P3_T1]: {template['p3_t1']}",
            f"[P3_T2]: {template['p3_t2']}",
            "[CAPTION]:",
            "\n".join(caption_lines).strip(),
        ]
    ).strip()


def normalize_caption(plan_text, article_detail):
    match = re.search(r"(\[CAPTION\]:\s*)(.*)", plan_text, re.DOTALL)
    if not match:
        return plan_text

    caption = match.group(2).strip()
    caption = re.sub(r"(?m)(?<!\S)@\S+", "", caption)
    caption = re.sub(r"(?im)^\s*url[:：].*$", "", caption)
    caption = re.sub(r"(?im)^\s*元記事url[:：].*$", "", caption)
    caption = re.sub(r"(?im)^\s*url（[^）]*）[:：]?\s*$", "", caption)
    caption = re.sub(r"(?im)^\s*url\([^)]*\)[:：]?\s*$", "", caption)
    final_hashtags = infer_hashtags(article_detail)[:4]

    caption_without_urls = re.sub(r"https?://\S+", "", caption)
    caption_without_tags = re.sub(r"#(?:[^\s#]+)", "", caption_without_urls)
    caption_without_tags = re.sub(r"\n{3,}", "\n\n", caption_without_tags).strip()
    caption_without_tags = re.sub(r"[ \t]{2,}", " ", caption_without_tags)

    if f"元記事: {article_detail['title']}" not in caption_without_tags:
        caption_without_tags = (f"{caption_without_tags}\n\n" f"元記事: {article_detail['title']}").strip()

    normalized_caption = (
        f"{caption_without_tags}\n"
        f"URL（コピペ用）: {article_detail['url']}\n\n"
        f"{' '.join(final_hashtags)}"
    ).strip()
    return f"{plan_text[:match.start(2)]}{normalized_caption}"


def generate_plan_text(article_detail):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    models = get_configured_models()
    fallback_plan = build_local_fallback_plan(article_detail)

    if not api_key:
        log("GEMINI_API_KEY が未設定のため、固定テストデータを使います")
        return fallback_plan

    if not models:
        log("GEMINI_MODELS が未設定のため、固定テストデータを使います")
        return fallback_plan

    if genai is None:
        log("google.generativeai を読み込めないため、固定テストデータを使います")
        return fallback_plan

    genai.configure(api_key=api_key)
    prompt = build_prompt(article_detail)
    last_error = None

    for model_name in models:
        try:
            log(f"Gemini モデルを試行します: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            plan_text = normalize_caption((getattr(response, "text", "") or "").strip(), article_detail)

            if not plan_text:
                raise ValueError("レスポンス本文が空でした")
            if not is_valid_plan_text(plan_text):
                raise ValueError("必要タグが不足しています")

            log(f"Gemini モデル採用: {model_name}")
            return plan_text
        except Exception as exc:
            last_error = exc
            log(f"Gemini モデル失敗: {model_name} ({exc})")

    if last_error is not None:
        log(f"全モデル失敗のため固定テストデータを使います: {last_error}")
    return fallback_plan
