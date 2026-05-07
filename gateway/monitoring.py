import time
import logging
import json
import os
import redis
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ai_gateway")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
if REDIS_URL.startswith("rediss://"):
    r = redis.from_url(REDIS_URL, ssl_cert_reqs=None, decode_responses=True)
else:
    r = redis.from_url(REDIS_URL, decode_responses=True)

def log_request(
    username: str,
    endpoint: str,
    question: str,
    cached: bool,
    latency_ms: float,
    status: str,
    error: str = None
):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "username": username,
        "endpoint": endpoint,
        "question": question[:100],
        "cached": cached,
        "latency_ms": round(latency_ms, 2),
        "status": status,
        "error": error
    }

    logger.info(json.dumps(log_entry))

    try:
        r.lpush("request_logs", json.dumps(log_entry))
        r.ltrim("request_logs", 0, 999)

        r.incr("stats:total_requests")
        if cached:
            r.incr("stats:cache_hits")
        else:
            r.incr("stats:cache_misses")
        if status == "error":
            r.incr("stats:errors")

        r.lpush("stats:latencies", latency_ms)
        r.ltrim("stats:latencies", 0, 99)

    except Exception as e:
        logger.error(f"Failed to store metrics: {e}")

def get_stats():
    try:
        total = int(r.get("stats:total_requests") or 0)
        hits = int(r.get("stats:cache_hits") or 0)
        misses = int(r.get("stats:cache_misses") or 0)
        errors = int(r.get("stats:errors") or 0)

        latencies = r.lrange("stats:latencies", 0, -1)
        avg_latency = 0
        if latencies:
            avg_latency = sum(float(l) for l in latencies) / len(latencies)

        cache_hit_rate = (hits / total * 100) if total > 0 else 0

        return {
            "total_requests": total,
            "cache_hits": hits,
            "cache_misses": misses,
            "cache_hit_rate": f"{round(cache_hit_rate, 1)}%",
            "errors": errors,
            "avg_latency_ms": round(avg_latency, 2),
            "success_rate": f"{round((total - errors) / total * 100, 1)}%" if total > 0 else "100%"
        }
    except Exception as e:
        return {"error": str(e)}

def get_recent_logs(limit: int = 10):
    try:
        logs = r.lrange("request_logs", 0, limit - 1)
        return [json.loads(log) for log in logs]
    except Exception:
        return []