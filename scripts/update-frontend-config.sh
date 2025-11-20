#!/bin/bash

# Script to update frontend configuration from Terraform outputs
# Usage: ./scripts/update-frontend-config.sh

set -e

echo "🔧 Updating frontend configuration..."

# Check if terraform outputs exist
if [ ! -f "tf_outputs.json" ]; then
    echo "❌ Error: tf_outputs.json not found!"
    echo "   Please run 'cd terraform && terraform output -json > ../tf_outputs.json' first"
    exit 1
fi

# Extract API Gateway URL
API_URL=$(cat tf_outputs.json | jq -r '.api_gateway_url.value')

if [ -z "$API_URL" ] || [ "$API_URL" == "null" ]; then
    echo "❌ Error: Could not extract API Gateway URL from tf_outputs.json"
    exit 1
fi

echo "📡 API Gateway URL: $API_URL"

# Update frontend .env file
ENV_FILE="frontend/.env"

if [ -f "$ENV_FILE" ]; then
    echo "📝 Updating existing $ENV_FILE..."
    # Backup existing file
    cp "$ENV_FILE" "${ENV_FILE}.backup"
    echo "   Backup created: ${ENV_FILE}.backup"
fi

# Write new configuration
cat > "$ENV_FILE" << EOF
# API Configuration - Auto-generated from Terraform outputs
# Last updated: $(date)
VITE_API_BASE_URL=$API_URL
EOF

echo "✅ Frontend configuration updated successfully!"
echo ""
echo "📋 Configuration:"
echo "   VITE_API_BASE_URL=$API_URL"
echo ""
echo "🚀 Next steps:"
echo "   1. cd frontend"
echo "   2. npm install (if not already done)"
echo "   3. npm run dev"
echo ""
