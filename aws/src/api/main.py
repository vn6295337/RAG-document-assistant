"""FastAPI application for RAG backend (AWS track with webhooks)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router

# Import webhook routes (AWS track only)
try:
    from src.api.webhook_routes import router as webhook_router
    HAS_WEBHOOKS = True
except ImportError:
    HAS_WEBHOOKS = False

app = FastAPI(
    title="RAG Document Assistant API",
    description="Privacy-first RAG API with Zero-Storage (AWS Track)",
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

# Include webhook routes (AWS track only)
if HAS_WEBHOOKS:
    app.include_router(webhook_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "RAG Document Assistant API",
        "track": "AWS",
        "docs": "/docs",
        "webhooks": HAS_WEBHOOKS
    }
