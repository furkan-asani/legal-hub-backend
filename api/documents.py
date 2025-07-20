"""
Sample curl to list all documents for a case:
curl -X GET http://localhost:8000/cases/1/documents
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Body, UploadFile, File, Query, Request
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
import os
from dotenv import load_dotenv
import shutil
from rag.rag_engine import RAGEngine
import datetime
from rag.doc_loader import load_docx_as_documents
from rag.semantic_chunker import semantic_chunk_documents
from rag.qdrant_uploader import upload_nodes_to_qdrant
from rag.embedder import embed_nodes
from ratelimit import global_limit

load_dotenv()
DATABASE_CONNECTION_STRING = os.getenv("DATABASE_CONNECTION_STRING")

router = APIRouter()

def get_current_user():
    # Implement authentication logic here
    pass

class DocumentResponse(BaseModel):
    id: int
    case_id: int
    file_path: str
    upload_timestamp: str
    tags: List[str]

class DocumentTagsUpdateRequest(BaseModel):
    tags: list[str]

class QueryRequest(BaseModel):
    query: str
    case_id: Optional[int] = None

class CitationResponse(BaseModel):
    source: str
    text: str
    case_id: Optional[int] = None
    score: Optional[float] = None

class QueryResponse(BaseModel):
    answer: str
    citations: List[CitationResponse]
    retrieved_chunks: int
    case_id_filter: Optional[int] = None
    error: Optional[str] = None

"""
Sample curl to query documents with AI assistance:
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main legal arguments in this case?",
    "case_id": 1
  }'
"""

"""
Sample curl to update tags of a document:
curl -X PATCH http://localhost:8000/documents/1/tags \
  -H "Content-Type: application/json" \
  -d '{
    "tags": ["confidential", "scanned"]
  }'
"""

"""
Sample curl to upload multiple documents:
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@/path/to/your/document1.pdf" \
  -F "file=@/path/to/your/document2.pdf" \
  -F "case_id=1"
"""

@router.get("/cases/{case_id}/documents", response_model=List[DocumentResponse])
@global_limit
def list_case_documents(request: Request, case_id: int = Path(..., description="ID of the case"), user=Depends(get_current_user)):
    try:
        with psycopg2.connect(DATABASE_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute('SET SEARCH_PATH TO "schneider-poc";')
                cur.execute('SELECT id, case_id, file_path, upload_timestamp FROM document WHERE case_id = %s;', (case_id,))
                docs = cur.fetchall()
                result = []
                for row in docs:
                    cur.execute('SELECT name FROM tag JOIN document_tag ON tag.id = document_tag.tag_id WHERE document_tag.document_id = %s;', (row[0],))
                    tags = [tag_row[0] for tag_row in cur.fetchall()]
                    result.append(DocumentResponse(
                        id=row[0],
                        case_id=row[1],
                        file_path=row[2],
                        upload_timestamp=str(row[3]),
                        tags=tags
                    ))
                return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/documents/{document_id}/tags", response_model=DocumentResponse)
@global_limit
def update_document_tags(request: Request, document_id: int, update: DocumentTagsUpdateRequest = Body(...), user=Depends(get_current_user)):
    try:
        with psycopg2.connect(DATABASE_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute('SET SEARCH_PATH TO "schneider-poc";')
                # Remove existing tags for this document
                cur.execute('DELETE FROM document_tag WHERE document_id = %s;', (document_id,))
                for tag in update.tags:
                    cur.execute('INSERT INTO tag (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id;', (tag,))
                    tag_id = cur.fetchone()[0]
                    cur.execute('INSERT INTO document_tag (document_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;', (document_id, tag_id))
                conn.commit()
                # Fetch updated document
                cur.execute('SELECT id, case_id, file_path, upload_timestamp FROM document WHERE id = %s;', (document_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Document not found")
                cur.execute('SELECT name FROM tag JOIN document_tag ON tag.id = document_tag.tag_id WHERE document_tag.document_id = %s;', (document_id,))
                tags = [tag_row[0] for tag_row in cur.fetchall()]
                return DocumentResponse(
                    id=row[0],
                    case_id=row[1],
                    file_path=row[2],
                    upload_timestamp=str(row[3]),
                    tags=tags
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

UPLOAD_DIR = "uploaded_docs"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/documents/upload", response_model=List[DocumentResponse])
@global_limit
def upload_document(
    request: Request,
    file: List[UploadFile] = File(...),
    case_id: int = File(...),
    user=Depends(get_current_user)
):
    responses = []
    try:
        for upload in file:
            # 1. Read the uploaded file in-memory and load document
            documents = load_docx_as_documents(file_obj=upload.file)
            # 2. Chunk the document
            nodes = semantic_chunk_documents(documents)
            # 3. Add filename metadata to all nodes
            for node in nodes:
                if hasattr(node, 'metadata') and isinstance(node.metadata, dict):
                    node.metadata["file_name"] = upload.filename
                else:
                    node.metadata = {"file_name": upload.filename}
            # 4. Embed the chunks
            embed_nodes(nodes)
            # 5. Upload to Qdrant with case_id metadata
            upload_nodes_to_qdrant(nodes, collection_name="law-test", case_id=case_id)
            # 6. Insert into DB (file_path can be original filename or blank)
            with psycopg2.connect(DATABASE_CONNECTION_STRING) as conn:
                with conn.cursor() as cur:
                    cur.execute('SET SEARCH_PATH TO "schneider-poc";')
                    cur.execute(
                        'INSERT INTO document (case_id, file_path, upload_timestamp) VALUES (%s, %s, %s) RETURNING id, upload_timestamp;',
                        (case_id, upload.filename, datetime.datetime.now())
                    )
                    doc_id, upload_timestamp = cur.fetchone()
                    conn.commit()
            responses.append(DocumentResponse(
                id=doc_id,
                case_id=case_id,
                file_path=upload.filename,
                upload_timestamp=str(upload_timestamp),
                tags=[]
            ))
        return responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", response_model=QueryResponse)
@global_limit
def query_documents(
    request: Request,
    query_request: QueryRequest = Body(...),
    user=Depends(get_current_user)
):
    """
    Query documents using AI-powered retrieval and generation.
    Searches through uploaded documents and provides AI-generated responses with citations.
    """
    try:
        # Initialize RAG engine
        rag_engine = RAGEngine(collection_name="law-test")

        # Perform AI-powered query with citations
        result = rag_engine.query(
            query=query_request.query,
            case_id=query_request.case_id
        )

        # Convert citations to response format
        citations = [
            CitationResponse(
                source=citation["source"],
                text=citation["text"],
                case_id=citation.get("case_id"),
                score=citation.get("score")
            )
            for citation in result.get("citations", [])
        ]

        return QueryResponse(
            answer=result.get("answer", ""),
            citations=citations,
            retrieved_chunks=result.get("retrieved_chunks", 0),
            case_id_filter=result.get("case_id_filter"),
            error=result.get("error")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 