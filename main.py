from fastapi import FastAPI
from rag_engine import RAGEngine

app = FastAPI()

# Import and include routers
from api.cases import router as cases_router
app.include_router(cases_router)

# You can include other routers here as needed 