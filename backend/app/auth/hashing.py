"""
Hachage des mots de passe avec bcrypt (via passlib).

Rappel de securite : on ne stocke JAMAIS un mot de passe en clair.
bcrypt integre automatiquement un "salt" different a chaque hachage,
ce qui empeche les attaques par table arc-en-ciel (rainbow tables).
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
