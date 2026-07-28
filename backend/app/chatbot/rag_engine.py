"""
Moteur RAG (Retrieval Augmented Generation).

IMPORTANT : le modele d'embeddings et la connexion ChromaDB sont charges
UNE SEULE FOIS, au demarrage du serveur FastAPI (voir get_rag_engine() +
son utilisation dans main.py via l'evenement "startup"). Les recharger a
chaque question ajouterait 1-2 secondes de latence inutile a chaque appel.


"""

import json
import os

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

SIMILARITY_THRESHOLD = 0.65  
TOP_K = 4

# Chemins par defaut, surchargables via variables d'environnement
DB_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_db")
DOCS_DIR = os.getenv("DOCS_DIR", "./docs_test")
COLLECTION_NAME = "rh_knowledge_base"


class RagEngine:
    """
    Encapsule le modele d'embeddings + la collection ChromaDB.
    Une seule instance est creee et reutilisee pour toutes les requetes
    (voir get_rag_engine ci-dessous).
    """

    def __init__(self):
        print("[RAG] Chargement du modele d'embeddings multilingual-e5-base...")
        self.model = SentenceTransformer("intfloat/multilingual-e5-base")

        print(f"[RAG] Connexion a la base ChromaDB ({DB_DIR})...")
        self.client = chromadb.PersistentClient(path=DB_DIR)
        self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)

        self.documents_associes = self._load_documents_associes()
        print(f"[RAG] Pret. {self.collection.count()} chunks indexes.")

    def _load_documents_associes(self):
        mapping_path = os.path.join(DOCS_DIR, "documents_associes.json")
        if not os.path.exists(mapping_path):
            return {}
        with open(mapping_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.pop("_commentaire", None)
        return data

    def _query_chroma(self, question: str, top_k: int, threshold: float):
        query_embedding = self.model.encode([f"query: {question}"]).tolist()

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
        )

        passages = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, distance in zip(docs, metas, distances):
            similarity = 1 - distance
            if similarity >= threshold:
                passages.append({
                    "text": doc,
                    "source": meta.get("source"),
                    "page": meta.get("page"),
                    "similarity": round(similarity, 3),
                })
        return passages

    def _correct_query(self, question: str) -> str:
        """Tentative de correction des coquilles via Ollama si aucun document n'est trouve."""
        try:
            from .ollama_client import generate_response
            prompt = (
                "Tu es un assistant RH. Corrige uniquement les fautes de frappe de cette question RH "
                "(exemple : 'khoraie' -> 'horaire', 'conge' -> 'congé'). "
                "Renvoie UNIQUEMENT la question corrigée, sans guillemets ni commentaire.\n\n"
                f"Question : {question}\nQuestion corrigée :"
            )
            corrected = generate_response(prompt)
            if corrected and len(corrected.strip()) > 3 and len(corrected) < len(question) * 2:
                return corrected.strip().strip('"').strip("'")
        except Exception:
            pass
        return question

    def search(self, question: str, top_k: int = TOP_K, threshold: float = SIMILARITY_THRESHOLD):
        """Recherche semantique multi-niveaux avec tolérance aux fautes de frappe (coquilles)."""
        # 1er essai : seuil standard (0.65)
        passages = self._query_chroma(question, top_k, threshold)
        if passages:
            return passages, question

        # 2ème essai : seuil assoupli (0.60) si coquille légère
        passages = self._query_chroma(question, top_k, threshold=0.60)
        if passages:
            return passages, question

        # 3ème essai : correction des coquilles par Ollama
        corrected_q = self._correct_query(question)
        if corrected_q and corrected_q.lower() != question.lower():
            passages = self._query_chroma(corrected_q, top_k, threshold=0.60)
            return passages, corrected_q

        return passages, question

    def get_attachments(self, passages):
        """Retrouve les formulaires associes aux documents sources cites."""
        seen = set()
        attachments = []
        sources_cited = {p["source"] for p in passages}

        for source in sources_cited:
            for form in self.documents_associes.get(source, []):
                if form["fichier"] not in seen:
                    seen.add(form["fichier"])
                    attachments.append({
                        "nom_affiche": form["nom_affiche"],
                        "fichier": form["fichier"],
                    })
        return attachments

    def build_prompt(self, question: str, passages: list) -> str:
        context = "\n\n".join(
            f"[Source: {p['source']}, page {p['page']}]\n{p['text']}"
            for p in passages
        )
        return f"""Tu es un assistant RH interne. Reponds UNIQUEMENT a partir du contexte
ci-dessous, en francais, de maniere claire et concise. Si le contexte ne
contient pas la reponse, dis UNIQUEMENT : "Je ne trouve pas cette information
dans les documents disponibles." Ne reponds JAMAIS avec tes propres connaissances.
Ne repete pas le contexte, va directement a la reponse.

Contexte :
{context}

Question : {question}

Reponse :"""


# --- Singleton : une seule instance partagee par toute l'application ---
_engine_instance: RagEngine | None = None


def load_rag_engine():
    """A appeler UNE FOIS au demarrage du serveur (voir main.py)."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RagEngine()
    return _engine_instance


def get_rag_engine() -> RagEngine:
    """A utiliser dans les routes pour recuperer l'instance deja chargee."""
    if _engine_instance is None:
        raise RuntimeError("Le moteur RAG n'a pas ete initialise. Appelez load_rag_engine() au demarrage.")
    return _engine_instance
