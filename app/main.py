from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import Response
from uuid import uuid4
from app.supabase_client import supabase
from app.pdf_service import process_document
from app.retrieval_service import query_document
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://apex-frontend-three.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/documents")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    document_id = str(uuid4())
    file_path = f"{document_id}/{file.filename}"

    try:
        file_bytes = await file.read()

        supabase.storage.from_("documents").upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf"},
        )

        supabase.table("documents").insert(
            {
                "id": document_id,
                "file_name": file.filename,
                "file_path": file_path,
                "status": "processing",
            }
        ).execute()

        # 🔥 Trigger background processing
        background_tasks.add_task(
            process_document,
            document_id,
            file_path,
        )

        return {
            "document_id": document_id,
            "status": "processing",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class QueryRequest(BaseModel):
    question: str


@app.post("/documents/{document_id}/query")
def ask_question(document_id: str, body: QueryRequest):
    return query_document(document_id, body.question)

@app.get("/documents")
def list_documents():
    response = supabase.table("documents") \
        .select(
            """
            id,
            file_name,
            status,
            created_at,
            extracted_metrics (
                purchase_price,
                noi,
                cap_rate,
                occupancy,
                units,
                year_built,
                property_type,
                location
            )
            """
        ) \
        .order("created_at", desc=True) \
        .execute()

    documents = []

    for doc in response.data:
        metrics = doc.get("extracted_metrics")
        metrics = metrics[0] if metrics else {}

        documents.append({
            "id": doc["id"],
            "file_name": doc["file_name"],
            "status": doc["status"],
            "created_at": doc["created_at"],
            "purchase_price": metrics.get("purchase_price"),
            "noi": metrics.get("noi"),
            "cap_rate": metrics.get("cap_rate"),
            "occupancy": metrics.get("occupancy"),
            "units": metrics.get("units"),
            "year_built": metrics.get("year_built"),
            "property_type": metrics.get("property_type"),
            "location": metrics.get("location"),
        })

    return documents

@app.get("/documents/{document_id}")
def get_document(document_id: str):
    doc_response = supabase.table("documents") \
        .select("*") \
        .eq("id", document_id) \
        .single() \
        .execute()

    if not doc_response.data:
        return {"error": "Document not found"}

    metrics_response = supabase.table("extracted_metrics") \
        .select("*") \
        .eq("document_id", document_id) \
        .single() \
        .execute()

    return {
        "id": doc_response.data["id"],
        "file_name": doc_response.data["file_name"],
        "status": doc_response.data["status"],
        "created_at": doc_response.data["created_at"],
        "metrics": metrics_response.data if metrics_response.data else None,
    }


@app.get("/documents/{document_id}/file")
def get_document_file(document_id: str):
    doc_response = supabase.table("documents") \
        .select("file_path, file_name") \
        .eq("id", document_id) \
        .single() \
        .execute()

    if not doc_response.data:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc_response.data["file_path"]
    file_name = doc_response.data["file_name"] or "document.pdf"

    file_bytes = supabase.storage.from_("documents").download(file_path)

    if file_bytes is None:
        raise HTTPException(status_code=404, detail="File not found in storage")

    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{file_name}"',
        },
    )