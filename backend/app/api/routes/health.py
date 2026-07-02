from fastapi import APIRouter  # type: ignore[import]
from ...core.logging import AppLogger

router = APIRouter (prefix="/health", tags=['Health Check'])

@router.get("/", summary="Liveness/health probe")
async def health_check():
    loggr = AppLogger("HealthCheck")
    loggr.info("Performing health check...")
    
    return {"status": "healthy"}
