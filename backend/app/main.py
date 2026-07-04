import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .core.config import settings
from .core.logging import AppLogger
from .core.exceptions import BaseResumeException
from .core.middleware import api_key_middleware, observability_middleware
from .api.deps import session_repository
from .services.cleanup_service import cleanup_loop
from .api.routes.health import router as health_router
from .api.routes.upload import router as resume_router
from .api.routes.results import router as results_router
from .api.routes.evaluation import router as evaluation_router
from .api.routes.jd import router as jd_router
from .api.routes.llm_config import router as llm_config_router
from .api.routes.benchmark import router as benchmark_router
from .api.routes.info import router as info_router

logger = AppLogger("App")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(cleanup_loop(session_repository))
    yield
    task.cancel()


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

# Use the configured allow-list instead of leaving CORS unconfigured.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Outermost first: auth gates everything, then request-id/logging/metrics.
app.middleware("http")(observability_middleware)
app.middleware("http")(api_key_middleware)

app.include_router(health_router)
app.include_router(resume_router)
app.include_router(results_router)
app.include_router(evaluation_router)
app.include_router(jd_router)
app.include_router(llm_config_router)
app.include_router(benchmark_router)
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


@app.get("/metrics", summary="Prometheus metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
