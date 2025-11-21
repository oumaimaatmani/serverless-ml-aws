"""
Lambda: Presigned URL Generator
Purpose: Issue secure S3 presigned PUT URLs for image uploads.
"""
import json
import os
import logging
import uuid
import re
from datetime import datetime
from typing import Dict, Any

import boto3

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

s3 = boto3.client("s3")

IMAGES_BUCKET = os.environ.get("IMAGES_BUCKET")
EXPIRATION = int(os.environ.get("PRESIGNED_URL_EXPIRATION", 300))  # seconds

ALLOWED_MIME = {
    "image/jpeg": (".jpg", ".jpeg"),
    "image/jpg": (".jpg", ".jpeg"),
    "image/png": (".png",),
    "image/gif": (".gif",),
    "image/bmp": (".bmp",),
    "image/webp": (".webp",),
}

USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    method = event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return _cors_preflight()

    if method != "POST":
        return _err(405, "Method Not Allowed. Use POST.")

    if not IMAGES_BUCKET:
        return _err(500, "IMAGES_BUCKET not configured")

    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return _err(400, "Invalid JSON body")

    file_name = body.get("fileName")
    file_type = (body.get("fileType") or "").lower()
    user_id = body.get("userId", "anonymous")

    if not file_name:
        return _err(400, "fileName is required")
    if not file_type:
        return _err(400, "fileType is required")
    if file_type not in ALLOWED_MIME:
        return _err(400, f"Invalid fileType. Allowed: {', '.join(sorted(ALLOWED_MIME.keys()))}")

    if not USER_ID_PATTERN.match(user_id):
        user_id = "anonymous"

    safe_name = _sanitize_filename(file_name)
    ext = os.path.splitext(safe_name)[1].lower()
    if ext and ext not in sum(ALLOWED_MIME.values(), ()):
        return _err(400, f"File extension {ext} not allowed")

    if ext and ext not in ALLOWED_MIME[file_type]:
        return _err(400, f"Extension {ext} does not match MIME {file_type}")

    image_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    key = f"uploads/{user_id}/{timestamp}_{image_id}_{safe_name}"

    try:
        url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": IMAGES_BUCKET, "Key": key, "ContentType": file_type},
            ExpiresIn=EXPIRATION,
            HttpMethod="PUT",
        )
    except Exception as e:
        logger.exception("presign_failed")
        return _err(500, f"Presign error: {str(e)}")

    return _ok(
        {
            "uploadUrl": url,
            "imageId": image_id,
            "key": key,
            "bucket": IMAGES_BUCKET,
            "expiresIn": EXPIRATION,
            "allowedTypes": list(ALLOWED_MIME.keys()),
            "message": "Upload with HTTP PUT to uploadUrl using provided Content-Type",
        }
    )


def _sanitize_filename(name: str) -> str:
    name = os.path.basename(name).replace(" ", "_")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    name = "".join(c if c in allowed else "_" for c in name)
    if len(name) > 120:
        stem, ext = os.path.splitext(name)
        name = stem[:100] + ext
    if not os.path.splitext(name)[1]:
        name += ".jpg"  # default extension if missing
    return name


def _cors_preflight() -> Dict[str, Any]:
    return {
        "statusCode": 204,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "300",
        },
        "body": "",
    }


def _ok(data: Any) -> Dict[str, Any]:
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(data),
    }


def _err(code: int, msg: str) -> Dict[str, Any]:
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"error": msg, "status_code": code}),
    }