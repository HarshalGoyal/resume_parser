from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.logging import AppLogger
from .core.exceptions import BaseResumeException
from .api.routes.health import router as health_router
from .api.routes.upload import router as resume_router
from .api.routes.info import router as info_router

logger = AppLogger("App")

app = FastAPI(title=settings.app_name, version=settings.version)

# Use the configured allow-list instead of leaving CORS unconfigured.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(resume_router)
app.include_router(info_router)


@app.exception_handler(BaseResumeException)
async def handle_resume_exception(request: Request, exc: BaseResumeException):
    """Translate the application's structured exceptions into consistent,
    error-coded JSON responses instead of leaking generic 500s."""
    logger.error(f"{request.method} {request.url.path} -> {exc}")
    return JSONResponse(status_code=exc.http_status_code, content=exc.to_dict())


@app.get("/", summary="Service liveness banner")
async def root():
    return {"message": "Resume parser up and running!"}
