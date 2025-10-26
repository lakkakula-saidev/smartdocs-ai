import { useLocation, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { ChatBox } from "../components/ChatBox";
import { useChatStore } from "../store/chatStore";
import { UploadDocument } from "../components/UploadDocument";
import { Sidebar } from "../components/sidebar/Sidebar";
import { renameDocument } from "../api/api";

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
  const currentDocument = useChatStore((s) => s.currentDocument);
  const currentDocumentId = useChatStore((s) => s.currentDocumentId);
  const setDocumentId = useChatStore((s) => s.setDocumentId);
  const updateDocumentName = useChatStore((s) => s.updateDocumentName);

  const [isRenaming, setIsRenaming] = useState(false);
  const [renameError, setRenameError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Sync incoming routed docId into global store (clears prior chat when changed)
  useEffect(() => {
    if (state.docId) {
      setDocumentId(state.docId);
    }
  }, [state.docId, setDocumentId]);

  const handleRename = async (newName: string) => {
    if (!currentDocumentId || !currentDocument) return;

    setIsRenaming(true);
    setRenameError(null);

    try {
      await renameDocument(currentDocumentId, newName);
      updateDocumentName(currentDocumentId, newName);
    } catch (error) {
      console.error("Failed to rename document:", error);
      setRenameError(
        error instanceof Error ? error.message : "Failed to rename document"
      );
      // Optionally show error to user - for now we'll just log it
    } finally {
      setIsRenaming(false);
    }
  };

  const handleDocumentSelect = (documentId: string) => {
    setDocumentId(documentId);
    // Close sidebar on mobile after selection
    setIsSidebarOpen(false);
  };

  return (
    <div className="flex h-96 md:h-[500px] lg:h-[600px] overflow-hidden bg-neutral-900/20 rounded-lg border border-white/5">
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={`
        w-80 flex-shrink-0 z-50
        md:relative md:translate-x-0
        ${
          isSidebarOpen
            ? "fixed inset-y-0 left-0 translate-x-0"
            : "fixed -translate-x-full"
        }
        transition-transform duration-300 ease-in-out
        md:transition-none
      `}
      >
        <Sidebar onDocumentSelect={handleDocumentSelect} />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex-shrink-0 px-4 py-4 border-b border-gray-200 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 md:space-x-4 min-w-0 flex-1">
              {/* Mobile Menu Button */}
              <button
                onClick={() => setIsSidebarOpen(true)}
                className="p-2 text-gray-600 hover:text-gray-900 md:hidden"
                title="Open sidebar"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              </button>

              <div className="min-w-0 flex-1">
                <div className="flex items-center space-x-2">
                  <h1 className="text-lg md:text-xl font-semibold text-gray-900 truncate">
                    {currentDocument?.displayName || "SmartDocs AI"}
                  </h1>
                  {currentDocument && (
                    <button
                      onClick={() => {
                        const newName = window.prompt(
                          "Enter new name:",
                          currentDocument.displayName
                        );
                        if (
                          newName &&
                          newName.trim() &&
                          newName !== currentDocument.displayName
                        ) {
                          handleRename(newName.trim());
                        }
                      }}
                      className="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
                      title="Rename document"
                      disabled={isRenaming}
                    >
                      ✏️
                    </button>
                  )}
                </div>
                {currentDocument && (
                  <span className="text-xs md:text-sm text-gray-500 truncate block md:inline">
                    <span className="hidden md:inline">• </span>
                    {currentDocument.filename}
                  </span>
                )}
              </div>
            </div>
            <Link
              to="/"
              className="text-xs md:text-sm text-brand-500 hover:text-brand-600 font-medium flex-shrink-0"
            >
              <span className="hidden md:inline">← Back to Home</span>
              <span className="md:hidden">← Home</span>
            </Link>
          </div>
        </div>

        {/* Chat Content */}
        <div className="flex-1 flex flex-col min-h-0">
          {!currentDocumentId ? (
            /* No document selected: show upload component */
            <div className="flex-1 flex items-center justify-center p-4 md:p-8">
              <div className="max-w-md w-full">
                <div className="text-center mb-6">
                  <h2 className="text-lg font-medium text-gray-900 mb-2">
                    Get Started
                  </h2>
                  <p className="text-sm text-gray-600">
                    Upload a document or
                    <button
                      onClick={() => setIsSidebarOpen(true)}
                      className="text-brand-500 hover:text-brand-600 font-medium md:hidden"
                    >
                      {" "}
                      open the menu{" "}
                    </button>
                    <span className="hidden md:inline">
                      select one from the sidebar{" "}
                    </span>
                    to start chatting
                  </p>
                </div>
                <UploadDocument
                  onUploaded={(id: string) => {
                    setDocumentId(id);
                  }}
                />
              </div>
            </div>
          ) : (
            /* Document selected: show chat interface */
            <>
              {/* Show rename error if any */}
              {renameError && (
                <div className="flex-shrink-0 mx-4 md:mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-700">
                    <strong>Rename failed:</strong> {renameError}
                  </p>
                  <button
                    onClick={() => setRenameError(null)}
                    className="mt-2 text-xs text-red-600 hover:text-red-800 underline"
                  >
                    Dismiss
                  </button>
                </div>
              )}

              <div className="flex-1 min-h-0 bg-white">
                <ChatBox documentId={currentDocumentId} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
