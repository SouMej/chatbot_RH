"""
Routes d'authentification :
- POST /auth/register        : inscription + envoi de l'email de verification
- GET  /auth/verify/{token}  : verification de l'email via le lien recu
- POST /auth/login           : connexion, retourne un token JWT
- POST /auth/logout          : deconnexion (cote client, voir commentaire)
- GET  /auth/me              : profil de l'utilisateur actuellement connecte
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..dependencies import get_current_user, get_db
from .email_verif import generate_verification_token, send_verification_email
from .hashing import hash_password, verify_password
from .jwt_handler import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=schemas.MessageResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    # 1. Verifier que l'email n'est pas deja utilise
    existing_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe deja avec cette adresse email.",
        )

    # 2. Hacher le mot de passe (jamais stocke en clair)
    hashed = hash_password(user_in.password)

    # 3. Generer le token de verification d'email
    token, expires = generate_verification_token()

    # 4. Creer l'utilisateur (non verifie par defaut)
    new_user = models.User(
        nom=user_in.nom,
        email=user_in.email,
        hashed_password=hashed,
        is_verified=False,
        verification_token=token,
        verification_token_expires=expires,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 5. Envoyer l'email de verification (mode console par defaut en local)
    send_verification_email(new_user.email, token)

    return {"message": "Compte cree. Verifiez votre email pour l'activer."}


@router.get("/verify/{token}", response_model=schemas.MessageResponse)
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.verification_token == token).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lien de verification invalide.")

    if user.is_verified:
        return {"message": "Ce compte est deja verifie."}

    expires = user.verification_token_expires
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if expires is None or expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce lien de verification a expire. Demandez-en un nouveau.",
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()

    return {"message": "Email verifie avec succes. Vous pouvez maintenant vous connecter."}


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()

    # Message volontairement generique (ne pas reveler si c'est l'email ou le mdp qui est faux)
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email ou mot de passe incorrect.",
    )

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise invalid_credentials

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veuillez verifier votre adresse email avant de vous connecter.",
        )

    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", response_model=schemas.MessageResponse)
def logout(current_user: models.User = Depends(get_current_user)):
    # Avec des JWT stateless, il n'y a rien a invalider cote serveur ici :
    # la deconnexion reelle consiste, cote frontend, a supprimer le token
    # stocke (ex: localStorage.removeItem("token")). Cette route sert
    # surtout a confirmer explicitement l'action et pourrait, dans une
    # version future, ajouter le token a une liste noire.
    return {"message": f"A bientot, {current_user.nom}."}


@router.get("/me", response_model=schemas.UserOut)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user
