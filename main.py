from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import JSONResponse
from rag_engine import RAGEngine
import os
from tempfile import NamedTemporaryFile
from fastapi import Form

app = FastAPI()

# Placeholder for authentication dependency
def get_current_user():
    # Implement authentication logic here
    pass

UPLOAD_DIR = "./uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

rag_engine = RAGEngine()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    try:
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_location, "wb") as f:
            content = await file.read()
            f.write(content)
        rag_engine.index_file(file_location)
        return {"message": f"File '{file.filename}' uploaded and indexed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_rag(query: str = Form(...), user=Depends(get_current_user)):
    try:
        result = rag_engine.query(query)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 