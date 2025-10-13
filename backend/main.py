import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from voiceassistant import router as voice_router
from auth import router as auth_router
from img import router as img_router  # ✅ Added image router
from agent import ask_agent
from state import chat_sessions, feedback_store
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# ✅ Include all routers
app.include_router(voice_router)
app.include_router(auth_router)
app.include_router(img_router)  # ✅ Added to enable /upload

# ✅ Allow frontend CORS access
origins = ["http://127.0.0.1:8000", "http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Keep * for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Models ----------------
class Query(BaseModel):
    session_id: str
    question: str


class Feedback(BaseModel):
    session_id: str
    message_index: int
    rating: int


# ---------------- Routes ----------------
@app.post("/chat")
async def chat_endpoint(query: Query):
    try:
        answer = await run_in_threadpool(ask_agent, query.question, query.session_id)  # ✅ fixed argument order
        return {"reply": answer, "from_db": True, "session_id": query.session_id}
    except Exception as e:
        print(f"❌ ERROR in /chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback")
async def feedback_endpoint(feedback: Feedback):
    if feedback.session_id not in feedback_store:
        feedback_store[feedback.session_id] = {}
    feedback_store[feedback.session_id][feedback.message_index] = feedback.rating
    return {"status": "feedback recorded"}
