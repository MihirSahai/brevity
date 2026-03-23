import redis.asyncio as aioredis
from app.core.config import settings

redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_slug(slug: str) -> str | None:
    return await redis.get(f"slug:{slug}")

async def set_slug(slug: str, original_url: str, ttl: int = 86400) -> None:
    await redis.set(f"slug:{slug}", original_url, ex=ttl)

async def increment_clicks(slug: str) -> None:
    await redis.incr(f"clicks:{slug}")

async def invalidate_slug(slug: str) -> None:
    await redis.delete(f"slug:{slug}")