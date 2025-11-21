"""
Lambda: Image Processor
Purpose: Validate an uploaded image object and prepare normalized metadata for downstream ML analysis.
"""
import json
import os
import logging
import re
import hashlib
from datetime import datetime
from typing import Dict, Any

import boto3

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

s3_client = boto3.client("s3")

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
UUID_REGEX = re.compile(r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})")


class ValidationError(Exception):
    """Raised when image validation fails."""
    pass


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Entry point.
    Supports Step Functions input format or raw S3 event records.
    Returns normalized image metadata or raises ValidationError.
    """
    logger.info("stage=start handler=ImageProcessor")
    try:
        image = extract_image_info(event)
        logger.info("detected key=%s bucket=%s", image["key"], image["bucket"])

        validate_image(image)

        image_id = derive_image_id(image["key"])
        metadata = fetch_s3_head(image["bucket"], image["key"])

        result = {
            "image_id": image_id,
            "bucket": image["bucket"],
            "key": image["key"],
            "size": image["size"],
            "format": image["format"],
            "upload_time": image.get("upload_time", datetime.utcnow().isoformat()),
            "metadata": metadata,
            "validation_status": "PASSED",
            "processor_timestamp": datetime.utcnow().isoformat(),
            "user_id": extract_user_id(image["key"]),
        }

        logger.info("stage=complete image_id=%s size=%s format=%s",
                    image_id, image["size"], image["format"])
        return result
    except ValidationError as ve:
        logger.warning("validation_failed reason=%s", str(ve))
        raise
    except Exception as e:
        logger.exception("unexpected_error")
        raise ValidationError(f"Unhandled processing error: {str(e)}") from e


def extract_image_info(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize incoming event to a unified image descriptor.
    Supports:
      - Step Functions pass-through: {image_bucket, image_key, image_size, upload_time}
      - S3 event: Records[0].s3.*
    """
    if "image_bucket" in event and "image_key" in event:
        return {
            "bucket": event["image_bucket"],
            "key": event["image_key"],
            "size": event.get("image_size", 0),
            "upload_time": event.get("upload_time"),
            "format": _extension(event["image_key"]),
        }

    if "Records" in event:
        record = event["Records"][0]
        s3obj = record["s3"]["object"]
        return {
            "bucket": record["s3"]["bucket"]["name"],
            "key": s3obj["key"],
            "size": s3obj.get("size", 0),
            "upload_time": record.get("eventTime"),
            "format": _extension(s3obj["key"]),
        }

    raise ValidationError("Unsupported event structure")


def validate_image(image: Dict[str, Any]) -> None:
    """
    Ensure image meets format and size constraints and exists in S3.
    """
    ext = image["format"]
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Unsupported format {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    size = int(image.get("size", 0))
    if size <= 0:
        raise ValidationError("Empty file (0 bytes)")
    if size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            f"File too large: {size / (1024*1024):.2f} MB (max {MAX_IMAGE_SIZE_BYTES / (1024*1024):.2f} MB)"
        )

    try:
        s3_client.head_object(Bucket=image["bucket"], Key=image["key"])
    except s3_client.exceptions.NoSuchKey:
        raise ValidationError(f"Object not found: {image['key']}")
    except Exception as e:
        raise ValidationError(f"S3 access error: {str(e)}")

    logger.info("validation_passed format=%s size=%d", ext, size)


def derive_image_id(key: str) -> str:
    """
    Extract UUID from key if present; otherwise derive a deterministic short hash fallback.
    """
    match = UUID_REGEX.search(key)
    if match:
        return match.group(1)

    logger.debug("uuid_missing key=%s generating_hash_fallback", key)
    base = f"{key}-{datetime.utcnow().isoformat()}"
    return hashlib.sha256(base.encode()).hexdigest()[:16]


def fetch_s3_head(bucket: str, key: str) -> Dict[str, Any]:
    """
    Retrieve basic S3 object metadata. Non-critical failures return {}.
    """
    try:
        resp = s3_client.head_object(Bucket=bucket, Key=key)
        lm = resp.get("LastModified")
        return {
            "content_type": resp.get("ContentType"),
            "etag": (resp.get("ETag") or "").strip('"'),
            "last_modified": lm.isoformat() if lm else None,
            "metadata": resp.get("Metadata", {}),
        }
    except Exception as e:
        logger.warning("metadata_fetch_failed key=%s error=%s", key, str(e))
        return {}


def extract_user_id(key: str) -> str:
    """
    Extract user identifier from key pattern uploads/<user>/...
    """
    parts = key.split("/")
    if len(parts) >= 2 and parts[0] == "uploads" and parts[1]:
        return parts[1]
    return "unknown"


def _extension(key: str) -> str:
    return os.path.splitext(key)[1].lower()