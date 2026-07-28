"""
Script de recherche 
Recherche semantique generique : ne depend d'aucun mot-cle ni structure
propre a une entreprise. Fonctionne avec n'importe quelle base ChromaDB
generee par indexation.py, quel que soit le contenu des documents.

Nouveaute : attache automatiquement les formulaires a remplir associes
a un document source, via le fichier documents_associes.json.

Installation prealable :
    pip install chromadb sentence-transformers

Utilisation :
    python recherche.py --db_dir ./chroma_db --docs_dir ./docs_test --question "Comment prendre un conge ?"
"""

import argparse
import json
import os

import chromadb
from sentence_transformers import SentenceTransformer

# Seuil de similarite en dessous duquel on considere qu'aucun document
# ne repond a la question (evite les reponses inventees / hors sujet).
# A ajuster empiriquement (0.75-0.80 est un bon point de depart avec e5).
SIMILARITY_THRESHOLD = 0.75

# Nombre de passages les plus pertinents a retourner
TOP_K = 4


def load_resources(db_dir, collection_name="rh_knowledge_base"):
    model = SentenceTransformer("intfloat/multilingual-e5-base")
    client = chromadb.PersistentClient(path=db_dir)
    collection = client.get_or_create_collection(name=collection_name)
    return model, collection


def load_documents_associes(docs_dir):
    """
    Charge le mapping document_source -> liste de formulaires associes.
    Si le fichier n'existe pas, retourne un mapping vide (fonctionnalite
    optionnelle, ne casse rien si absente).
    """
    mapping_path = os.path.join(docs_dir, "documents_associes.json")
    if not os.path.exists(mapping_path):
        return {}
    with open(mapping_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.pop("_commentaire", None)
    return data


def get_attachments(passages, documents_associes, docs_dir):
    """
    Pour chaque document source retrouve dans les passages pertinents,
    verifie s'il existe un ou plusieurs formulaires associes, et retourne
    leur chemin complet pour que le frontend puisse proposer le telechargement.
    Les doublons (meme formulaire cite via plusieurs passages) sont evites.
    """
    seen = set()
    attachments = []
    sources_cited = {p["source"] for p in passages}

    for source in sources_cited:
        for form in documents_associes.get(source, []):
            if form["fichier"] not in seen:
                seen.add(form["fichier"])
                attachments.append({
                    "nom_affiche": form["nom_affiche"],
                    "fichier": form["fichier"],
                    "chemin": os.path.join(docs_dir, form["fichier"]),
                    "document_source_lie": source,
                })
    return attachments


def search(question, model, collection, top_k=TOP_K, threshold=SIMILARITY_THRESHOLD):
    """
    Recherche purement semantique : la question est comparee aux chunks
    indexes par similarite de sens, jamais par correspondance de mots-cles.
    Fonctionne donc quel que soit le vocabulaire propre a l'entreprise
    (ex: "conges" vs "absences", "attestation" vs "certificat").
    """
    # prefixe "query: " recommande par multilingual-e5 pour les requetes
    query_embedding = model.encode([f"query: {question}"]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
    )

    passages = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # ChromaDB retourne une distance ; on la convertit en score de similarite
        similarity = 1 - distance
        if similarity >= threshold:
            passages.append({
                "text": doc,
                "source": meta["source"],
                "page": meta["page"],
                "similarity": round(similarity, 3),
            })

    return passages


def build_prompt(question, passages):
    """Construit le prompt envoye au LLM local, avec les sources exactes."""
    if not passages:
        return None  # aucun passage pertinent -> pas de generation, reponse fixe

    context = "\n\n".join(
        f"[Source: {p['source']}, page {p['page']}]\n{p['text']}"
        for p in passages
    )

    prompt = f"""Tu es un assistant RH interne. Reponds UNIQUEMENT a partir du contexte
ci-dessous, en francais, de maniere claire et concise. Si le contexte ne
contient pas la reponse, dis clairement que tu ne trouves pas l'information.
Cite toujours le document source a la fin de ta reponse.

Contexte :
{context}

Question : {question}

Reponse :"""
    return prompt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db_dir", required=True, help="Dossier de la base ChromaDB")
    parser.add_argument("--docs_dir", required=True, help="Dossier des documents (pour retrouver documents_associes.json et les formulaires)")
    parser.add_argument("--question", required=True, help="Question posee par l'employe")
    args = parser.parse_args()

    model, collection = load_resources(args.db_dir)
    documents_associes = load_documents_associes(args.docs_dir)
    passages = search(args.question, model, collection)

    if not passages:
        print("Aucune information trouvee dans la base documentaire pour cette question.")
    else:
        print(f"{len(passages)} passage(s) pertinent(s) trouve(s) :\n")
        for p in passages:
            print(f"- {p['source']} (page {p['page']}, similarite {p['similarity']}) :")
            print(f"  {p['text'][:200]}...\n")

        attachments = get_attachments(passages, documents_associes, args.docs_dir)
        if attachments:
            print("Formulaire(s) a joindre a la reponse :")
            for a in attachments:
                print(f"  - {a['nom_affiche']} ({a['fichier']}) -- lie a : {a['document_source_lie']}")
            print()

        prompt = build_prompt(args.question, passages)
        print("---- Prompt pret a etre envoye au LLM (Ollama) ----")
        print(prompt)