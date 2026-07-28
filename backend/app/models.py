"""
Modele SQLAlchemy representant un utilisateur en base de donnees.
"""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from .database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    nom = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String, nullable=True, index=True)
    verification_token_expires = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, index=True, nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    question = Column(Text, nullable=False)
    reponse = Column(Text, nullable=False)

    # Stockees en JSON (texte) : structure variable, pas besoin de tables
    # separees pour un MVP. sources_json = liste de {document, page, similarite},
    # pieces_jointes_json = liste de {nom_affiche, fichier}.
    sources_json = Column(Text, default="[]")
    pieces_jointes_json = Column(Text, default="[]")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="messages")

    def sources(self):
        return json.loads(self.sources_json or "[]")

    def pieces_jointes(self):
        return json.loads(self.pieces_jointes_json or "[]")
