# Complete Deployment Guide

This guide walks you through deploying the entire serverless ML image processing pipeline with frontend.

## 📋 Prerequisites

Before starting, ensure you have:

- ✅ AWS Account with appropriate permissions
- ✅ AWS CLI v2 installed and configured (`aws configure`)
- ✅ Terraform >= 1.0 installed
- ✅ Node.js >= 18 and npm installed
- ✅ Git installed

## 🚀 Step-by-Step Deployment

### Step 1: Clone the Repository

```bash
git clone https://github.com/oumaimaatmani/serverless-ml-aws.git
cd serverless-ml-aws
```

### Step 2: Deploy Backend Infrastructure

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan -out=tfplan

# Apply the infrastructure
terraform apply tfplan

# Export outputs for later use
terraform output -json > ../tf_outputs.json
cd ..
```

**Expected Outputs:**
- S3 bucket for image storage
- DynamoDB tables for results
- 6 Lambda functions
- Step Functions state machine
- API Gateway with 3 routes
- EventBridge event bus
- IAM roles and policies

**Deployment Time:** ~3-5 minutes

### Step 3: Configure Frontend

```bash
# Run the auto-configuration script
chmod +x scripts/update-frontend-config.sh
./scripts/update-frontend-config.sh
```

This script automatically:
- Reads the API Gateway URL from Terraform outputs
- Updates `frontend/.env` with the correct API endpoint
- Creates a backup of the existing configuration

**Manual Alternative:**
```bash
# Get API URL
API_URL=$(cat tf_outputs.json | jq -r '.api_gateway_url.value')

# Update frontend/.env
echo "VITE_API_BASE_URL=$API_URL" > frontend/.env
```

### Step 4: Install Frontend Dependencies

```bash
cd frontend
npm install
```

**Expected Installation Time:** ~2-3 minutes

### Step 5: Start Development Server

```bash
npm run dev
```

The application will be available at: `http://localhost:5173`

### Step 6: Test the Application

1. **Open your browser** to `http://localhost:5173`
2. **Upload a test image**:
   - Click "Choose an image file" or drag & drop
   - Select an image (JPEG, PNG, GIF, BMP, or WEBP)
   - Click "Upload & Analyze"
3. **Wait for analysis** (2-3 seconds)
4. **View results**:
   - Object detection labels
   - Face detection (if present)
   - Content moderation status
   - Confidence scores

## 🔍 Verification Steps

### Backend Verification

```bash
# Check S3 bucket exists
aws s3 ls | grep serverless-ml-dev

# Verify Lambda functions
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `serverless-ml-dev`)].FunctionName'

# Test API Gateway
API_URL=$(cat tf_outputs.json | jq -r '.api_gateway_url.value')
curl $API_URL/results

# Check Step Functions
aws stepfunctions list-state-machines --query 'stateMachines[?starts_with(name, `serverless-ml-dev`)].name'
```

### Frontend Verification

```bash
# Check environment configuration
cat frontend/.env

# Verify API connectivity
cd frontend
npm run build  # Should complete without errors
```

## 📦 Production Deployment

### Option 1: S3 + CloudFront (Recommended)

```bash
# Build the frontend
cd frontend
npm run build

# Create S3 bucket for frontend hosting
aws s3 mb s3://your-frontend-bucket

# Enable static website hosting
aws s3 website s3://your-frontend-bucket --index-document index.html

# Upload built files
aws s3 sync dist/ s3://your-frontend-bucket/ --delete

# Set bucket policy for public read
aws s3api put-bucket-policy --bucket your-frontend-bucket --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::your-frontend-bucket/*"
  }]
}'

# Optional: Create CloudFront distribution for HTTPS and caching
aws cloudfront create-distribution --origin-domain-name your-frontend-bucket.s3-website-us-east-1.amazonaws.com
```

### Option 2: AWS Amplify

```bash
# Install Amplify CLI
npm install -g @aws-amplify/cli

# Initialize Amplify
cd frontend
amplify init

# Add hosting
amplify add hosting

# Publish
amplify publish
```

### Option 3: Netlify

1. Connect GitHub repository to Netlify
2. Configure build settings:
   - **Build command:** `npm run build`
   - **Publish directory:** `dist`
3. Add environment variable: `VITE_API_BASE_URL` = `<your-api-gateway-url>`
4. Deploy

### Option 4: Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel --prod
```

When prompted, set:
- Environment variable: `VITE_API_BASE_URL` = `<your-api-gateway-url>`

## 🔧 Configuration Options

### Terraform Variables

Edit `terraform/terraform.tfvars` to customize:

```hcl
# Region and environment
aws_region  = "us-east-1"
environment = "dev"

# Lambda configuration
lambda_memory_size = 512
lambda_timeout     = 60

# DynamoDB capacity
dynamodb_read_capacity  = 5
dynamodb_write_capacity = 5

# Rekognition threshold
rekognition_confidence_threshold = 80

# Optional: Email notifications
notification_email = "your-email@example.com"
```

After changing variables:
```bash
cd terraform
terraform plan -out=tfplan
terraform apply tfplan
```

### Frontend Configuration

Edit `frontend/.env`:

```bash
# API Gateway endpoint
VITE_API_BASE_URL=https://your-api.execute-api.us-east-1.amazonaws.com/prod
```

## 🧪 Testing

### Unit Testing (Backend)

```bash
# Install pytest
pip install pytest boto3 moto

