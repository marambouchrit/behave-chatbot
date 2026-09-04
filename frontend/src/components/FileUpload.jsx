import { useRef, useCallback } from 'react';
import { FiPaperclip, FiX, FiFile } from 'react-icons/fi';

// ─── Constantes ───────────────────────────────────────────────────────────────

const MAX_FILES      = 3;
const MAX_SIZE_BYTES = 5 * 1024 * 1024; 

const ACCEPTED_MIME_SET= new Set([
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]);

const INPUT_ACCEPT = [
  '.pdf,.docx',
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
].join(',');

// ─── Helpers ──────────────────────────────────────────────────────────────────

const _formatSize = (bytes) => {
  if (bytes < 1024)        return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
};

const _validate = (newFiles, existingFiles) => {
  if (existingFiles.length + newFiles.length > MAX_FILES) {
    return `Maximum ${MAX_FILES} fichiers par message.`;
  }
  for (const file of newFiles) {
    if (!ACCEPTED_MIME_SET.has(file.type)) {
      return `Type non supporté : ${file.name}. Acceptés : PDF, DOCX.`;
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `${file.name} dépasse 5 Mo.`;
    }
  }
  return null;
};

// ─── Sous-composant : preview d'un fichier ────────────────────────────────────

const _FilePreview = ({ file, onRemove }) => (
  <div className="relative flex items-center gap-2 bg-white border
                  border-gray-200 rounded-lg px-2 py-1.5 max-w-[180px]">

    <div className="w-8 h-8 rounded bg-blue-50 flex items-center
                    justify-center flex-shrink-0">
      <FiFile size={16} color="#2D3A8C" aria-hidden="true" />
    </div>

    <div className="flex flex-col min-w-0">
      <span className="text-xs text-gray-700 font-medium truncate leading-tight">
        {file.name}
      </span>
      <span className="text-xs text-gray-400 leading-tight">
        {_formatSize(file.size)}
      </span>
    </div>

    <button
      type="button"
      onClick={() => onRemove(file.name)}
      aria-label={`Retirer ${file.name}`}
      className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full
                 bg-gray-400 hover:bg-red-500 flex items-center justify-center
                 transition-colors duration-150"
    >
      <FiX size={10} color="white" aria-hidden="true" />
    </button>
  </div>
);

// ─── Composant principal ──────────────────────────────────────────────────────

const FileUpload = ({
  files       = [],
  onChange,
  error       = null,
  onError,
  disabled    = false,
  buttonOnly  = false,
  previewOnly = false,
}) => {
  const inputRef = useRef(null);

  // ── Sélection ────────────────────────────────────────────────────────────

  const handleButtonClick = useCallback(() => {
    if (disabled || files.length >= MAX_FILES) return;
    inputRef.current?.click();
  }, [disabled, files.length]);

  const handleFileChange = useCallback((e) => {
    const selected = Array.from(e.target.files || []);
    if (!selected.length) return;

    const errorMsg = _validate(selected, files);
    if (errorMsg) {
      onError(errorMsg);
      e.target.value = '';
      return;
    }

    onError(null);
    onChange([...files, ...selected]);
    e.target.value = '';
  }, [files, onChange, onError]);

  // ── Suppression ───────────────────────────────────────────────────────────

  const handleRemove = useCallback((filename) => {
    onChange(files.filter((f) => f.name !== filename));
    onError(null);
  }, [files, onChange, onError]);

  // ── Dérivations ───────────────────────────────────────────────────────────

  const canAddMore = files.length < MAX_FILES;
  const isDisabled = disabled || !canAddMore;

  const buttonTitle = isDisabled
    ? (disabled ? 'Envoi en cours…' : `Maximum ${MAX_FILES} fichiers atteint`)
    : 'Joindre un PDF ou un DOCX';

  // ── Rendu : mode preview ──────────────────────────────────────────────────

  if (previewOnly) {
    return (
      <div className="flex flex-col gap-1.5 mb-1">
        {files.length > 0 && (
          <div className="flex flex-wrap gap-2 px-1">
            {files.map((file) => (
              <_FilePreview
                key={file.name}
                file={file}
                onRemove={handleRemove}
              />
            ))}
          </div>
        )}
        {error && (
          <p role="alert" className="text-xs text-red-500 px-1" aria-live="polite">
            {error}
          </p>
        )}
      </div>
    );
  }

  // ── Rendu : mode bouton ───────────────────────────────────────────────────

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={INPUT_ACCEPT}
        onChange={handleFileChange}
        className="hidden"
        aria-hidden="true"
        tabIndex={-1}
      />

      <button
        type="button"
        onClick={handleButtonClick}
        disabled={isDisabled}
        aria-label="Joindre un fichier"
        title={buttonTitle}
        className={[
          'relative flex items-center justify-center',
          'w-9 h-9 rounded-full transition-all duration-200',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-[#29B6E8]',
          files.length > 0 ? 'text-[#2D3A8C]' : 'text-gray-400',
          isDisabled
            ? 'opacity-40 cursor-not-allowed'
            : 'hover:bg-gray-100 cursor-pointer',
        ].join(' ')}
      >
        <FiPaperclip size={18} aria-hidden="true" />

        {/* Badge nombre de fichiers */}
        {files.length > 0 && (
          <span
            className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full
                       bg-[#2D3A8C] text-white text-[10px] font-medium
                       flex items-center justify-center"
            aria-label={`${files.length} fichier(s) joint(s)`}
          >
            {files.length}
          </span>
        )}
      </button>
    </>
  );
};

export default FileUpload;