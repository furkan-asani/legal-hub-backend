from fastapi import APIRouter, Depends, HTTPException, Path, Body
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
    state: str

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
                cur.execute('SELECT id, name, description, defendant_id, plaintiff_id, state FROM "case";')
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
                        tags=tags,
                        state=row[5]
                    ))
                return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CaseUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    state: Optional[str] = None
    tags: Optional[List[str]] = None

"""
Sample curl to update a case:
curl -X PATCH http://localhost:8000/cases/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Case Name",
    "description": "Updated description.",
    "state": "archived",
    "tags": ["important", "archived"]
  }'
"""

@router.patch("/cases/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: int,
    update: CaseUpdateRequest = Body(...),
    user=Depends(get_current_user)
):
    try:
        with psycopg2.connect(DATABASE_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute('SET SEARCH_PATH TO "schneider-poc";')
                # Build dynamic update query
                fields = []
                values = []
                if update.name is not None:
                    fields.append('name = %s')
                    values.append(update.name)
                if update.description is not None:
                    fields.append('description = %s')
                    values.append(update.description)
                if update.state is not None:
                    fields.append('state = %s')
                    values.append(update.state)
                if fields:
                    query = f'UPDATE "case" SET {", ".join(fields)} WHERE id = %s'
                    values.append(case_id)
                    cur.execute(query, tuple(values))
                # Update tags if provided
                if update.tags is not None:
                    # Remove existing tags for this case
                    cur.execute('DELETE FROM case_tag WHERE case_id = %s;', (case_id,))
                    for tag in update.tags:
                        cur.execute('INSERT INTO tag (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id;', (tag,))
                        tag_id = cur.fetchone()[0]
                        cur.execute('INSERT INTO case_tag (case_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;', (case_id, tag_id))
                conn.commit()
                # Fetch updated case
                cur.execute('SELECT id, name, description, defendant_id, plaintiff_id, state FROM "case" WHERE id = %s;', (case_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Case not found")
                cur.execute('SELECT name FROM tag JOIN case_tag ON tag.id = case_tag.tag_id WHERE case_tag.case_id = %s;', (case_id,))
                tags = [tag_row[0] for tag_row in cur.fetchall()]
                return CaseResponse(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    defendant_id=row[3],
                    plaintiff_id=row[4],
                    tags=tags,
                    state=row[5]
                )
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

class DocumentResponse(BaseModel):
    id: int
    case_id: int
    file_path: str
    upload_timestamp: str
    tags: list[str]

"""
Sample curl to list all documents for a case:
curl -X GET http://localhost:8000/cases/1/documents
"""

@router.get("/cases/{case_id}/documents", response_model=list[DocumentResponse])
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