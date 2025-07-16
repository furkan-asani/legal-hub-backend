from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_CONNECTION_STRING = os.getenv("DATABASE_CONNECTION_STRING")

router = APIRouter()

# Placeholder for authentication dependency
def get_current_user():
    # Implement authentication logic here
    pass

class CaseCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    defendant_id: int
    plaintiff_id: int
    tags: Optional[List[str]] = None

class CaseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    defendant_id: int
    plaintiff_id: int
    tags: List[str]

@router.post("/cases", response_model=CaseResponse)
def create_case(case: CaseCreateRequest, user=Depends(get_current_user)):
    try:
        with psycopg2.connect(DATABASE_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                # Set schema
                cur.execute('SET SEARCH_PATH TO "schneider-poc";')
                # Insert case
                cur.execute(
                    'INSERT INTO "case" (name, description, defendant_id, plaintiff_id) VALUES (%s, %s, %s, %s) RETURNING id;',
                    (case.name, case.description, case.defendant_id, case.plaintiff_id)
                )
                case_id = cur.fetchone()[0]
                tag_names = case.tags or []
                tag_ids = []
                for tag in tag_names:
                    # Insert tag if not exists
                    cur.execute('INSERT INTO tag (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id;', (tag,))
                    tag_id = cur.fetchone()[0]
                    tag_ids.append(tag_id)
                    # Associate tag with case
                    cur.execute('INSERT INTO case_tag (case_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;', (case_id, tag_id))
                conn.commit()
                # Fetch tags for response
                cur.execute('SELECT name FROM tag JOIN case_tag ON tag.id = case_tag.tag_id WHERE case_tag.case_id = %s;', (case_id,))
                tags = [row[0] for row in cur.fetchall()]
                return CaseResponse(
                    id=case_id,
                    name=case.name,
                    description=case.description,
                    defendant_id=case.defendant_id,
                    plaintiff_id=case.plaintiff_id,
                    tags=tags
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 