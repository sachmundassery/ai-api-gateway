import os
import json
import redis
from celery import Celery
from dotenv import load_dotenv
from gateway.cache import get_cached_response, store_in_cache
from gateway.llm import ask_llm

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

celery_app = Celery(
    "ai_gateway",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_use_ssl={"ssl_cert_reqs": None} if REDIS_URL.startswith("rediss://") else {},
    redis_backend_use_ssl={"ssl_cert_reqs": None} if REDIS_URL.startswith("rediss://") else {},
)

if REDIS_URL.startswith("rediss://"):
    r = redis.from_url(REDIS_URL, ssl_cert_reqs=None, decode_responses=True)
else:
    r = redis.from_url(REDIS_URL, decode_responses=True)

@celery_app.task(bind=True)
def process_ai_query(self, question: str, context: str, username: str):
    try:
        cached = get_cached_response(question)
        if cached:
            return {
                "status": "completed",
                "question": question,
                "answer": cached["answer"],
                "cached": True,
                "similarity_score": cached["similarity_score"],
                "user": username
            }

        result = ask_llm(question, context)
        store_in_cache(question, result["answer"])

        return {
            "status": "completed",
            "question": question,
            "answer": result["answer"],
            "cached": False,
            "model": result["model"],
            "user": username
        }

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "question": question,
            "user": username
        }