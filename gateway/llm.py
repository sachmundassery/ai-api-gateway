import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tracers.context import tracing_v2_enabled

load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "ai-api-gateway")

def get_llm():
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.7,
        max_tokens=1024
    )

def ask_llm(question: str, context: str = "", username: str = "anonymous") -> dict:
    llm = get_llm()

    with tracing_v2_enabled(project_name="ai-api-gateway"):
        if context:
            prompt = ChatPromptTemplate.from_template("""
You are a helpful AI assistant.
Use the following context to answer the question.
If the context is not relevant, answer from your own knowledge.

Context: {context}
Question: {question}
Answer:""")
            chain = prompt | llm | StrOutputParser()
            answer = chain.invoke({
                "question": question,
                "context": context
            })
        else:
            prompt = ChatPromptTemplate.from_template("""
You are a helpful AI assistant.
Answer the following question clearly and concisely.

Question: {question}
Answer:""")
            chain = prompt | llm | StrOutputParser()
            answer = chain.invoke({"question": question})

    return {
        "answer": answer,
        "model": "llama-3.1-8b-instant",
        "cached": False
    }