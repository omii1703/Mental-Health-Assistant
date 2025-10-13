import os
import io
import tempfile
import fitz  # PyMuPDF
from PIL import Image
import easyocr
from fastapi import APIRouter, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool  # ✅ Import this
from agent import ask_agent  # ✅ your existing AI logic from main.py

router = APIRouter()
UPLOAD_DIR = "uploaded_media"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = {
    "image": ["image/png", "image/jpeg", "image/jpg"],
    "video": ["video/mp4", "video/mov", "video/avi"],
    "pdf": ["application/pdf"]
}

# Initialize EasyOCR reader once
reader = easyocr.Reader(['en'], gpu=False)


def extract_text_from_image(image_path: str) -> str:
    try:
        results = reader.readtext(image_path, detail=0)
        if not results:
            return ""
        return " ".join(results)
    except Exception as e:
        print(f"Image OCR error: {e}")
        return ""


def extract_text_from_video(video_path: str) -> str:
    try:
        import moviepy.editor as mp
        clip = mp.VideoFileClip(video_path)
        frame = clip.get_frame(clip.duration / 2)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
            Image.fromarray(frame).save(tmp_img.name)
            text = extract_text_from_image(tmp_img.name)
        clip.close()
        return text
    except Exception as e:
        print(f"Video OCR error: {e}")
        return ""


def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text("text")
        return text.strip()
    except Exception as e:
        print(f"PDF OCR error: {e}")
        return ""


@router.post("/upload")
async def upload_media(file: UploadFile, session_id: str = Form(...)):
    content_type = file.content_type
    media_type = None
    for key, types in ALLOWED_TYPES.items():
        if content_type in types:
            media_type = key
            break

    if not media_type:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    extracted_text = ""
    if media_type == "image":
        extracted_text = extract_text_from_image(file_path)
    elif media_type == "video":
        extracted_text = extract_text_from_video(file_path)
    elif media_type == "pdf":
        extracted_text = extract_text_from_pdf(file_path)

    # ✅ FIXED: use run_in_threadpool since ask_agent is synchronous
    if extracted_text.strip():
        try:
            res = await run_in_threadpool(ask_agent, session_id, extracted_text)
            ai_reply = res if isinstance(res, str) else res.get("reply", "No response generated.")
        except Exception as e:
            ai_reply = f"Error getting AI reply: {str(e)}"
    else:
        ai_reply = "No readable text found in the file."

    return JSONResponse({
        "filename": file.filename,
        "url": f"/{UPLOAD_DIR}/{file.filename}",
        "type": media_type,
        "extracted_text": extracted_text.strip(),
        "ai_reply": ai_reply
    })
