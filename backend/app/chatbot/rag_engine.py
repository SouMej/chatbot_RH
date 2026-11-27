"""
Moteur RAG (Retrieval Augmented Generation).

IMPORTANT : le modele d'embeddings et la connexion ChromaDB sont charges
UNE SEULE FOIS, au demarrage du serveur FastAPI (voir get_rag_engine() +
son utilisation dans main.py via l'evenement "startup"). Les recharger a
chaque question ajouterait 1-2 secondes de latence inutile a chaque appel.


"""

import json
import os
import pickle
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb
from .config import CHROMA_DB_DIR, BM25_PATH, TOP_K_DENSE, TOP_K_BM25, RRF_K, RERANKER_MODEL, RERANKER_TOP_N, RERANKER_SCORE_THRESHOLD, LLM_REWRITE_ENABLED, FIXED_NO_INFO_REPLY
from sentence_transformers import CrossEncoder
import numpy as np
import re

load_dotenv()

SIMILARITY_THRESHOLD = 0.65  
TOP_K = 4

# Chemins par defaut, surchargables via variables d'environnement
DB_DIR = CHROMA_DB_DIR
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

        # Load BM25 index – must be present; otherwise require re‑indexing
        try:
            with open(BM25_PATH, "rb") as f:
                self.bm25 = pickle.load(f)
            print(f"[RAG] BM25 index loaded from {BM25_PATH}")
        except Exception as e:
            raise RuntimeError("BM25 index missing or corrupted. Run indexation.py first.") from e
        self.documents_associes = self._load_documents_associes()

        # Load all chunks (ids, texts, metadata) for BM25 mapping and reranking
        all_data = self.collection.get(include=["documents", "metadatas"])
        self.all_chunks = [
            {"id": cid, "text": doc, "metadata": meta}
            for cid, doc, meta in zip(all_data["ids"], all_data["documents"], all_data["metadatas"])
        ]
        # Initialize cross‑encoder reranker
        self.reranker = CrossEncoder(RERANKER_MODEL)
        print(f"[RAG] Pret. {self.collection.count()} chunks indexes, reranker loaded.")

    def _load_documents_associes(self):
        mapping_path = os.path.join(DOCS_DIR, "documents_associes.json")
        if not os.path.exists(mapping_path):
            return {}
        with open(mapping_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.pop("_commentaire", None)
        return data

    def _query_chroma(self, question: str, top_k: int, threshold: float = 0.0):
        """Dense retrieval from Chroma, returns list of dicts with id and similarity."""
        query_embedding = self.model.encode([f"query: {question}"]).tolist()
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        passages = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]
        for doc, meta, distance, cid in zip(docs, metas, distances, ids):
            similarity = 1 - distance
            if similarity >= threshold:
                passages.append({
                    "id": cid,
                    "text": doc,
                    "source": meta.get("source"),
                    "page": meta.get("page"),
                    "similarity": round(similarity, 3),
                })
        return passages

    def _query_bm25(self, question: str, top_k: int):
        """BM25 retrieval. Returns list of dicts with id, text, source, page, bm25_score."""
        tokens = re.findall(r"\w+", question.lower())
        scores = self.bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            chunk = self.all_chunks[idx]
            results.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "source": chunk["metadata"].get("source"),
                "page": chunk["metadata"].get("page"),
                "bm25_score": float(scores[idx]),
            })
        return results

    def _rrf_merge(self, dense: list, bm25: list, k: int = RRF_K):
        """Reciprocal Rank Fusion merging two result lists."""
        fusion = {}
        for rank, doc in enumerate(dense, start=1):
            doc_id = doc["id"]
            fusion.setdefault(doc_id, {"doc": doc, "score": 0.0})
            fusion[doc_id]["score"] += 1.0 / (k + rank)
        for rank, doc in enumerate(bm25, start=1):
            doc_id = doc["id"]
            fusion.setdefault(doc_id, {"doc": doc, "score": 0.0})
            fusion[doc_id]["score"] += 1.0 / (k + rank)
        merged = [v["doc"] for v in fusion.values()]
        for doc in merged:
            doc["rrf_score"] = fusion[doc["id"]]["score"]
        merged.sort(key=lambda d: d["rrf_score"], reverse=True)
        return merged

    def _rerank(self, candidates: list, query: str):
        """Cross‑encoder reranking. Returns top N candidates sorted by rerank score."""
        texts = [c["text"] for c in candidates]
        scores = self.reranker.predict([(query, txt) for txt in texts])
        for cand, sc in zip(candidates, scores):
            cand["rerank_score"] = float(sc)
        candidates.sort(key=lambda d: d["rerank_score"], reverse=True)
        return candidates[:RERANKER_TOP_N]

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
        """Hybrid retrieval (dense + BM25) with RRF fusion and cross‑encoder reranking.
        Returns top_k passages and the (possibly rewritten) query.
        Implements early‑exit based on RERANKER_SCORE_THRESHOLD and optional LLM rewrite.
        """
        # 1. Dense retrieval (no similarity threshold to keep max candidates)
        dense_hits = self._query_chroma(question, TOP_K_DENSE, threshold=0.0)
        # 2. BM25 retrieval
        bm25_hits = self._query_bm25(question, TOP_K_BM25)
        # 3. Fuse results with Reciprocal Rank Fusion
        fused = self._rrf_merge(dense_hits, bm25_hits, k=RRF_K)
        # 4. Rerank with cross‑encoder
        reranked = self._rerank(fused, question)
        # 5. Check best rerank score against threshold
        if reranked and reranked[0].get("rerank_score", 0) >= RERANKER_SCORE_THRESHOLD:
            return reranked[:top_k], question

        # 6. Optional query rewrite via LLM if enabled
        if LLM_REWRITE_ENABLED:
            rewritten = self._correct_query(question)
            if rewritten and rewritten.lower() != question.lower():
                dense_hits = self._query_chroma(rewritten, TOP_K_DENSE, threshold=0.0)
                bm25_hits = self._query_bm25(rewritten, TOP_K_BM25)
                fused = self._rrf_merge(dense_hits, bm25_hits, k=RRF_K)
                reranked = self._rerank(fused, rewritten)
                if reranked and reranked[0].get("rerank_score", 0) >= RERANKER_SCORE_THRESHOLD:
                    return reranked[:top_k], rewritten

        # 7. No relevant passage found – return fixed reply
        return [], FIXED_NO_INFO_REPLY

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
