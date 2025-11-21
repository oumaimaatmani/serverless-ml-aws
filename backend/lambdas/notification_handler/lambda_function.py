"""
Lambda: Notification Handler
Purpose: Publish workflow notifications (success, error, validation, generic) to EventBridge
"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any

import boto3

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", f"serverless-ml-{ENVIRONMENT}-event-bus")
METRIC_NAMESPACE = "ServerlessML"

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

eventbridge = boto3.client("events")
cloudwatch = boto3.client("cloudwatch")


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Dispatch notification type.
    Expected event.notification_type in: success | error | validation_failed | generic
    """
    ntype = event.get("notification_type", "generic")
    logger.info("notification_type=%s", ntype)
    try:
        if ntype == "success":
            return _handle_success(event)
        if ntype == "error":
            return _handle_error(event)
        if ntype == "validation_failed":
            return _handle_validation_failure(event)
        return _handle_generic(event)
    except Exception as e:
        logger.exception("notification_failure")
        return {
            "status": "FAILED",
            "notification_sent": False,
            "error": str(e),
            "type": ntype,
        }


# Handlers ------------------------------------------------------------------


def _handle_success(event: Dict[str, Any]) -> Dict[str, Any]:
    analysis = event.get("analysis", {})
    detail = {
        "event_type": "IMAGE_PROCESSING_SUCCESS",
        "image_id": event.get("image_id", "unknown"),
        "confidence": float(analysis.get("confidence", 0)),
        "summary": analysis.get("summary", ""),
        "labels_count": analysis.get("labels", {}).get("count", 0),
        "faces_count": analysis.get("faces", {}).get("count", 0),
        "has_text": analysis.get("text", {}).get("has_text", False),
        "is_safe": analysis.get("moderation", {}).get("is_safe", True),
        "environment": ENVIRONMENT,
        "timestamp": _now(),
    }
    resp = _put_event("ImageProcessingSuccess", detail)
    _put_metrics(
        "success",
        confidence=detail["confidence"],
        labels_count=detail["labels_count"],
        faces_count=detail["faces_count"],
    )
    return _ok("SUCCESS", resp, detail["image_id"])


def _handle_error(event: Dict[str, Any]) -> Dict[str, Any]:
    err = event.get("error", {})
    detail = {
        "event_type": "IMAGE_PROCESSING_ERROR",
        "image_id": event.get("image_id", "unknown"),
        "error_message": err.get("Error", "Unknown"),
        "error_cause": err.get("Cause", ""),
        "severity": "HIGH",
        "environment": ENVIRONMENT,
        "timestamp": _now(),
    }
    resp = _put_event("ImageProcessingError", detail)
    _put_metrics("error")
    _log_alert(detail)
    return _ok("ERROR_NOTIFIED", resp, detail["image_id"])


def _handle_validation_failure(event: Dict[str, Any]) -> Dict[str, Any]:
    err = event.get("error", {})
    detail = {
        "event_type": "IMAGE_VALIDATION_FAILED",
        "image_key": event.get("key", "unknown"),
        "validation_error": err.get("Cause", "Validation failed"),
        "severity": "MEDIUM",
        "environment": ENVIRONMENT,
        "timestamp": _now(),
    }
    resp = _put_event("ImageValidationFailed", detail)
    _put_metrics("validation_failed")
    return _ok("VALIDATION_ERROR_NOTIFIED", resp, detail["image_key"])


def _handle_generic(event: Dict[str, Any]) -> Dict[str, Any]:
    detail = {
        "event_type": "GENERIC_NOTIFICATION",
        "data": event,
        "environment": ENVIRONMENT,
        "timestamp": _now(),
    }
    resp = _put_event("GenericNotification", detail)
    _put_metrics("generic")
    return _ok("NOTIFIED", resp, event.get("image_id", "n/a"))


# Helpers -------------------------------------------------------------------


def _put_event(detail_type: str, detail: Dict[str, Any]) -> Dict[str, Any]:
    response = eventbridge.put_events(
        Entries=[
            {
                "Time": datetime.utcnow(),
                "Source": "custom.ml.pipeline",
                "DetailType": detail_type,
                "Detail": json.dumps(detail),
                "EventBusName": EVENT_BUS_NAME,
            }
        ]
    )
    if response.get("FailedEntryCount", 0) > 0:
        logger.error("eventbridge_failure detail_type=%s entries=%s", detail_type, response.get("Entries"))
    else:
        logger.info("eventbridge_success detail_type=%s event_id=%s",
                    detail_type,
                    response.get("Entries", [{}])[0].get("EventId"))
    return response


def _put_metrics(notification_type: str, **extra) -> None:
    try:
        metrics = [
            {
                "MetricName": "NotificationsSent",
                "Value": 1,
                "Unit": "Count",
                "Dimensions": [
                    {"Name": "NotificationType", "Value": notification_type},
                    {"Name": "Environment", "Value": ENVIRONMENT},
                ],
            }
        ]
        if "confidence" in extra:
            metrics.append(
                {
                    "MetricName": "ProcessingConfidence",
                    "Value": float(extra["confidence"]),
                    "Unit": "Percent",
                    "Dimensions": [{"Name": "Environment", "Value": ENVIRONMENT}],
                }
            )
        cloudwatch.put_metric_data(Namespace=METRIC_NAMESPACE, MetricData=metrics)
    except Exception as e:
        logger.warning("metric_publish_failed error=%s", str(e))


def _log_alert(detail: Dict[str, Any]) -> None:
    logger.warning("ALERT type=%s message=%s", detail.get("event_type"), detail.get("error_message"))
    # SNS integration placeholder:
    # sns = boto3.client("sns")
    # sns.publish(TopicArn=os.environ["ALERT_TOPIC_ARN"], Subject="ML Processing Error", Message=json.dumps(detail))


def _ok(status: str, resp: Dict[str, Any], ref_id: str) -> Dict[str, Any]:
    return {
        "status": status,
        "notification_sent": True,
        "event_id": resp.get("Entries", [{}])[0].get("EventId"),
        "ref": ref_id,
    }


def _now() -> str:
    return datetime.utcnow().isoformat()