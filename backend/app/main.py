import asyncio
import sys

# Playwright subprocess launch requires ProactorEventLoop on Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import get_api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.services.bulk_job_persistence import recover_interrupted_bulk_jobs


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    await recover_interrupted_bulk_jobs()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(get_api_router(), prefix=settings.api_v1_prefix)
    return app


app = create_app()
