"""
Client pour l'API locale d'Ollama.

Ollama expose une API REST sur http://localhost:11434 des qu'il tourne
(lance automatiquement en arriere-plan apres installation, ou via
`ollama serve` si besoin de le relancer manuellement).

Documentation de l'API : POST /api/generate
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))  


def generate_response(prompt: str, timeout: int | None = None) -> str:
    """
    Envoie le prompt a Ollama et retourne le texte genere.
    Leve une exception explicite si Ollama n'est pas joignable ou expiré.
    """
    req_timeout = timeout if timeout is not None else OLLAMA_TIMEOUT
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,  # reponse complete d'un coup (plus simple a gerer)
                "options": {
                    "temperature": 0.3,  # peu de creativite
                },
            },
            timeout=req_timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Impossible de contacter Ollama. Verifiez qu'il tourne bien "
            "(commande : ollama run mistral, ou ollama serve)."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Ollama a mis trop de temps a repondre (depassement du delai de {req_timeout}s). Si Ollama demarre sur CPU, relancez la requete.")
