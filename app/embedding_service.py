import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def generate_embedding(text: str):
    result = genai.embed_content(
        model="gemini-embedding-001",
        content=text,
        task_type="retrieval_document",
        output_dimensionality=768,
    )

    return result["embedding"]