import json
import decimal
import os
import logging
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
}

def json_response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Standardized API response with CORS headers."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, default=str),
    }

def to_plain(obj: Any) -> Any:
    """Convert DynamoDB Decimal types to native Python types."""
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, list):
        return [to_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_plain(v) for k, v in obj.items()}
    return obj

def log_structured(event: Dict[str, Any], label: str = "event") -> None:
    """Log event as structured JSON."""
    logger.info(json.dumps({"type": label, "data": event}, default=str))
