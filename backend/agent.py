# agent.py
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from state import chat_sessions, feedback_store
from utils import search_similar  # your semantic search
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("CHAT_MODEL", "gemini-2.5-pro")
MAX_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", 400))
TOP_K = 5

# Initialize Gemini LLM
chat_llm = ChatGoogleGenerativeAI(model=MODEL_NAME, google_api_key=GEMINI_API_KEY)


def adjust_with_feedback(session_id: str, chunks: List[str]) -> List[str]:
    penalized = feedback_store.get(session_id, {})
    return [c for i, c in enumerate(chunks) if penalized.get(i) != -1]


def save_message(session_id: str, role: str, content: str):
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    chat_sessions[session_id].append({"role": role, "content": content})


def get_history(session_id: str, limit: int = 5) -> List[str]:
    history = chat_sessions.get(session_id, [])
    return [f"{m['role']}: {m['content']}" for m in history[-limit:]]


def ask_agent(session_id: str, query: str) -> str:
    # 1️⃣ Semantic search
    chunks = search_similar(query)[:TOP_K]
    chunks = adjust_with_feedback(session_id, chunks)
    if not chunks:
        return "Sorry — I don't have enough information in my database to answer that. Please consult a professional if needed."

    # 2️⃣ Retrieve last few messages
    history_text = "\n".join(get_history(session_id, limit=5))

    # 3️⃣ Build context (truncate if too long)
    context = "\n".join(chunks)
    if len(context) > MAX_CHARS:
        context = context[:MAX_CHARS]

    # 4️⃣ Build prompt
    prompt = f"""
You are a compassionate mental health assistant for parents of children with developmental or mental disabilities.
Use the context below (from trusted resources) and the chat history to answer concisely, empathetically, and safely.
Do NOT provide medical diagnosis or prescribe treatment — always recommend professional consultation.

Context:
{context}

Chat History:
{history_text}

User Question:
{query}

Answer concisely in 2-4 sentences:
"""

    try:
        response = chat_llm.invoke(prompt)
        reply = response.content if hasattr(response, "content") else str(response)

        # 5️⃣ Save user + assistant messages to session
        save_message(session_id, "user", query)
        save_message(session_id, "assistant", reply)

        return reply
    except Exception as e:
        print(f"❌ ERROR calling Gemini LLM: {e}")
        return "Sorry, I am unable to generate a response right now. Please try again later."
