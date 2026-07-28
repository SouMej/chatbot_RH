"""
Script d'indexation
Pipeline : extraction -> decoupage -> embeddings -> stockage ChromaDB

Installation prealable :
    pip install pdfplumber python-docx sentence-transformers chromadb langchain-text-splitters

Utilisation :
    python indexation.py --docs_dir ./docs_test --db_dir ./chroma_db
"""

import argparse
import os
import uuid

import chromadb
import pdfplumber
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer


# ----------------------------------------------------------------------
# 1. EXTRACTION DU TEXTE 
# ----------------------------------------------------------------------

def extract_pdf(path):
    """Retourne une liste de (texte, page)."""
    chunks = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                chunks.append((text, i))
    return chunks


def extract_docx(path):
    """Word n'a pas de notion de page fiable -> on renvoie page=None."""
    doc = DocxDocument(path)
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [(full_text, None)]


def extract_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [(f.read(), None)]


def extract_document(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return extract_pdf(path)
    elif ext == ".docx":
        return extract_docx(path)
    elif ext == ".txt":
        return extract_txt(path)
    else:
        print(f"Format non supporte, ignore : {path}")
        return []


# ----------------------------------------------------------------------
# 2. DECOUPAGE EN CHUNKS
# ----------------------------------------------------------------------

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,       # caracteres par chunk
    chunk_overlap=80,     # chevauchement pour ne pas couper une idee en deux
    separators=["\n\n", "\n", ". ", " ", ""],
)


def build_chunks(doc_path):
    """Extrait puis decoupe un document en chunks avec metadonnees."""
    results = []
    filename = os.path.basename(doc_path)
    for text, page in extract_document(doc_path):
        for piece in splitter.split_text(text):
            results.append({
                "id": str(uuid.uuid4()),
                "text": piece,
                "source": filename,
                "page": page if page is not None else "N/A",
            })
    return results


# ----------------------------------------------------------------------
# 3. EMBEDDINGS + STOCKAGE DANS CHROMADB
# ----------------------------------------------------------------------

def index_documents(docs_dir, db_dir, collection_name="rh_knowledge_base"):
    print("Chargement du modele d'embeddings multilingue...")
    model = SentenceTransformer("intfloat/multilingual-e5-base")

    client = chromadb.PersistentClient(path=db_dir)
    collection = client.get_or_create_collection(name=collection_name)

    all_chunks = []
    for filename in os.listdir(docs_dir):
        full_path = os.path.join(docs_dir, filename)
        if not os.path.isfile(full_path):
            continue
        print(f"Traitement : {filename}")
        chunks = build_chunks(full_path)
        all_chunks.extend(chunks)

    if not all_chunks:
        print("Aucun chunk genere. Verifiez le dossier de documents.")
        return

    print(f"{len(all_chunks)} chunks a indexer. Calcul des embeddings...")
    texts = [c["text"] for c in all_chunks]
    # prefixe "passage: " recommande par le modele multilingual-e5 pour l'indexation
    embeddings = model.encode(
        [f"passage: {t}" for t in texts],
        show_progress_bar=True,
    ).tolist()

    collection.add(
        ids=[c["id"] for c in all_chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{"source": c["source"], "page": c["page"]} for c in all_chunks],
    )

    print(f"Indexation terminee. Base stockee dans : {db_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs_dir", required=True, help="Dossier contenant les documents RH")
    parser.add_argument("--db_dir", default="./chroma_db", help="Dossier de stockage ChromaDB")
    args = parser.parse_args()

    index_documents(args.docs_dir, args.db_dir)