FROM public.ecr.aws/docker/library/python:3.11-slim

# AWS Lambda Web Adapter
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4-x86_64 /lambda-adapter /opt/extensions/lambda-adapter
RUN chmod +x /opt/extensions/lambda-adapter

ENV PORT=8080
ENV AWS_LAMBDA_ADAPTER_SERVICE_PORT=8080
ENV ENV=production

# Install system dependencies: build tools + Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make curl \
    tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy AWS-specific requirements
COPY aws/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared source code
COPY src/ ./src/

# Copy AWS-specific security module (overwrites if exists)
COPY aws/src/ ./src/

EXPOSE 8080

CMD ["python3", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
