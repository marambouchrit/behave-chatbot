import { FiRefreshCw, FiLogOut } from "react-icons/fi";
import { BsCircleFill } from "react-icons/bs";
import { useNavigate } from "react-router-dom";
import { getUser, logout, isAdmin } from "../services/authApi";

function Header({ onReset, isOnline }) {
  const navigate = useNavigate();
  const user     = getUser();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="bg-[#2D3A8C] px-5 py-4 flex items-center justify-between flex-shrink-0">
      <div className="flex items-center gap-3">
        <svg width="28" height="28" viewBox="0 0 40 40" fill="none">
          <path d="M8 32 L20 8 L32 32" fill="none" stroke="#29B6E8"
            strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M8 32 L20 21 L32 32" fill="#29B6E8" opacity="0.35"/>
        </svg>
        <span className="text-white text-base font-semibold">
          BeHave Assistant
        </span>
      </div>

      <div className="flex items-center gap-4">

        <div className="flex items-center gap-1.5">
          <BsCircleFill className={`text-xs ${isOnline ? "text-green-400" : "text-red-400"}`} />
          <span className="text-white/75 text-xs">
            {isOnline ? "En ligne" : "Hors ligne"}
          </span>
        </div>

        {user && (
          <div className="flex items-center gap-1.5">
            <div className="w-6 h-6 rounded-full bg-[#29B6E8] flex items-center justify-center text-white text-xs font-semibold">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <span className="text-white/75 text-xs">{user.username}</span>
          </div>
        )}

        <button
          onClick={onReset}
          className="flex items-center gap-1.5 text-white/70 hover:text-white text-xs px-2 py-1 rounded hover:bg-white/10 transition-colors"
        >
          <FiRefreshCw size={13} />
          Réinitialiser
        </button>

        {/* Logout — uniquement pour les users, l'admin utilise la sidebar */}
        {!isAdmin() && (
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-white/70 hover:text-white text-xs px-2 py-1 rounded hover:bg-white/10 transition-colors"
            aria-label="Se déconnecter"
          >
            <FiLogOut size={13} />
            Déconnexion
          </button>
        )}

      </div>
    </div>
  );
}

export default Header;