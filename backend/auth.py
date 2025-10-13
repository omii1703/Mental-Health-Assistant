from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2
import bcrypt
from db import get_connection

router = APIRouter()

# Pydantic models for request validation
class SignupRequest(BaseModel):
    name: str
    email: str
    phone_number: str
    birthdate: str  # you can change to datetime if needed
    gender: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# Signup route
@router.post("/signup")
def signup(user: SignupRequest):
    conn = get_connection()
    cur = conn.cursor()

    # check if email already exists
    cur.execute("SELECT * FROM users WHERE email = %s", (user.email,))
    existing = cur.fetchone()
    if existing:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    # hash password
    hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt())

    # insert into database
    cur.execute("""
        INSERT INTO users (name, email, phone_number, birthdate, gender, password_hash)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user.name, user.email, user.phone_number, user.birthdate, user.gender, hashed_password.decode("utf-8")))


    conn.commit()
    cur.close()
    conn.close()

    return {"message": "✅ User registered successfully!"}

# Login route
@router.post("/login")
def login(request: LoginRequest):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (request.email,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    user_id, password_hash = user
    if not bcrypt.checkpw(request.password.encode("utf-8"), password_hash.encode("utf-8")):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    return {"message": "✅ Login successful!", "user_id": user_id}
