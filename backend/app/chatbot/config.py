import os

# Paths for storage – can be overridden by environment variables
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_db")
BM25_PATH = os.getenv("BM25_PATH", "./bm25_index.pkl")

# Retrieval parameters for Phase 2 hybrid search
TOP_K_DENSE = int(os.getenv("TOP_K_DENSE", "20"))  # number of dense candidates
TOP_K_BM25 = int(os.getenv("TOP_K_BM25", "20"))   # number of BM25 candidates
RRF_K = int(os.getenv("RRF_K", "60"))            # k parameter for Reciprocal Rank Fusion

# Cross‑encoder reranker configuration
RERANKER_MODEL = os.getenv(
    "RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"
)  # model identifier for sentence‑transformers
RERANKER_TOP_N = int(os.getenv("RERANKER_TOP_N", "5"))  # final number of passages to keep
RERANKER_SCORE_THRESHOLD = float(
    os.getenv("RERANKER_SCORE_THRESHOLD", "0.6")
)  # minimum score to consider a passage relevant

# Optional LLM‑based query rewrite (fallback when no relevant passage)
LLM_REWRITE_ENABLED = os.getenv("LLM_REWRITE_ENABLED", "true").lower() == "true"

# Fixed reply when no information is found
FIXED_NO_INFO_REPLY = "Je ne trouve pas cette information dans les documents disponibles."
