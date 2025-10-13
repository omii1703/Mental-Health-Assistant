import os
import psycopg2
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from sentence_transformers import SentenceTransformer
from db import get_connection  # your existing DB connection

load_dotenv()

PDF_FOLDER = "data"  # folder where PDFs are stored
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim embeddings

# Load HuggingFace embedding model
model = SentenceTransformer(MODEL_NAME)

def embed_pdf(pdf_path, cur):
    print(f"Processing {pdf_path} ...")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    # Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(documents)

    for doc in docs:
        text = doc.page_content
        vector = model.encode(text).tolist()  # 384-dim list of floats
        cur.execute(
            "INSERT INTO mental_health_embeddings (content, embedding) VALUES (%s, %s)",
            (text, vector)
        )

def embed_all_pdfs():
    conn = get_connection()
    cur = conn.cursor()
    for filename in os.listdir(PDF_FOLDER):
        if filename.lower().endswith(".pdf"):
            embed_pdf(os.path.join(PDF_FOLDER, filename), cur)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ All PDFs embedded successfully!")

if __name__ == "__main__":
    embed_all_pdfs()
