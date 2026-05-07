import redis
import os
from dotenv import load_dotenv

load_dotenv()

r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
r.set("test", "gateway works!")
value = r.get("test")
print(f"Redis connected: {value.decode()}")