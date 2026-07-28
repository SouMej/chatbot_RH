"""
Routes du chatbot :
- POST /chat         : recoit une question, cherche les passages pertinents
                       dans ChromaDB, genere une reponse via Ollama, sauvegarde
                       l'echange en base, et renvoie le tout avec les sources.
- GET  /chat/history : renvoie l'historique des questions/reponses de
                       l'utilisateur connecte, du plus ancien au plus recent.
"""

import json
import uuid
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import models, schemas
from ..dependencies import get_current_user, get_db
from .ollama_client import generate_response
from .rag_engine import get_rag_engine

router = APIRouter(tags=["Chatbot"])


def ensure_conversation_id_column(db: Session):
    """Ajoute la colonne conversation_id a SQLite si elle n'existe pas encore."""
    try:
        db.execute(text("ALTER TABLE chat_messages ADD COLUMN conversation_id VARCHAR;"))
        db.commit()
    except Exception:
        db.rollback()


@router.post("/chat", response_model=schemas.ChatResponse)
def chat(
    request: schemas.ChatRequest,
    current_user: models.User = Depends(get_current_user),  # route protegee : token requis
    db: Session = Depends(get_db),
):
    ensure_conversation_id_column(db)
    engine = get_rag_engine()

    # Si aucun conversation_id n'est fourni, on cree une nouvelle session de conversation
    conv_id = request.conversation_id or str(uuid.uuid4())

    # 1. Recherche semantique dans la base documentaire
    passages, final_question = engine.search(request.question)

    # 2. Si rien de pertinent trouve, on ne perd pas de temps a appeler le LLM
    if not passages:
        reponse_texte = (
            "Je ne trouve pas cette information dans les documents disponibles. "
            "N'hésitez pas à reformuler votre question, ou à contacter directement "
            "le service RH."
        )
        sources = []
        pieces_jointes = []
    else:
        # 3. Construction du prompt et generation de la reponse
        prompt = engine.build_prompt(final_question, passages)
        try:
            reponse_texte = generate_response(prompt)
        except RuntimeError as err:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=str(err),
            )

        # 4. Formatage et deduplication des sources et des pieces jointes eventuelles
        seen_sources = set()
        sources = []
        for p in passages:
            key = (p["source"], p["page"])
            if key not in seen_sources:
                seen_sources.add(key)
                sources.append({
                    "document": p["source"],
                    "page": p["page"],
                    "similarite": p["similarity"],
                })
        pieces_jointes = engine.get_attachments(passages)

    # 5. Sauvegarde de l'echange en base, rattache a l'utilisateur et a la conversation
    message = models.ChatMessage(
        user_id=current_user.id,
        conversation_id=conv_id,
        question=request.question,
        reponse=reponse_texte,
        sources_json=json.dumps(sources, ensure_ascii=False),
        pieces_jointes_json=json.dumps(pieces_jointes, ensure_ascii=False),
    )
    db.add(message)
    db.commit()

    return schemas.ChatResponse(
        conversation_id=conv_id,
        reponse=reponse_texte,
        sources=[schemas.SourceCitee(**s) for s in sources],
        pieces_jointes=[schemas.PieceJointe(**p) for p in pieces_jointes],
    )


@router.get("/chat/history", response_model=list[schemas.ChatHistoryItem])
def get_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_conversation_id_column(db)
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == current_user.id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )

    return [
        schemas.ChatHistoryItem(
            id=m.id,
            conversation_id=m.conversation_id or m.id,
            question=m.question,
            reponse=m.reponse,
            sources=[schemas.SourceCitee(**s) for s in m.sources()],
            pieces_jointes=[schemas.PieceJointe(**p) for p in m.pieces_jointes()],
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.get("/chat/conversations", response_model=list[schemas.ConversationSummary])
def get_conversations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_conversation_id_column(db)
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == current_user.id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )

    grouped = defaultdict(list)
    for m in messages:
        c_id = m.conversation_id or m.id
        item = schemas.ChatHistoryItem(
            id=m.id,
            conversation_id=c_id,
            question=m.question,
            reponse=m.reponse,
            sources=[schemas.SourceCitee(**s) for s in m.sources()],
            pieces_jointes=[schemas.PieceJointe(**p) for p in m.pieces_jointes()],
            created_at=m.created_at,
        )
        grouped[c_id].append(item)

    conversations = []
    for c_id, msgs in grouped.items():
        title = msgs[0].question if msgs else "Nouvelle conversation"
        conversations.append(
            schemas.ConversationSummary(
                id=c_id,
                title=title,
                created_at=msgs[0].created_at,
                messages=msgs,
            )
        )

    # Du plus recent au plus ancien
    conversations.sort(key=lambda x: x.created_at, reverse=True)
    return conversations


@router.delete("/chat/conversations/{conversation_id}", response_model=schemas.MessageResponse)
def delete_conversation(
    conversation_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_conversation_id_column(db)
    # Supprime tous les messages de cette conversation pour l'utilisateur
    deleted = db.query(models.ChatMessage).filter(
        models.ChatMessage.conversation_id == conversation_id,
        models.ChatMessage.user_id == current_user.id
    ).delete()
    
    # Fallback pour les anciennes conversations où l'id était utilisé comme conversation_id
    if deleted == 0:
        deleted = db.query(models.ChatMessage).filter(
            models.ChatMessage.id == conversation_id,
            models.ChatMessage.user_id == current_user.id
        ).delete()
        
    db.commit()
    
    if deleted == 0:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation non trouvée.")
        
    return {"message": "Conversation supprimée."}
