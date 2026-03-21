"""FastAPI application for RAG backend."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router

# Try to import webhook routes (AWS track only)
HAS_WEBHOOKS = False
WEBHOOK_ERROR = None
try:
    from src.api.webhook_routes import router as webhook_router
    HAS_WEBHOOKS = True
except ImportError as e:
    WEBHOOK_ERROR = str(e)
except Exception as e:
    WEBHOOK_ERROR = f"{type(e).__name__}: {e}"

app = FastAPI(
    title="RAG Document Assistant API",
    description="Privacy-first RAG API with Zero-Storage",
    version="2.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Include webhook routes if available (AWS track)
if HAS_WEBHOOKS:
    app.include_router(webhook_router, prefix="/api")


@app.get("/")
async def root():
    result = {
        "message": "RAG Document Assistant API",
        "docs": "/docs",
        "webhooks": HAS_WEBHOOKS,
        "env": os.getenv("ENV", "development")
    }
    if WEBHOOK_ERROR:
        result["webhook_error"] = WEBHOOK_ERROR
    return result
