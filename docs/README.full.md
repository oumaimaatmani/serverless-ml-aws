# Serverless ML Image Processing Pipeline

## 📋 Overview
A fully automated, event-driven image processing pipeline built on AWS serverless services. Upload images through a React web interface, automatically process them with AI (AWS Rekognition), and view detailed analysis results in real-time.

**✨ Now includes a complete web frontend for easy image uploads and results viewing!**

## 🏗️ Architecture

```
S3 Upload → EventBridge → Step Functions → Lambda Functions → DynamoDB
                                    ↓
                            AWS Rekognition (AI)
```

### Components
- **Frontend**: React + Vite web interface for uploads and results
- **API Gateway**: RESTful API for upload URLs and results queries
- **S3**: Image storage with versioning & encryption
- **EventBridge**: Event-driven triggers
- **Step Functions**: Workflow orchestration with error handling
- **Lambda**: 6 functions (upload URL generator, validate, analyze, save, notify, results viewer)
- **AWS Rekognition**: AI image analysis (labels, faces, text, moderation)
- **DynamoDB**: Results persistence with TTL

## 🚀 Quick Start

### Prerequisites
- AWS Account with credentials configured
- Terraform >= 1.0
- AWS CLI v2

### Deployment

```bash
# Clone repository
git clone https://github.com/oumaimaatmani/serverless-ml-aws.git
cd serverless-ml-aws

# Initialize Terraform
cd terraform
terraform init

# Plan deployment
terraform plan -out=tfplan

# Apply configuration
terraform apply tfplan

# Store outputs
terraform output -json > ../tf_outputs.json
cd ..

# Configure frontend
./scripts/update-frontend-config.sh

# Start frontend
cd frontend
npm install
npm run dev
```

### Usage

#### Option 1: Web Interface (Recommended)
1. Open `http://localhost:5173` in your browser
2. Upload an image through the web interface
3. View real-time analysis results

#### Option 2: AWS CLI
```bash
# Upload image directly to S3
aws s3 cp test.jpg s3://serverless-ml-dev-images-XXXXX/uploads/

# Check workflow status
aws stepfunctions list-executions \
  --state-machine-arn $(cd terraform && terraform output -raw step_functions_arn) \
  --query 'executions[0].status'

# Query results via API
curl $(cd terraform && terraform output -raw api_gateway_url)/results
```

## 📊 Key Features

✅ **Automatic Image Validation**
- Format checking (JPEG, PNG, etc.)
- Size validation
- Metadata extraction

✅ **AI-Powered Analysis**
- Object detection (50+ labels)
- Face detection
- Text recognition
- Content moderation

✅ **Error Handling & Retries**
- Automatic retry logic
- Comprehensive error catching
- CloudWatch logging

✅ **Scalable & Serverless**
- Auto-scaling Lambda
- No servers to manage
- Pay-per-execution pricing

## 📈 Performance

| Metric | Value |
|--------|-------|
| Processing Time | 2-3 seconds |
| AI Confidence | 93.28% |
| Labels Detected | 50 |
| Monthly Cost | $15-25 |

## 💰 Cost Estimation

```
AWS Rekognition:  $1 per 1000 images = $0.001/image
Lambda:          Free tier 1M/month, then $0.20 per 1M
DynamoDB:        $1.25 per 1M writes
S3 Storage:      $0.023 per GB
CloudWatch:      ~$5/month

Total (10K images/month): ~$20-25
```

## 📁 Project Structure

```
serverless-ml-aws/
├── terraform/                       # Infrastructure as Code
│   ├── main.tf                     # Provider & locals
│   ├── s3.tf                       # S3 configuration
│   ├── dynamodb.tf                 # DynamoDB tables
│   ├── eventbridge.tf              # Event routing
│   ├── step_functions.tf           # Workflow orchestration
│   ├── lambda.tf                   # Lambda + API Gateway
│   ├── iam.tf                      # IAM roles & policies
│   ├── variables.tf                # Input variables
│   ├── outputs.tf                  # Output values
│   └── terraform.tfvars            # Variable values
├── lambda_functions/                # Lambda source code
│   ├── presigned_url_generator/    # Generate S3 upload URLs
│   ├── image_processor/            # Validate images
│   ├── rekognition_analyzer/       # AI analysis
│   ├── result_saver/               # Save to DynamoDB
│   ├── notification_handler/       # Send notifications
│   └── result_viewer/              # Query results API
├── frontend/                        # React web interface
│   ├── src/
│   │   ├── components/             # UI components
│   │   ├── services/               # API client
│   │   └── App.jsx                 # Main app
│   ├── package.json
│   ├── .env                        # API configuration
│   └── SETUP.md                    # Frontend setup guide
├── scripts/
│   └── update-frontend-config.sh   # Auto-config script
├── README.md
└── LICENSE
```

