import uuid
import json
import redis.asyncio as redis
from fastapi import HTTPException
from app.core.config import settings

# Initialize redis connection
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def create_refresh_token(user_id: int) -> str:
    """Create a new refresh token and store in redis with a 30 day TTL."""
    token = str(uuid.uuid4())
    ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    await redis_client.setex(f"refresh_token:{token}", ttl_seconds, str(user_id))
    return token

async def verify_refresh_token(token: str) -> int:
    """Verify refresh token in redis and return user_id."""
    user_id = await redis_client.get(f"refresh_token:{token}")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return int(user_id)

async def delete_refresh_token(token: str):
    """Remove refresh token from redis on logout."""
    await redis_client.delete(f"refresh_token:{token}")
