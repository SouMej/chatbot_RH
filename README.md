<div align="center">

![header](https://capsule-render.vercel.app/api?type=waving&color=0:1f3b6f,100:2e6fdb&height=200&section=header&text=DocuRH&fontSize=52&fontColor=ffffff&desc=Chatbot%20RH%20Interne%20%E2%80%93%20RAG%20%2B%20Hybrid%20Retrieval&descAlignY=68&descSize=18)

**Chatbot intelligent pour les ressources humaines, propulsé par RAG et un pipeline de recherche hybride.**
Indexation · Dense + BM25 · Reciprocal Rank Fusion · Cross-Encoder Reranking · Ollama LLM

![Python](https://img.shields.io/badge/Python-3.11-1f3b6f?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-2e6fdb?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61dafb?logo=react&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector%20store-0b1f3a)
![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-9db8e8)
![Sentence Transformers](https://img.shields.io/badge/Sentence%20Transformers-embeddings-f37626)

[Aperçu](#aperçu) · [Architecture](#architecture) · [Pipeline RAG](#pipeline-rag) · [Stack technique](#stack-technique) · [Installation](#installation) · [Utilisation](#utilisation) · [Structure du projet](#structure-du-projet)

</div>

---

## Aperçu

| Documents RH | Chunks indexés | Retrieval | Reranking | LLM |
|:---:|:---:|:---:|:---:|:---:|
| **17** (PDF, DOCX, TXT) | **104** | **Dense + BM25 hybride** | **Cross-Encoder** | **Ollama (local)** |

DocuRH est un chatbot RH interne qui permet aux employés de poser des questions en langage naturel sur les politiques de l'entreprise (congés, télétravail, règlement intérieur, notes de frais, etc.). Le système retrouve les passages pertinents dans la base documentaire et génère une réponse sourcée grâce à un LLM local.

> [!IMPORTANT]
> Le chatbot ne répond **jamais** à partir de ses propres connaissances. Si aucun document pertinent n'est trouvé (score de reranking sous le seuil), il retourne un message fixe sans appeler le LLM, ce qui évite les hallucinations.

## Architecture

```mermaid
flowchart LR
    A[("👤 Utilisateur")] --> B["Frontend React\n(Vite)"]
    B -->|REST API| C["Backend FastAPI"]
    C --> D["Auth\n(JWT + email)"]
    C --> E["RAG Engine"]
    E --> F[("ChromaDB\n(dense)")]
    E --> G[("BM25 Index\n(sparse)")]
    F --> H["RRF Fusion"]
    G --> H
    H --> I["Cross-Encoder\nReranking"]
    I -->|score ≥ seuil| J["Ollama LLM\n(qwen2.5:3b)"]
    I -->|score < seuil| K["Réponse fixe\n(pas d'appel LLM)"]
    J --> B
    K --> B

    style A fill:#e8f0fe,stroke:#2e6fdb,color:#0b1f3a
    style E fill:#fff4e5,stroke:#f59e0b,color:#0b1f3a
    style I fill:#f3e8ff,stroke:#9333ea,color:#0b1f3a
    style J fill:#e6f7ec,stroke:#16a34a,color:#0b1f3a
    style K fill:#fde8e8,stroke:#dc2626,color:#0b1f3a
```

## Pipeline RAG

Le cœur du système est un pipeline de recherche hybride en 7 étapes :

### Phase 1 – Indexation

| Étape | Description |
|---|---|
| Extraction | PDF (pdfplumber), DOCX (python-docx), TXT |
| Détection de structure | Headings markdown, tables simples |
| Chunking | `RecursiveCharacterTextSplitter` (500 tokens, 80 overlap) |
| Embeddings | `intfloat/multilingual-e5-base` (768d, multilingue) |
| Stockage dense | ChromaDB (persistant) |
| Stockage sparse | BM25Okapi (pickle sérialisé) |
| Fingerprinting | Évite la ré-indexation si les documents n'ont pas changé |

### Phase 2 – Recherche hybride + Reranking

```mermaid
flowchart TD
    Q["Question utilisateur"] --> D["Dense top-20\n(ChromaDB)"]
    Q --> S["BM25 top-20\n(sparse)"]
    D --> R["Reciprocal Rank Fusion\n(k=60)"]
    S --> R
    R --> RE["Cross-Encoder Reranking\n(BAAI/bge-reranker-v2-m3)"]
    RE --> T{"Score max\n≥ 0.6 ?"}
    T -->|Oui| TOP["Top 5 passages\n→ prompt LLM"]
    T -->|Non| RW{"Réécriture LLM\nactivée ?"}
    RW -->|Oui| CQ["Correction de la query\n(Ollama)"]
    CQ --> D2["Répéter pipeline\navec query corrigée"]
    D2 --> T2{"Score max\n≥ 0.6 ?"}
    T2 -->|Oui| TOP
    T2 -->|Non| FIX["Réponse fixe\n(pas d'appel LLM)"]
    RW -->|Non| FIX

    style Q fill:#e8f0fe,stroke:#2e6fdb,color:#0b1f3a
    style RE fill:#f3e8ff,stroke:#9333ea,color:#0b1f3a
    style TOP fill:#e6f7ec,stroke:#16a34a,color:#0b1f3a
    style FIX fill:#fde8e8,stroke:#dc2626,color:#0b1f3a
```

### Paramètres configurables

Tous les hyperparamètres du pipeline vivent dans `backend/config.py` :

| Paramètre | Défaut | Rôle |
|---|:---:|---|
| `TOP_K_DENSE` | 20 | Nombre de candidats dense (Chroma) |
| `TOP_K_BM25` | 20 | Nombre de candidats sparse (BM25) |
| `RRF_K` | 60 | Constante k de la formule RRF |
| `RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | Modèle cross-encoder |
| `RERANKER_TOP_N` | 5 | Passages conservés après reranking |
| `RERANKER_SCORE_THRESHOLD` | 0.6 | Seuil de pertinence minimum |
| `LLM_REWRITE_ENABLED` | `true` | Réécriture de la query en cas de score faible |

> [!TIP]
> Le seuil de reranking est un **levier métier** : l'abaisser retourne plus de réponses (au risque de moins de pertinence), le relever réduit les faux positifs.

## Stack technique

| Couche | Technologies |
|---|---|
| **Frontend** | React 18, Vite, React Router |
| **Backend** | FastAPI, SQLAlchemy, Uvicorn |
| **Auth** | JWT (python-jose), bcrypt, vérification email |
| **Embeddings** | `intfloat/multilingual-e5-base` (Sentence Transformers) |
| **Vector Store** | ChromaDB (persistant) |
| **Sparse Index** | BM25Okapi (rank_bm25) |
| **Reranker** | `BAAI/bge-reranker-v2-m3` (CrossEncoder) |
| **LLM** | Ollama (local, `qwen2.5:3b` par défaut) |
| **Documents** | pdfplumber, python-docx |

## Installation

### Prérequis

- **Python 3.11+**
- **Node.js 18+**
- **[Ollama](https://ollama.com/)** installé et en cours d'exécution

### 1. Cloner le dépôt

```bash
git clone https://github.com/SouMej/chatbot_RH.git
cd chatbot_RH
```

### 2. Backend

```bash
cd backend

# Créer et activer l'environnement virtuel
python -m venv venv
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditez .env avec votre clé secrète JWT

# Lancer le modèle Ollama
ollama pull qwen2.5:3b

# Indexer les documents RH
python indexation.py --docs_dir ./docs_test

# Lancer le serveur
uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

> [!NOTE]
> Le frontend sera accessible sur `http://localhost:5173` et le backend sur `http://localhost:8000`.

## Utilisation

1. **Créer un compte** via la page d'inscription (vérification email en mode console par défaut).
2. **Se connecter** pour obtenir un token JWT.
3. **Poser des questions** en langage naturel :
   - *"Quelle est la politique de congés ?"*
   - *"Comment faire une note de frais ?"*
   - *"Quelles sont les sanctions disciplinaires ?"*
   - *"Comment signaler un harcèlement ?"*

Le chatbot retourne une réponse sourcée avec les documents et pages d'origine, ainsi que les formulaires associés le cas échéant.

## Structure du projet

```
chatbot_RH/
├── backend/
│   ├── app/
│   │   ├── auth/                   # Authentification (JWT, email, hashing)
│   │   │   ├── routes.py
│   │   │   ├── jwt_handler.py
│   │   │   ├── hashing.py
│   │   │   └── email_verif.py
│   │   ├── chatbot/                # Cœur du RAG
│   │   │   ├── config.py           # Paramètres du pipeline hybride
│   │   │   ├── rag_engine.py       # Dense + BM25 + RRF + Reranker
│   │   │   ├── ollama_client.py    # Client Ollama (LLM local)
│   │   │   └── routes.py           # Endpoints /chat, /chat/history
│   │   ├── main.py                 # Point d'entrée FastAPI
│   │   ├── models.py               # Modèles SQLAlchemy
│   │   ├── schemas.py              # Schémas Pydantic
│   │   ├── database.py             # Configuration SQLite
│   │   └── dependencies.py         # Dépendances FastAPI (auth, DB)
│   ├── docs_test/                  # Documents RH sources (17 fichiers)
│   ├── config.py                   # Configuration globale (chemins, BM25)
│   ├── indexation.py               # Script d'indexation (Chroma + BM25)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/             # AuthLayout, FormField, ProtectedRoute, ThemeToggle
│   │   ├── pages/                  # Chat, Home, Login, Register, VerifyEmail
│   │   ├── context/                # ThemeContext
│   │   ├── styles/                 # theme.css
│   │   ├── utils/                  # api.js (client HTTP)
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── .gitignore
└── README.md
```

## Améliorations futures

| Fonctionnalité | Description |
|---|---|
| Streaming LLM | Réponse en temps réel (Server-Sent Events) |
| Multi-turn | Mémoire conversationnelle avec historique dans le prompt |
| Upload de documents | Interface pour ajouter de nouveaux documents sans CLI |
| Évaluation automatique | Jeu de questions/réponses pour mesurer la qualité du retrieval |
| Déploiement Docker | `docker-compose` avec Ollama, backend et frontend |

---

<div align="center">

**Sonia Mejri** · Étudiante en ingénierie (Réseaux et Télécommunications) · INSAT

![footer](https://capsule-render.vercel.app/api?type=waving&color=0:2e6fdb,100:1f3b6f&height=100&section=footer)

</div>
