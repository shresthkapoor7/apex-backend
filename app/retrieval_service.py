from app.embedding_service import generate_embedding
from app.supabase_client import supabase
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3-flash-preview")


def query_document(document_id: str, question: str):
    # 1️⃣ Embed question
    query_embedding = generate_embedding(question)

    # 2️⃣ Vector similarity search
    response = supabase.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_embedding,
            "doc_id": document_id,
            "match_count": 10,
        },
    ).execute()

    matches = response.data

    if not matches:
        return {
            "answer": "No relevant information found.",
            "sources": [],
        }

    # 3️⃣ Build context for LLM
    context_blocks = []
    sources = []

    for match in matches:
        context_blocks.append(
            f"(Page {match['page_number']}) {match['content']}"
        )

        sources.append(
            {
                "page": match["page_number"],
                "excerpt": match["content"][:300],
            }
        )

    context_text = "\n\n".join(context_blocks)

    prompt = f"""
Answer the question using ONLY the provided context.
If answer not found, say so clearly.

Question:
{question}

Context:
{context_text}
"""

    result = model.generate_content(prompt)

    return {
        "answer": result.text.strip(),
        "sources": sources,
    }