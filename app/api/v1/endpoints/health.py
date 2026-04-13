"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check."""
    return {"status": "ok", "service": "BoneBET API", "version": "0.1.0"}


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "BoneBET API",
        "endpoints": {
            "/health": "GET - health check",
            "/api/v1/bet": "GET - betting analysis",
        }
    }