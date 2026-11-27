import { Link } from "react-router-dom";
import ThemeToggle from "./ThemeToggle.jsx";

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div
      style={{
        minHeight: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        position: "relative",
      }}
    >
      <div style={{ position: "absolute", top: 24, right: 24 }}>
        <ThemeToggle />
      </div>

      <Link
        to="/"
        style={{
          position: "absolute",
          top: 28,
          left: 32,
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontFamily: "var(--font-display)",
          fontWeight: 600,
          fontSize: 16,
        }}
      >
        <img src="/logo.png" alt="ChatbotRH" style={{ width: 24, height: 24, borderRadius: 6, objectFit: "contain" }} />
        ChatbotRH
      </Link>

      <div
        className="corner-fold"
        style={{
          width: "100%",
          maxWidth: 400,
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)",
          padding: "40px 36px",
          boxShadow: "var(--shadow)",
        }}
      >
        <h1 style={{ fontSize: 24, marginBottom: 8 }}>{title}</h1>
        <p style={{ fontSize: 14, color: "var(--ink-muted)", marginBottom: 28 }}>{subtitle}</p>

        {children}

        {footer && (
          <p style={{ fontSize: 14, color: "var(--ink-muted)", marginTop: 24, textAlign: "center" }}>
            {footer}
          </p>
        )}
      </div>
    </div>
  );
}
