from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rag.rag_engine import RAGEngine
import os
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from ratelimit import limiter

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS setup
allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")
allowed_origins = [origin.strip() for origin in allowed_origins]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Import and include routers
from api.cases import router as cases_router
app.include_router(cases_router)

from api.persons import router as persons_router
app.include_router(persons_router)

from api.documents import router as documents_router
app.include_router(documents_router)

from api.notes import router as notes_router
app.include_router(notes_router)

from api.websocket import router as websocket_router
app.include_router(websocket_router)

# You can include other routers here as needed 