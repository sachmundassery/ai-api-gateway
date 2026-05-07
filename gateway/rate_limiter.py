import redis
import os
import time
from fastapi import HTTPException, status
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

if REDIS_URL.startswith("rediss://"):
    r = redis.from_url(REDIS_URL, ssl_cert_reqs=None, decode_responses=True)
else:
    r = redis.from_url(REDIS_URL, decode_responses=True)

RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60

def check_rate_limit(username: str):
    key = f"rate_limit:{username}"
    current_time = int(time.time())
    window_start = current_time - RATE_LIMIT_WINDOW

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    pipe.zadd(key, {str(current_time): current_time})
    pipe.expire(key, RATE_LIMIT_WINDOW)
    results = pipe.execute()

    request_count = results[1]

    if request_count >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": RATE_LIMIT_REQUESTS,
                "window": f"{RATE_LIMIT_WINDOW} seconds",
                "message": f"You have made {request_count} requests in the last {RATE_LIMIT_WINDOW} seconds. Please wait."
            }
        )

    return {
        "requests_made": request_count + 1,
        "requests_remaining": RATE_LIMIT_REQUESTS - request_count - 1,
        "limit": RATE_LIMIT_REQUESTS,
        "window": f"{RATE_LIMIT_WINDOW} seconds"
    }