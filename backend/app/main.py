"""
Point d'entree de l'application FastAPI.

Lancement :
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth.routes import router as auth_router
from .chatbot.routes import router as chatbot_router
from .database import Base, engine
from . import models
from fastapi.staticfiles import StaticFiles
import os
from .chatbot.rag_engine import DOCS_DIR, load_rag_engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DocuRH API",
    description="API d'authentification et de chatbot RH interne",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists(DOCS_DIR):
    app.mount("/documents", StaticFiles(directory=DOCS_DIR), name="documents")


@app.on_event("startup")
def startup_event():
    # Charge le modele d'embeddings + ChromaDB UNE SEULE FOIS ici.
    # Sans ca, chaque question rechargerait le modele (1-2 secondes perdues
    # a chaque appel).
    load_rag_engine()


app.include_router(auth_router)
app.include_router(chatbot_router)


@app.get("/")
def root():
    return {"message": "DocuRH API en ligne."}
