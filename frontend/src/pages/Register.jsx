import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { register, isAuthenticated } from "../services/authApi";

function Register() {
  const navigate = useNavigate();

  const [username, setUsername]           = useState("");
  const [password, setPassword]           = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError]                 = useState("");
  const [isLoading, setIsLoading]         = useState(false);

  useEffect(() => {
    if (isAuthenticated()) {
      navigate("/", { replace: true });
    }
  }, [navigate]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }

    if (password.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }

    setIsLoading(true);

    try {
      await register(username, password);
      navigate("/login", { replace: true, state: { registered: true } });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F0F4FA] flex items-center justify-center p-4">
      <div className="w-full max-w-sm">

        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 bg-[#2D3A8C] rounded-xl flex items-center justify-center mb-3">
            <svg width="22" height="22" viewBox="0 0 40 40" fill="none">
              <path d="M8 32 L20 8 L32 32" fill="none" stroke="#29B6E8" strokeWidth="5" strokeLinecap="round"/>
              <path d="M8 32 L20 21 L32 32" fill="#29B6E8" opacity="0.6"/>
            </svg>
          </div>
          <h1 className="text-xl font-semibold text-[#2D3A8C]">Créer un compte</h1>
          <p className="text-sm text-gray-500 mt-1">Rejoignez BeHave Assistant</p>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700" htmlFor="username">
                Nom d'utilisateur
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Choisissez un username"
                required
                minLength={3}
                autoComplete="username"
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-[#29B6E8] focus:border-transparent
                           placeholder:text-gray-300 transition-all"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700" htmlFor="password">
                Mot de passe
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min. 8 caractères"
                required
                minLength={8}
                autoComplete="new-password"
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-[#29B6E8] focus:border-transparent
                           placeholder:text-gray-300 transition-all"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700" htmlFor="confirmPassword">
                Confirmer le mot de passe
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Répétez votre mot de passe"
                required
                autoComplete="new-password"
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-[#29B6E8] focus:border-transparent
                           placeholder:text-gray-300 transition-all"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="7" stroke="#ef4444" strokeWidth="1.5"/>
                  <path d="M8 5v4M8 11v.5" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || !username || !password || !confirmPassword}
              className="w-full bg-[#2D3A8C] text-white text-sm font-medium py-2.5 rounded-lg
                         hover:bg-[#233070] transition-colors
                         disabled:opacity-50 disabled:cursor-not-allowed
                         flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="3" strokeOpacity="0.3"/>
                    <path d="M12 2 A10 10 0 0 1 22 12" stroke="white" strokeWidth="3" strokeLinecap="round"/>
                  </svg>
                  Inscription...
                </>
              ) : "S'inscrire"}
            </button>

          </form>

          <p className="text-center text-sm text-gray-500 mt-4">
            Déjà un compte ?{" "}
            <Link to="/login" className="text-[#2D3A8C] font-medium hover:underline">
              Se connecter
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Register;