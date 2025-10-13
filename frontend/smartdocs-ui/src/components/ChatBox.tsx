import { useEffect, useRef, useState, useMemo } from "react";
import { askQuestion } from "../api/api";
import { MessageBubble } from "./MessageBubble";
import {
  useChatStore,
  selectMessages,
  selectIsLoading
} from "../store/chatStore";

interface Props {
  documentId: string | null;
}

/**
 * ChatBox now backed by persisted Zustand store.
 * - Maintains previous UX & features.
 * - Uses store.isLoading instead of local 'sending'.
 */
export function ChatBox({ documentId }: Props) {
  // Pull ALL persisted messages, but only show them when a document is active.
  const allMessages = useChatStore(selectMessages);
  // Memoize derived messages to keep stable reference when documentId unchanged
  const messages = useMemo(
    () => (documentId ? allMessages : []),
    [documentId, allMessages]
  );
  const isLoading = useChatStore(selectIsLoading);
  const addUserMessage = useChatStore((s) => s.addUserMessage);
  const addAssistantMessage = useChatStore((s) => s.addAssistantMessage);
  const setLoading = useChatStore((s) => s.setLoading);
  const setError = useChatStore((s) => s.setError); // reserved for future UI surfacing
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [input, setInput] = useState("");

  // Auto-scroll on new messages / loading state change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    if (!documentId) {
      addAssistantMessage(
        "⚠️ Upload a PDF document first to enable contextual answers."
      );
      return;
    }
    const text = input.trim();
    console.debug("[Chat] Sending user message:", text);
    addUserMessage(text);
    setInput("");

    // Dev/test markdown sample command
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

    setLoading(true);
    try {
      const { answer } = await askQuestion(text, documentId);
      console.debug("[Chat] Backend raw answer (before render):", answer);
      addAssistantMessage(answer);
    } catch (err) {
      console.error("[Chat] askQuestion error:", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      addAssistantMessage("Error: failed to get an answer. Please retry.");
    } finally {
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
              : "Upload a PDF to enable the chat. Once processed you can ask contextual questions."}
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
              placeholder={
                documentId
                  ? "Ask a question about your document..."
                  : "Upload a document to enable chat..."
              }
              disabled={!documentId || isLoading}
              className="w-full resize-none rounded-md bg-neutral-900 border border-neutral-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 scrollbar-thin disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
          <button
            type="submit"
            disabled={!documentId || !input.trim() || isLoading}
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
