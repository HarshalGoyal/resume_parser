"""Dev/prod entry point. Host, port, and reload are environment-driven:

    HOST=0.0.0.0 PORT=8080 RELOAD=false python run.py
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "localhost"),
        port=int(os.getenv("PORT", "3030")),
        reload=os.getenv("RELOAD", "true").lower() in ("1", "true", "yes"),
    )
