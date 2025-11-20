"""
Lambda Function: Rekognition Analyzer
Role: Analyze images with AWS Rekognition (ML)
"""
import os
import logging
from typing import Dict, Any, List

import boto3

logger = logging.getLogger()
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

rekognition_client = boto3.client('rekognition')
s3_client = boto3.client('s3')

CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', 80))
MAX_LABELS = int(os.environ.get('MAX_LABELS', 50))
MAX_FACES = int(os.environ.get('MAX_FACES', 10))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info(f"Starting Rekognition analysis - event keys: {list(event.keys())}")
    bucket = event.get('bucket') or event.get('s3_bucket')
    key = event.get('key') or event.get('s3_key')
    image_id = event.get('image_id') or f"{bucket}/{key}"

    if not bucket or not key:
        logger.error("Missing bucket or key in event")
        raise ValueError("Missing bucket or key in event")

    results: Dict[str, Any] = {
        "image_id": image_id,
        "confidence": 0.0,
        "labels": {},
        "faces": {},
        "text": {},
        "moderation": {},
        "summary": ""
    }

    try:
        results['labels'] = detect_labels(bucket, key)
        results['faces'] = detect_faces(bucket, key)
        results['text'] = detect_text(bucket, key)
        results['moderation'] = detect_moderation_labels(bucket, key)

        results['confidence'] = calculate_overall_confidence(results)
        results['summary'] = generate_summary(results)
        results['analysis_timestamp'] = __import__('datetime').datetime.utcnow().isoformat()

        logger.info(f"Rekognition analysis complete for {image_id}: confidence={results['confidence']}")
        return results
    except Exception as e:
        logger.exception("Error during Rekognition analysis")
        raise


def detect_labels(bucket: str, key: str) -> Dict[str, Any]:
    try:
        resp = rekognition_client.detect_labels(
            Image={"S3Object": {"Bucket": bucket, "Name": key}},
            MaxLabels=MAX_LABELS,
            MinConfidence=0
        )
        labels = [{"Name": l['Name'], "Confidence": float(l.get('Confidence', 0.0))} for l in resp.get('Labels', [])]
        return {"count": len(labels), "labels": labels}
    except Exception as e:
        logger.exception("detect_labels failed")
        return {"count": 0, "labels": [], "error": str(e)}


def detect_faces(bucket: str, key: str) -> Dict[str, Any]:
    try:
        resp = rekognition_client.detect_faces(
            Image={"S3Object": {"Bucket": bucket, "Name": key}},
            Attributes=["ALL"]
        )
        faces = resp.get('FaceDetails', [])
        faces_simplified = []
        for f in faces[:MAX_FACES]:
            faces_simplified.append({
                "confidence": float(f.get('Confidence', 0.0)),
                "age_range": f.get('AgeRange'),
                "gender": f.get('Gender', {}).get('Value'),
                "emotions": [{"Type": e.get('Type'), "Confidence": float(e.get('Confidence', 0.0))} for e in f.get('Emotions', [])]
            })
        return {"count": len(faces_simplified), "has_faces": len(faces_simplified) > 0, "faces": faces_simplified}
    except Exception as e:
        logger.exception("detect_faces failed")
        return {"count": 0, "has_faces": False, "faces": [], "error": str(e)}


def detect_text(bucket: str, key: str) -> Dict[str, Any]:
    try:
        resp = rekognition_client.detect_text(
            Image={"S3Object": {"Bucket": bucket, "Name": key}}
        )
        texts = [t.get('DetectedText') for t in resp.get('TextDetections', []) if t.get('Type') == 'LINE']
        texts = [t for t in texts if t]
        return {"count": len(texts), "has_text": len(texts) > 0, "text": texts}
    except Exception as e:
        logger.exception("detect_text failed")
        return {"count": 0, "has_text": False, "text": [], "error": str(e)}


def detect_moderation_labels(bucket: str, key: str) -> Dict[str, Any]:
    try:
        resp = rekognition_client.detect_moderation_labels(
            Image={"S3Object": {"Bucket": bucket, "Name": key}},
            MinConfidence=0
        )
        labels = [{"Name": l['Name'], "Confidence": float(l.get('Confidence', 0.0))} for l in resp.get('ModerationLabels', [])]
        is_safe = True
        for l in labels:
            if l['Confidence'] >= 70:
                is_safe = False
                break
        return {"count": len(labels), "is_safe": is_safe, "labels": labels}
    except Exception as e:
        logger.exception("detect_moderation_labels failed")
        return {"count": 0, "is_safe": True, "labels": [], "error": str(e)}


def calculate_overall_confidence(results: Dict[str, Any]) -> float:
    confidences: List[float] = []

    labels = results.get('labels', {})
    if labels.get('count', 0) > 0:
        top_label_conf = max([l.get('Confidence', 0.0) for l in labels.get('labels', [])], default=0.0)
        confidences.append(top_label_conf)

    faces = results.get('faces', {})
    if faces.get('count', 0) > 0:
        avg_face_conf = sum([f.get('confidence', 0.0) for f in faces.get('faces', [])]) / max(1, faces.get('count', 1))
        confidences.append(avg_face_conf)

    text = results.get('text', {})
    if text.get('count', 0) > 0:
        confidences.append(80.0)

    if confidences:
        return round(sum(confidences) / len(confidences), 2)

    return 0.0


def generate_summary(results: Dict[str, Any]) -> str:
    summary_parts: List[str] = []

    if results.get('labels', {}).get('count', 0) > 0:
        top = results['labels']['labels'][0]
        summary_parts.append(f"Top label: {top.get('Name')} ({top.get('Confidence')}%)")

    if results.get('faces', {}).get('has_faces'):
        summary_parts.append(f"Faces detected: {results['faces']['count']}")

    if results.get('text', {}).get('has_text'):
        summary_parts.append("Text detected in image")

    if not results.get('moderation', {}).get('is_safe', True):
        summary_parts.append("Content flagged by moderation")

    return ". ".join(summary_parts) if summary_parts else "Image analyzed with no significant detections"
