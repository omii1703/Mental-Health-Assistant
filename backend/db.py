# Connects to PostgreSQL using psycopg2 and .env credentials.

# Defines get_connection() → reusable DB connection function.

# Creates embeddings table (mental_health_embeddings) for AI vector search.

# Creates users and diary_entries tables for authentication + journaling.

# Running the file directly (python db.py) sets up all required tables.

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    # Extension for vector similarity search
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Embeddings table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mental_health_embeddings(
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding vector(384)
        );
    """)

    # Users table for authentication
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            phone_number VARCHAR(15),
            birthdate DATE,
            gender VARCHAR(10),
            password_hash TEXT NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS diary_entries (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            date DATE NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
        id SERIAL PRIMARY KEY,
        session_id VARCHAR(100) NOT NULL,
        role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
        id SERIAL PRIMARY KEY,
        session_id VARCHAR(100) NOT NULL,
        message_index INT NOT NULL,
        rating INT NOT NULL,  -- +1 good, -1 bad
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    """)

    

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database tables ready!")

if __name__ == "__main__":
    create_tables()
