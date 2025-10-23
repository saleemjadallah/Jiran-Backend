from contextlib import asynccontextmanager
import os

import uvicorn
from fastapi import FastAPI

from app.api.v1 import api_router
from app.config import settings
from app.core.logging import configure_logging
from app.websocket.server import socket_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(app.debug)

    # Initialize Redis cache manager
    from app.core.cache.redis_manager import init_redis_manager, close_redis_manager, get_redis_manager
    from app.core.cache.cache_warming import init_cache_warming_service

    redis_manager = await init_redis_manager()
    app.debug and print("✅ Redis cache manager initialized")

    # Initialize cache warming service
    warming_service = init_cache_warming_service(redis_manager)
    app.debug and print("✅ Cache warming service initialized")

    # Warm cache on startup (run in background to not block startup)
    import asyncio
    asyncio.create_task(warming_service.warm_all())

    # Initialize Elasticsearch (optional)
    from app.services.elasticsearch_service import elasticsearch_service
    try:
        await elasticsearch_service.connect()
        app.debug and print("✅ Elasticsearch service initialized")
    except Exception as e:
        app.debug and print(f"⚠️ Elasticsearch not available: {e}")
        app.debug and print("ℹ️ Search features will be disabled")

    # Start background jobs (disabled for initial deployment)
    # Uncomment when database is ready
    # from app.services.background_jobs import start_background_jobs
    # await start_background_jobs()

    yield

    # Cleanup on shutdown
    try:
        await elasticsearch_service.disconnect()
        app.debug and print("✅ Elasticsearch service closed")
    except Exception:
        pass  # Elasticsearch was not connected

    await close_redis_manager()
    app.debug and print("✅ Redis cache manager closed")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Jiran API",
        description="Hyperlocal social commerce platform for the UAE.",
        version="1.0.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    @app.get("/health", tags=["Health"])
    async def health_check():
        from datetime import datetime
        return {"status": "ok", "deployment_time": "2025-01-20T10:50:00Z", "current_time": datetime.utcnow().isoformat()}

    app.include_router(api_router, prefix="/api/v1")
    app.mount("/ws", socket_app)

    return app


app = create_app()


if __name__ == "__main__":
    # Read PORT from environment variable (Railway/production) or default to 8000 (local)
    port = int(os.getenv("PORT", 8000))

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
    )