## 🔧 Configuration

Edit `terraform/terraform.tfvars`:

```hcl
aws_region  = "us-east-1"
environment = "dev"

lambda_memory_size = 512
lambda_timeout     = 60

dynamodb_read_capacity  = 5
dynamodb_write_capacity = 5

rekognition_confidence_threshold = 80
```

## 🌐 API Endpoints

The API Gateway provides the following endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload-url` | Generate presigned S3 URL for secure uploads |
| `GET` | `/results` | List all analysis results (supports `?limit=N&user_id=X`) |
| `GET` | `/results/{image_id}` | Get detailed results for a specific image |

Example API calls:
```bash
# Get presigned upload URL
curl -X POST https://your-api.execute-api.us-east-1.amazonaws.com/prod/upload-url \
  -H "Content-Type: application/json" \
  -d '{"fileName": "test.jpg", "fileType": "image/jpeg"}'

# List recent results
curl https://your-api.execute-api.us-east-1.amazonaws.com/prod/results?limit=10

# Get specific result
curl https://your-api.execute-api.us-east-1.amazonaws.com/prod/results/{image_id}
```

## 📝 Workflow States

1. **ValidateImage**: Validates image format and size
2. **AnalyzeWithRekognition**: Calls AWS Rekognition API
3. **CheckConfidence**: Routes based on confidence score
4. **SaveResults**: Persists to DynamoDB
5. **ParallelNotifications**: Sends notifications

## 🧪 Testing

```bash
# Upload test image
aws s3 cp test.jpg s3://serverless-ml-dev-images-XXXXX/uploads/test-$(date +%s).jpg

# Monitor execution
watch -n 1 'aws stepfunctions list-executions --state-machine-arn ARN --query "executions[0].status"'

# View logs
aws logs tail /aws/lambda/serverless-ml-dev-rekognition-analyzer --follow
```

## 📊 Monitoring

**CloudWatch Dashboard**
- Lambda execution metrics
- Step Functions execution history
- DynamoDB write/read capacity

**EventBridge Archive**
- 30-day event retention
- Event replay capability

## 🚨 Troubleshooting

### Workflow Failed
```bash
aws stepfunctions describe-execution --execution-arn ARN
```

### Lambda Error
```bash
aws logs get-log-events --log-group-name NAME --log-stream-name STREAM
```

### Permission Denied
Check IAM roles in `terraform/iam.tf`

## 🔐 Security

- ✅ S3 public access blocked
- ✅ Encryption at rest (S3 & DynamoDB)
- ✅ IAM least-privilege policies
- ✅ VPC isolation (optional)
- ✅ CloudTrail logging

## 📚 Documentation

- [AWS Step Functions](https://docs.aws.amazon.com/step-functions/)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [AWS Rekognition](https://docs.aws.amazon.com/rekognition/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

## 🎯 Future Enhancements

- [x] ~~API Gateway for direct image uploads~~ ✅ **COMPLETED**
- [x] ~~Web dashboard UI~~ ✅ **COMPLETED**
- [ ] Batch processing support
- [ ] Real-time SNS notifications
- [ ] Custom ML models
- [ ] Results export to S3
- [ ] Multi-region support
- [ ] User authentication (Cognito)
- [ ] Image preview in results

## 📄 License

MIT License - see LICENSE file for details

## 👤 Author

Oumaima ATMANI - [GitHub Profile](https://github.com/oumaimaatmani)

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to branch
5. Open a Pull Request

---

**Built with ❤️ using AWS Serverless & Terraform**