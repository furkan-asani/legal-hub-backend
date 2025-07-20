"""
Sample curl to list all notes for a case:
curl -X GET http://localhost:8000/cases/1/notes

Sample curl to create a note for a case:
curl -X POST http://localhost:8000/cases/1/notes \
  -H "Content-Type: application/json" \
  -d '{
    "author_id": 1,
    "note_content": "This is a new note."
  }'
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
from ratelimit import global_limit

load_dotenv()
DATABASE_CONNECTION_STRING = os.getenv("DATABASE_CONNECTION_STRING")

router = APIRouter()

def get_current_user():
    # Implement authentication logic here
    pass

class NoteResponse(BaseModel):
    id: int
    case_id: int
    author_id: int
    note_content: str
    timestamp: str

class NoteCreateRequest(BaseModel):
    author_id: int
    note_content: str

@router.get("/cases/{case_id}/notes", response_model=List[NoteResponse])
@global_limit
def list_case_notes(request: Request, case_id: int = Path(..., description="ID of the case"), user=Depends(get_current_user)):
    try:
        with psycopg2.connect(DATABASE_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute('SET SEARCH_PATH TO "schneider-poc";')
                cur.execute('SELECT id, case_id, author_id, note_content, timestamp FROM note WHERE case_id = %s ORDER BY timestamp ASC;', (case_id,))
                notes = cur.fetchall()
                return [NoteResponse(
                    id=row[0],
                    case_id=row[1],
                    author_id=row[2],
                    note_content=row[3],
                    timestamp=str(row[4])
                ) for row in notes]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cases/{case_id}/notes", response_model=NoteResponse)
@global_limit
def create_case_note(request: Request, case_id: int, note: NoteCreateRequest, user=Depends(get_current_user)):
    try:
        with psycopg2.connect(DATABASE_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute('SET SEARCH_PATH TO "schneider-poc";')
                cur.execute(
                    'INSERT INTO note (case_id, author_id, note_content, timestamp) VALUES (%s, %s, %s, %s) RETURNING id, timestamp;',
                    (case_id, note.author_id, note.note_content, datetime.now())
                )
                note_id, timestamp = cur.fetchone()
                conn.commit()
                return NoteResponse(
                    id=note_id,
                    case_id=case_id,
                    author_id=note.author_id,
                    note_content=note.note_content,
                    timestamp=str(timestamp)
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 