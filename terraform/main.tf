# terraform/main.tf

provider "aws" {
  region = var.aws_region
}

# ECR Repository for the backend image
resource "aws_ecr_repository" "backend" {
  name                 = "rag-document-assistant-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "rag_assistant_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Lambda (SSM, Bedrock, Logging)
resource "aws_iam_role_policy" "lambda_policy" {
  name = "rag_assistant_lambda_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/rag_assistant/*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "*"
      }
    ]
  })
}

data "aws_caller_identity" "current" {}

# Lambda Function (Container)
resource "aws_lambda_function" "backend" {
  function_name = "rag-document-assistant-api"
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.backend.repository_url}:latest"
  timeout       = 30
  memory_size   = 2048 # Docling needs at least 512MB-1GB, 2GB is safer

  environment {
    variables = {
      ENV = "production"
      # These will be fetched from SSM in the app code or passed here
      PINECONE_INDEX_NAME = "rag-semantic-384"
      AWS_REGION          = var.aws_region
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy
  ]
}

# API Gateway (v2 HTTP API)
resource "aws_apigatewayv2_api" "api" {
  name          = "rag-assistant-gateway"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"] # Adjust for production
    allow_methods = ["*"]
    allow_headers = ["*"]
  }
}

resource "aws_apigatewayv2_stage" "stage" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.backend.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "route" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

# SSM Parameters (Placeholders)
resource "aws_ssm_parameter" "pinecone_key" {
  name  = "/rag_assistant/PINECONE_API_KEY"
  type  = "SecureString"
  value = "PLACEHOLDER"
  lifecycle { ignore_changes = [value] }
}

resource "aws_ssm_parameter" "gemini_key" {
  name  = "/rag_assistant/GEMINI_API_KEY"
  type  = "SecureString"
  value = "PLACEHOLDER"
  lifecycle { ignore_changes = [value] }
}

# S3 Bucket for Frontend
resource "aws_s3_bucket" "frontend" {
  bucket = "rag-assistant-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  index_document { suffix = "index.html" }
  error_document { key = "index.html" }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })
  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

output "api_endpoint" {
  value = aws_apigatewayv2_api.api.api_endpoint
}

output "frontend_url" {
  value = aws_s3_bucket_website_configuration.frontend.website_endpoint
}
