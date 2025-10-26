// Zustand chat store WITH persistence (survives browser refreshes)
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { fetchDocumentInfo, documentInfoToMetadata } from "../api/api";

/**
 * Unified ChatMessage shape:
 * - role: "user" | "assistant"
 * - content: markdown-capable message body
 */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

/**
 * Document metadata for display purposes
 */
export interface DocumentMetadata {
  id: string;
  displayName: string;
  filename?: string;
  extractedTitle?: string;
  userDisplayName?: string;
}

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  chatHistories: Record<string, ChatMessage[]>; // documentId -> messages
  addMessage: (
    msg: Omit<ChatMessage, "id" | "timestamp"> & {
      id?: string;
      timestamp?: number;
    }
  ) => string;
  addUserMessage: (content: string) => string;
  addAssistantMessage: (content: string) => string;
  replaceLastAssistantMessage: (
    updater: (prev: ChatMessage) => ChatMessage
  ) => void;
  clearChat: () => void;
  clearAllChats: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  loadChatHistory: (documentId: string) => void;
  saveChatHistory: (documentId: string) => void;
}

const genId = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

export const useChatStore = create<
  ChatState & {
    currentDocument: DocumentMetadata | null;
    currentDocumentId: string | null; // Keep for backward compatibility
    setDocument: (doc: DocumentMetadata | null) => void;
    setDocumentId: (id: string | null) => void; // Keep for backward compatibility
    updateDocumentName: (docId: string, newName: string) => void;
  }
