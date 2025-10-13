# backend/diary.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from db import get_connection

router = APIRouter()

class DiaryEntry(BaseModel):
    user_id: int
    date: str
    title: str
    content: str

@router.post("/diary", response_model=DiaryEntry)
def add_entry(entry: DiaryEntry):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO diary_entries (user_id, date, title, content) VALUES (%s, %s, %s, %s) RETURNING *",
        (entry.user_id, entry.date, entry.title, entry.content)
    )
    saved_entry = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return saved_entry

@router.get("/diary/{user_id}", response_model=List[DiaryEntry])
def get_entries(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM diary_entries WHERE user_id=%s ORDER BY date DESC", (user_id,))
    entries = cur.fetchall()
    cur.close()
    conn.close()
    return entries
