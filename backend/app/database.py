"""
Configuration de la base de donnees (SQLite via SQLAlchemy).
SQLite est choisi pour le MVP : aucun serveur a installer, un simple fichier
local (app.db) qui respecte la contrainte de fonctionnement 100% local.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # necessaire pour SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
