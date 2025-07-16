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

"""
Sample curl to list all cases:
curl -X GET http://localhost:8000/cases
"""

from typing import List

@router.get("/cases", response_model=List[CaseResponse])
def list_cases(user=Depends(get_current_user)):
    try:
        with psycopg2.connect(DATABASE_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute('SET SEARCH_PATH TO "schneider-poc";')
                cur.execute('SELECT id, name, description, defendant_id, plaintiff_id FROM "case";')
                cases = cur.fetchall()
                result = []
                for row in cases:
                    cur.execute('SELECT name FROM tag JOIN case_tag ON tag.id = case_tag.tag_id WHERE case_tag.case_id = %s;', (row[0],))
                    tags = [tag_row[0] for tag_row in cur.fetchall()]
                    result.append(CaseResponse(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        defendant_id=row[3],
                        plaintiff_id=row[4],
                        tags=tags
                    ))
                return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PersonCreateRequest(BaseModel):
    name: str
    lastname: str
    contact_info: Optional[str] = None
    legal_representative_id: Optional[int] = None
    role: str  # 'plaintiff' or 'defendant'

class PersonResponse(BaseModel):
    id: int
    name: str
    lastname: str
    contact_info: Optional[str]
    legal_representative_id: Optional[int]
    role: str

@router.post("/persons", response_model=PersonResponse)
def create_person(person: PersonCreateRequest, user=Depends(get_current_user)):
    if person.role not in ("plaintiff", "defendant"):
        raise HTTPException(status_code=400, detail="Role must be 'plaintiff' or 'defendant'.")
    try:
        with psycopg2.connect(DATABASE_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute('SET SEARCH_PATH TO "schneider-poc";')
                cur.execute(
                    'INSERT INTO person (name, contact_info, legal_representative_id) VALUES (%s, %s, %s) RETURNING id;',
                    (f"{person.name} {person.lastname}", person.contact_info, person.legal_representative_id)
                )
                person_id = cur.fetchone()[0]
                conn.commit()
                return PersonResponse(
                    id=person_id,
                    name=person.name,
                    lastname=person.lastname,
                    contact_info=person.contact_info,
                    legal_representative_id=person.legal_representative_id,
                    role=person.role
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 