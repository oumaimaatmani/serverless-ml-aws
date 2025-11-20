# Serverless ML Image Pipeline

Pipeline serverless d'analyse d'images: upload S3 (URL présignée) → EventBridge → Step Functions → Lambdas (validation, Rekognition, sauvegarde) → DynamoDB → API Gateway → Frontend React.

## Endpoints (résumé)
Base: (terraform outputs après déploiement)
GET /results
GET /results/{image_id}
GET /results?confidence=80&is_safe=true
GET /upload-url (URL présignée)

## Démarrage rapide
```bash
cd terraform
terraform init
terraform apply
terraform output -json > ../tmp_outputs.json  # local seulement
./scripts/update-frontend-config.sh
cd ../frontend && npm install && npm run dev
```

## Ressources
S3 (uploads/), Step Functions (image-workflow), DynamoDB (analysis-results), Lambdas (processor, rekognition, saver, viewer, presigned-url, notification), EventBridge bus.

## Documentation
Voir docs/ pour architecture, API, déploiement, changements.

Licence: MIT