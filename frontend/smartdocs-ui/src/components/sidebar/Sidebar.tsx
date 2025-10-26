import { useEffect, useState } from "react";
import { SidebarItem } from "./SidebarItem";
import { fetchDocuments, type DocumentInfo } from "../../api/api";
import { useChatStore } from "../../store/chatStore";

interface SidebarProps {
  className?: string;
  onDocumentSelect?: (documentId: string) => void;
}

export function Sidebar({ className = "", onDocumentSelect }: SidebarProps) {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const currentDocumentId = useChatStore((state) => state.currentDocumentId);

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const docs = await fetchDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to load documents:", err);
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  };

  const handleDocumentSelect = (documentId: string) => {
    onDocumentSelect?.(documentId);
  };

  // Convert DocumentInfo to format expected by SidebarItem
  const documentItems = documents.map((doc) => ({
    id: doc.document_id,
    displayName:
      doc.display_name ||
      doc.filename ||
      `Document ${doc.document_id.slice(0, 8)}...`,
    filename: doc.filename,
    created_at: doc.created_at
  }));

  return (
    <div
      className={`flex flex-col h-full bg-white border-r border-gray-200 ${className}`}
    >
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Documents</h2>
          <button
            onClick={loadDocuments}
            className="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
            title="Refresh documents"
          >
            🔄
          </button>
        </div>
        <p className="text-sm text-gray-500 mt-1">
          {documents.length} document{documents.length !== 1 ? "s" : ""}
        </p>
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="text-sm text-gray-500">Loading documents...</div>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={loadDocuments}
              className="mt-2 text-xs text-red-600 hover:text-red-800 underline"
            >
              Try again
            </button>
          </div>
        )}

        {!loading && !error && documents.length === 0 && (
          <div className="text-center py-8">
            <p className="text-sm text-gray-500 mb-2">No documents yet</p>
            <p className="text-xs text-gray-400">
              Upload a document to get started
            </p>
          </div>
        )}

        {!loading &&
          !error &&
          documentItems.map((doc) => (
            <SidebarItem
              key={doc.id}
              document={doc}
              isActive={doc.id === currentDocumentId}
              onClick={() => handleDocumentSelect(doc.id)}
            />
          ))}
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 p-4">
        <div className="text-xs text-gray-400 text-center">SmartDocs AI</div>
      </div>
    </div>
  );
}
