import { useEffect, useRef, useState } from "react";
import { askQuestion } from "../api/api";
import { MessageBubble } from "./MessageBubble";
import {
  useChatStore,
  selectMessages,
  selectIsLoading,
  selectError
} from "../store/chatStore";

// Type guard for aborted errors (created in api.ts)
interface AbortedError extends Error {
  aborted: true;
}
function isAbortedError(e: unknown): e is AbortedError {
  if (typeof e !== "object" || e === null) return false;
  return (e as { aborted?: unknown }).aborted === true;
}

interface Props {
  documentId: string | null;
}

/**
 * ChatBox now backed by persisted Zustand store.
 * - Maintains previous UX & features.
 * - Uses store.isLoading instead of local 'sending'.
 */
export function ChatBox({ documentId }: Props) {
  const messages = useChatStore(selectMessages);
  const isLoading = useChatStore(selectIsLoading);
  const error = useChatStore(selectError);
  const addUserMessage = useChatStore((s) => s.addUserMessage);
  const addAssistantMessage = useChatStore((s) => s.addAssistantMessage);
  const setLoading = useChatStore((s) => s.setLoading);
  const setError = useChatStore((s) => s.setError);
  const clearError = useChatStore((s) => s.clearError);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const lastQueryRef = useRef<string | null>(null);
  const [input, setInput] = useState("");

  // Auto-scroll on new messages / loading state change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  // Cleanup (abort in-flight request) on unmount
  useEffect(() => {
    return () => {
      if (controllerRef.current) {
        controllerRef.current.abort();
      }
    };
  }, []);

  const handleSend = async () => {
    if (!input.trim()) return;
    const text = input.trim();

    // Abort prior in-flight request if still running (prevents race conditions)
    if (isLoading && controllerRef.current) {
      controllerRef.current.abort();
    }

    clearError();
    console.debug("[Chat] Sending user message:", text);
    addUserMessage(text);
    lastQueryRef.current = text;
    setInput("");

    // Dev/test markdown sample command passthrough
    if (text === "/mdtest") {
      console.debug("[Chat] Injecting internal /mdtest markdown sample");
      addAssistantMessage(`# Markdown Rendering Test

**Bold text check** and *italic text* plus ~~strikethrough~~.

> Blockquote line to verify styling.

## Lists
1. Ordered item one
2. Ordered item two
3. Ordered item three

- Bullet alpha
- Bullet beta
  - Nested bullet
- Bullet gamma

## Inline Code
Here is some \`inline code\` inside a sentence.

## Code Block
\`\`\`ts
function greet(name: string): void {
  console.log("Hello " + name);
}

interface User {
  id: string;
  name: string;
}

const user: User = { id: "u1", name: "Ada" };
greet(user.name);
\`\`\`

## Table
| Key | Value | Note |
| --- | ----- | ---- |
| A   | 1     | First |
| B   | 2     | Second |
| C   | 3     | Third |

## Task List
- [x] Bold
- [x] Lists
- [x] Code block
- [x] Table
- [ ] Unchecked item

Done.`);
      textareaRef.current?.focus();
      return;
    }

    const controller = new AbortController();
    controllerRef.current = controller;
    setLoading(true);
    try {
      const { answer } = await askQuestion(text, { signal: controller.signal });
      console.debug("[Chat] Backend raw answer (before render):", answer);
      addAssistantMessage(answer);
    } catch (err) {
      if (!isAbortedError(err)) {
        console.error("[Chat] askQuestion error:", err);
        setError(err instanceof Error ? err.message : "Unknown error");
      } else {
        console.debug("[Chat] Request aborted");
      }
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null;
      }
      setLoading(false);
      textareaRef.current?.focus();
    }
  };

  const handleRetry = async () => {
    if (!lastQueryRef.current) return;
    // Abort any current request
    if (isLoading && controllerRef.current) {
      controllerRef.current.abort();
    }
    clearError();
    const query = lastQueryRef.current;
    const controller = new AbortController();
    controllerRef.current = controller;
    setLoading(true);
    try {
      const { answer } = await askQuestion(query, {
        signal: controller.signal
      });
      addAssistantMessage(answer);
    } catch (err) {
      if (!isAbortedError(err)) {
        console.error("[Chat] retry askQuestion error:", err);
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null;
      }
      setLoading(false);
      textareaRef.current?.focus();
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      <div
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-y-auto space-y-3 pr-1 pb-28 scrollbar-thin"
      >
        {messages.map((m) => (
          <MessageBubble key={m.id} role={m.role} content={m.content} />
        ))}
        {messages.length === 0 && (
          <p className="text-xs text-neutral-500">
            {documentId
              ? "Start chatting about the uploaded document."
              : "Ask a question. Uploading a document adds context (optional)."}
          </p>
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="text-[0.65rem] text-neutral-500 px-3 py-1 rounded-md bg-neutral-800/60">
              Thinking…
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-2 px-3 py-2 rounded-md bg-red-900/40 border border-red-700 text-red-300 text-xs flex items-start gap-3">
          <div className="flex-1">
            <strong className="block font-semibold mb-0.5">Chat Error</strong>
            <span className="break-words">{error}</span>
          </div>
          <div className="flex flex-col gap-1">
            <button
              type="button"
              onClick={handleRetry}
              disabled={isLoading}
              className="text-[0.6rem] px-2 py-1 rounded bg-red-700/60 hover:bg-red-700 disabled:opacity-50"
            >
              Retry
            </button>
            <button
              type="button"
              onClick={() => clearError()}
              className="text-[0.6rem] px-2 py-1 rounded bg-neutral-700/60 hover:bg-neutral-700"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="mt-4"
      >
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              rows={2}
              placeholder="Ask a question..."
              className="w-full resize-none rounded-md bg-neutral-900 border border-neutral-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 scrollbar-thin"
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="btn disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "..." : "Send"}
          </button>
        </div>
        <p className="mt-1 text-[0.55rem] uppercase tracking-wide text-neutral-500">
          Enter to send • Shift+Enter for newline
        </p>
      </form>
    </div>
  );
}
