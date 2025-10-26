// Zustand chat store WITHOUT persistence (clears every full reload)
import { create } from "zustand";
import { devtools } from "zustand/middleware";

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

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
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
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

const genId = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

export const useChatStore = create<
  ChatState & {
    currentDocumentId: string | null;
    setDocumentId: (id: string | null) => void;
  }
>()(
  devtools(
    (set, get) => ({
      currentDocumentId: null,
      messages: [],
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
      addUserMessage: (content) => get().addMessage({ role: "user", content }),
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
      setDocumentId: (id) =>
        set(
          (state) => {
            if (state.currentDocumentId === id) return {};
            return {
              currentDocumentId: id,
              messages: [],
              error: null,
              isLoading: false
            };
          },
          false,
          "chat/setDocumentId"
        ),
      setLoading: (loading) =>
        set(() => ({ isLoading: loading }), false, "chat/setLoading"),
      setError: (error) => set(() => ({ error }), false, "chat/setError")
    }),
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
  state: ChatState & { currentDocumentId: string | null }
) => state.messages;
export const selectIsLoading = (
  state: ChatState & { currentDocumentId: string | null }
) => state.isLoading;
export const selectError = (
  state: ChatState & { currentDocumentId: string | null }
) => state.error;
