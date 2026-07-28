import { Navigate } from "react-router-dom";
import { isLoggedIn } from "../utils/api.js";

export default function ProtectedRoute({ children }) {
  if (!isLoggedIn()) {
    return <Navigate to="/connexion" replace />;
  }
  return children;
}
