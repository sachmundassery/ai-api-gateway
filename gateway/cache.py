import os
import json
import hashlib
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
import chromadb
from chromadb.config import Settings

load_dotenv()

L2_DISTANCE_THRESHOLD = 0.5

embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path="chroma_cache")

collection = chroma_client.get_or_create_collection(
    name="semantic_cache",
    metadata={"hnsw:space": "cosine"}
)

def get_embedding(text: str):
    return embedding_model.embed_query(text)

def get_cached_response(question: str):
    try:
        query_embedding = get_embedding(question)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=1
        )

        if not results["documents"] or not results["documents"][0]:
            return None

        distance = results["distances"][0][0]
        document = results["documents"][0][0]

        print(f"DEBUG - Cosine distance: {distance}")
        print(f"DEBUG - Similarity: {1 - distance}")

        if distance <= L2_DISTANCE_THRESHOLD:
            cached_data = json.loads(document)
            return {
                "answer": cached_data["answer"],
                "cached": True,
                "similarity_score": round(1 - distance, 3),
                "original_question": cached_data["question"]
            }
        return None
    except Exception as e:
        print(f"Cache search error: {e}")
        return None

def store_in_cache(question: str, answer: str):
    try:
        cache_data = json.dumps({
            "question": question,
            "answer": answer
        })
        doc_id = hashlib.md5(question.encode()).hexdigest()
        question_embedding = get_embedding(question)

        collection.upsert(
            ids=[doc_id],
            documents=[cache_data],
            embeddings=[question_embedding]
        )
        print(f"Stored in cache: {question}")
    except Exception as e:
        print(f"Cache store error: {e}")

def get_cache_stats():
    try:
        count = collection.count()
        return {
            "total_cached_responses": count,
            "distance_threshold": L2_DISTANCE_THRESHOLD,
            "collection": "semantic_cache",
            "metric": "cosine"
        }
    except Exception:
        return {"total_cached_responses": 0}