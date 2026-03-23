from nanoid import generate
import validators
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models.url import Url
from app.models.click import Click
from app.schemas.url import ShortenRequest

ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

BLOCKED_DOMAINS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "169.254.169.254",  # AWS metadata endpoint — very important to block
    "192.168.0.1",
]

def validate_url(url: str) -> None:
    if not validators.url(url):
        raise HTTPException(status_code=422, detail="Invalid URL format")
    
    from urllib.parse import urlparse
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    
    if hostname in BLOCKED_DOMAINS:
        raise HTTPException(status_code=422, detail="This URL is not allowed")
    
    if hostname.startswith("192.168.") or hostname.startswith("10."):
        raise HTTPException(status_code=422, detail="Private network URLs are not allowed")
    
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=422, detail="Only http and https URLs are allowed")

async def create_short_url(db: AsyncSession, request: ShortenRequest) -> Url:
    validate_url(str(request.url))
    
    if request.custom_slug:
        existing = await db.execute(select(Url).where(Url.slug == request.custom_slug))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="This custom slug is already taken")
        slug = request.custom_slug
    else:
        slug = await _generate_unique_slug(db)
    
    url = Url(
        slug=slug,
        original_url=str(request.url),
        expires_at=request.expires_at,
    )
    db.add(url)
    await db.commit()
    return url

async def get_url_by_slug(db: AsyncSession, slug: str) -> Url | None:
    result = await db.execute(select(Url).where(Url.slug == slug, Url.is_active == True))
    return result.scalar_one_or_none()

async def record_click(db: AsyncSession, url: Url, ip: str, user_agent: str, referer: str) -> None:
    click = Click(
        url_id=url.id,
        ip_hash=hashlib.sha256(ip.encode()).hexdigest()[:16],
        user_agent=user_agent[:256] if user_agent else None,
        referer=referer[:512] if referer else None,
    )
    db.add(click)
    await db.commit()

async def get_stats(db: AsyncSession, slug: str) -> dict:
    url = await get_url_by_slug(db, slug)
    if not url:
        return None
    total = await db.execute(select(func.count()).where(Click.url_id == url.id))
    unique = await db.execute(select(func.count(Click.ip_hash.distinct())).where(Click.url_id == url.id))
    return {
        "slug": slug,
        "original_url": url.original_url,
        "total_clicks": total.scalar(),
        "unique_clicks": unique.scalar(),
        "created_at": url.created_at,
    }

async def _generate_unique_slug(db: AsyncSession, length: int = 6) -> str:
    for _ in range(5):
        slug = generate(ALPHABET, length)
        existing = await db.execute(select(Url).where(Url.slug == slug))
        if not existing.scalar_one_or_none():
            return slug
    raise Exception("Could not generate unique slug after 5 attempts")