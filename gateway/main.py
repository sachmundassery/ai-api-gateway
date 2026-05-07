from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from gateway.auth import authenticate_user, create_access_token, get_current_user
from gateway.rate_limiter import check_rate_limit
from gateway.cache import get_cached_response, store_in_cache, get_cache_stats
from gateway.llm import ask_llm
from pydantic import BaseModel
from gateway.queue import process_ai_query
from celery.result import AsyncResult
from gateway.monitoring import log_request, get_stats, get_recent_logs
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI API Gateway",
    description="Production-grade AI gateway with auth, rate limiting, caching and queuing",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = round(time.time() - start_time, 3)
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration}s")
    return response

@app.get("/")
async def root():
    return {
        "service": "AI API Gateway",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "redis": "connected",
        "llm": "groq"
    }


class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/login")
async def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"]
    }

@app.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user["username"],
        "role": current_user["role"]
    }

@app.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    return {
        "message": f"Hello {current_user['username']}! You have access.",
        "role": current_user["role"]
    }

@app.get("/rate-limit-test")
async def rate_limit_test(current_user: dict = Depends(get_current_user)):
    rate_info = check_rate_limit(current_user["username"])
    return {
        "message": f"Request allowed for {current_user['username']}",
        "rate_limit_info": rate_info
    }

@app.post("/cache/store")
async def store_cache(
    question: str,
    answer: str,
    current_user: dict = Depends(get_current_user)
):
    store_in_cache(question, answer)
    return {"message": "Stored in cache", "question": question}

@app.post("/cache/search")
async def search_cache(
    question: str,
    current_user: dict = Depends(get_current_user)
):
    cached = get_cached_response(question)
    if cached:
        return {"found": True, "result": cached}
    return {"found": False, "message": "No similar question found in cache"}

@app.get("/cache/stats")
async def cache_stats(current_user: dict = Depends(get_current_user)):
    return get_cache_stats()


class QueryRequest(BaseModel):
    question: str
    context: str = ""

@app.post("/ai/query")
async def ai_query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    start_time = time.time()
    username = current_user["username"]

    try:
        rate_info = check_rate_limit(username)

        cached = get_cached_response(request.question)
        if cached:
            latency = (time.time() - start_time) * 1000
            log_request(username, "/ai/query", request.question, True, latency, "success")
            return {
                "question": request.question,
                "answer": cached["answer"],
                "cached": True,
                "similarity_score": cached["similarity_score"],
                "rate_limit_info": rate_info,
                "latency_ms": round(latency, 2),
                "user": username
            }

        result = ask_llm(request.question, request.context, username)
        store_in_cache(request.question, result["answer"])

        latency = (time.time() - start_time) * 1000
        log_request(username, "/ai/query", request.question, False, latency, "success")

        return {
            "question": request.question,
            "answer": result["answer"],
            "cached": False,
            "model": result["model"],
            "rate_limit_info": rate_info,
            "latency_ms": round(latency, 2),
            "user": username
        }

    except Exception as e:
        latency = (time.time() - start_time) * 1000
        log_request(username, "/ai/query", request.question, False, latency, "error", str(e))
        raise

# Start Celery worker
# You need two terminals running simultaneously:

# ----------------------------------------
# Terminal 1 — FastAPI server
# ----------------------------------------

# Activate virtual environment
# source venv/Scripts/activate

# Start FastAPI application
# uvicorn gateway.main:app --reload


# ----------------------------------------
# Terminal 2 — Celery worker
# ----------------------------------------

# Activate virtual environment
# source venv/Scripts/activate

# Start Celery worker
# celery -A gateway.queue.celery_app worker --loglevel=info -P solo


@app.post("/ai/query/async")
async def ai_query_async(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    rate_info = check_rate_limit(current_user["username"])

    task = process_ai_query.delay(
        question=request.question,
        context=request.context,
        username=current_user["username"]
    )

    return {
        "job_id": task.id,
        "status": "queued",
        "message": "Your request is being processed",
        "poll_url": f"/ai/result/{task.id}",
        "rate_limit_info": rate_info,
        "user": current_user["username"]
    }

@app.get("/ai/result/{job_id}")
async def get_result(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    task_result = AsyncResult(job_id)

    if task_result.state == "PENDING":
        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Task is waiting in queue"
        }
    elif task_result.state == "STARTED":
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Task is being processed"
        }
    elif task_result.state == "SUCCESS":
        return {
            "job_id": job_id,
            "status": "completed",
            "result": task_result.result
        }
    else:
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(task_result.result)
        }

@app.get("/ai/queue/stats")
async def queue_stats(current_user: dict = Depends(get_current_user)):
    from gateway.queue import celery_app
    inspect = celery_app.control.inspect()
    active = inspect.active()
    reserved = inspect.reserved()
    return {
        "active_tasks": active,
        "queued_tasks": reserved,
    }

# -----------------------------------------
@app.get("/monitoring/stats")
async def monitoring_stats(current_user: dict = Depends(get_current_user)):
    return get_stats()

@app.get("/monitoring/logs")
async def monitoring_logs(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    return {
        "logs": get_recent_logs(limit),
        "total_shown": limit
    }