import { useState, useRef, useCallback } from 'react';
import { FiSend } from 'react-icons/fi';
import VoiceRecorder from './VoiceRecorder';
import FileUpload from './FileUpload';

// ─── Constante ────────────────────────────────────────────────────────────────

const MAX_INPUT_LENGTH = 2000;

// ─── Composant ────────────────────────────────────────────────────────────────

/**
 * InputBar
 *
 * Barre de saisie du chatbot.
 * Intègre VoiceRecorder (dictée vocale) et FileUpload (fichiers joints).
 *
 * Gestion des fichiers :
 * - Les fichiers joints sont envoyés avec la question au endpoint /chat.
 * - Le backend les indexe dans le mini-RAG (ChromaDB, isolé par chat_id) et
 *   répond automatiquement à partir du fichier si pertinent. Pas de badge,
 *   pas de bascule manuelle — l'utilisateur pose simplement sa question.
 *
 * @param {function} onSend      Appelé avec un FormData contenant question + fichiers.
 * @param {boolean}  isLoading   Désactive les contrôles pendant la réponse de l'IA.
 * @param {string}   sessionId   Identifiant de session (chat_id) transmis au backend.
 *                                Doit être défini avant tout envoi — un upload de
 *                                fichier sans chat_id valide est rejeté par le backend.
 */
const InputBar = ({ onSend, isLoading = false, sessionId }) => {
  const [inputValue, setInputValue] = useState('');
  const [files,      setFiles]      = useState([]);
  const [fileError,  setFileError]  = useState(null);

  const textareaRef = useRef(null);

  // ── Transcript vocal → injection dans le champ texte ─────────────────────

  const handleTranscript = useCallback((transcribedText) => {
    setInputValue((prev) => {
      const separator = prev.trim() ? ' ' : '';
      return prev + separator + transcribedText;
    });
    textareaRef.current?.focus();
  }, []);

  // ── Gestion des fichiers sélectionnés ─────────────────────────────────────

  const handleFilesChange = useCallback((newFiles) => {
    setFiles(newFiles);
  }, []);

  // ── Envoi du message ──────────────────────────────────────────────────────

  const handleSend = useCallback(() => {
    const trimmed = inputValue.trim();
    if (!trimmed || isLoading) return;

    if (files.length > 0 && !sessionId) {
      setFileError(
        "Impossible de joindre un fichier : aucune conversation active. "
        + "Créez ou sélectionnez un chat avant d'envoyer un fichier."
      );
      return;
    }

    const formData = new FormData();
    formData.append('question',   trimmed);
    formData.append('session_id', sessionId ?? 'default');
    files.forEach((file) => formData.append('files', file));

    onSend(formData);

    setInputValue('');
    setFiles([]);
    setFileError(null);
  }, [inputValue, isLoading, sessionId, files, onSend]);

  // Envoi sur Entrée (sans Shift)
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  // ── Auto-resize du textarea ───────────────────────────────────────────────

  const handleChange = useCallback((e) => {
    const value = e.target.value;
    if (value.length > MAX_INPUT_LENGTH) return;

    setInputValue(value);

    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
    }
  }, []);

  // ── Dérivations ───────────────────────────────────────────────────────────

  const canSend = (inputValue.trim().length > 0 || files.length > 0) && !isLoading;

  // ── Rendu ─────────────────────────────────────────────────────────────────

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">

      {/* Previews + erreur fichier (au-dessus de la barre) */}
      {(files.length > 0 || fileError) && (
        <FileUpload
          files={files}
          onChange={handleFilesChange}
          error={fileError}
          onError={setFileError}
          disabled={isLoading}
          previewOnly
        />
      )}

      <div
        className={[
          'flex items-end gap-2 rounded-xl border transition-colors duration-150',
          'bg-gray-50 px-3 py-2 mt-1',
          isLoading
            ? 'border-gray-200'
            : 'border-gray-300 focus-within:border-[#29B6E8]',
        ].join(' ')}
      >
        {/* ── Bouton microphone ── */}
        <div className="flex-shrink-0 mb-0.5">
          <VoiceRecorder
            onTranscript={handleTranscript}
            disabled={isLoading}
          />
        </div>

        {/* ── Zone de saisie texte ── */}
        <textarea
          ref={textareaRef}
          value={inputValue}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          placeholder="Posez une question sur BeHave, ou joignez un document…"
          rows={1}
          maxLength={MAX_INPUT_LENGTH}
          aria-label="Message à envoyer"
          className={[
            'flex-1 resize-none bg-transparent text-sm text-gray-800',
            'placeholder-gray-400 outline-none leading-relaxed',
            'min-h-[36px] max-h-[160px]',
            isLoading ? 'cursor-not-allowed opacity-60' : '',
          ].join(' ')}
          style={{ overflowY: 'auto' }}
        />

        {/* ── Bouton paperclip ── */}
        <div className="relative flex-shrink-0 mb-0.5">
          <FileUpload
            files={files}
            onChange={handleFilesChange}
            error={fileError}
            onError={setFileError}
            disabled={isLoading}
            buttonOnly
          />
        </div>

        {/* ── Bouton envoi ── */}
        <button
          type="button"
          onClick={handleSend}
          disabled={!canSend}
          aria-label="Envoyer le message"
          title={canSend ? 'Envoyer' : 'Écrivez, dictez ou joignez un fichier'}
          className={[
            'flex-shrink-0 mb-0.5 flex items-center justify-center',
            'w-9 h-9 rounded-full transition-all duration-200',
            canSend
              ? 'bg-[#2D3A8C] hover:bg-[#29B6E8] cursor-pointer'
              : 'bg-gray-200 cursor-not-allowed',
          ].join(' ')}
        >
          <FiSend
            size={16}
            color={canSend ? '#FFFFFF' : '#9CA3AF'}
            aria-hidden="true"
          />
        </button>
      </div>

      {/* ── Compteur de caractères ── */}
      {inputValue.length > MAX_INPUT_LENGTH * 0.8 && (
        <p
          className={[
            'text-right text-xs mt-1 pr-1',
            inputValue.length >= MAX_INPUT_LENGTH
              ? 'text-red-500'
              : 'text-gray-400',
          ].join(' ')}
          aria-live="polite"
        >
          {inputValue.length} / {MAX_INPUT_LENGTH}
        </p>
      )}
    </div>
  );
};

export default InputBar;