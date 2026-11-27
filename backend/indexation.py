import argparse
import json
import os
import pickle
import re
import uuid
from typing import List, Dict, Tuple

import chromadb
import pdfplumber
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

# Local configuration
from config import CHROMA_DB_DIR, BM25_PATH, INDEX_STATE_PATH

# ----------------------------------------------------------------------
# 1. TEXT EXTRACTION
# ----------------------------------------------------------------------

def extract_pdf(path: str) -> List[Tuple[str, int]]:
    """Return a list of (text, page_number) for each PDF page."""
    chunks: List[Tuple[str, int]] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                chunks.append((text, i))
    return chunks


def extract_docx(path: str) -> List[Tuple[str, None]]:
    """Word documents lack reliable page numbers – return page=None."""
    doc = DocxDocument(path)
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [(full_text, None)]


def extract_txt(path: str) -> List[Tuple[str, None]]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [(f.read(), None)]


def extract_document(path: str) -> List[Tuple[str, int | None]]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return extract_pdf(path)
    elif ext == ".docx":
        return extract_docx(path)
    elif ext == ".txt":
        return extract_txt(path)
    else:
        print(f"Unsupported format, ignoring: {path}")
        return []

# ----------------------------------------------------------------------
# 2. STRUCTURE DETECTION (headings & simple tables)
# ----------------------------------------------------------------------

def detect_headings(text: str) -> List[Tuple[int, str, int]]:
    """Detect markdown‑style headings. Returns (level, title, line_number)."""
    headings: List[Tuple[int, str, int]] = []
    for i, line in enumerate(text.splitlines()):
        m = re.match(r"^(#{1,6})\s*(.+)", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            headings.append((level, title, i))
    return headings


def extract_tables(text: str) -> List[str]:
    """Very simple table extractor: captures consecutive lines containing '|'."""
    tables: List[str] = []
    current: List[str] = []
    for line in text.splitlines():
        if "|" in line:
            current.append(line)
        else:
            if len(current) >= 2:
                tables.append("\n".join(current))
            current = []
    if len(current) >= 2:
        tables.append("\n".join(current))
    return tables

# ----------------------------------------------------------------------
# 3. CHUNKING WITH METADATA
# ----------------------------------------------------------------------

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=80,
    separators=["\n\n", "\n", ". ", " ", ""],
)

def build_chunks(doc_path: str) -> List[Dict]:
    """Extract, split and enrich a document with rich metadata.
    Metadata includes source file, page, heading hierarchy and whether a table is present in the chunk.
    """
    results: List[Dict] = []
    filename = os.path.basename(doc_path)
    for raw_text, page in extract_document(doc_path):
        headings = detect_headings(raw_text)
        tables = extract_tables(raw_text)
        for piece in splitter.split_text(raw_text):
            heading_title = None
            heading_level = None
            if headings:
                for lvl, title, _ in reversed(headings):
                    if title in piece:
                        heading_title = title
                        heading_level = lvl
                        break
            tables_present = any(tbl in piece for tbl in tables)
            results.append({
                "id": str(uuid.uuid4()),
                "text": piece,
                "source": filename,
                "page": page if page is not None else "N/A",
                "heading": heading_title or "",
                "heading_level": heading_level or "",
                "tables_present": tables_present,
            })
    return results

# ----------------------------------------------------------------------
# 4. HELPERS – fingerprinting and state handling
# ----------------------------------------------------------------------

def compute_fingerprint(docs_dir: str) -> Dict[str, float]:
    """Create a simple fingerprint mapping filename -> last modification timestamp."""
    fp: Dict[str, float] = {}
    for fname in os.listdir(docs_dir):
        fpath = os.path.join(docs_dir, fname)
        if os.path.isfile(fpath):
            fp[fname] = os.path.getmtime(fpath)
    return fp

def load_index_state() -> Dict:
    if os.path.exists(INDEX_STATE_PATH):
        with open(INDEX_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_index_state(state: Dict) -> None:
    with open(INDEX_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

# ----------------------------------------------------------------------
# 5. BM25 INDEX CREATION
# ----------------------------------------------------------------------

def build_bm25_index(chunks: List[Dict]) -> None:
    tokenized = [re.findall(r"\w+", c["text"].lower()) for c in chunks]
    bm25 = BM25Okapi(tokenized)
    with open(BM25_PATH, "wb") as f:
        pickle.dump(bm25, f)
    print(f"BM25 index persisted to {BM25_PATH}")

# ----------------------------------------------------------------------
# 6. EMBEDDINGS + STORAGE IN CHROMADB
# ----------------------------------------------------------------------

def index_documents(docs_dir: str, collection_name: str = "rh_knowledge_base") -> None:
    # Check whether we need to re‑index
    new_fp = compute_fingerprint(docs_dir)
    old_state = load_index_state()
    if old_state.get("fingerprint") == new_fp:
        print("No document changes detected – skipping indexing.")
        return

    print("Loading multilingual e5 embedding model...")
    model = SentenceTransformer("intfloat/multilingual-e5-base")

    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    # Ensure a clean start for both Chroma and BM25
    try:
        client.delete_collection(name=collection_name)
        print(f"Deleted existing collection '{collection_name}'.")
    except Exception:
        pass
    if os.path.exists(BM25_PATH):
        os.remove(BM25_PATH)
        print("Removed previous BM25 index.")
    collection = client.get_or_create_collection(name=collection_name)

    all_chunks: List[Dict] = []
    for filename in os.listdir(docs_dir):
        full_path = os.path.join(docs_dir, filename)
        if not os.path.isfile(full_path):
            continue
        print(f"Processing: {filename}")
        chunks = build_chunks(full_path)
        all_chunks.extend(chunks)

    if not all_chunks:
        print("No chunks generated – check the documents directory.")
        return

    print(f"{len(all_chunks)} chunks to index. Computing embeddings...")
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode([f"passage: {t}" for t in texts], show_progress_bar=True).tolist()

    metadatas = [
        {
            "source": c["source"],
            "page": c["page"],
            "heading": c.get("heading") or "",
            "heading_level": c.get("heading_level") or "",
            "tables_present": c.get("tables_present", False),
        }
        for c in all_chunks
    ]

    collection.add(
        ids=[c["id"] for c in all_chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    # Build BM25 index after the Chroma collection is ready
    build_bm25_index(all_chunks)

    # Persist new fingerprint state
    save_index_state({"fingerprint": new_fp})
    print(f"Indexation completed. Database stored in: {CHROMA_DB_DIR}")

# ----------------------------------------------------------------------
# 7. COMMAND‑LINE INTERFACE
# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs_dir", required=True, help="Directory containing HR documents")
    parser.add_argument("--db_dir", default=CHROMA_DB_DIR, help="Directory for ChromaDB storage (overridden by config)")
    args = parser.parse_args()
    # Allow an explicit db_dir to override config for one‑off runs
    if args.db_dir != CHROMA_DB_DIR:
        CHROMA_DB_DIR = args.db_dir
    index_documents(args.docs_dir)