"""
Lambda: Result Viewer
Purpose: Serve analysis results via API Gateway
"""

import json
import os
import logging
import boto3
from decimal import Decimal
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE")


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    logger.info("event=%s", json.dumps(event))
    try:
        method = (
            event.get("httpMethod")
            or event.get("requestContext", {}).get("http", {}).get("method")
        )
        path_params = event.get("pathParameters") or {}
        query = event.get("queryStringParameters") or {}

        if method == "GET":
            image_id = path_params.get("image_id")
            if image_id:
                return _success(get_result_by_id(image_id))
            return _success(get_all_results(query))
        return _error(405, "Method Not Allowed")
    except Exception as e:
        logger.exception("unhandled_error")
        return _error(500, str(e))


def get_all_results(query: Dict[str, str]) -> Dict[str, Any]:
    table = dynamodb.Table(TABLE_NAME)
    limit = int(query.get("limit", 20))
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100

    user_id = query.get("user_id")
    items: list = []
    if user_id:
        resp = table.query(
            IndexName="UserIdIndex",
            KeyConditionExpression="user_id = :u",
            ExpressionAttributeValues={":u": user_id},
            ScanIndexForward=False,
            Limit=limit,
        )
        items = resp.get("Items", [])
    else:
        resp = table.scan(Limit=limit)
        items = resp.get("Items", [])

    results = []
    for it in items:
        results.append(
            {
                "image_id": it.get("image_id"),
                "processed_timestamp": it.get("processed_timestamp"),
                "user_id": it.get("user_id"),
                "key": it.get("key"),
                "confidence": float(it.get("confidence", 0)),
                "has_faces": it.get("has_faces", False),
                "has_text": it.get("has_text", False),
                "is_safe": it.get("is_safe", True),
                "labels_count": it.get("labels_count", 0),
                "faces_count": it.get("faces_count", 0),
                "top_label": it.get("top_label", ""),
            }
        )

    return {
        "count": len(results),
        "results": results,
        "has_more": "LastEvaluatedKey" in resp,
    }


def get_result_by_id(image_id: str) -> Dict[str, Any]:
    table = dynamodb.Table(TABLE_NAME)
    resp = table.query(
        KeyConditionExpression="image_id = :i",
        ExpressionAttributeValues={":i": image_id},
        ScanIndexForward=False,
        Limit=1,
    )
    items = resp.get("Items", [])
    if not items:
        raise ValueError(f"Image {image_id} not found")

    item = items[0]
    analysis = item.get("analysis", {})
    result = {
        "image_id": item.get("image_id"),
        "status": "completed",
        "processed_timestamp": item.get("processed_timestamp"),
        "bucket": item.get("bucket"),
        "key": item.get("key"),
        "format": item.get("format"),
        "confidence": float(item.get("confidence", 0)),
        "has_faces": item.get("has_faces", False),
        "has_text": item.get("has_text", False),
        "is_safe": item.get("is_safe", True),
        "labels": _safe_extract(analysis, "labels", "labels"),
        "faces": _safe_extract(analysis, "faces", "faces"),
        "moderation": _safe_extract(analysis, "moderation", "labels"),
        "text": _safe_extract(analysis, "text", "text"),
        "summary": analysis.get("summary", ""),
    }
    return _convert_decimals(result)


def _safe_extract(parent: Dict[str, Any], section: str, key: str):
    sec = parent.get(section, {})
    if isinstance(sec, dict):
        return sec.get(key, [])
    return []


def _convert_decimals(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, list):
        return [_convert_decimals(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    return obj


def _success(data: Any) -> Dict[str, Any]:
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(data, cls=DecimalEncoder),
    }


def _error(code: int, message: str) -> Dict[str, Any]:
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"error": message, "status_code": code}),
    }