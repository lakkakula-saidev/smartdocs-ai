// Zustand chat store with persistence + schema migration
import { create } from "zustand";
import { persist, devtools, createJSONStorage } from "zustand/middleware";

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

// Build-scoped persistence (reset on each dev server restart)
// Injected by Vite via define in vite.config.ts
// eslint-disable-next-line @typescript-eslint/no-unused-vars
declare const __BUILD_ID__: string;

const STORAGE_BASE_NAME = "chat-storage";
const BUILD_ID = typeof __BUILD_ID__ !== "undefined" ? __BUILD_ID__ : "prod";
const PERSIST_NAME = import.meta.env.DEV
  ? `${STORAGE_BASE_NAME}-${BUILD_ID}`
  : STORAGE_BASE_NAME;

// Helper to generate ids (falls back if crypto unavailable)
const genId = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

// Legacy persisted schema (v1)
interface LegacyMessage {
  id?: string;
  sender?: "user" | "ai";
  text?: string;
  timestamp?: number;
}
interface PersistedV1 {
  messages?: LegacyMessage[];
  isLoading?: boolean;
  error?: string | null;
}

export const useChatStore = create<ChatState>()(
  devtools(
    persist(
      (set, get) => ({
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
        addUserMessage: (content) => {
          return get().addMessage({ role: "user", content });
        },
        addAssistantMessage: (content) => {
          return get().addMessage({ role: "assistant", content });
        },
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
        setLoading: (loading) =>
          set(() => ({ isLoading: loading }), false, "chat/setLoading"),
        setError: (error) => set(() => ({ error }), false, "chat/setError")
      }),
      {
        name: PERSIST_NAME,
        version: 2,
        storage: createJSONStorage(() => localStorage),
        migrate: (state: unknown, version) => {
          const looksLikeChatMessage = (m: unknown): m is ChatMessage => {
            if (typeof m !== "object" || m === null) return false;
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const mm: any = m;
            return (
              (mm.role === "user" || mm.role === "assistant") &&
              typeof mm.content === "string"
            );
          };
          if (version === 1 && state && typeof state === "object") {
            const legacy = state as PersistedV1;
            if (Array.isArray(legacy.messages)) {
              const migrated: ChatMessage[] = legacy.messages.map((m) => {
                if (looksLikeChatMessage(m)) {
                  return {
                    id: m.id ?? genId(),
                    role: m.role,
                    content: m.content,
                    timestamp: m.timestamp ?? Date.now()
                  };
                }
                const role =
                  m.sender === "ai"
                    ? "assistant"
                    : m.sender === "user"
                    ? "user"
                    : "assistant";
                return {
                  id: m.id ?? genId(),
                  role,
                  content: m.text ?? "",
                  timestamp: m.timestamp ?? Date.now()
                };
              });
              return {
                ...(legacy as Omit<ChatState, "messages">),
                messages: migrated
              } as ChatState;
            }
          }
          return state as ChatState;
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
export const selectMessages = (state: ChatState) => state.messages;
export const selectIsLoading = (state: ChatState) => state.isLoading;
export const selectError = (state: ChatState) => state.error;
