# Production Deployment URLs

This file contains all the production URLs for the Serverless ML Image Processing Pipeline.

## 🌐 Frontend (S3 Static Website)

**Public URL:**
```
http://serverless-ml-frontend-1763148161.s3-website-us-east-1.amazonaws.com
```

**S3 Bucket:** `serverless-ml-frontend-1763148161`

**Deployment Date:** November 14, 2025

---

## 🔌 Backend API (API Gateway)

**Base URL:**
```
https://eekq7136ti.execute-api.us-east-1.amazonaws.com/prod
```

### **Endpoints:**

#### Upload URL Generation
```
POST https://eekq7136ti.execute-api.us-east-1.amazonaws.com/prod/upload-url
```

**Request Body:**
```json
{
  "fileName": "image.jpg",
  "fileType": "image/jpeg",
  "userId": "optional-user-id"
}
```

#### Get All Results
```
GET https://eekq7136ti.execute-api.us-east-1.amazonaws.com/prod/results?limit=20
```

#### Get Specific Result
```
GET https://eekq7136ti.execute-api.us-east-1.amazonaws.com/prod/results/{image_id}
```

---

## 📦 AWS Resources

### **S3 Buckets**
- **Images:** `serverless-ml-dev-images-92ccd094`
- **Frontend:** `serverless-ml-frontend-1763148161`

### **DynamoDB Tables**
- **Analysis Results:** `serverless-ml-dev-analysis-results`
- **Workflow Logs:** `serverless-ml-dev-workflow-logs`

### **Lambda Functions**
1. `serverless-ml-dev-presigned-url-generator`
2. `serverless-ml-dev-image-processor`
3. `serverless-ml-dev-rekognition-analyzer`
4. `serverless-ml-dev-result-saver`
5. `serverless-ml-dev-notification-handler`
6. `serverless-ml-dev-result-viewer`

### **Step Functions**
- **State Machine:** `serverless-ml-dev-image-workflow`
- **Dashboard:** [View in AWS Console](https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines/view/arn:aws:states:us-east-1:095074107586:stateMachine:serverless-ml-dev-image-workflow)

---

## 🚀 Quick Start

### **Access the Application**
Simply open the frontend URL in your browser:
```
http://serverless-ml-frontend-1763148161.s3-website-us-east-1.amazonaws.com
```

### **Upload an Image**
1. Click "Choose an image file" or drag & drop
2. Select any image (max 10MB)
3. Click "Upload & Analyze"
4. Wait 2-3 seconds for AI analysis
5. View results!

---

## 🔄 Update Frontend

To deploy updates to the frontend:

```bash
# Navigate to frontend directory
cd frontend

# Build production version
npm run build

# Sync to S3
aws s3 sync dist/ s3://serverless-ml-frontend-1763148161/ --delete

# Verify deployment
curl -I http://serverless-ml-frontend-1763148161.s3-website-us-east-1.amazonaws.com
```

---

## 🗑️ Cleanup

To remove all resources and stop charges:

### **Frontend:**
```bash
# Delete frontend bucket
aws s3 rb s3://serverless-ml-frontend-1763148161 --force
```

### **Backend:**
```bash
# Navigate to terraform directory
cd terraform

# Destroy all infrastructure
terraform destroy
```

---

## 💰 Cost Estimate

**Monthly costs (10K images):**
- AWS Rekognition: ~$10
- Lambda: ~$2-3
- DynamoDB: ~$2-3
- S3 Storage: ~$1-2
- API Gateway: ~$1-2
- CloudWatch: ~$5
- **Total: ~$20-30/month**

---

## 📊 Monitoring

### **CloudWatch Logs**
```bash
# View API Gateway logs
aws logs tail /aws/apigateway/serverless-ml-dev-results-api --follow

# View Lambda logs
aws logs tail /aws/lambda/serverless-ml-dev-rekognition-analyzer --follow
```

### **Step Functions Executions**
```bash
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:095074107586:stateMachine:serverless-ml-dev-image-workflow \
  --max-results 10
```

### **DynamoDB Items**
```bash
aws dynamodb scan --table-name serverless-ml-dev-analysis-results --limit 10
```

---

## 🔐 Security Notes

- Frontend is publicly accessible (static website)
- API endpoints have CORS configured for all origins (*)
- S3 images bucket has public access blocked
- Uploads use presigned URLs (5-minute expiry)
- All Lambda functions use IAM least-privilege policies

### **Production Recommendations:**
- Add API Gateway API keys for rate limiting
- Implement user authentication (AWS Cognito)
- Enable AWS WAF for API protection
- Set up CloudFront for HTTPS and caching
- Add monitoring alerts for errors and costs

---

## 📝 Notes

- Frontend automatically connects to the backend API
- No CORS issues since both are on AWS
- Images are automatically deleted after 365 days (S3 lifecycle rule)
- Analysis results have 30-day TTL in DynamoDB
- All infrastructure is defined in Terraform for easy redeployment

---

**Last Updated:** November 14, 2025
**Deployed By:** Claude Code
**Region:** us-east-1
