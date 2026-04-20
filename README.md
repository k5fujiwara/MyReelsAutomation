# MyReelsAutomation

`note` と `HP` の記事を取得し、Instagram 用カルーセル画像とキャプションを生成し、そのまま Instagram へカルーセル投稿できる Python プロジェクトです。  
ローカル生成だけでなく、本番環境での自動投稿にも対応できる構成にしています。

## できること

- `note` と `HP` の記事を交互に取得
- RSS から候補記事を集め、ランダムに 1 件選択
- Gemini でカルーセル用コピーとキャプションを生成
- Gemini が失敗した場合はローカル fallback で継続生成
- 3 テーマ (`dark` / `clean` / `energetic`) をローテーション
- 記事内容に応じて 3 枚または 4 枚構成を切り替え
- HTML/CSS を Playwright で描画して `jpg` を出力
- Cloudinary に画像をアップロードして Instagram Graph API でカルーセル投稿

## ディレクトリ構成

```text
MyReelsAutomation/
├─ main.py
├─ article_sources.py
├─ content_generation.py
├─ instagram_publisher.py
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

- `instagram_publisher.py`  
  Cloudinary への画像アップロードと Instagram Graph API を使ったカルーセル投稿を担当します。

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
- 雛形は `.env.example` を参照してください。

## Instagram 自動投稿に必要な環境変数

Instagram への本番投稿を有効にする場合は、以下も設定してください。

```env
INSTAGRAM_BUSINESS_ID=your_instagram_business_id
INSTAGRAM_ACCESS_TOKEN=your_long_lived_access_token
INSTAGRAM_PUBLISH_ENABLED=true
INSTAGRAM_GRAPH_API_VERSION=v22.0

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
CLOUDINARY_FOLDER=myreelsautomation
```

補足:

- Instagram Graph API はローカルファイルを直接受け取れないため、公開 URL 化のために Cloudinary を使っています。
- `INSTAGRAM_PUBLISH_ENABLED=true` の時だけ、画像生成後にそのまま投稿されます。
- 投稿結果は `output/publish_result.json` に保存されます。

## GitHub Actions での本番運用

GitHub Actions 前提で運用する場合は、`.env` ではなく GitHub Secrets を使用してください。  
workflow は `.github/workflows/post-to-instagram.yml` に用意しています。

登録する Secrets:

- `INSTAGRAM_BUSINESS_ID`
- `INSTAGRAM_ACCESS_TOKEN`
- `INSTAGRAM_GRAPH_API_VERSION`  
  未設定でもコード側は `v22.0` を使いますが、Secrets に入れておくと管理しやすいです。
- `GEMINI_API_KEY`
- `GEMINI_MODELS`
- `HP_URL`
- `NOTE_URL`
- `HP_RSS_URL`
- `NOTE_RSS_URL`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `CLOUDINARY_FOLDER`

補足:

- GitHub Actions は毎回クリーンな実行環境で起動するため、`state/` の永続化には依存しません。
- `source` と `theme` のローテーションは、Actions 実行時は日付ベースで決まるようにしています。
- 手動実行時に確認したい場合は、`FORCE_SOURCE` と `FORCE_THEME` を環境変数で上書きできます。
- スケジュールは `cron: "0 22 * * *"` で、UTC 22:00、JST では毎日 07:00 を想定しています。

## 実行方法

```powershell
.\.venv\Scripts\python.exe main.py
```

## 出力されるもの

実行後、`output/` に以下が生成されます。

- `post_1.jpg` から `post_4.jpg`
- `caption.txt`
- `selected_article.txt`
- `publish_result.json`（投稿時のみ）

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

## Instagram 投稿フロー

1. 記事取得
2. Gemini またはローカル fallback でコピー生成
3. Playwright で画像を生成
4. Cloudinary へ画像をアップロード
5. Instagram Graph API でカルーセル子コンテナを作成
6. カルーセル親コンテナを作成
7. 投稿を publish

## 現状の注意点

- `content_generation.py` では現在 `google.generativeai` を利用しています。
- 実行時に非推奨警告が出るため、将来的には `google.genai` への移行を検討してください。
- `output/` と `state/` は生成物置き場のため、Git 管理対象外です。
- `INSTAGRAM_PUBLISH_ENABLED=true` のまま本番トークンを使うと、実行時に実際に投稿されます。
- Meta 側の設定は [developers.facebook.com](https://developers.facebook.com/) で行い、Instagram Graph API を使います。

## Git 管理の方針

- 実装ファイルのみをコミット対象にする
- `.env`、`.venv`、`output/`、`state/`、`__pycache__/` はコミットしない
- 生成結果の確認はローカルで行う
