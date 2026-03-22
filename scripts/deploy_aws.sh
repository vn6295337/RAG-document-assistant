#!/bin/bash
# scripts/deploy_aws.sh
# Automates building and pushing Docker image to ECR, then updating Lambda.

set -e

# Configuration
PROJECT_NAME="rag-document-assistant"
AWS_REGION=$(aws configure get region || echo "us-east-1")
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO_NAME="rag-document-assistant-backend"
LAMBDA_FUNCTION_NAME="rag-document-assistant-api"
IMAGE_TAG="latest"

echo "Deploying $PROJECT_NAME to AWS..."

# 1. Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# 2. Build Docker Image
echo "Building Docker image..."
# Move to project root
cd "$(dirname "$0")/.."
docker build -t $ECR_REPO_NAME .

# 3. Tag and Push
echo "Pushing image to ECR..."
docker tag $ECR_REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG

# 4. Update Lambda Function
echo "Updating Lambda function $LAMBDA_FUNCTION_NAME..."
aws lambda update-function-code \
    --function-name $LAMBDA_FUNCTION_NAME \
    --image-uri $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG

echo "Deployment complete!"
