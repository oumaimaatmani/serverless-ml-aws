# Serverless ML Image Analysis Pipeline 🚀

A production-ready serverless image analysis workflow using AWS Rekognition, Lambda, Step Functions, EventBridge, S3, DynamoDB, and a minimal React + Vite frontend.

## ✨ Features
- Direct browser upload via secure presigned S3 URLs
- Automated workflow: validate → analyze → persist → notify
- ML detections: labels, faces (age/emotions), text, moderation
- Fast result polling (typical latency 2–5s)
- Infrastructure as Code (Terraform)
- Minimal, extensible architecture

## 🧱 Architecture
```
Client (React) → API Gateway → Lambda (Presigned URL)
           └── PUT to S3 (uploads/)
                    ↓
              EventBridge (Object Created)
                    ↓
             Step Functions State Machine
     ┌──────────┬─────────────┬──────────────┐
     │Processor │ Rekognition  │ Result Saver │
     └──────────┴─────────────┴──────────────┘
                    ↓
                 DynamoDB
                    ↓
     Client polls /results/{image_id}
```

## 🗂 Directory Structure
```
backend/
  lambdas/
    image_processor/
    rekognition_analyzer/
    result_saver/
    result_viewer/
    presigned_url_generator/
    notification_handler/
  common/
frontend/
  src/
    components/
    services/
terraform/
docs/
scripts/
.github/workflows/
```

## ✅ Prerequisites
- AWS CLI v2 configured
- Terraform ≥ 1.5
- Node.js ≥ 18
- Python ≥ 3.11

## 🚀 Deployment
```bash
cd terraform
terraform init
terraform apply
terraform output -json > ../tf_outputs.json
cd ..
./scripts/update-frontend-config.sh
cd frontend
npm install
npm run dev
```

## 🔌 Core API Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST   | /upload-url         | Generate presigned URL |
| GET    | /results            | List recent results    |
| GET    | /results/{image_id} | Fetch one result       |

Example:
```bash
curl -X POST $API/upload-url -H "Content-Type: application/json" \
  -d '{"fileName":"test.jpg","fileType":"image/jpeg"}'
```

## 🔧 Configuration
Terraform variables (terraform/variables.tf) control memory, timeouts, thresholds.
Frontend `.env`:
```
VITE_API_BASE_URL=https://<api-id>.execute-api.<region>.amazonaws.com/prod
```

## 📈 Monitoring
```bash
aws logs tail /aws/lambda/serverless-ml-dev-rekognition-analyzer --since 5m
aws stepfunctions list-executions --state-machine-arn <arn> --max-results 5
aws dynamodb scan --table-name serverless-ml-dev-analysis-results --limit 3
```

## 🔐 Security
- S3 bucket: public access blocked + encryption
- DynamoDB: PITR + TTL
- Presigned URLs expire (default 300s)
- IAM least privilege roles
- HTTPS-only API

## 💰 Approx Cost (10K images/month)
| Service | USD |
|---------|-----|
| Rekognition | ~10 |
| Lambda      | 2–3 |
| DynamoDB    | 2–3 |
| S3          | 1–2 |
| API Gateway | 1–2 |
| CloudWatch  | 3–5 |
| Total       | 19–25 |

## 🛣 Roadmap
- Cognito auth
- WebSocket push updates
- Pagination & advanced filtering
- CI/CD deploy pipeline
- CloudFront distribution
- Custom moderation classification

## 🤝 Contributing
```bash
git checkout -b feature/xyz
# implement
git commit -m "feat: add xyz"
git push origin feature/xyz
```
Open a PR with clear description.

## 📄 License
MIT License (see LICENSE)

Maintained by Oumaima Atmani (@oumaimaatmani)

**Built with ❤️ using AWS Serverless & Terraform**