>()(
  devtools(
    persist(
      (set, get) => ({
        currentDocument: null,
        currentDocumentId: null,
        messages: [],
        chatHistories: {},
        isLoading: false,
        error: null,
        addMessage: (msg) => {
          const id = msg.id ?? genId();
          const timestamp = msg.timestamp ?? Date.now();
          const newMessage: ChatMessage = {
            id,
            role: msg.role,
            content: msg.content,
            timestamp
          };
          set(
            (state) => ({ messages: [...state.messages, newMessage] }),
            false,
            "chat/addMessage"
          );
          return id;
        },
        addUserMessage: (content) =>
          get().addMessage({ role: "user", content }),
        addAssistantMessage: (content) =>
          get().addMessage({ role: "assistant", content }),
        replaceLastAssistantMessage: (updater) =>
          set(
            (state) => {
              for (let i = state.messages.length - 1; i >= 0; i--) {
                if (state.messages[i].role === "assistant") {
                  const updated = updater(state.messages[i]);
                  const copy = state.messages.slice();
                  copy[i] = { ...updated };
                  return { messages: copy };
                }
              }
              return {};
            },
            false,
            "chat/replaceLastAssistantMessage"
          ),
        clearChat: () =>
          set(
            () => ({
              messages: [],
              error: null,
              isLoading: false
            }),
            false,
            "chat/clearChat"
          ),
        clearAllChats: () =>
          set(
            () => ({
              messages: [],
              chatHistories: {},
              error: null,
              isLoading: false
            }),
            false,
            "chat/clearAllChats"
          ),
        loadChatHistory: (documentId: string) =>
          set(
            (state) => {
              const history = state.chatHistories[documentId] || [];
              return {
                messages: [...history],
                error: null,
                isLoading: false
              };
            },
            false,
            "chat/loadChatHistory"
          ),
        saveChatHistory: (documentId: string) =>
          set(
            (state) => {
              if (!documentId) return {};
              return {
                chatHistories: {
                  ...state.chatHistories,
                  [documentId]: [...state.messages]
                }
              };
            },
            false,
            "chat/saveChatHistory"
          ),
        setDocument: (doc) =>
          set(
            (state) => {
              if (state.currentDocument?.id === doc?.id) return {};

              // Save current chat history before switching
              if (state.currentDocumentId && state.messages.length > 0) {
                state.chatHistories[state.currentDocumentId] = [
                  ...state.messages
                ];
              }

              // Load new document's chat history
              const newMessages = doc?.id
                ? state.chatHistories[doc.id] || []
                : [];

              return {
                currentDocument: doc,
                currentDocumentId: doc?.id || null,
                messages: newMessages,
                chatHistories:
                  state.currentDocumentId && state.messages.length > 0
                    ? {
                        ...state.chatHistories,
                        [state.currentDocumentId]: [...state.messages]
                      }
                    : state.chatHistories,
                error: null,
                isLoading: false
              };
            },
            false,
            "chat/setDocument"
          ),
        setDocumentId: async (id) => {
          if (!id) {
            set(
              (state) => {
                if (state.currentDocumentId === null) return {};

                // Save current chat history before clearing
                const updatedHistories =
                  state.currentDocumentId && state.messages.length > 0
                    ? {
                        ...state.chatHistories,
                        [state.currentDocumentId]: [...state.messages]
                      }
                    : state.chatHistories;

                return {
                  currentDocumentId: null,
                  currentDocument: null,
                  messages: [],
                  chatHistories: updatedHistories,
                  error: null,
                  isLoading: false
                };
              },
              false,
              "chat/setDocumentId/clear"
            );
            return;
          }

          const currentState = get();
          if (currentState.currentDocumentId === id) return;

          // Save current chat history before switching
          const updatedHistories =
            currentState.currentDocumentId && currentState.messages.length > 0
              ? {
                  ...currentState.chatHistories,
                  [currentState.currentDocumentId]: [...currentState.messages]
                }
              : currentState.chatHistories;

          // Load new document's chat history
          const newMessages = updatedHistories[id] || [];

          // Set temporary state with fallback display name and loaded chat history
          set(
            () => ({
              currentDocumentId: id,
              currentDocument: {
                id,
                displayName: `Document ${id.slice(0, 8)}...`
              },
              messages: newMessages,
              chatHistories: updatedHistories,
              error: null,
              isLoading: false
            }),
            false,
            "chat/setDocumentId/temp"
          );

          // Try to fetch real document metadata
          try {
            const documentInfo = await fetchDocumentInfo(id);
            const metadata = documentInfoToMetadata(documentInfo);
            set(
              (state) => {
                if (state.currentDocumentId !== id) return {}; // Don't update if document changed
                return {
                  currentDocument: metadata
                };
              },
              false,
              "chat/setDocumentId/fetched"
            );
          } catch (error) {
            console.warn(`Failed to fetch document metadata for ${id}:`, error);
            // Keep the fallback name - no need to update state
          }
        },
        updateDocumentName: (docId, newName) =>
          set(
            (state) => {
              if (state.currentDocument?.id === docId) {
                return {
                  currentDocument: {
                    ...state.currentDocument,
                    displayName: newName,
                    userDisplayName: newName
                  }
                };
              }
              return {};
            },
            false,
            "chat/updateDocumentName"
          ),
        setLoading: (loading) =>
          set(() => ({ isLoading: loading }), false, "chat/setLoading"),
        setError: (error) => set(() => ({ error }), false, "chat/setError")
      }),
      {
        name: "smartdocs-chat-storage", // localStorage key name
        version: 1, // Storage version for future migrations
        partialize: (state) => ({
          // Only persist these specific fields
          chatHistories: state.chatHistories,
          currentDocument: state.currentDocument,
          currentDocumentId: state.currentDocumentId,
          messages: state.messages
        }),
        // Optional: Add migration logic for future versions
        migrate: (persistedState: unknown, version: number) => {
          if (version === 0) {
            // Migration logic for version 0 -> 1 if needed in future
          }
          return persistedState;
        }
      }
    ),
    { name: "chat-store" }
  )
);

// Optional debug exposure (development only)
if (typeof window !== "undefined" && import.meta.env.MODE !== "production") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (window as any).__CHAT_STORE__ = useChatStore;
}

// Selectors
export const selectMessages = (
  state: ChatState & {
    currentDocument: DocumentMetadata | null;
    currentDocumentId: string | null;
  }
) => state.messages;

export const selectIsLoading = (
  state: ChatState & {
    currentDocument: DocumentMetadata | null;
    currentDocumentId: string | null;
  }
) => state.isLoading;

export const selectError = (
  state: ChatState & {
    currentDocument: DocumentMetadata | null;
    currentDocumentId: string | null;
  }
) => state.error;

export const selectCurrentDocument = (
  state: ChatState & {
    currentDocument: DocumentMetadata | null;
    currentDocumentId: string | null;
  }
) => state.currentDocument;

export const selectCurrentDocumentId = (
  state: ChatState & {
    currentDocument: DocumentMetadata | null;
    currentDocumentId: string | null;
  }
) => state.currentDocumentId;
