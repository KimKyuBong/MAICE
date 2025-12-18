import os
import json
from datetime import datetime, timezone
from typing import Optional

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover - optional import guard
    redis = None

from .constants import TTL_PROGRESS_EVENTS_SECONDS, TTL_ANSWER_EVENTS_SECONDS


def progress_events_key(request_id: str) -> str:
    return f"progress_events:{request_id}"


def answer_events_key(request_id: str) -> str:
    return f"answer_events:{request_id}"


async def get_redis_client(url: Optional[str] = None):
    if redis is None:
        return None
    redis_url = url or os.getenv("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(redis_url)


async def push_answer_chunk(redis_client, request_id: str, text: str):
    if not (redis_client and request_id and text is not None):
        return
    key = answer_events_key(request_id)
    payload = {
        "type": "chunk",
        "content": text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await redis_client.rpush(key, json.dumps(payload))
    await redis_client.expire(key, TTL_ANSWER_EVENTS_SECONDS)


async def push_answer_complete(redis_client, request_id: str):
    if not (redis_client and request_id):
        return
    key = answer_events_key(request_id)
    payload = {
        "type": "complete",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await redis_client.rpush(key, json.dumps(payload))
    await redis_client.expire(key, TTL_ANSWER_EVENTS_SECONDS)


async def push_progress(redis_client, request_id: str, stage: str, message: str, progress: int = 0):
    if not (redis_client and request_id):
        return
    key = progress_events_key(request_id)
    payload = {
        "request_id": request_id,
        "stage": stage,
        "message": message,
        "progress": progress,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await redis_client.rpush(key, json.dumps(payload))
    await redis_client.expire(key, TTL_PROGRESS_EVENTS_SECONDS)


