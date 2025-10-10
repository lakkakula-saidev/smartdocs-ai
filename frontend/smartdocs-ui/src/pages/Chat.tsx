import { useLocation, Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { ChatBox } from "../components/ChatBox";
import { NoDocumentState } from "../components/NoDocumentState";

interface LocationState {
  docId?: string | null;
}

export function Chat() {
  const location = useLocation();
  const state = (location.state as LocationState) || {};
  const [documentId, setDocumentId] = useState<string | null>(state.docId || null);

  useEffect(() => {
    if (state.docId) setDocumentId(state.docId);
  }, [state.docId]);

  return (
    <div className="flex flex-col h-full max-h-[calc(100vh-5rem)]">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">Chat</h1>
        <Link to="/" className="text-sm text-brand-400 hover:text-brand-300">← Back</Link>
      </div>

      {!documentId && (
        <NoDocumentState onDocumentUploaded={setDocumentId} />
      )}

      {documentId && (
        <div className="mb-4">
          <p className="text-xs text-neutral-500">
            Document context: <code className="text-neutral-300">{documentId}</code>
          </p>
        </div>
      )}

      <div className="flex-1 min-h-0">
        <ChatBox documentId={documentId} />
      </div>
    </div>
  );
}
