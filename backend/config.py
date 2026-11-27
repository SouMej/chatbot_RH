import os

# Base directory of the backend package
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Directory for persistent ChromaDB storage (default is ./chroma_db inside backend)
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", os.path.join(BASE_DIR, "chroma_db"))

# Path to the persisted BM25 index pickle (stored alongside ChromaDB)
BM25_PATH = os.path.join(BASE_DIR, "bm25_index.pkl")

# Path to a small JSON file that stores a fingerprint of the indexed documents.
# Used to avoid unnecessary re‑indexing when the source documents have not changed.
INDEX_STATE_PATH = os.path.join(BASE_DIR, "index_state.json")
TOP_K_DENSE = 20
TOP_K_BM25 = 20
RRF_K = 60
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
RERANKER_TOP_N = 5
RERANKER_SCORE_THRESHOLD = 0.6
LLM_REWRITE_ENABLED = True
FIXED_NO_INFO_REPLY = "Je ne trouve pas cette information dans les documents disponibles."
