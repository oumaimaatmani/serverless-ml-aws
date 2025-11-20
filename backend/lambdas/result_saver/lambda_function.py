"""
Lambda Function: Result Saver
Rôle: Sauvegarde les résultats d'analyse dans DynamoDB
"""

import json
import os
import logging
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any

# Configuration du logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Clients AWS
dynamodb = boto3.resource('dynamodb')

# Configuration
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
WORKFLOW_LOG_TABLE = os.environ.get('WORKFLOW_LOG_TABLE')
TTL_DAYS = 30  # Durée de conservation des données


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principal - Sauvegarde les résultats dans DynamoDB
    
    Args:
        event: Événement contenant les résultats de l'analyse
        context: Contexte d'exécution Lambda
        
    Returns:
        Dict confirmant la sauvegarde
    """
    logger.info(f"Sauvegarde des résultats - Image ID: {event.get('image_id')}")
    
    try:
        # Préparation des données pour DynamoDB
        item = prepare_dynamodb_item(event)
        
        # Sauvegarde dans la table des résultats
        save_to_results_table(item)
        logger.info(f"Résultats sauvegardés pour image_id: {item['image_id']}")
        
        # Log du workflow
        log_workflow_execution(event, context)
        
        # Génération des statistiques
        stats = calculate_statistics(item)
        
        return {
            'status': 'SUCCESS',
            'image_id': item['image_id'],
            'saved_at': item['processed_timestamp'],
            'table_name': DYNAMODB_TABLE,
            'statistics': stats,
            'message': 'Résultats sauvegardés avec succès'
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde: {str(e)}", exc_info=True)
        raise


def prepare_dynamodb_item(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prépare l'item pour DynamoDB en convertissant les types
    
    Args:
        event: Événement contenant les données
        
    Returns:
        Dict formaté pour DynamoDB
    """
    # Timestamp actuel
    now = datetime.utcnow()
    timestamp = int(now.timestamp())
    
    # Calcul de l'expiration (TTL)
    expiration_date = now + timedelta(days=TTL_DAYS)
    expiration_timestamp = int(expiration_date.timestamp())
    
    # Construction de l'item
    item = {
        # Clés primaires
        'image_id': event['image_id'],
        'processed_timestamp': timestamp,
        
        # Informations de l'image
        'bucket': event['bucket'],
        'key': event['key'],
        'size': event.get('size', 0),
        'format': event.get('format', 'unknown'),
        'user_id': event.get('user_id', 'unknown'),
        'upload_time': event.get('upload_time', now.isoformat()),
        
        # Résultats de l'analyse
        'analysis': convert_floats_to_decimal(event.get('analysis', {})),
        
        # Métadonnées
        'confidence': Decimal(str(event.get('analysis', {}).get('confidence', 0))),
        'summary': event.get('analysis', {}).get('summary', ''),
        'analysis_timestamp': event.get('analysis', {}).get('analysis_timestamp', now.isoformat()),
        
        # Flags booléens pour requêtes rapides
        'has_faces': event.get('analysis', {}).get('faces', {}).get('has_faces', False),
        'has_text': event.get('analysis', {}).get('text', {}).get('has_text', False),
        'is_safe': event.get('analysis', {}).get('moderation', {}).get('is_safe', True),
        
        # Compteurs
        'labels_count': event.get('analysis', {}).get('labels', {}).get('count', 0),
        'faces_count': event.get('analysis', {}).get('faces', {}).get('count', 0),
        'text_count': event.get('analysis', {}).get('text', {}).get('count', 0),
        
        # Top label pour recherche
        'top_label': event.get('analysis', {}).get('labels', {}).get('top_label', {}).get('name', 'none'),
        
        # Warnings (si confiance faible)
        'warning': event.get('warning', {}),
        
        # TTL pour auto-suppression
        'expiration_time': expiration_timestamp,
        
        # Métadonnées de traitement
        'processor_info': {
            'image_processor': event.get('processor_timestamp', ''),
            'rekognition_analyzer': event.get('analysis', {}).get('analysis_timestamp', ''),
            'result_saver': now.isoformat()
        },
        
        # Version du schéma (pour migrations futures)
        'schema_version': '1.0'
    }
    
    return item