# Run tests (if implemented)
cd lambda_functions/image_processor
pytest
```

### Integration Testing

```bash
# Upload test image via API
cd frontend
npm run build
npm run preview

# Or test via CLI
aws s3 cp test-image.jpg s3://$(cat ../tf_outputs.json | jq -r '.s3_bucket_name.value')/uploads/

# Monitor execution
aws stepfunctions list-executions \
  --state-machine-arn $(cat ../tf_outputs.json | jq -r '.step_functions_arn.value') \
  --max-results 1

# Check results
API_URL=$(cat ../tf_outputs.json | jq -r '.api_gateway_url.value')
curl $API_URL/results | jq '.'
```

### Load Testing

```bash
# Install artillery
npm install -g artillery

# Create test config
cat > artillery-test.yml <<EOF
config:
  target: "$(cat tf_outputs.json | jq -r '.api_gateway_url.value')"
  phases:
    - duration: 60
      arrivalRate: 10
scenarios:
  - name: "Get results"
    flow:
      - get:
          url: "/results?limit=10"
EOF

# Run load test
artillery run artillery-test.yml
```

## 📊 Monitoring and Observability

### CloudWatch Dashboards

```bash
# View Lambda logs
aws logs tail /aws/lambda/serverless-ml-dev-rekognition-analyzer --follow

# View API Gateway logs
aws logs tail /aws/apigateway/serverless-ml-dev-results-api --follow

# View Step Functions execution
API_URL=$(cat tf_outputs.json | jq -r '.step_functions_dashboard_url.value')
echo "Open: $API_URL"
```

### Metrics to Monitor

- **Lambda Duration:** Should be < 3 seconds for Rekognition analyzer
- **API Gateway 4xx/5xx Errors:** Should be < 1%
- **Step Functions Failed Executions:** Should be 0
- **DynamoDB Throttled Requests:** Should be 0

### Setting Up Alarms

```bash
# Create SNS topic for alerts
aws sns create-topic --name serverless-ml-alerts

# Subscribe to alerts
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:serverless-ml-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Create CloudWatch alarm for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name serverless-ml-lambda-errors \
  --alarm-description "Alert on Lambda function errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:serverless-ml-alerts
```

## 🔐 Security Hardening

### Production Checklist

- [ ] Enable AWS CloudTrail for audit logging
- [ ] Set up AWS WAF rules for API Gateway
- [ ] Implement API key authentication
- [ ] Add rate limiting to API Gateway
- [ ] Enable GuardDuty for threat detection
- [ ] Rotate IAM access keys regularly
- [ ] Enable S3 bucket versioning and lifecycle policies
- [ ] Set up AWS Backup for DynamoDB tables
- [ ] Implement AWS Secrets Manager for sensitive data
- [ ] Enable VPC endpoints for private API access

### Example: Add API Key Authentication

```hcl
# Add to terraform/lambda.tf

resource "aws_api_gateway_api_key" "frontend_key" {
  name = "${local.project_name}-frontend-key"
}

resource "aws_api_gateway_usage_plan" "frontend_plan" {
  name = "${local.project_name}-frontend-usage-plan"

  api_stages {
    api_id = aws_apigatewayv2_api.results_api.id
    stage  = aws_apigatewayv2_stage.results_api_stage.name
  }

  quota_settings {
    limit  = 10000
    period = "MONTH"
  }

  throttle_settings {
    burst_limit = 100
    rate_limit  = 50
  }
}
```

## 🗑️ Cleanup

To remove all resources and avoid charges:

```bash
# Destroy infrastructure
cd terraform
terraform destroy

# Remove frontend bucket (if created)
aws s3 rb s3://your-frontend-bucket --force

# Remove local files
cd ..
rm -rf node_modules frontend/node_modules frontend/dist terraform/.terraform*
```

## 🐛 Troubleshooting

### Issue: Terraform apply fails

**Solution:**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Check Terraform state
cd terraform
terraform state list

# Re-initialize if needed
terraform init -reconfigure
```

### Issue: Frontend can't connect to API

**Solution:**
```bash
# Verify API URL in .env
cat frontend/.env

# Test API directly
curl $(cat tf_outputs.json | jq -r '.api_gateway_url.value')/results

# Check CORS configuration in terraform/lambda.tf
```

### Issue: Upload fails with 403 error

**Solution:**
- Check Lambda has S3 PutObject permissions in IAM policy
- Verify presigned URL hasn't expired (5-minute timeout)
- Check S3 bucket policy allows uploads

### Issue: No results after upload

**Solution:**
```bash
# Check Step Functions execution
aws stepfunctions list-executions \
  --state-machine-arn $(cat tf_outputs.json | jq -r '.step_functions_arn.value') \
  --max-results 1

# View Lambda logs
aws logs tail /aws/lambda/serverless-ml-dev-image-processor --since 5m

# Check EventBridge rule is enabled
aws events describe-rule --name serverless-ml-dev-s3-upload-rule
```

## 📞 Support

For issues:
1. Check CloudWatch logs for error messages
2. Review Terraform outputs: `cd terraform && terraform output`
3. Verify IAM permissions
4. Check GitHub issues: https://github.com/oumaimaatmani/serverless-ml-aws/issues

## 📚 Additional Resources

- [AWS Serverless Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [React + Vite Guide](https://vitejs.dev/guide/)
- [AWS Rekognition Documentation](https://docs.aws.amazon.com/rekognition/)

---

**Deployment Complete! 🎉**

Your serverless ML image processing pipeline is now live and ready to analyze images!
