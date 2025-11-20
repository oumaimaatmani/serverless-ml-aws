"""
Lambda Function: Notification Handler
Rôle: Gère les notifications via EventBridge et autres canaux
"""

import json
import os
import logging
import boto3
from datetime import datetime
from typing import Dict, Any, List

# Configuration du logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Clients AWS
eventbridge_client = boto3.client('events')

# Configuration
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME', f"serverless-ml-{ENVIRONMENT}-event-bus")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principal - Gère les notifications
    
    Args:
        event: Événement de notification
        context: Contexte d'exécution Lambda
        
    Returns:
        Dict confirmant l'envoi de la notification
    """
    logger.info(f"Traitement notification - Type: {event.get('notification_type')}")
    
    try:
        notification_type = event.get('notification_type', 'general')
        
        # Routage selon le type de notification
        if notification_type == 'success':
            result = handle_success_notification(event)
        elif notification_type == 'error':
            result = handle_error_notification(event)
        elif notification_type == 'validation_failed':
            result = handle_validation_error(event)
        else:
            result = handle_generic_notification(event)
        
        logger.info(f"Notification traitée avec succès: {notification_type}")
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la notification: {str(e)}", exc_info=True)
        raise


def handle_success_notification(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gère les notifications de succès
    
    Args:
        event: Données de l'événement
        
    Returns:
        Résultat de la notification
    """
    logger.info("Traitement notification de succès")
    
    # Extraction des données importantes
    image_id = event.get('image_id', 'unknown')
    analysis = event.get('analysis', {})
    confidence = analysis.get('confidence', 0)
    summary = analysis.get('summary', '')
    
    # Création de l'événement EventBridge
    detail = {
        'event_type': 'IMAGE_PROCESSING_SUCCESS',
        'image_id': image_id,
        'confidence': float(confidence),
        'summary': summary,
        'timestamp': datetime.utcnow().isoformat(),
        'environment': ENVIRONMENT,
        'metadata': {
            'labels_count': analysis.get('labels', {}).get('count', 0),
            'faces_count': analysis.get('faces', {}).get('count', 0),
            'has_text': analysis.get('text', {}).get('has_text', False),
            'is_safe': analysis.get('moderation', {}).get('is_safe', True)
        }
    }
    
    # Envoi à EventBridge
    response = send_to_eventbridge(
        detail_type='Image Processing Complete',
        detail=detail,
        source='custom.ml.processing'
    )
    
    # Log dans CloudWatch
    log_notification_metrics(
        notification_type='success',
        image_id=image_id,
        confidence=confidence
    )
    
    return {
        'status': 'SUCCESS',
        'notification_sent': True,
        'event_id': response.get('Entries', [{}])[0].get('EventId'),
        'message': f"Image {image_id} traitée avec succès (confiance: {confidence}%)"
    }