def convert_floats_to_decimal(obj: Any) -> Any:
    """
    Convertit récursivement les floats en Decimal pour DynamoDB
    
    Args:
        obj: Objet à convertir
        
    Returns:
        Objet avec floats convertis en Decimal
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    else:
        return obj


def save_to_results_table(item: Dict[str, Any]) -> None:
    """
    Sauvegarde l'item dans la table DynamoDB
    
    Args:
        item: Item à sauvegarder
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        response = table.put_item(
            Item=item,
            # Condition: ne pas écraser un item existant avec le même ID
            ConditionExpression='attribute_not_exists(image_id) OR processed_timestamp < :new_timestamp',
            ExpressionAttributeValues={
                ':new_timestamp': item['processed_timestamp']
            }
        )
        
        logger.info(f"Item sauvegardé - ConsumedCapacity: {response.get('ConsumedCapacity')}")
        
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        logger.warning(f"Item déjà existant avec timestamp plus récent: {item['image_id']}")
        # On continue sans erreur car c'est une mise à jour redondante
        
    except Exception as e:
        logger.error(f"Erreur DynamoDB put_item: {str(e)}")
        raise


def log_workflow_execution(event: Dict[str, Any], context: Any) -> None:
    """
    Log l'exécution dans la table de logs
    
    Args:
        event: Événement contenant les données
        context: Contexte Lambda
    """
    try:
        table = dynamodb.Table(WORKFLOW_LOG_TABLE)
        
        # Extraction de l'ID d'exécution Step Functions (si disponible)
        execution_id = extract_execution_id(context)
        
        log_item = {
            'execution_id': execution_id,
            'step_timestamp': int(datetime.utcnow().timestamp()),
            'step_name': 'SaveResults',
            'image_id': event.get('image_id'),
            'status': 'SUCCESS',
            'function_name': context.function_name,
            'request_id': context.request_id,
            'expiration_time': int((datetime.utcnow() + timedelta(days=7)).timestamp())
        }
        
        table.put_item(Item=log_item)
        logger.debug("Log workflow sauvegardé")
        
    except Exception as e:
        logger.warning(f"Impossible de logger le workflow: {str(e)}")
        # On ne lève pas d'erreur car le log n'est pas critique


def extract_execution_id(context: Any) -> str:
    """
    Extrait l'ID d'exécution Step Functions depuis le contexte
    
    Args:
        context: Contexte Lambda
        
    Returns:
        ID d'exécution ou un ID généré
    """
    try:
        # Tenter d'extraire depuis les variables d'environnement
        # Step Functions injecte automatiquement ces variables
        return os.environ.get('EXECUTION_NAME', f"manual-{context.request_id}")
    except:
        return f"unknown-{context.request_id}"


def calculate_statistics(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcule des statistiques sur les résultats sauvegardés
    
    Args:
        item: Item sauvegardé
        
    Returns:
        Dict contenant les statistiques
    """
    return {
        'total_detections': (
            item.get('labels_count', 0) + 
            item.get('faces_count', 0) + 
            item.get('text_count', 0)
        ),
        'confidence_level': 'HIGH' if float(item.get('confidence', 0)) >= 90 else 
                           'MEDIUM' if float(item.get('confidence', 0)) >= 70 else 'LOW',
        'content_type': determine_content_type(item),
        'processing_complete': True
    }


def determine_content_type(item: Dict[str, Any]) -> str:
    """
    Détermine le type de contenu de l'image
    
    Args:
        item: Item contenant les résultats
        
    Returns:
        Type de contenu détecté
    """
    if item.get('faces_count', 0) > 0:
        return 'PORTRAIT' if item['faces_count'] == 1 else 'GROUP_PHOTO'
    elif item.get('text_count', 0) > 0:
        return 'DOCUMENT'
    elif item.get('labels_count', 0) > 0:
        top_label = item.get('top_label', '').lower()
        if 'landscape' in top_label or 'nature' in top_label:
            return 'LANDSCAPE'
        elif 'food' in top_label:
            return 'FOOD'
        else:
            return 'GENERAL'
    else:
        return 'UNKNOWN'
