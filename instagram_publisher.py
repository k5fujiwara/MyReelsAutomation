import hashlib
import mimetypes
import time
from pathlib import Path

import requests

from settings import log


class InstagramPublishError(RuntimeError):
    pass


def _raise_for_response(response, action_label):
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise InstagramPublishError(f"{action_label} に失敗しました: {detail}") from exc


def _upload_image_to_cloudinary(image_path, config):
    cloud_name = config["cloudinary_cloud_name"]
    api_key = config["cloudinary_api_key"]
    api_secret = config["cloudinary_api_secret"]
    folder = config["cloudinary_folder"]

    if not cloud_name or not api_key or not api_secret:
        raise InstagramPublishError(
            "Cloudinary 設定が不足しています。"
            "CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET を設定してください。"
        )

    endpoint = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
    timestamp = int(time.time())
    params = {"timestamp": str(timestamp)}
    if folder:
        params["folder"] = folder

    signature_base = "&".join(f"{key}={value}" for key, value in sorted(params.items()) if value)
    signature = hashlib.sha1(f"{signature_base}{api_secret}".encode("utf-8")).hexdigest()

    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    with open(image_path, "rb") as file_obj:
        response = requests.post(
            endpoint,
            data={**params, "api_key": api_key, "signature": signature},
            files={"file": (Path(image_path).name, file_obj, mime_type)},
            timeout=60,
        )

    _raise_for_response(response, f"Cloudinary アップロード ({Path(image_path).name})")
    body = response.json()
    secure_url = body.get("secure_url", "").strip()
    if not secure_url:
        raise InstagramPublishError("Cloudinary のレスポンスに secure_url がありませんでした")
    return secure_url


def _instagram_request(method, endpoint, access_token, *, api_version="v22.0", params=None, data=None):
    url = f"https://graph.facebook.com/{api_version}/{endpoint.lstrip('/')}"
    if method.upper() == "GET":
        response = requests.get(url, params={**(params or {}), "access_token": access_token}, timeout=60)
    else:
        response = requests.post(url, data={**(data or {}), "access_token": access_token}, timeout=60)

    _raise_for_response(response, f"Facebook Graph API 呼び出し ({endpoint})")
    return response.json()


def _wait_for_container_ready(creation_id, access_token, *, api_version="v22.0", timeout_seconds=300):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        body = _instagram_request(
            "GET",
            creation_id,
            access_token,
            api_version=api_version,
            params={"fields": "status_code"},
        )
        status_code = (body.get("status_code") or "").strip().upper()
        if not status_code or status_code == "FINISHED":
            return
        if status_code in {"ERROR", "EXPIRED"}:
            raise InstagramPublishError(f"コンテナ処理が失敗しました: {creation_id} ({status_code})")
        time.sleep(5)
    raise InstagramPublishError(f"コンテナ処理がタイムアウトしました: {creation_id}")


def publish_instagram_carousel(image_paths, caption, config):
    business_id = config["business_id"]
    access_token = config["access_token"]
    api_version = config["api_version"]

    if not business_id or not access_token:
        raise InstagramPublishError(
            "Instagram 設定が不足しています。"
            "INSTAGRAM_BUSINESS_ID と FACEBOOK_ACCESS_TOKEN を設定してください。"
        )

    if len(image_paths) < 2:
        raise InstagramPublishError("カルーセル投稿には 2 枚以上の画像が必要です")

    cloudinary_urls = []
    for image_path in image_paths:
        log(f"画像を Cloudinary へアップロードします: {Path(image_path).name}")
        cloudinary_urls.append(_upload_image_to_cloudinary(image_path, config))

    child_ids = []
    for image_url in cloudinary_urls:
        body = _instagram_request(
            "POST",
            f"{business_id}/media",
            access_token,
            api_version=api_version,
            data={
                "image_url": image_url,
                "is_carousel_item": "true",
            },
        )
        creation_id = body.get("id", "").strip()
        if not creation_id:
            raise InstagramPublishError("子コンテナ作成結果に id がありませんでした")
        _wait_for_container_ready(creation_id, access_token, api_version=api_version)
        child_ids.append(creation_id)

    carousel_body = _instagram_request(
        "POST",
        f"{business_id}/media",
        access_token,
        api_version=api_version,
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
        },
    )
    carousel_creation_id = carousel_body.get("id", "").strip()
    if not carousel_creation_id:
        raise InstagramPublishError("カルーセルコンテナ作成結果に id がありませんでした")

    _wait_for_container_ready(carousel_creation_id, access_token, api_version=api_version)

    publish_body = _instagram_request(
        "POST",
        f"{business_id}/media_publish",
        access_token,
        api_version=api_version,
        data={"creation_id": carousel_creation_id},
    )
    published_media_id = publish_body.get("id", "").strip()
    if not published_media_id:
        raise InstagramPublishError("Instagram 投稿結果に media id がありませんでした")

    published_info = _instagram_request(
        "GET",
        published_media_id,
        access_token,
        api_version=api_version,
        params={"fields": "id,permalink"},
    )

    return {
        "media_id": published_info.get("id", published_media_id),
        "permalink": published_info.get("permalink", ""),
        "child_container_ids": child_ids,
        "carousel_container_id": carousel_creation_id,
        "uploaded_image_urls": cloudinary_urls,
    }
