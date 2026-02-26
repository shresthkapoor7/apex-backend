import fitz  # pymupdf
import tempfile
import re
from app.supabase_client import supabase
from app.embedding_service import generate_embedding
from app.extraction_service import extract_metrics


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def process_document(document_id: str, file_path: str):
    try:
        # 1️⃣ Download file from Supabase
        response = supabase.storage.from_("documents").download(file_path)

        if response is None:
            raise Exception("Failed to download file")

        # 2️⃣ Write to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(response)
            tmp_path = tmp.name

        # 3️⃣ Open with pymupdf
        doc = fitz.open(tmp_path)

        for page_number in range(len(doc)):
            page = doc.load_page(page_number)
            text = page.get_text()

            cleaned = clean_text(text)

            if cleaned:
                # Store full page
                supabase.table("document_pages").insert(
                    {
                        "document_id": document_id,
                        "page_number": page_number + 1,
                        "raw_text": cleaned,
                    }
                ).execute()

                # Chunk page
                page_chunks = chunk_text(cleaned, page_number + 1)

                for chunk in page_chunks:
                    embedding = generate_embedding(chunk["content"])
                    supabase.table("document_chunks").insert(
                        {
                            "document_id": document_id,
                            "page_number": chunk["page_number"],
                            "content": chunk["content"],
                            "embedding": embedding,
                        }
                    ).execute()

        pages = supabase.table("document_pages") \
            .select("raw_text") \
            .eq("document_id", document_id) \
            .execute()

        full_text = " ".join([p["raw_text"] for p in pages.data])

        metrics = extract_metrics(full_text)
        supabase.table("extracted_metrics").insert(
            {
                "document_id": document_id,
                **metrics,
            }
        ).execute()

        # 4️⃣ Update status to ready
        supabase.table("documents").update(
            {"status": "ready"}
        ).eq("id", document_id).execute()

    except Exception as e:
        supabase.table("documents").update(
            {"status": "failed"}
        ).eq("id", document_id).execute()

        print("Processing error:", str(e))

def chunk_text(text: str, page_number: int, chunk_size=4000, overlap=500):
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]

        chunks.append(
            {
                "page_number": page_number,
                "content": chunk,
            }
        )

        start = end - overlap

    return chunks