"""
Schemas Pydantic : definissent la forme des donnees attendues en entree
(requetes) et renvoyees en sortie (reponses), avec validation automatique.
"""

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    nom: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_doit_etre_forte(cls, v):
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caracteres.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule.")
        if not re.search(r"[0-9]", v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre.")
        return v

    @field_validator("nom")
    @classmethod
    def nom_non_vide(cls, v):
        if not v.strip():
            raise ValueError("Le nom ne peut pas etre vide.")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    nom: str
    email: EmailStr
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True  # permet de construire ce schema depuis un objet SQLAlchemy


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class SourceCitee(BaseModel):
    document: str
    page: str | int | None = None
    similarite: float


class PieceJointe(BaseModel):
    nom_affiche: str
    fichier: str


class ChatResponse(BaseModel):
    conversation_id: str
    reponse: str
    sources: list[SourceCitee]
    pieces_jointes: list[PieceJointe]


class ChatHistoryItem(BaseModel):
    id: str
    conversation_id: str
    question: str
    reponse: str
    sources: list[SourceCitee]
    pieces_jointes: list[PieceJointe]
    created_at: datetime


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    messages: list[ChatHistoryItem]
