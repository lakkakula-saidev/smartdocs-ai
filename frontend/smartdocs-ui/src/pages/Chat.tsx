import { useLocation, Link } from "react-router-dom";
import { useEffect } from "react";
import { ChatBox } from "../components/ChatBox";
import { useChatStore } from "../store/chatStore";
import { UploadDocument } from "../components/UploadDocument";

/**
 * Chat page
 * - Gated by document upload: hide ChatBox until a document is active.
 * - Document context is passed from Home via router state { docId } OR uploaded here.
 */
interface LocationState {
  docId?: string | null;
}

export function Chat() {
  const location = useLocation();
  const state = (location.state as LocationState) || {};
  const currentDocumentId = useChatStore((s) => s.currentDocumentId);
  const setDocumentId = useChatStore((s) => s.setDocumentId);

  // Sync incoming routed docId into global store (clears prior chat when changed)
  useEffect(() => {
    if (state.docId) {
      setDocumentId(state.docId);
    }
  }, [state.docId, setDocumentId]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">Chat</h1>
        <Link to="/" className="text-sm text-brand-400 hover:text-brand-300">
          ← Back
        </Link>
      </div>

      {/* No document uploaded yet: show upload component (its internal heading already includes the text) */}
      {!currentDocumentId ? (
        <div className="mb-6">
          <UploadDocument
            onUploaded={(id) => {
              setDocumentId(id);
            }}
          />
        </div>
      ) : (
        <>
          <div className="mb-3">
            <p className="text-[0.65rem] uppercase tracking-wide text-neutral-500">
              Document:{" "}
              <code className="text-neutral-300">{currentDocumentId}</code>
            </p>
          </div>
          <div className="flex-1 min-h-0">
            <ChatBox documentId={currentDocumentId} />
          </div>
        </>
      )}
    </div>
  );
}
