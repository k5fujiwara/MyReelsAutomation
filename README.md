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
FACEBOOK_ACCESS_TOKEN=your_facebook_graph_access_token
INSTAGRAM_PUBLISH_ENABLED=true
INSTAGRAM_GRAPH_API_VERSION=v22.0

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
CLOUDINARY_FOLDER=myreelsautomation
```

補足:

- Facebook Login 経由で取得した Graph API アクセストークンを使う前提です。
- Instagram Graph API はローカルファイルを直接受け取れないため、公開 URL 化のために Cloudinary を使っています。
- `INSTAGRAM_PUBLISH_ENABLED=true` の時だけ、画像生成後にそのまま投稿されます。
- 投稿結果は `output/publish_result.json` に保存されます。

## FACEBOOK_ACCESS_TOKEN の更新手順

`FACEBOOK_ACCESS_TOKEN` は無期限ではありません。  
平日自動投稿を継続するため、期限切れ前に更新してください。

### まず確認すること

Meta の Access Token Debugger で、現在のトークンの `有効期限` を確認します。

- `developers.facebook.com`
- `Tools`
- `Access Token Debugger`

ここで以下を見ます。

- `有効`
- `有効期限`
- `Scopes`

`有効期限` が 1 時間前後なら短期トークンです。  
本番運用では、約 60 日の長期トークンを使ってください。

### 短期トークンを長期トークンへ交換する

Meta App の `App ID` と `App Secret` を使って、短期トークンを長期トークンへ交換します。

確認場所:

- `developers.facebook.com`
- 対象アプリ
- `Settings`
- `Basic`

そこで以下を確認します。

- `App ID`
- `App Secret`

そのうえで、次の URL をブラウザで開きます。  
`APP_ID`、`APP_SECRET`、`SHORT_LIVED_TOKEN` は自分の値に置き換えてください。

```text
https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN
```

成功すると、次のような JSON が返ります。

```json
{
  "access_token": "EAAB...",
  "token_type": "bearer",
  "expires_in": 5182163
}
```

`expires_in` が数百万秒なら、長期トークンの可能性が高いです。  
返ってきた `access_token` を、もう一度 Access Token Debugger へ入れて `有効期限` を確認してください。

### GitHub Secrets を更新する

長期トークンが取れたら、GitHub の Repository secrets にある `FACEBOOK_ACCESS_TOKEN` を更新します。

手順:

1. リポジトリを開く
2. `Settings`
3. `Secrets and variables`
4. `Actions`
5. `Repository secrets`
6. `FACEBOOK_ACCESS_TOKEN` を更新

注意:

- 値だけを入れる
- `FACEBOOK_ACCESS_TOKEN=` は入れない
- `"` は入れない
- 前後の空白を入れない

### 更新後の確認方法

1. `Actions`
2. `Post To Instagram`
3. `Run workflow`
4. `debug_token_fingerprint=true`

ログの `FACEBOOK_ACCESS_TOKEN SHA256 prefix: ...` を確認し、手元のトークン指紋と一致することを確認します。

PowerShell での確認例:

```powershell
$token = Read-Host "FACEBOOK_ACCESS_TOKEN"
$sha = [System.Security.Cryptography.SHA256]::Create()
$bytes = [System.Text.Encoding]::UTF8.GetBytes($token)
$hash = $sha.ComputeHash($bytes)
$hex = -join ($hash | ForEach-Object { $_.ToString("x2") })
$hex.Substring(0,12)
```

### 運用メモ

- 月 1 回は Access Token Debugger で期限確認
- 遅くとも期限の 1〜2 週間前には更新
- 更新後は GitHub Actions を手動で 1 回流して確認

## GitHub Actions での本番運用

GitHub Actions 前提で運用する場合は、`.env` ではなく GitHub Secrets を使用してください。  
workflow は `.github/workflows/post-to-instagram.yml` に用意しています。

登録する Secrets:

- `INSTAGRAM_BUSINESS_ID`
- `FACEBOOK_ACCESS_TOKEN`  
  Facebook Login 経由で取得した Graph API 用トークンです。
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
- スケジュールは `cron: "30 22 * * 0-4"` で、UTC 22:30、JST では平日 07:30 を想定しています。

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
5. Facebook Graph API 経由でカルーセル子コンテナを作成
6. カルーセル親コンテナを作成
7. 投稿を publish

## 現状の注意点

- `content_generation.py` では現在 `google.generativeai` を利用しています。
- 実行時に非推奨警告が出るため、将来的には `google.genai` への移行を検討してください。
- `output/` と `state/` は生成物置き場のため、Git 管理対象外です。
- `INSTAGRAM_PUBLISH_ENABLED=true` のまま本番トークンを使うと、実行時に実際に投稿されます。
- Meta 側の設定は [developers.facebook.com](https://developers.facebook.com/) で行い、Facebook 経由の Instagram Graph API を使います。

## Git 管理の方針

- 実装ファイルのみをコミット対象にする
- `.env`、`.venv`、`output/`、`state/`、`__pycache__/` はコミットしない
- 生成結果の確認はローカルで行う
