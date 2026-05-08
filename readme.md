# 🚀 AI API Gateway

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?style=flat-square&logo=fastapi)
![Redis](https://img.shields.io/badge/Redis-Cloud-red?style=flat-square&logo=redis)
![Celery](https://img.shields.io/badge/Celery-5.x-brightgreen?style=flat-square)
![LangChain](https://img.shields.io/badge/LangChain-0.2-orange?style=flat-square)
![Deploy](https://img.shields.io/badge/Backend-Railway-blueviolet?style=flat-square)
![Deploy](https://img.shields.io/badge/Frontend-Streamlit_Cloud-ff4b4b?style=flat-square)

A **production-grade AI API Gateway** built with FastAPI that handles the core challenges of serving LLMs at scale — authentication, rate limiting, semantic caching, async request queuing and full observability.

🌐 **Live Demo:** [ai-api-gateway-3h44t6gwua6blefpxfowdk.streamlit.app](https://ai-api-gateway-3h44t6gwua6blefpxfowdk.streamlit.app/)  
⚙️ **Backend API:** [web-production-e6735.up.railway.app](https://web-production-e6735.up.railway.app/)  
📖 **API Docs:** [web-production-e6735.up.railway.app/docs](https://web-production-e6735.up.railway.app/docs)

---

## 🏗️ Architecture

```
Client (Streamlit Frontend)
           │
           ▼
    ┌─────────────────────────────────────┐
    │         FastAPI Gateway             │
    │                                     │
    │  1. JWT Authentication              │
    │  2. Sliding Window Rate Limiter     │
    │  3. Semantic Cache (ChromaDB)       │
    │  4. Async Request Queue (Celery)    │
    │  5. LLM Integration (Groq)          │
    │  6. Monitoring & Logging            │
    └─────────────────────────────────────┘
           │
           ▼
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │  Redis Cloud│     │  ChromaDB   │     │  LangSmith  │
    │  (Cache +   │     │  (Semantic  │     │  (LLM       │
    │   Queue)    │     │   Cache)    │     │   Tracing)  │
    └─────────────┘     └─────────────┘     └─────────────┘
```

---

## ✨ Features

### 🔐 Security
- **JWT Authentication** — every request requires a valid signed token
- **BCrypt password hashing** — passwords never stored in plain text
- **Role-based access** — admin and user roles with different permissions
- **Token expiry** — tokens automatically expire after 60 minutes

### 🚦 Rate Limiting
- **Sliding window algorithm** — more accurate than fixed window approach
- **Per-user limits** — each user gets 10 requests per 60-second window
- **Redis-backed** — distributed rate limiting that works across multiple instances
- **Graceful rejection** — returns remaining quota info on every request

### 🧠 Semantic Cache
- **Meaning-based matching** — caches by intent, not exact text
- **ChromaDB + cosine similarity** — finds similar past questions with configurable threshold
- **Reduces LLM calls by up to 40%** — equivalent questions served instantly from cache
- *"What is AI?"* and *"Can you explain AI to me?"* both hit the same cache entry

### 📬 Async Request Queue
- **Celery + Redis** — handles burst traffic without server crashes
- **Non-blocking** — returns job ID instantly (< 100ms), processes in background
- **Result polling** — clients poll `/ai/result/{job_id}` for completed responses
- **Scalable** — add more workers to increase throughput

### 📊 Monitoring & Observability
- **LangSmith tracing** — every LLM call tracked with inputs, outputs, latency, token usage
- **Redis metrics** — total requests, cache hit rate, average latency, error count
- **Request logging** — last 1000 requests stored with full metadata
- **Live dashboard** — real-time stats visible in Streamlit frontend

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI + Uvicorn |
| Authentication | JWT (python-jose) + Passlib |
| Rate Limiting | Redis (Sliding Window) |
| Semantic Cache | ChromaDB + HuggingFace Embeddings |
| Task Queue | Celery + Redis |
| LLM | Groq (Llama 3.1) via LangChain |
| Observability | LangSmith + Custom Redis Metrics |
| Frontend | Streamlit |
| Backend Deployment | Railway |
| Frontend Deployment | Streamlit Cloud |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Redis (local or Redis Cloud)
- Groq API key (free at console.groq.com)
- LangSmith API key (free at smith.langchain.com)

### Installation

```bash
# Clone the repository
git clone https://github.com/sachmundassery/ai-api-gateway.git
cd ai-api-gateway

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
# or
source venv/bin/activate       # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_key_here
JWT_SECRET_KEY=your_jwt_secret_here
REDIS_URL=rediss://default:password@your-redis-host:port
LANGCHAIN_API_KEY=your_langsmith_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=ai-api-gateway
```

### Running Locally

**Terminal 1 — FastAPI Backend:**
```bash
uvicorn gateway.main:app --reload
```

**Terminal 2 — Celery Worker:**
```bash
celery -A gateway.queue.celery_app worker --loglevel=info -P solo
```

**Terminal 3 — Streamlit Frontend:**
```bash
cd frontend
streamlit run app.py
```

Visit:
- Frontend: http://localhost:8501
- API Docs: http://localhost:8000/docs

### Demo Credentials
```
Username: sachin    Password: password123  (Admin)
Username: user1     Password: userpass     (User)
```

---

## 📁 Project Structure

```
ai-api-gateway/
│
├── gateway/
│   ├── main.py           ← FastAPI app + all endpoints
│   ├── auth.py           ← JWT authentication & user management
│   ├── rate_limiter.py   ← Sliding window rate limiting
│   ├── cache.py          ← Semantic cache with ChromaDB
│   ├── queue.py          ← Celery async task processing
│   ├── llm.py            ← Groq + LangChain + LangSmith
│   └── monitoring.py     ← Logging & metrics
│
├── frontend/
│   └── app.py            ← Streamlit dashboard
│
├── tests/
│   ├── test_setup.py     ← Redis connectivity test
│   └── test_rate_limit.py← Automated rate limit testing
│
├── Procfile              ← Railway deployment config
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 🔌 API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | ❌ | Get JWT token |
| GET | `/auth/me` | ✅ | Get current user info |
| GET | `/health` | ❌ | Service health check |
| POST | `/ai/query` | ✅ | Sync AI query with caching |
| POST | `/ai/query/async` | ✅ | Async AI query via queue |
| GET | `/ai/result/{job_id}` | ✅ | Poll async job result |
| GET | `/rate-limit-test` | ✅ | Check rate limit status |
| POST | `/cache/store` | ✅ | Manually store in cache |
| POST | `/cache/search` | ✅ | Search semantic cache |
| GET | `/cache/stats` | ✅ | Cache statistics |
| GET | `/monitoring/stats` | ✅ | System metrics |
| GET | `/monitoring/logs` | ✅ | Recent request logs |

---

## 💡 Key Design Decisions

**Why Sliding Window Rate Limiting?**  
Fixed window rate limiters allow burst traffic at window boundaries. Sliding window tracks requests over a rolling time period — fairer and more accurate. This is the approach used by Stripe and OpenAI.

**Why Semantic Cache over Simple Cache?**  
Simple caches only match exact strings. Semantic cache uses cosine similarity on embeddings — meaning-equivalent questions hit the same cache entry, reducing redundant LLM calls significantly.

**Why Async Queue?**  
LLM calls take 2-5 seconds. Synchronous handling blocks server threads during this time. Celery processes tasks in background workers, keeping the API server free to accept new requests — essential for handling traffic spikes.

---

## 📊 Performance Characteristics

| Scenario | Response Time |
|---|---|
| Cache hit | ~50ms |
| Fresh LLM call (sync) | 2000-4000ms |
| Async job submission | ~100ms |
| Rate limit check | ~10ms |

---

## 🧑‍💻 Author

**Sachin Mundassery**  
[![GitHub](https://img.shields.io/badge/GitHub-sachmundassery-black?style=flat-square&logo=github)](https://github.com/sachmundassery)

---

## 📄 License

MIT License — feel free to use this project as a reference or starting point.