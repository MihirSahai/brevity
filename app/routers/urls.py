from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.core.database import get_db
from app.core.middleware import limiter
from app.schemas.url import ShortenRequest, ShortenResponse, StatsResponse
from app.services import shortener, cache
from app.core.config import settings

router = APIRouter()

@router.post("/api/v1/shorten", response_model=ShortenResponse)
@limiter.limit("10/minute")
async def shorten_url(request: Request, body: ShortenRequest, db: AsyncSession = Depends(get_db)):
    url = await shortener.create_short_url(db, body)
    await cache.set_slug(url.slug, url.original_url)
    return ShortenResponse(
        slug=url.slug,
        short_url=f"{settings.BASE_URL}/{url.slug}",
        original_url=url.original_url,
        created_at=url.created_at,
    )

@router.get("/api/v1/urls/{slug}/stats", response_model=StatsResponse)
async def get_stats(slug: str, db: AsyncSession = Depends(get_db)):
    stats = await shortener.get_stats(db, slug)
    if not stats:
        raise HTTPException(status_code=404, detail="URL not found")
    return stats

@router.get("/{slug}")
@limiter.limit("60/minute")
async def redirect_url(slug: str, request: Request, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    original_url = await cache.get_slug(slug)
    if not original_url:
        url = await shortener.get_url_by_slug(db, slug)
        if not url:
            raise HTTPException(status_code=404, detail="URL not found")
        if url.expires_at and url.expires_at < datetime.utcnow():
            raise HTTPException(status_code=410, detail="URL has expired")
        original_url = url.original_url
        await cache.set_slug(slug, original_url)
    else:
        url = await shortener.get_url_by_slug(db, slug)

    background_tasks.add_task(
        shortener.record_click, db, url,
        request.client.host,
        request.headers.get("user-agent", ""),
        request.headers.get("referer", ""),
    )
    return RedirectResponse(url=original_url, status_code=302)