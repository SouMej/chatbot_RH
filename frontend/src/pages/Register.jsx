import { useState } from "react";
import { Link } from "react-router-dom";
import AuthLayout from "../components/AuthLayout.jsx";
import FormField from "../components/FormField.jsx";
import { registerRequest } from "../utils/api.js";

export default function Register() {
  const [nom, setNom] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await registerRequest(nom, email, password);
      setSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <AuthLayout
        title="Vérifiez votre boîte mail"
        subtitle={`Un lien de vérification a été envoyé à ${email}. Cliquez dessus pour activer votre compte.`}
        footer={
          <Link to="/connexion" style={{ color: "var(--secondary)", fontWeight: 500 }}>
            Retour à la connexion
          </Link>
        }
      >
        <p style={{ fontSize: 13, color: "var(--ink-faint)" }}>
          En développement local, le lien apparaît aussi dans les logs du serveur FastAPI
          (console où tourne <code>uvicorn</code>).
        </p>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Créer un compte"
      subtitle="Rejoignez DocuRH pour accéder à l'assistant RH."
      footer={
        <>
          Déjà un compte ?{" "}
          <Link to="/connexion" style={{ color: "var(--secondary)", fontWeight: 500 }}>
            Se connecter
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <FormField
          label="Nom complet"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Sonia Mejri"
        />
        <FormField
          label="Adresse e-mail"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="prenom.nom@entreprise.tn"
        />
        <FormField
          label="Mot de passe"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="8 caractères minimum"
        />

        {error && (
          <p style={{ color: "var(--danger)", fontSize: 13, marginBottom: 16 }}>{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: "12px 0",
            background: "var(--primary)",
            color: "#fff",
            border: "none",
            borderRadius: "var(--radius-sm)",
            fontSize: 15,
            fontWeight: 600,
            marginTop: 8,
          }}
        >
          {loading ? "Création..." : "Créer mon compte"}
        </button>
      </form>
    </AuthLayout>
  );
}
