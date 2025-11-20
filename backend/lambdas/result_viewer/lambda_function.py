"""
Lambda Function: Result Viewer
Role: Query analysis results via API Gateway
"""

import json
import os
import logging
import boto3
from decimal import Decimal
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
dynamodb = boto3.resource('dynamodb')

# Configuration
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler - Processes API Gateway requests
    
    Args:
        event: API Gateway event
        context: Lambda execution context
        
    Returns:
        API Gateway response
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract HTTP method and path
        http_method = event.get('requestContext', {}).get('http', {}).get('method')
        path = event.get('requestContext', {}).get('http', {}).get('path', '')
        path_parameters = event.get('pathParameters', {})
        query_parameters = event.get('queryStringParameters', {}) or {}
        
        logger.info(f"Method: {http_method}, Path: {path}")
        
        # Route requests
        if http_method == 'GET':
            if path_parameters and 'image_id' in path_parameters:
                # GET /results/{image_id}
                return get_result_by_id(path_parameters['image_id'])
            else:
                # GET /results
                return get_all_results(query_parameters)
        else:
            return error_response(405, 'Method Not Allowed')
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return error_response(500, str(e))


def get_all_results(query_params: Dict[str, str]) -> Dict[str, Any]:
    """
    Get all analysis results with optional filtering
    
    Args:
        query_params: Query string parameters (limit, user_id, etc.)
        
    Returns:
        API Gateway response with results list
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        # Parse query parameters
        limit = int(query_params.get('limit', 20))
        user_id = query_params.get('user_id')
        
        # Validate limit
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 1
        
        # Query by user_id if provided
        if user_id:
            logger.info(f"Querying by user_id: {user_id}")
            response = table.query(
                IndexName='UserIdIndex',
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={
                    ':uid': user_id
                },
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
        else:
            # Scan all items (use with caution in production!)
            logger.info("Scanning all items")
            response = table.scan(
                Limit=limit
            )
        
        items = response.get('Items', [])
        
        # Convert to simplified format
        results = []
        for item in items:
            results.append({
                'image_id': item.get('image_id'),
                'processed_timestamp': item.get('processed_timestamp'),
                'user_id': item.get('user_id'),
                'key': item.get('key'),
                'confidence': float(item.get('confidence', 0)),
                'summary': item.get('summary', ''),
                'has_faces': item.get('has_faces', False),
                'has_text': item.get('has_text', False),
                'is_safe': item.get('is_safe', True),
                'labels_count': item.get('labels_count', 0),
                'faces_count': item.get('faces_count', 0),
                'top_label': item.get('top_label', ''),
                'analysis_timestamp': item.get('analysis', {}).get('analysis_timestamp', '')
            })
        
        return success_response({
            'count': len(results),
            'results': results,
            'has_more': 'LastEvaluatedKey' in response
        })
        
    except Exception as e:
        logger.error(f"Error getting all results: {str(e)}")
        return error_response(500, str(e))


def get_result_by_id(image_id: str) -> Dict[str, Any]:
    """
    Get specific analysis result by image_id
    
    Args:
        image_id: Unique image identifier
        
    Returns:
        API Gateway response with result details
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        logger.info(f"Querying for image_id: {image_id}")
        
        # Query by image_id (partition key)
        response = table.query(
            KeyConditionExpression='image_id = :iid',
            ExpressionAttributeValues={
                ':iid': image_id
            },
            Limit=1,
            ScanIndexForward=False  # Most recent first
        )
        
        items = response.get('Items', [])
        
        if not items:
            return error_response(404, f"Image {image_id} not found")
        
        item = items[0]
        
        # Build detailed response
        result = {
            'image_id': item.get('image_id'),
            'processed_timestamp': item.get('processed_timestamp'),
            'user_id': item.get('user_id'),
            'bucket': item.get('bucket'),
            'key': item.get('key'),
            'size': item.get('size'),
            'format': item.get('format'),
            'upload_time': item.get('upload_time'),
            'confidence': float(item.get('confidence', 0)),
            'summary': item.get('summary', ''),
            'has_faces': item.get('has_faces', False),
            'has_text': item.get('has_text', False),
            'is_safe': item.get('is_safe', True),
            'analysis': convert_decimals(item.get('analysis', {})),
            'warning': item.get('warning', {}),
            'processor_info': item.get('processor_info', {})
        }
        
        return success_response(result)
        
    except Exception as e:
        logger.error(f"Error getting result by ID: {str(e)}")
        return error_response(500, str(e))


def convert_decimals(obj: Any) -> Any:
    """
    Recursively convert Decimal to float for JSON serialization
    
    Args:
        obj: Object to convert
        
    Returns:
        Converted object
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    else:
        return obj


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
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(data, cls=DecimalEncoder)
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