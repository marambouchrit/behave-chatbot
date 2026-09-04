import { useNavigate } from "react-router-dom";
import { getUser, logout } from "../../services/authApi";

const NAV_ITEMS = [
  {
    key:   "chat",
    label: "Chatbot",
    path:  "/admin/chat",
    icon:  (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
      </svg>
    ),
  },
  {
  key:   "history",
  label: "Historique",
  path:  "/admin/history",
  icon:  (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
    </svg>
  ),
  },
  {
    key:   "documents",
    label: "Documents",
    path:  "/admin/dashboard",
    icon:  (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
    ),
  },
];

function AdminSidebar({ activePage }) {
  const navigate = useNavigate();
  const user     = getUser();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <aside className="w-56 bg-[#2D3A8C] flex flex-col flex-shrink-0">

      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-4 border-b border-white/10">
        <div className="w-7 h-7 bg-[#29B6E8] rounded-md flex items-center justify-center flex-shrink-0">
          <svg width="14" height="14" viewBox="0 0 40 40" fill="none">
            <path d="M8 32 L20 8 L32 32" fill="none" stroke="white" strokeWidth="5" strokeLinecap="round"/>
            <path d="M8 32 L20 21 L32 32" fill="white" opacity="0.6"/>
          </svg>
        </div>
        <div>
          <div className="text-white text-sm font-semibold leading-none">BeHave</div>
          <div className="text-white/40 text-[10px] tracking-widest mt-0.5">ADMIN</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 flex flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive = activePage === item.key;
          return (
            <button
              key={item.key}
              onClick={() => navigate(item.path)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left transition-colors
                ${isActive
                  ? "bg-white/10 border-l-2 border-[#29B6E8]"
                  : "hover:bg-white/10 border-l-2 border-transparent"
                }`}
            >
              <span className={isActive ? "text-[#29B6E8]" : "text-white/50"}>
                {item.icon}
              </span>
              <span className={`text-sm ${isActive ? "text-white" : "text-white/50"}`}>
                {item.label}
              </span>
            </button>
          );
        })}
      </nav>

      {/* User + logout */}
      <div className="px-4 py-3 border-t border-white/10 flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-[#29B6E8] flex items-center justify-center text-xs font-semibold text-white flex-shrink-0">
          {user?.username?.charAt(0).toUpperCase() || "A"}
        </div>
        <span className="text-white/80 text-sm flex-1 truncate">{user?.username}</span>
        <button
          onClick={handleLogout}
          className="text-white/40 hover:text-white transition-colors"
          aria-label="Se déconnecter"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
    </aside>
  );
}

export default AdminSidebar;