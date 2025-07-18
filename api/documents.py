"""
Sample curl to list all documents for a case:
curl -X GET http://localhost:8000/cases/1/documents
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Body
from pydantic import BaseModel
from typing import List
import psycopg2
import os
from dotenv import load_dotenv

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

"""
Sample curl to update tags of a document:
curl -X PATCH http://localhost:8000/documents/1/tags \
  -H "Content-Type: application/json" \
  -d '{
    "tags": ["confidential", "scanned"]
  }'
"""

@router.get("/cases/{case_id}/documents", response_model=List[DocumentResponse])
def list_case_documents(case_id: int = Path(..., description="ID of the case"), user=Depends(get_current_user)):
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
def update_document_tags(document_id: int, update: DocumentTagsUpdateRequest = Body(...), user=Depends(get_current_user)):
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