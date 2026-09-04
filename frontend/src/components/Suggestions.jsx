const SUGGESTIONS = [
  "Créer un client dans BeHave Master Data ?",
  "Quels modèles IA utilise BeHave Predictive ?",
  "Comment analyser les conflits SoD dans BeHave Access ?",
  "Comment extraire les tables SAP pour BeHave ?",
];

function Suggestions({ onSelect, isLoading }) {
  return (
    <div className="px-4 pt-3 pb-2 flex-shrink-0">
      <p className="text-xs text-[#6B7A99] font-medium uppercase tracking-wide mb-2">
        Suggestions
      </p>
      <div className="flex gap-2 flex-wrap">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            onClick={() => !isLoading && onSelect(s)}
            disabled={isLoading}
            className="bg-white border border-[#B8C8E0] rounded-full px-3 py-1.5 text-xs text-[#2D3A8C] hover:bg-[#E8F0FB] hover:border-[#29B6E8] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

export default Suggestions;