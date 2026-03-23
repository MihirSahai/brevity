from pydantic import BaseModel, HttpUrl
from datetime import datetime

class ShortenRequest(BaseModel):
    url: HttpUrl
    custom_slug: str | None = None
    expires_at: datetime | None = None

class ShortenResponse(BaseModel):
    slug: str
    short_url: str
    original_url: str
    created_at: datetime

class StatsResponse(BaseModel):
    slug: str
    original_url: str
    total_clicks: int
    unique_clicks: int
    created_at: datetime