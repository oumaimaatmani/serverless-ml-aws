# Frontend Setup Guide

## Prerequisites
- Node.js 18+ and npm installed
- Backend infrastructure deployed via Terraform

## Quick Start

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configure API Endpoint
The API endpoint URL is automatically set in `.env` file. If you need to update it:

```bash
# Get the API Gateway URL from terraform outputs
cd ../terraform
terraform output -json | jq -r '.api_gateway_url.value'

# Update frontend/.env with the URL
echo "VITE_API_BASE_URL=<your-api-gateway-url>" > .env
```

Or use the provided helper script:
```bash
# From project root
./scripts/update-frontend-config.sh
```

### 3. Run Development Server
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### 4. Build for Production
```bash
npm run build
```

The built files will be in the `dist/` directory.

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | API Gateway endpoint URL | `https://xxx.execute-api.us-east-1.amazonaws.com/prod` |

## API Endpoints Used

The frontend connects to the following backend endpoints:

- `POST /upload-url` - Get presigned S3 upload URL
- `GET /results` - List recent analysis results
- `GET /results/{image_id}` - Get specific analysis result

## Features

1. **Image Upload**
   - Drag & drop or file selector
   - Client-side validation (format, size)
   - Secure upload via presigned S3 URLs
   - Real-time upload progress

2. **Results Display**
   - Real-time polling for analysis completion
   - Object detection with confidence scores
   - Face detection with attributes (age, gender, emotions)
   - Content moderation status
   - Recent uploads history

## Development

### Project Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── ImageUpload.jsx       # Upload interface
│   │   ├── ImageUpload.css
│   │   ├── ResultsDisplay.jsx    # Results viewer
│   │   └── ResultsDisplay.css
│   ├── services/
│   │   └── api.js                # API client
│   ├── App.jsx                   # Main component
│   ├── App.css
│   └── main.jsx                  # Entry point
├── .env                          # Environment variables
├── .env.example                  # Example configuration
├── package.json
├── vite.config.js
└── index.html
```

### Running Linter
```bash
npm run lint
```

### Building for Production
```bash
npm run build
npm run preview  # Preview production build
```

## Deployment Options

### Option 1: S3 + CloudFront (Recommended)
```bash
# Build the app
npm run build

# Deploy to S3 bucket
aws s3 sync dist/ s3://your-frontend-bucket/ --delete

# Invalidate CloudFront cache (if using)
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

### Option 2: Netlify/Vercel
1. Connect your git repository
2. Set build command: `npm run build`
3. Set publish directory: `dist`
4. Add environment variable: `VITE_API_BASE_URL`

### Option 3: Docker
```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Troubleshooting

### CORS Errors
If you see CORS errors, verify that:
1. API Gateway CORS is configured correctly (already done in Terraform)
2. The API URL in `.env` is correct
3. You're using the correct HTTP methods (POST for upload, GET for results)

### 404 Errors on Results
This is normal! When you first upload an image, the analysis takes 2-3 seconds. The frontend automatically polls every 3 seconds until results are available.

### Image Upload Fails
Check:
1. File size is under 10MB
2. File format is supported (JPEG, PNG, GIF, BMP, WEBP)
3. Presigned URL hasn't expired (5-minute timeout)
4. S3 bucket exists and Lambda has permissions

## Support

For issues with:
- **Frontend**: Check browser console for errors
- **Backend API**: Check API Gateway logs in CloudWatch
- **Lambda Functions**: Check Lambda logs in CloudWatch
- **Infrastructure**: Run `terraform plan` to verify configuration
