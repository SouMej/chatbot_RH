"""
Gestion de la verification d'email :
- generation d'un token unique a duree limitee
- "envoi" de l'email, avec deux modes :
    - "console" (par defaut) : affiche le lien dans les logs du serveur,
      pratique pour tester en local sans configurer de vrai compte email.
    - "smtp" : envoi reel via un serveur SMTP (ex: Gmail avec mot de passe
      d'application). Necessite de remplir les variables SMTP_* du .env.

Note : le mode "smtp" fait sortir une information (l'email du salarie,
pas de donnee RH sensible) vers un service externe. A documenter comme
exception justifiee a la contrainte de fonctionnement 100% local.
"""

import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

EMAIL_MODE = os.getenv("EMAIL_MODE", "console")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
VERIF_EXPIRE_MINUTES = int(os.getenv("EMAIL_VERIFICATION_EXPIRE_MINUTES", "1440"))

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def generate_verification_token() -> tuple[str, datetime]:
    """Genere un token aleatoire securise + sa date d'expiration."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(minutes=VERIF_EXPIRE_MINUTES)
    return token, expires


def send_verification_email(destinataire: str, token: str) -> None:
    lien = f"{FRONTEND_URL}/verifier-email?token={token}"

    if EMAIL_MODE == "smtp":
        _send_via_smtp(destinataire, lien)
    else:
        # Mode par defaut pour le developpement local : pas de vrai envoi,
        # on affiche simplement le lien dans la console du serveur FastAPI.
        print("\n" + "=" * 60)
        print(f"[EMAIL DE VERIFICATION - MODE CONSOLE]")
        print(f"Destinataire : {destinataire}")
        print(f"Lien de verification : {lien}")
        print("=" * 60 + "\n")


def _send_via_smtp(destinataire: str, lien: str) -> None:
    corps = (
        f"Bonjour,\n\n"
        f"Merci de vous etre inscrit(e) sur DocuRH.\n"
        f"Cliquez sur le lien suivant pour verifier votre adresse email :\n\n"
        f"{lien}\n\n"
        f"Ce lien expire dans {VERIF_EXPIRE_MINUTES // 60} heures.\n\n"
        f"L'equipe DocuRH"
    )
    message = MIMEText(corps, "plain", "utf-8")
    message["Subject"] = "Verifiez votre adresse email - DocuRH"
    message["From"] = SMTP_USER
    message["To"] = destinataire

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, destinataire, message.as_string())
