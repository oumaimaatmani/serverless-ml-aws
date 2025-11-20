"""
Lambda Function: Image Processor
Rôle: Valide et prépare les images pour le traitement ML
"""

import json
import os
import logging
import boto3
from datetime import datetime
import hashlib
from typing import Dict, Any

# Configuration du logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Clients AWS
s3_client = boto3.client('s3')

# Configuration
IMAGES_BUCKET = os.environ.get('IMAGES_BUCKET')
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']


class ValidationError(Exception):
    """Exception personnalisée pour erreurs de validation"""
    pass


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principal de la fonction Lambda
    
    Args:
        event: Événement d'entrée contenant les informations de l'image
        context: Contexte d'exécution Lambda
        
    Returns:
        Dict contenant les informations validées de l'image
        
    Raises:
        ValidationError: Si l'image ne passe pas la validation
    """
    logger.info(f"Démarrage du traitement - Event: {json.dumps(event)}")
    
    try:
        # Extraction des informations de l'image
        image_info = extract_image_info(event)
        logger.info(f"Image détectée: {image_info['key']}")
        
        # Validation de l'image
        validate_image(image_info)
        logger.info("Image validée avec succès")
        
        # Génération d'un ID unique pour l'image
        image_id = generate_image_id(image_info)
        
        # Récupération des métadonnées S3
        metadata = get_s3_metadata(image_info['bucket'], image_info['key'])
        
        # Préparation de la réponse
        result = {
            'image_id': image_id,
            'bucket': image_info['bucket'],
            'key': image_info['key'],
            'size': image_info['size'],
            'format': image_info['format'],
            'upload_time': image_info.get('upload_time', datetime.utcnow().isoformat()),
            'metadata': metadata,
            'validation_status': 'PASSED',
            'processor_timestamp': datetime.utcnow().isoformat(),
            'user_id': extract_user_id(image_info['key'])
        }
        
        logger.info(f"Traitement réussi pour image_id: {image_id}")
        return result
        
    except ValidationError as e:
        logger.error(f"Erreur de validation: {str(e)}")
        raise ValidationError(f"Image validation failed: {str(e)}")
        
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}", exc_info=True)
        raise


def extract_image_info(event: Dict[str, Any]) -> Dict[str, str]:
    """
    Extrait les informations de l'image depuis l'événement
    
    Args:
        event: Événement d'entrée
        
    Returns:
        Dict contenant les informations de l'image
    """
    # Support de différents formats d'événement
    if 'image_bucket' in event and 'image_key' in event:
        # Format Step Functions
        return {
            'bucket': event['image_bucket'],
            'key': event['image_key'],
            'size': event.get('image_size', 0),
            'upload_time': event.get('upload_time'),
            'format': os.path.splitext(event['image_key'])[1].lower()
        }
    elif 'Records' in event:
        # Format S3 Event
        record = event['Records'][0]
        s3_info = record['s3']
        return {
            'bucket': s3_info['bucket']['name'],
            'key': s3_info['object']['key'],
            'size': s3_info['object']['size'],
            'upload_time': record['eventTime'],
            'format': os.path.splitext(s3_info['object']['key'])[1].lower()
        }
    else:
        raise ValidationError("Format d'événement non reconnu")


def validate_image(image_info: Dict[str, str]) -> None:
    """
    Valide l'image selon plusieurs critères
    
    Args:
        image_info: Informations de l'image à valider
        
    Raises:
        ValidationError: Si la validation échoue
    """
    # Vérification du format
    if image_info['format'] not in ALLOWED_FORMATS:
        raise ValidationError(
            f"Format non supporté: {image_info['format']}. "
            f"Formats acceptés: {', '.join(ALLOWED_FORMATS)}"
        )
    
    # Vérification de la taille
    size = int(image_info['size'])
    if size == 0:
        raise ValidationError("L'image est vide (0 bytes)")
    
    if size > MAX_IMAGE_SIZE:
        raise ValidationError(
            f"Image trop volumineuse: {size / 1024 / 1024:.2f} MB. "
            f"Taille maximale: {MAX_IMAGE_SIZE / 1024 / 1024} MB"
        )
    
    # Vérification que le fichier existe dans S3
    try:
        s3_client.head_object(
            Bucket=image_info['bucket'],
            Key=image_info['key']
        )
    except s3_client.exceptions.NoSuchKey:
        raise ValidationError(f"Image introuvable: {image_info['key']}")
    except Exception as e:
        raise ValidationError(f"Erreur lors de l'accès à l'image: {str(e)}")
    
    logger.info(f"Validation réussie - Format: {image_info['format']}, Taille: {size} bytes")


def generate_image_id(image_info: Dict[str, str]) -> str:
    """
    Génère un ID unique pour l'image
    
    Args:
        image_info: Informations de l'image
        
    Returns:
        ID unique (hash SHA256)
    """
    # Création d'une chaîne unique combinant bucket, key et timestamp
    unique_string = f"{image_info['bucket']}/{image_info['key']}/{datetime.utcnow().isoformat()}"
    
    # Génération du hash SHA256
    image_id = hashlib.sha256(unique_string.encode()).hexdigest()[:16]
    
    return image_id


def get_s3_metadata(bucket: str, key: str) -> Dict[str, Any]:
    """
    Récupère les métadonnées S3 de l'image
    
    Args:
        bucket: Nom du bucket S3
        key: Clé de l'objet S3
        
    Returns:
        Dict contenant les métadonnées
    """
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        
        return {
            'content_type': response.get('ContentType', 'unknown'),
            'last_modified': response.get('LastModified', '').isoformat() if response.get('LastModified') else None,
            'etag': response.get('ETag', '').strip('"'),
            'metadata': response.get('Metadata', {})
        }
    except Exception as e:
        logger.warning(f"Impossible de récupérer les métadonnées: {str(e)}")
        return {}


def extract_user_id(key: str) -> str:
    """
    Extrait l'ID utilisateur depuis le chemin de l'image
    Format attendu: uploads/user123/image.jpg
    
    Args:
        key: Clé S3 de l'image
        
    Returns:
        ID utilisateur ou 'unknown'
    """
    try:
        parts = key.split('/')
        if len(parts) >= 2 and parts[0] == 'uploads':
            return parts[1]
    except Exception as e:
        logger.warning(f"Impossible d'extraire user_id: {str(e)}")
    
    return 'unknown'
