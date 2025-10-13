# import os
# from dotenv import load_dotenv
# import psycopg2
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
# #do embedding and has search funtion
# load_dotenv()
# from db import get_connection

# TOP_K = 5  # number of most similar chunks to retrieve

# def search_similar(query):
#     embeddings = GoogleGenerativeAIEmbeddings(
#         model="models/embedding-001",
#         google_api_key=os.getenv("GEMINI_API_KEY")
#     )

#     # Embed the query
#     query_vector = embeddings.embed_query(query)

#     conn = get_connection()
#     cur = conn.cursor()

#     # Postgres similarity search using <-> operator (cosine distance)
#     cur.execute(f"""
#         SELECT content, embedding <-> %s::vector AS distance
#         FROM mental_health_embeddings
#         ORDER BY distance
#         LIMIT {TOP_K};
#     """, (query_vector,))

#     results = cur.fetchall()
#     cur.close()
#     conn.close()

#     return [row[0] for row in results]  # return content only

# if __name__ == "__main__":
#     user_query = input("Enter your query: ")
#     chunks = search_similar(user_query)
    
#     print("\nTop matching chunks from PDFs:\n")
#     for i, chunk in enumerate(chunks, 1):
#         print(f"{i}. {chunk[:500]}...\n")  # print first 500 chars of each chunk

# utils.py
from sentence_transformers import SentenceTransformer
from db import get_connection

TOP_K = 5  # number of most similar chunks to retrieve

# Load HuggingFace embedding model globally (384-dim)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def search_similar(query):
    """
    Search for the TOP_K most similar PDF chunks to the query.
    Returns a list of chunk texts.
    """
    # Encode the query as a 384-dim vector
    query_vector = embedding_model.encode(query).tolist()

    conn = get_connection()
    cur = conn.cursor()

    # Postgres vector similarity search (<-> operator)
    cur.execute(f"""
        SELECT content, embedding <-> %s::vector AS distance
        FROM mental_health_embeddings
        ORDER BY distance
        LIMIT {TOP_K};
    """, (query_vector,))

    results = cur.fetchall()
    cur.close()
    conn.close()

    return [row[0] for row in results]  # only return the text content


if __name__ == "__main__":
    user_query = input("Enter your query: ")
    chunks = search_similar(user_query)

    print("\nTop matching chunks from PDFs:\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"{i}. {chunk[:500]}...\n")  # first 500 chars for preview
