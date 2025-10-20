from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.v1 import api_router
from app.config import settings
from app.core.logging import configure_logging
from app.websocket.server import socket_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(app.debug)

    # Start background jobs
    from app.services.background_jobs import start_background_jobs
    await start_background_jobs()

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Souk Loop API",
        description="Hyperlocal social commerce platform for the UAE.",
        version="1.0.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok"}

    app.include_router(api_router, prefix="/api/v1")
    app.mount("/ws", socket_app)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
