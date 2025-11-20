"""
Lambda Function: Presigned URL Generator
Role: Generate presigned S3 URLs for secure file uploads
"""

import json
import os
import logging
import boto3
import uuid
from datetime import datetime
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
s3_client = boto3.client('s3')

# Configuration
IMAGES_BUCKET = os.environ.get('IMAGES_BUCKET')
PRESIGNED_URL_EXPIRATION = int(os.environ.get('PRESIGNED_URL_EXPIRATION', 300))  # 5 minutes default


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler - Generates presigned S3 upload URLs

    Args:
        event: API Gateway event
        context: Lambda execution context

    Returns:
        API Gateway response with presigned URL
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract HTTP method
        http_method = event.get('requestContext', {}).get('http', {}).get('method')

        if http_method != 'POST':
            return error_response(405, 'Method Not Allowed. Use POST.')

        # Parse request body
        body = json.loads(event.get('body', '{}'))
        file_name = body.get('fileName')
        file_type = body.get('fileType')
        user_id = body.get('userId', 'anonymous')

        # Validate inputs
        if not file_name:
            return error_response(400, 'fileName is required')

        if not file_type:
            return error_response(400, 'fileType is required')

        # Validate file type
        allowed_types = [
            'image/jpeg', 'image/jpg', 'image/png',
            'image/gif', 'image/bmp', 'image/webp'
        ]
        if file_type not in allowed_types:
            return error_response(400, f'Invalid file type. Allowed: {", ".join(allowed_types)}')

        # Generate unique image ID and S3 key
        image_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

        # Sanitize filename
        safe_filename = sanitize_filename(file_name)
        s3_key = f"uploads/{user_id}/{timestamp}_{image_id}_{safe_filename}"

        logger.info(f"Generating presigned URL for: {s3_key}")

        # Generate presigned URL for PUT operation
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': IMAGES_BUCKET,
                'Key': s3_key,
                'ContentType': file_type,
            },
            ExpiresIn=PRESIGNED_URL_EXPIRATION,
            HttpMethod='PUT'
        )

        # Return response
        response_data = {
            'uploadUrl': presigned_url,
            'imageId': image_id,
            'key': s3_key,
            'bucket': IMAGES_BUCKET,
            'expiresIn': PRESIGNED_URL_EXPIRATION,
            'message': 'Upload the file using PUT request to the uploadUrl'
        }

        logger.info(f"Successfully generated presigned URL for image_id: {image_id}")

        return success_response(response_data)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {str(e)}")
        return error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
        return error_response(500, str(e))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to be safe for S3

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove any path components
    filename = os.path.basename(filename)

    # Replace spaces with underscores
    filename = filename.replace(' ', '_')

    # Remove any potentially problematic characters
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.')
    filename = ''.join(c if c in allowed_chars else '_' for c in filename)

    # Limit length
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:90] + ext

    return filename


def success_response(data: Any) -> Dict[str, Any]:
    """
    Create successful API Gateway response

    Args:
        data: Response data

    Returns:
        Formatted API Gateway response
    """
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(data)
    }


def error_response(status_code: int, message: str) -> Dict[str, Any]:
    """
    Create error API Gateway response

    Args:
        status_code: HTTP status code
        message: Error message

    Returns:
        Formatted error response
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'error': message,
            'status_code': status_code
        })
    }
