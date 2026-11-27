import { Link } from "react-router-dom";
import ThemeToggle from "../components/ThemeToggle.jsx";

export default function Home() {
  return (
    <div style={{ minHeight: "100%", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "24px 48px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <img src="/logo.png" alt="ChatbotRH" style={{ width: 32, height: 32, borderRadius: 8, objectFit: "contain" }} />
          <span style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 18 }}>
            ChatbotRH
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <ThemeToggle />
          <Link
            to="/connexion"
            style={{ fontSize: 14, color: "var(--ink-muted)", fontWeight: 500 }}
          >
            Connexion
          </Link>
          <Link
            to="/inscription"
            style={{
              fontSize: 14,
              fontWeight: 500,
              color: "#fff",
              background: "var(--primary)",
              padding: "10px 20px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            Créer un compte
          </Link>
        </div>
      </header>

      <main style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", padding: "80px 24px" }}>
        <h1
          style={{
            fontSize: 48,
            maxWidth: 720,
            textAlign: "center",
            lineHeight: 1.15,
            color: "var(--ink)",
          }}
        >
          Vos questions RH, répondues avec la source à l'appui.
        </h1>

        <p
          style={{
            marginTop: 24,
            maxWidth: 560,
            textAlign: "center",
            fontSize: 17,
            color: "var(--ink-muted)",
          }}
        >
          ChatbotRH est l'assistant interne qui répond aux questions de congés, d'horaires et de
          procédures administratives — en citant toujours le document officiel utilisé, et en
          fonctionnant entièrement en local pour protéger vos données.
        </p>

        <div style={{ display: "flex", gap: 16, marginTop: 40 }}>
          <Link
            to="/inscription"
            style={{
              fontSize: 15,
              fontWeight: 600,
              color: "#fff",
              background: "var(--primary)",
              padding: "14px 28px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            Commencer
          </Link>
          <Link
            to="/connexion"
            style={{
              fontSize: 15,
              fontWeight: 600,
              color: "var(--ink)",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              padding: "14px 28px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            J'ai déjà un compte
          </Link>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
            gap: 20,
            marginTop: 96,
            maxWidth: 900,
            width: "100%",
          }}
        >
          {[
            {
              titre: "Réponses sourcées",
              texte: "Chaque réponse indique le document et la page exacts d'où elle provient.",
            },
            {
              titre: "100 % local",
              texte: "Aucune donnée RH ne quitte l'infrastructure de l'entreprise.",
            },
            {
              titre: "Disponible 24h/24",
              texte: "Posez vos questions RH à tout moment, sans attendre le service RH.",
            },
          ].map((f) => (
            <div
              key={f.titre}
              className="corner-fold"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-md)",
                padding: 24,
              }}
            >
              <h3 style={{ fontSize: 16, marginBottom: 8 }}>{f.titre}</h3>
              <p style={{ fontSize: 14, color: "var(--ink-muted)" }}>{f.texte}</p>
            </div>
          ))}
        </div>
      </main>

      <footer
        style={{
          textAlign: "center",
          padding: 24,
          fontSize: 13,
          color: "var(--ink-faint)",
          borderTop: "1px solid var(--border)",
        }}
      >
        ChatbotRH — prototype interne, projet de stage
      </footer>
    </div>
  );
}
