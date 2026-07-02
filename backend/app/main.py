from fastapi import FastAPI # type: ignore
from .api.routes.health import router as health_router
from .api.routes.upload import router as resume_router
from .api.routes.parser_config import router as parser_config_router

app = FastAPI(title = "Resume Parser Api", version = "1.0.0")
app.include_router(health_router)
app.include_router(resume_router)
app.include_router(parser_config_router)
@app.get("/")
async def root():
    return {"message": "Resume parser up and running!"}

