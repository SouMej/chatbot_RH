import { useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import ThemeToggle from "../components/ThemeToggle.jsx";
import { logoutRequest, chatRequest, getConversations, getCurrentUser, deleteConversationRequest } from "../utils/api.js";

const SUGGESTIONS = [
  { titre: "Congés", texte: "Comment prendre un congé annuel ?" },
  { titre: "Horaires", texte: "Quel est l'horaire pendant l'été ?" },
  { titre: "Télétravail", texte: "Combien de jours de télétravail par semaine ?" },
  { titre: "Certificat", texte: "Comment obtenir un certificat d'emploi ?" },
];

export default function Chat() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [user, setUser] = useState(null);
  
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Charge l'historique des conversations regroupees au demarrage
  const loadHistory = () => {
    getConversations()
      .then((convs) => {
        setConversations(convs);
        // Si aucune conversation active n'est selectionnee et qu'il y a des conversations
        if (convs.length > 0 && messages.length === 0) {
          // On peut soit laisser vide (Nouvelle conversation), soit charger la derniere
        }
      })
      .catch(() => {})
      .finally(() => setHistoryLoaded(true));
  };

  useEffect(() => {
    loadHistory();
    getCurrentUser().then(setUser).catch(() => {});
  }, []);

  const handleMouseDown = (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = sidebarWidth;

    const onMouseMove = (moveEvent) => {
      const newWidth = Math.max(200, Math.min(600, startWidth + (moveEvent.clientX - startX)));
      setSidebarWidth(newWidth);
    };

    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  const handleDeleteConversation = (e, id) => {
    e.stopPropagation();
    setConversationToDelete(id);
  };

  const confirmDeleteConversation = async () => {
    if (!conversationToDelete) return;
    try {
      await deleteConversationRequest(conversationToDelete);
      if (activeConversationId === conversationToDelete) {
        startNewConversation();
      }
      loadHistory();
    } catch (err) {
      alert("Erreur lors de la suppression");
    } finally {
      setConversationToDelete(null);
    }
  };

  const handleCopy = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  async function sendMessage(text) {
    const question = text ?? input;
    if (!question.trim()) return;

    setMessages((m) => [...m, { role: "user", content: question }]);
    setInput("");
    setLoading(true);

    try {
      const data = await chatRequest(question, activeConversationId);

      // Si c'etait un nouveau fil, on enregistre son ID pour les prochaines questions
      if (!activeConversationId && data.conversation_id) {
        setActiveConversationId(data.conversation_id);
      }

      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: data.reponse,
          sources: data.sources,
          pieces_jointes: data.pieces_jointes,
        },
      ]);

      // Re-charge la liste des conversations dans la barre latérale
      getConversations().then(setConversations).catch(() => {});
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `Erreur : ${err.message}`, sources: [], pieces_jointes: [] },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const startNewConversation = () => {
    setMessages([]);
    setActiveConversationId(null);
    setShowHistory(false);
  };

  const loadConversationSession = (conv) => {
    setActiveConversationId(conv.id);
    const restored = conv.messages.flatMap((item) => [
      { role: "user", content: item.question },
      {
        role: "assistant",
        content: item.reponse,
        sources: item.sources,
        pieces_jointes: item.pieces_jointes,
      },
    ]);
    setMessages(restored);
  };

  return (
    <div style={{ display: "flex", height: "100vh", position: "relative", overflow: "hidden" }}>
      {isSidebarOpen && (
        <aside
          style={{
            width: sidebarWidth,
            borderRight: "1px solid var(--border)",
            background: "var(--surface)",
            display: "flex",
            flexDirection: "column",
            padding: 20,
            overflowY: "auto",
            position: "relative",
            flexShrink: 0,
          }}
        >
          <div
            onMouseDown={handleMouseDown}
            style={{
              position: "absolute",
              top: 0,
              right: 0,
              width: 6,
              height: "100%",
              cursor: "col-resize",
              zIndex: 10,
            }}
          />
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 28 }}>
            <Link
              to="/"
              style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none", color: "var(--ink)" }}
            >
          <div
            style={{
              width: 26,
              height: 26,
              borderRadius: 6,
              background: "var(--primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <path d="M14 2v6h6" />
            </svg>
          </div>
          <span style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 16 }}>
            DocuRH
          </span>
        </Link>
        <button onClick={() => setIsSidebarOpen(false)} style={{ background: "transparent", border: "none", cursor: "pointer", color: "var(--ink-muted)", display: "flex" }}>
           <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
      </div>

        <button
          onClick={startNewConversation}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            width: "100%",
            padding: "10px 14px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border)",
            background: "var(--surface-alt)",
            color: "var(--ink)",
            fontSize: 14,
            fontWeight: 500,
            marginBottom: 20,
            cursor: "pointer",
          }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Nouvelle conversation
        </button>

        
        <NavItem
          label={`Historique ${conversations.length > 0 ? `(${conversations.length})` : ""}`}
          icon="clock"
          active={showHistory}
          onClick={() => {
            setShowHistory(!showHistory);
            loadHistory();
          }}
        />

        {showHistory && (
          <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6, maxHeight: 240, overflowY: "auto" }}>
            <p style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", color: "var(--ink-muted)", marginBottom: 4 }}>
              Conversations passées
            </p>
            {conversations.length === 0 ? (
              <p style={{ fontSize: 12, color: "var(--ink-muted)", fontStyle: "italic" }}>Aucun historique</p>
            ) : (
              conversations.map((conv) => {
                const isSelected = conv.id === activeConversationId;
                return (
                  <button
                    key={conv.id}
                    onClick={() => loadConversationSession(conv)}
                    style={{
                      textAlign: "left",
                      padding: "8px 10px",
                      borderRadius: "var(--radius-sm)",
                      border: isSelected ? "1px solid var(--primary)" : "1px solid var(--border)",
                      background: isSelected ? "var(--surface-alt)" : "transparent",
                      fontSize: 12.5,
                      color: "var(--ink)",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: 2,
                    }}
                  >
                    <span style={{ fontWeight: isSelected ? 600 : 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                       {conv.title}
                    </span>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: 10.5, color: "var(--ink-muted)" }}>
                        {conv.messages.length} échange{conv.messages.length > 1 ? "s" : ""}
                      </span>
                      <button
                        onClick={(e) => handleDeleteConversation(e, conv.id)}
                        style={{ background: "transparent", border: "none", cursor: "pointer", color: "var(--ink-muted)", padding: 2, display: "flex" }}
                        title="Supprimer la conversation"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                      </button>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        )}

        <div style={{ marginTop: "auto", paddingTop: 16 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "12px 4px",
              borderTop: "1px solid var(--border)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: "50%",
                  background: "var(--secondary)",
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                {user ? user.nom.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2) : "?"}
              </div>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{user ? user.nom : "..."}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  setShowLogoutModal(true);
                }}
                title="Se déconnecter"
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: "50%",
                  border: "1px solid var(--border)",
                  background: "var(--surface)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--ink-muted)",
                  cursor: "pointer",
                }}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
                </svg>
              </button>
              <ThemeToggle />
            </div>
          </div>
        </div>
      </aside>
      )}

      <main style={{ flex: 1, display: "flex", flexDirection: "column", background: "var(--bg)", position: "relative" }}>
        {!isSidebarOpen && (
          <button 
            onClick={() => setIsSidebarOpen(true)}
            style={{ position: "absolute", top: 16, left: 16, zIndex: 10, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: 8, cursor: "pointer", color: "var(--ink)", display: "flex" }}
            title="Ouvrir le menu"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
          </button>
        )}
        <div style={{ flex: 1, overflowY: "auto", padding: "40px 24px" }}>
          {messages.length === 0 ? (
            <div
              style={{
                maxWidth: 680,
                margin: "60px auto 0",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: "50%",
                  background: "var(--primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: 20,
                }}
              >
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <path d="M14 2v6h6" />
                </svg>
              </div>
              <h2 style={{ fontSize: 26, marginBottom: 8 }}>Bonjour, {user ? user.nom.split(" ")[0] : ""}</h2>
              <p style={{ color: "var(--ink-muted)", fontSize: 15, marginBottom: 36 }}>
                Posez une question RH — congés, horaires, procédures administratives.
              </p>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                  gap: 12,
                  width: "100%",
                }}
              >
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s.titre}
                    onClick={() => sendMessage(s.texte)}
                    className="corner-fold"
                    style={{
                      textAlign: "left",
                      padding: 16,
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      borderRadius: "var(--radius-md)",
                      cursor: "pointer",
                    }}
                  >
                    <p style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{s.titre}</p>
                    <p style={{ fontSize: 13, color: "var(--ink-muted)" }}>{s.texte}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ maxWidth: 680, margin: "0 auto", display: "flex", flexDirection: "column", gap: 16 }}>
              {messages.map((m, i) => {
                const isUser = m.role === "user";

                // Deduplication des sources par document + page
                const uniqueSources = m.sources
                  ? Array.from(
                      new Map(
                        m.sources.map((s) => [`${s.document}-${s.page}`, s])
                      ).values()
                    )
                  : [];

                return (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      width: "100%",
                      justifyContent: isUser ? "flex-end" : "flex-start",
                    }}
                  >
                    <div
                      style={{
                        maxWidth: "75%",
                        padding: "12px 16px",
                        borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                        background: isUser ? "var(--primary)" : "var(--surface)",
                        color: isUser ? "#fff" : "var(--ink)",
                        border: isUser ? "none" : "1px solid var(--border)",
                        boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
                      }}
                    >
                      <p style={{ fontSize: 14.5, whiteSpace: "pre-wrap", margin: 0, lineHeight: 1.45 }}>{m.content}</p>

                      {uniqueSources.length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
                          {uniqueSources.map((s, idx) => (
                            <a
                              key={idx}
                              href={`http://localhost:8000/documents/${encodeURIComponent(s.document)}`}
                              target="_blank"
                              rel="noreferrer"
                              className="doc-tag"
                              style={{ textDecoration: "none", cursor: "pointer" }}
                              title={`Cliquer pour consulter/télécharger ${s.document}`}
                            >
                               {s.document}{s.page && s.page !== "N/A" ? ` — page ${s.page}` : ""}
                            </a>
                          ))}
                        </div>
                      )}

                      {m.pieces_jointes && m.pieces_jointes.length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                          {m.pieces_jointes.map((p, idx) => (
                            <a
                              key={idx}
                              href={`http://localhost:8000/documents/${encodeURIComponent(p.fichier)}`}
                              target="_blank"
                              rel="noreferrer"
                              className="doc-tag"
                              style={{ textDecoration: "none", cursor: "pointer" }}
                              title={`Télécharger le formulaire ${p.nom_affiche}`}
                            >
                              📎 {p.nom_affiche}
                            </a>
                          ))}
                        </div>
                      )}

                      {!isUser && (
                        <div style={{ marginTop: 12, display: "flex", justifyContent: "flex-end" }}>
                          <button
                            onClick={() => handleCopy(m.content, i)}
                            style={{ display: "flex", alignItems: "center", gap: 6, background: "transparent", border: "none", color: "var(--ink-muted)", cursor: "pointer", fontSize: 13, padding: 0 }}
                          >
                            {copiedIndex === i ? (
                              <>
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="green" strokeWidth="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                                <span style={{ color: "green", fontWeight: 500 }}>Copié !</span>
                              </>
                            ) : (
                              <>
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                                Copier
                              </>
                            )}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
              {loading && (
                <div style={{ display: "flex", justifyContent: "flex-start", width: "100%" }}>
                  <div
                    style={{
                      padding: "12px 16px",
                      borderRadius: "18px 18px 18px 4px",
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      color: "var(--ink-muted)",
                      fontSize: 14,
                    }}
                  >
                    DocuRH recherche dans les documents…
                  </div>
                </div>
              )}
              <div ref={endRef} />
            </div>
          )}
        </div>

        <div style={{ padding: "0 24px 28px" }}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage();
            }}
            style={{
              maxWidth: 680,
              margin: "0 auto",
              display: "flex",
              alignItems: "center",
              gap: 10,
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-lg)",
              padding: "8px 8px 8px 18px",
              boxShadow: "var(--shadow)",
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Posez votre question RH…"
              style={{
                flex: 1,
                border: "none",
                outline: "none",
                background: "transparent",
                color: "var(--ink)",
                fontSize: 15,
              }}
            />
            <button
              type="submit"
              disabled={loading}
              style={{
                width: 38,
                height: 38,
                borderRadius: "50%",
                border: "none",
                background: "var(--primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                cursor: "pointer",
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </button>
          </form>
        </div>
      </main>

      {showLogoutModal && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ background: "var(--surface)", padding: 24, borderRadius: "var(--radius-lg)", width: 340, boxShadow: "var(--shadow)", textAlign: "center" }}>
            <h3 style={{ marginBottom: 20, color: "var(--ink)", fontSize: 18 }}>Souhaitez-vous vraiment vous déconnecter ?</h3>
            
            <div style={{ background: "var(--surface-alt)", padding: "12px 16px", borderRadius: "var(--radius-md)", display: "flex", alignItems: "center", gap: 14, marginBottom: 24, border: "1px solid var(--border)", textAlign: "left" }}>
              <div style={{ width: 44, height: 44, borderRadius: "50%", background: "var(--secondary)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 600, fontSize: 16 }}>
                {user ? user.nom.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2) : "?"}
              </div>
              <div style={{ overflow: "hidden" }}>
                <div style={{ fontWeight: 600, fontSize: 15, color: "var(--ink)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{user ? user.nom : "..."}</div>
                <div style={{ fontSize: 13, color: "var(--ink-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{user ? user.email : "..."}</div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <button 
                onClick={async () => {
                  await logoutRequest();
                  navigate("/connexion");
                }}
                style={{ background: "var(--ink)", color: "var(--bg)", border: "none", padding: "12px", borderRadius: "var(--radius-md)", fontWeight: 600, cursor: "pointer", fontSize: 14 }}
              >
                Se déconnecter
              </button>
              <button 
                onClick={() => setShowLogoutModal(false)}
                style={{ background: "transparent", color: "var(--ink)", border: "1px solid var(--border)", padding: "12px", borderRadius: "var(--radius-md)", fontWeight: 500, cursor: "pointer", fontSize: 14 }}
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      {conversationToDelete && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ background: "var(--surface)", padding: 24, borderRadius: "var(--radius-lg)", width: 340, boxShadow: "var(--shadow)", textAlign: "center" }}>
            <div style={{ width: 48, height: 48, borderRadius: "50%", background: "#fee2e2", color: "#dc2626", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            </div>
            <h3 style={{ marginBottom: 12, color: "var(--ink)", fontSize: 18 }}>Supprimer l'historique ?</h3>
            <p style={{ fontSize: 14, color: "var(--ink-muted)", marginBottom: 24, lineHeight: 1.4 }}>
              Cette action est irréversible. L'historique de cette conversation sera définitivement effacé.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <button 
                onClick={confirmDeleteConversation}
                style={{ background: "#dc2626", color: "#fff", border: "none", padding: "12px", borderRadius: "var(--radius-md)", fontWeight: 600, cursor: "pointer", fontSize: 14 }}
              >
                Oui, supprimer
              </button>
              <button 
                onClick={() => setConversationToDelete(null)}
                style={{ background: "transparent", color: "var(--ink)", border: "1px solid var(--border)", padding: "12px", borderRadius: "var(--radius-md)", fontWeight: 500, cursor: "pointer", fontSize: 14 }}
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function NavItem({ label, icon, active, onClick }) {
  const icons = {
    folder: <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />,
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 3" />
      </>
    ),
  };
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        width: "100%",
        padding: "9px 10px",
        border: "none",
        background: active ? "var(--surface-alt)" : "transparent",
        color: active ? "var(--primary)" : "var(--ink-muted)",
        fontSize: 14,
        borderRadius: "var(--radius-sm)",
        textAlign: "left",
        cursor: "pointer",
        fontWeight: active ? 600 : 400,
      }}
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        {icons[icon]}
      </svg>
      {label}
    </button>
  );
}
