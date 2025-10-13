# api_server.py
import os
import uuid
from typing import Optional, List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# import your functions
from utils import search_similar  # must return a list of chunks (strings)
# NOTE: we don't import the Chat code from agent.py here; we'll instantiate it when needed
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("CHAT_MODEL", "gemini-2.5-pro")
MAX_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", 400))

app = FastAPI()

# Allow Next.js dev server origin
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory session store: session_id -> list of dicts [{'role': 'User'/'Assistant', 'content': '...'}]
sessions = {}

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    from_db: bool

@app.get("/session/new")
def new_session():
    sid = str(uuid.uuid4())
    sessions[sid] = []
    return {"session_id": sid}

@app.post("/session/clear")
def clear_session(session_id: str):
    if session_id in sessions:
        sessions[session_id] = []
        return {"ok": True}
    else:
        raise HTTPException(status_code=404, detail="session not found")

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query required")

    # pick or create session
    sid = req.session_id or str(uuid.uuid4())
    if sid not in sessions:
        sessions[sid] = []

    # 1) Semantic search in your DB
    chunks = search_similar(query)  # should return list[str]
    if not chunks:
        # If DB has no relevant info, return explicit answer (per your requirement)
        reply = "Sorry — I don't have enough information in my database to answer that. Please consult a professional if needed."
        # append to session history as user + assistant
        sessions[sid].append({"role": "User", "content": query})
        sessions[sid].append({"role": "Assistant", "content": reply})
        return ChatResponse(reply=reply, session_id=sid, from_db=False)

    # 2) Build context
    context = "\n".join(chunks)
    if len(context) > MAX_CHARS:
        context = context[:MAX_CHARS]

    # 3) build a readable conversation history
    history_lines = []
    for turn in sessions[sid]:
        role = turn.get("role", "User")
        content = turn.get("content", "")
        history_lines.append(f"{role}: {content}")
    # include current user query in history_text as "User: ..."
    history_lines.append(f"User: {query}")
    history_text = "\n".join(history_lines)

    # 4) prompt template (empathetic, concise)
    prompt = f"""
You are a compassionate support assistant for parents of children with developmental or mental disabilities.
Use the context below (from trusted resources) and the conversation history to answer concisely, empathetically and safely.
Do NOT provide a medical diagnosis or prescribe treatment — always recommend professional consultation for serious issues.

Context:
{context}

Conversation:
{history_text}

Assistant (answer concisely in 2-4 sentences):
"""

    # 5) Call Gemini chat
    chat = ChatGoogleGenerativeAI(model=MODEL_NAME, google_api_key=GEMINI_API_KEY)
    # prefer .invoke() if your wrapper supports it; fall back to predict()
    try:
        response_obj = chat.invoke(prompt)  # may return object with .content
    except Exception:
        response_obj = chat.predict(prompt)  # older wrapper returns str

    # Extract reply text safely
    if hasattr(response_obj, "content"):
        reply_text = response_obj.content
    else:
        # could be string already
        reply_text = str(response_obj)

    # 6) Append to session history
    sessions[sid].append({"role": "User", "content": query})
    sessions[sid].append({"role": "Assistant", "content": reply_text})

    return ChatResponse(reply=reply_text, session_id=sid, from_db=True)
