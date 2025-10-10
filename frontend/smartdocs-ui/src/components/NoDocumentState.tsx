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
  // Simplified: only keep the inline upload control (remove instructional wrapper & badges)
  return (
    <div className="mb-4">
      <UploadDocument
        onUploaded={(id) => {
          onDocumentUploaded(id);
        }}
      />
    </div>
  );
};
