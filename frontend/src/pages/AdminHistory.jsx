import { useState, useEffect, useCallback } from "react";
import AdminSidebar from "../components/admin/AdminSidebar";
import { fetchHistory } from "../services/adminApi";

const PAGE_SIZE = 20;

function formatDate(isoDate) {
  return new Date(isoDate).toLocaleString("fr-FR", {
    day:    "2-digit",
    month:  "short",
    year:   "numeric",
    hour:   "2-digit",
    minute: "2-digit",
  });
}

function SkeletonRow() {
  return (
    <tr className="border-b border-gray-100">
      {[60, 200, 300, 200, 100].map((w, i) => (
        <td key={i} className="px-4 py-4">
          <div className="h-3 bg-gray-100 rounded animate-pulse" style={{ width: w }} />
        </td>
      ))}
    </tr>
  );
}

function EmptyState() {
  return (
    <tr>
      <td colSpan={5}>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="w-12 h-12 bg-[#E8F0FB] rounded-xl flex items-center justify-center mb-3">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2D3A8C" strokeWidth="1.5">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-700">Aucune conversation enregistrée</p>
          <p className="text-xs text-gray-400 mt-1">Les conversations apparaîtront ici après les premières questions</p>
        </div>
      </td>
    </tr>
  );
}

function AdminHistory() {
  const [conversations, setConversations] = useState([]);
  const [total, setTotal]                 = useState(0);
  const [skip, setSkip]                   = useState(0);
  const [isLoading, setIsLoading]         = useState(true);
  const [error, setError]                 = useState("");
  const [expanded, setExpanded]           = useState(null);

  const totalPages  = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(skip / PAGE_SIZE) + 1;

  const loadHistory = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await fetchHistory(skip, PAGE_SIZE);
      setConversations(data.conversations);
      setTotal(data.total);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [skip]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  function handlePrev() {
    setSkip((prev) => Math.max(0, prev - PAGE_SIZE));
  }

  function handleNext() {
    setSkip((prev) => prev + PAGE_SIZE);
  }

  function toggleExpand(id) {
    setExpanded((prev) => (prev === id ? null : id));
  }

  return (
    <div className="min-h-screen bg-[#F0F4FA] flex">

      <AdminSidebar activePage="history" />

      <main className="flex-1 flex flex-col min-w-0">

        <header className="bg-white border-b-4 border-[#29B6E8] px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Historique des conversations</h1>
              <p className="text-xs text-gray-400 mt-1">Toutes les conversations — users et admin</p>
            </div>
            <div className="bg-[#eef2ff] rounded-xl px-6 py-3 text-center">
              <div className="text-2xl font-bold text-[#2D3A8C]">{total}</div>
              <div className="text-xs text-[#2D3A8C]/70 uppercase tracking-wide">échanges</div>
            </div>
          </div>
        </header>

        <div className="flex-1 p-6 flex flex-col gap-4 overflow-auto">

          {error && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-2.5">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="7" stroke="#ef4444" strokeWidth="1.5"/>
                <path d="M8 5v4M8 11v.5" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full table-fixed">
              <colgroup>
                <col style={{ width: "10%" }} />
                <col style={{ width: "25%" }} />
                <col style={{ width: "30%" }} />
                <col style={{ width: "15%" }} />
                <col style={{ width: "20%" }} />
              </colgroup>

              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  {["User", "Question", "Réponse", "Module", "Date"].map((label) => (
                    <th
                      key={label}
                      className="px-4 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"
                    >
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {isLoading ? (
                  Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)
                ) : conversations.length === 0 ? (
                  <EmptyState />
                ) : (
                  conversations.map((conv, index) => {
                    const isExpanded = expanded === conv.id;
                    return (
                      <tr
                        key={conv.id}
                        onClick={() => toggleExpand(conv.id)}
                        className={`border-b border-gray-100 cursor-pointer transition-colors
                          ${index % 2 === 1 ? "bg-[#fafbfc]" : "bg-white"}
                          ${isExpanded ? "bg-[#eef2ff]" : "hover:bg-gray-50"}`}
                      >
                        <td className="px-4 py-4">
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-full bg-[#29B6E8] flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
                              {conv.username.charAt(0).toUpperCase()}
                            </div>
                            <span className="text-xs font-medium text-gray-700 truncate">
                              {conv.username}
                            </span>
                          </div>
                        </td>

                        <td className="px-4 py-4">
                          <p className={`text-sm text-gray-800 ${isExpanded ? "" : "truncate"}`}>
                            {conv.question}
                          </p>
                        </td>

                        <td className="px-4 py-4">
                          <p className={`text-sm text-gray-600 ${isExpanded ? "" : "line-clamp-2"}`}>
                            {conv.answer}
                          </p>
                        </td>

                        <td className="px-4 py-4">
                          {conv.module && (
                            <span className="text-xs bg-[#eef2ff] text-[#2D3A8C] px-2 py-1 rounded-full font-medium">
                              {conv.module}
                            </span>
                          )}
                        </td>

                        <td className="px-4 py-4 text-xs text-gray-400">
                          {formatDate(conv.created_at)}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-1">
              <span className="text-xs text-gray-500">
                Page {currentPage} sur {totalPages} — {total} échanges au total
              </span>
              <div className="flex gap-2">
                <button
                  onClick={handlePrev}
                  disabled={skip === 0}
                  className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-200
                             rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  ← Précédent
                </button>
                <button
                  onClick={handleNext}
                  disabled={skip + PAGE_SIZE >= total}
                  className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-200
                             rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Suivant →
                </button>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}

export default AdminHistory;