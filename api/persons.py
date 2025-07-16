"""
Sample curl to test this endpoint:
curl -X POST http://localhost:8000/persons \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane",
    "lastname": "Doe",
    "role": "plaintiff"
  }'
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_CONNECTION_STRING = os.getenv("DATABASE_CONNECTION_STRING")

router = APIRouter()

def get_current_user():
    # Implement authentication logic here
    pass

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

"""
Sample curl to list all persons:
curl -X GET http://localhost:8000/persons
"""

@router.get("/persons", response_model=List[PersonResponse])
def list_persons(user=Depends(get_current_user)):
    try:
        with psycopg2.connect(DATABASE_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                cur.execute('SET SEARCH_PATH TO "schneider-poc";')
                cur.execute('SELECT id, name, contact_info, legal_representative_id FROM person;')
                persons = cur.fetchall()
                result = []
                for row in persons:
                    # Split name into name and lastname (assumes last word is lastname)
                    name_parts = row[1].rsplit(' ', 1)
                    name = name_parts[0] if len(name_parts) > 1 else row[1]
                    lastname = name_parts[1] if len(name_parts) > 1 else ''
                    # Role is not stored, so return empty string
                    result.append(PersonResponse(
                        id=row[0],
                        name=name,
                        lastname=lastname,
                        contact_info=row[2],
                        legal_representative_id=row[3],
                        role=""
                    ))
                return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 