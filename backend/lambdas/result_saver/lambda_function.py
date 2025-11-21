"""
Lambda: Result Saver
Purpose: Persist processed analysis to DynamoDB
"""

import os
import json
import logging
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE")
TTL_DAYS = int(os.environ.get("RESULT_TTL_DAYS", "30"))


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    logger.info("saving_results image_id=%s", event.get("image_id"))
    try:
        item = _build_item(event)
        _put_item(item)
        stats = _stats(item)
        return {
            "status": "SUCCESS",
            "image_id": item["image_id"],
            "saved_at": item["processed_timestamp"],
            "statistics": stats,
        }
    except Exception as e:
        logger.exception("save_error")
        raise


def _build_item(event: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow()
    ts = int(now.timestamp())
    exp = int((now + timedelta(days=TTL_DAYS)).timestamp())
    analysis = event.get("analysis", {})

    item = {
        "image_id": event["image_id"],
        "processed_timestamp": ts,
        "bucket": event.get("bucket"),
        "key": event.get("key"),
        "size": event.get("size", 0),
        "format": event.get("format", "unknown"),
        "user_id": event.get("user_id", "unknown"),
        "upload_time": event.get("upload_time", now.isoformat()),
        "analysis": _to_decimal(analysis),
        "confidence": Decimal(str(analysis.get("confidence", 0))),
        "summary": analysis.get("summary", ""),
        "has_faces": analysis.get("faces", {}).get("has_faces", False),
        "has_text": analysis.get("text", {}).get("has_text", False),
        "is_safe": analysis.get("moderation", {}).get("is_safe", True),
        "labels_count": analysis.get("labels", {}).get("count", 0),
        "faces_count": analysis.get("faces", {}).get("count", 0),
        "text_count": analysis.get("text", {}).get("count", 0),
        "top_label": (
            analysis.get("labels", {})
            .get("labels", [{}])[0]
            .get("Name", "none")
            if analysis.get("labels", {}).get("count", 0) > 0
            else "none"
        ),
        "warning": event.get("warning", {}),
        "expiration_time": exp,
        "schema_version": "1.0",
    }
    return item


def _to_decimal(obj: Any) -> Any:
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_decimal(x) for x in obj]
    return obj


def _put_item(item: Dict[str, Any]) -> None:
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item=item)


def _stats(item: Dict[str, Any]) -> Dict[str, Any]:
    total = (
        item.get("labels_count", 0)
        + item.get("faces_count", 0)
        + item.get("text_count", 0)
    )
    confidence = float(item.get("confidence", 0))
    level = "HIGH" if confidence >= 90 else "MEDIUM" if confidence >= 70 else "LOW"
    return {
        "total_detections": total,
        "confidence_level": level,
        "has_faces": item.get("has_faces"),
        "is_safe": item.get("is_safe"),
    }
