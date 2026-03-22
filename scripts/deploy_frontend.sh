#!/bin/bash
# scripts/deploy_frontend.sh
# Automates building and syncing React frontend to AWS S3.

set -e

# Configuration
PROJECT_NAME="rag-document-assistant"
AWS_REGION=$(aws configure get region || echo "us-east-1")
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="rag-assistant-frontend-$AWS_ACCOUNT_ID"

echo "Deploying frontend for $PROJECT_NAME to AWS S3..."

# 1. Build Frontend
echo "Building React app..."
cd "$(dirname "$0")/../frontend"
npm install
npm run build

# 2. Sync to S3
echo "Syncing to S3 bucket $S3_BUCKET..."
aws s3 sync dist/ s3://$S3_BUCKET/ --delete

echo "Frontend deployment complete!"
