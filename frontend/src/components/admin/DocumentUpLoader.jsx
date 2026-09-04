import { useState, useRef, useCallback } from "react";
import { uploadDocument } from "../../services/adminApi";

const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"];
const MAX_SIZE_MB         = 100;
const MAX_SIZE_BYTES      = MAX_SIZE_MB * 1024 * 1024;

function validateFile(file) {
  const ext = "." + file.name.split(".").pop().toLowerCase();

  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `Format non supporté. Formats acceptés : ${ALLOWED_EXTENSIONS.join(", ")}`;
  }
  if (file.size > MAX_SIZE_BYTES) {
    return `Fichier trop volumineux. Taille maximale : ${MAX_SIZE_MB} Mo`;
  }
  return null;
}

function DocumentUploader({ onUploadSuccess }) {
  const fileInputRef = useRef(null);

  const [isDragOver, setIsDragOver]   = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress]       = useState(0);
  const [error, setError]             = useState("");
  const [successMsg, setSuccessMsg]   = useState("");

  const processFile = useCallback(async (file) => {
    setError("");
    setSuccessMsg("");

    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsUploading(true);
    setProgress(0);

    try {
      const result = await uploadDocument(file, (percent) => setProgress(percent));
      setSuccessMsg(`"${result.filename}" indexé avec succès — ${result.chunks_indexed} chunks créés.`);
      onUploadSuccess(result);
      setTimeout(() => {
        setProgress(0);
        setSuccessMsg("");
      }, 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }, [onUploadSuccess]);

  function handleDrop(e) {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }

  function handleFileChange(e) {
    const file = e.target.files[0];
    if (file) processFile(file);
  }

  return (
    <div className="flex flex-col gap-3">

      <div
        onClick={() => !isUploading && fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-xl p-8 text-center transition-all
          ${isUploading ? "cursor-not-allowed border-gray-200 bg-gray-50" : "cursor-pointer"}
          ${isDragOver
            ? "border-[#29B6E8] bg-[#E8F7FD]"
            : "border-gray-200 hover:border-[#29B6E8] hover:bg-[#F5FBFE]"}
        `}
      >
        <div className={`w-12 h-12 rounded-xl mx-auto mb-3 flex items-center justify-center transition-colors
          ${isDragOver ? "bg-[#29B6E8]" : "bg-[#E8F0FB]"}`}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
            stroke={isDragOver ? "white" : "#2D3A8C"} strokeWidth="1.5">
            <polyline points="16 16 12 12 8 16"/>
            <line x1="12" y1="12" x2="12" y2="21"/>
            <path d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3"/>
          </svg>
        </div>

        <p className="text-sm font-medium text-gray-700">
          {isDragOver ? "Déposez le fichier ici" : "Glissez un fichier ou cliquez pour parcourir"}
        </p>
        <p className="text-xs text-gray-400 mt-1">PDF,  et TXT— max {MAX_SIZE_MB} Mo</p>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleFileChange}
          className="hidden"
          aria-label="Sélectionner un fichier à uploader"
        />
      </div>

      {isUploading && (
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-500">Upload en cours...</span>
            <span className="text-xs font-medium text-[#2D3A8C]">{progress}%</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#29B6E8] rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {successMsg && (
        <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-lg px-3 py-2.5">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="7" stroke="#16a34a" strokeWidth="1.5"/>
            <polyline points="5 8 7 10 11 6" stroke="#16a34a" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <p className="text-sm text-green-700">{successMsg}</p>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="7" stroke="#ef4444" strokeWidth="1.5"/>
            <path d="M8 5v4M8 11v.5" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

    </div>
  );
}

export default DocumentUploader;