def handle_error_notification(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gère les notifications d'erreur
    
    Args:
        event: Données de l'événement
        
    Returns:
        Résultat de la notification
    """
    logger.warning("Traitement notification d'erreur")
    
    error_info = event.get('error', {})
    image_id = event.get('image_id', 'unknown')
    
    # Création de l'événement d'erreur
    detail = {
        'event_type': 'IMAGE_PROCESSING_ERROR',
        'image_id': image_id,
        'error_message': error_info.get('Error', 'Unknown error'),
        'error_cause': error_info.get('Cause', ''),
        'timestamp': datetime.utcnow().isoformat(),
        'environment': ENVIRONMENT,
        'severity': 'HIGH'
    }
    
    # Envoi à EventBridge
    response = send_to_eventbridge(
        detail_type='Image Processing Failed',
        detail=detail,
        source='custom.ml.processing'
    )
    
    # Log des métriques d'erreur
    log_notification_metrics(
        notification_type='error',
        image_id=image_id,
        error_type=error_info.get('Error', 'Unknown')
    )
    
    # Potentiellement envoyer un email/SMS (si configuré)
    send_alert_notification(detail)
    
    return {
        'status': 'ERROR_NOTIFIED',
        'notification_sent': True,
        'event_id': response.get('Entries', [{}])[0].get('EventId'),
        'message': f"Erreur de traitement notifiée pour image {image_id}"
    }


def handle_validation_error(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gère les notifications d'échec de validation
    
    Args:
        event: Données de l'événement
        
    Returns:
        Résultat de la notification
    """
    logger.info("Traitement notification d'échec de validation")
    
    error_info = event.get('error', {})
    
    detail = {
        'event_type': 'IMAGE_VALIDATION_FAILED',
        'image_key': event.get('key', 'unknown'),
        'validation_error': error_info.get('Cause', 'Validation failed'),
        'timestamp': datetime.utcnow().isoformat(),
        'environment': ENVIRONMENT,
        'severity': 'MEDIUM'
    }
    
    response = send_to_eventbridge(
        detail_type='Image Validation Failed',
        detail=detail,
        source='custom.ml.processing'
    )
    
    return {
        'status': 'VALIDATION_ERROR_NOTIFIED',
        'notification_sent': True,
        'event_id': response.get('Entries', [{}])[0].get('EventId')
    }


def handle_generic_notification(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gère les notifications génériques
    
    Args:
        event: Données de l'événement
        
    Returns:
        Résultat de la notification
    """
    logger.info("Traitement notification générique")
    
    detail = {
        'event_type': 'GENERIC_NOTIFICATION',
        'data': event,
        'timestamp': datetime.utcnow().isoformat(),
        'environment': ENVIRONMENT
    }
    
    response = send_to_eventbridge(
        detail_type='Generic Notification',
        detail=detail,
        source='custom.ml.processing'
    )
    
    return {
        'status': 'NOTIFIED',
        'notification_sent': True,
        'event_id': response.get('Entries', [{}])[0].get('EventId')
    }


def send_to_eventbridge(detail_type: str, detail: Dict[str, Any], source: str) -> Dict[str, Any]:
    """
    Envoie un événement à EventBridge
    
    Args:
        detail_type: Type d'événement
        detail: Détails de l'événement
        source: Source de l'événement
        
    Returns:
        Réponse d'EventBridge
    """
    try:
        response = eventbridge_client.put_events(
            Entries=[
                {
                    'Time': datetime.utcnow(),
                    'Source': source,
                    'DetailType': detail_type,
                    'Detail': json.dumps(detail),
                    'EventBusName': EVENT_BUS_NAME
                }
            ]
        )
        
        # Vérification des erreurs
        if response.get('FailedEntryCount', 0) > 0:
            logger.error(f"Échec d'envoi d'événements: {response.get('Entries')}")
        else:
            logger.info(f"Événement envoyé avec succès: {detail_type}")
        
        return response
        
    except eventbridge_client.exceptions.ResourceNotFoundException:
        logger.warning(f"Bus d'événements non trouvé: {EVENT_BUS_NAME}, utilisation du bus par défaut")
        # Fallback sur le bus par défaut
        response = eventbridge_client.put_events(
            Entries=[
                {
                    'Time': datetime.utcnow(),
                    'Source': source,
                    'DetailType': detail_type,
                    'Detail': json.dumps(detail)
                }
            ]
        )
        return response
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi à EventBridge: {str(e)}")
        raise


def log_notification_metrics(notification_type: str, **kwargs) -> None:
    """
    Log des métriques de notification dans CloudWatch
    
    Args:
        notification_type: Type de notification
        **kwargs: Métriques additionnelles
    """
    try:
        cloudwatch = boto3.client('cloudwatch')
        
        metrics = [
            {
                'MetricName': 'NotificationsSent',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {
                        'Name': 'NotificationType',
                        'Value': notification_type
                    },
                    {
                        'Name': 'Environment',
                        'Value': ENVIRONMENT
                    }
                ]
            }
        ]
        
        # Ajout de métriques de confiance si disponible
        if 'confidence' in kwargs:
            metrics.append({
                'MetricName': 'ProcessingConfidence',
                'Value': float(kwargs['confidence']),
                'Unit': 'Percent',
                'Dimensions': [
                    {
                        'Name': 'Environment',
                        'Value': ENVIRONMENT
                    }
                ]
            })
        
        cloudwatch.put_metric_data(
            Namespace='ServerlessML',
            MetricData=metrics
        )
        
        logger.debug(f"Métriques CloudWatch envoyées: {notification_type}")
        
    except Exception as e:
        logger.warning(f"Impossible d'envoyer les métriques: {str(e)}")


def send_alert_notification(detail: Dict[str, Any]) -> None:
    """
    Envoie une alerte (email/SMS) en cas d'erreur critique
    Cette fonction peut être étendue avec SNS pour des vraies alertes
    
    Args:
        detail: Détails de l'alerte
    """
    try:
        # Pour l'instant, on log seulement
        # Dans un vrai environnement, on utiliserait SNS
        logger.warning(f"ALERTE: {detail.get('error_message')}")
        
        # Exemple d'intégration SNS (à décommenter si configuré):
        # sns_client = boto3.client('sns')
        # sns_client.publish(
        #     TopicArn='arn:aws:sns:region:account:topic',
        #     Subject='Erreur de traitement ML',
        #     Message=json.dumps(detail, indent=2)
        # )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi d'alerte: {str(e)}")
