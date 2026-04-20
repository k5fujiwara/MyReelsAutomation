# MyReelsAutomation

`note` と `HP` の記事を取得し、Instagram 用カルーセル画像とキャプション素材をローカル生成する Python プロジェクトです。  
現在は投稿そのものではなく、記事取得、要約、コピー生成、画像レンダリングの検証を主目的にしています。

## できること

- `note` と `HP` の記事を交互に取得
- RSS から候補記事を集め、ランダムに 1 件選択
- Gemini でカルーセル用コピーとキャプションを生成
- Gemini が失敗した場合はローカル fallback で継続生成
- 3 テーマ (`dark` / `clean` / `energetic`) をローテーション
- 記事内容に応じて 3 枚または 4 枚構成を切り替え
- HTML/CSS を Playwright で描画して `jpg` を出力

## ディレクトリ構成

```text
MyReelsAutomation/
├─ main.py
├─ article_sources.py
├─ content_generation.py
├─ renderer.py
├─ render.js
├─ settings.py
├─ template.html
├─ style.css
├─ requirements.txt
├─ target_links.txt
├─ output/        # 生成画像・caption・選択記事
├─ state/         # ローテーション状態
└─ .env
```

## 主なファイル

- `main.py`  
  全体の実行入口です。記事取得、コピー生成、画像生成、キャプション保存を順番に実行します。

- `article_sources.py`  
  RSS 取得、候補記事選定、本文抽出を担当します。

- `content_generation.py`  
  Gemini へのプロンプト生成、トピック判定、fallback コピー生成、ハッシュタグ整形を担当します。

- `renderer.py`  
  各ページの HTML を組み立て、Playwright で画像化します。

- `settings.py`  
  出力先、テーマローテーション、使用モデル一覧などの設定をまとめています。

## 必要環境

- Python 3.11 以降推奨
- Windows / PowerShell で動作確認
- Chromium を使える Playwright 環境

## セットアップ

### 1. 仮想環境を作成

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 依存関係をインストール

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

## 環境変数

`.env` に最低限、以下を設定してください。

```env
GEMINI_API_KEY=your_api_key
GEMINI_MODELS=gemini-3.1-flash-lite-preview,gemini-2.5-flash,gemini-2.5-flash-lite,gemini-2.0-flash

HP_URL=https://info-study.com/
NOTE_URL=https://note.com/your_account
HP_RSS_URL=https://info-study.com/feed
NOTE_RSS_URL=https://note.com/your_account/rss
```

補足:

- `.env` は `.gitignore` に含まれているため、Git へは追加しません。
- Instagram 用の値を入れていても、現状の `main.py` は投稿処理までは行いません。

## 実行方法

```powershell
.\.venv\Scripts\python.exe main.py
```

## 出力されるもの

実行後、`output/` に以下が生成されます。

- `post_1.jpg` から `post_4.jpg`
- `caption.txt`
- `selected_article.txt`

`state/` には以下が保存されます。

- `last_source.txt`  
  次回取得する媒体の切り替え用
- `theme_pos.txt`  
  テーマローテーション用

## 記事取得の優先順

1. RSS から候補記事を取得
2. 候補が取れない場合は `target_links.txt` を参照

## モデル fallback の考え方

`GEMINI_MODELS` に設定されたモデルを上から順に試します。  
成功したモデルが採用され、すべて失敗した場合はローカル fallback に切り替わります。

## 現状の注意点

- `content_generation.py` では現在 `google.generativeai` を利用しています。
- 実行時に非推奨警告が出るため、将来的には `google.genai` への移行を検討してください。
- `output/` と `state/` は生成物置き場のため、Git 管理対象外です。

## Git 管理の方針

- 実装ファイルのみをコミット対象にする
- `.env`、`.venv`、`output/`、`state/`、`__pycache__/` はコミットしない
- 生成結果の確認はローカルで行う
