"""
Dependances FastAPI reutilisables via Depends() :
- get_db : fournit une session de base de donnees, fermee automatiquement
  apres la requete.
- get_current_user : decode le token JWT recu, verifie qu'il est valide,
  et retourne l'utilisateur correspondant. Utilisee pour proteger toute
  route qui doit etre reservee aux utilisateurs connectes.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .auth.jwt_handler import decode_access_token
from .database import SessionLocal
from . import models

# tokenUrl pointe vers l'endpoint de login (utilise par la doc auto /docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou session expiree.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user
