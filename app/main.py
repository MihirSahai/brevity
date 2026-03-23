from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.routers.urls import router
from app.core.middleware import limiter

app = FastAPI(title="URL Shortener", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "ok"}
