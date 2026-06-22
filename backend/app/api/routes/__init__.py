from fastapi import APIRouter

from app.api.routes import health, prospects, scraping, searches


def get_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(health.router)
    router.include_router(searches.router)
    router.include_router(scraping.router)
    router.include_router(prospects.router)
    return router
