"""
Sample curl to list all documents for a case:
curl -X GET http://localhost:8000/cases/1/documents
"""

from fastapi import APIRouter, Depends, HTTPException, Path
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