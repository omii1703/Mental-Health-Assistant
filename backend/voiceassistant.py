import os
import uuid
from fastapi import APIRouter, UploadFile, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.concurrency import run_in_threadpool
from pydub import AudioSegment
import speech_recognition as sr
from gtts import gTTS
import httpx  # Async requests

router = APIRouter(prefix="")
TEMP_AUDIO_FOLDER = "temp_audio"
os.makedirs(TEMP_AUDIO_FOLDER, exist_ok=True)

API_BASE = "http://127.0.0.1:8000"  # FastAPI base URL


def transcribe_audio(file_path: str) -> str:
    """Convert uploaded audio to text using speech_recognition."""
    recognizer = sr.Recognizer()
    
    # Convert webm → wav safely
    wav_path = file_path.replace(".webm", f"_{uuid.uuid4().hex}.wav")
    AudioSegment.from_file(file_path).export(wav_path, format="wav")

    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            print(f"[DEBUG] Transcribed text: {text}")
            return text
        except sr.UnknownValueError:
            print("[DEBUG] Speech not recognized")
            return ""
        except sr.RequestError as e:
            print(f"[DEBUG] Google API error: {e}")
            return ""


@router.post("/voice-query")
async def voice_query(
    audio_file: UploadFile = Form(...),
    session_id: str = Form(...),
    request: Request = None
):
    try:
        # Save uploaded audio
        filename = audio_file.filename or f"{session_id}_{uuid.uuid4().hex}.webm"
        uploaded_path = os.path.join(TEMP_AUDIO_FOLDER, filename)
        with open(uploaded_path, "wb") as f:
            f.write(await audio_file.read())
        print(f"[DEBUG] Audio file saved: {uploaded_path}")

        # Transcribe audio → text
        query_text = await run_in_threadpool(transcribe_audio, uploaded_path)
        if not query_text:
            query_text = "Sorry, I could not understand your voice."
        print(f"[DEBUG] Query text: {query_text}")

        # Send text to /chat endpoint asynchronously
        async with httpx.AsyncClient() as client:
            chat_response = await client.post(
                f"{API_BASE}/chat",
                json={"session_id": session_id, "question": query_text},
                timeout=20
            )
        chat_response.raise_for_status()
        chat_data = chat_response.json()
        reply_text = chat_data.get("reply", "I couldn't generate a reply.")
        print(f"[DEBUG] Reply text: {reply_text}")

        # Convert reply → speech (TTS) with unique filename
        tts_filename = f"{session_id}_{uuid.uuid4().hex}_reply.mp3"
        tts_path = os.path.join(TEMP_AUDIO_FOLDER, tts_filename)
        gTTS(text=reply_text, lang="en").save(tts_path)
        print(f"[DEBUG] TTS audio saved: {tts_path}")

        # Build URL for frontend
        base_url = str(request.base_url).rstrip("/")
        audio_url = f"{base_url}/voice-reply/{tts_filename}"

        return JSONResponse({
            "query_text": query_text,
            "reply_text": reply_text,
            "audio_file": f"/voice-reply/{tts_filename}",
            "audio_file_url": audio_url,
        })

    except Exception as e:
        print(f"[ERROR] Voice query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice query failed: {str(e)}")


@router.get("/voice-reply/{filename}")
async def get_voice_file(filename: str):
    file_path = os.path.join(TEMP_AUDIO_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)
