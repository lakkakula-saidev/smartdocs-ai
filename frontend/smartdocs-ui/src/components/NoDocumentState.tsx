import React from "react";
import { UploadDocument } from "./UploadDocument";

interface NoDocumentStateProps {
  onDocumentUploaded: (documentId: string) => void;
}

/**
 * NoDocumentState
 *
 * Renders an inline onboarding panel inside the Chat page when
 * no document has yet been uploaded. Provides:
 * - Clear instructional messaging
 * - Inline upload capability (reuses existing UploadDocument component)
 * - Visual separation from the (disabled) ChatBox below
 */
export const NoDocumentState: React.FC<NoDocumentStateProps> = ({
  onDocumentUploaded
}) => {
  return (
    <div className="mb-6 rounded-xl border border-white/5 bg-neutral-900/60 backdrop-blur-sm p-6 space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight flex items-center gap-2">
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-brand-600/20 text-brand-300 text-xs font-bold ring-1 ring-inset ring-brand-500/30">
            1
          </span>
          Upload a Document to Begin
        </h2>
        <p className="text-xs text-neutral-400 leading-relaxed max-w-prose">
          To start a contextual conversation, upload a PDF. We will extract its
          text, build embeddings, and enable the chat interface. Once processing
          completes, you can ask detailed questions about the content.
        </p>
      </div>

      <UploadDocument
        onUploaded={(id) => {
          onDocumentUploaded(id);
        }}
      />

      <div className="text-[0.6rem] text-neutral-500 flex flex-wrap gap-3 pt-1">
        <span className="badge bg-neutral-800/50 ring-white/5">
          PDF Only (Demo)
        </span>
        <span className="badge bg-neutral-800/50 ring-white/5">
          Local Processing
        </span>
        <span className="badge bg-neutral-800/50 ring-white/5">
          Semantic Retrieval
        </span>
      </div>

      <p className="text-[0.6rem] text-neutral-500 italic">
        After upload, the input box becomes active and you can start asking
        questions. Your first answer may take a few seconds if dependencies are
        cold-loading.
      </p>
    </div>
  );
};
