import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import AuthLayout from "../components/AuthLayout.jsx";
import { verifyEmailRequest } from "../utils/api.js";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState("chargement"); // chargement | succes | erreur
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("erreur");
      setMessage("Lien de vérification manquant ou invalide.");
      return;
    }

    verifyEmailRequest(token)
      .then((data) => {
        setStatus("succes");
        setMessage(data.message);
      })
      .catch((err) => {
        setStatus("erreur");
        setMessage(err.message);
      });
  }, [token]);

  const titres = {
    chargement: "Vérification en cours…",
    succes: "Email vérifié",
    erreur: "Lien invalide",
  };

  return (
    <AuthLayout
      title={titres[status]}
      subtitle={message || "Un instant, nous vérifions votre lien."}
      footer={
        status !== "chargement" && (
          <Link to="/connexion" style={{ color: "var(--secondary)", fontWeight: 500 }}>
            Aller à la page de connexion
          </Link>
        )
      }
    >
      {status === "chargement" && (
        <div style={{ display: "flex", justifyContent: "center", padding: "12px 0" }}>
          <div
            style={{
              width: 24,
              height: 24,
              border: "3px solid var(--border)",
              borderTopColor: "var(--primary)",
              borderRadius: "50%",
              animation: "spin 0.8s linear infinite",
            }}
          />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}
    </AuthLayout>
  );
}
