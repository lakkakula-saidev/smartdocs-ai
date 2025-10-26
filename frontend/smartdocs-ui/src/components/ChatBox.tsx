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
    <div className="flex flex-col h-full">
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 md:px-6 pt-4 scrollbar-thin"
      >
        <div className="space-y-3 pb-4">
          {messages.length === 0 && (
            <div className="flex items-center justify-center min-h-[200px]">
              <p className="text-sm text-gray-500 text-center">
                {documentId
                  ? "Start chatting about the uploaded document."
                  : "Upload a PDF to enable the chat. Once processed you can ask contextual questions."}
              </p>
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role} content={m.content} />
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="text-[0.65rem] text-gray-600 px-3 py-1 rounded-md bg-gray-100 border border-gray-200">
                Thinking…
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex-shrink-0 bg-gray-50 px-4 md:px-6 py-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <div className="flex items-center gap-3">
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
                rows={1}
                placeholder={
                  documentId
                    ? "Ask a question about your document..."
                    : "Upload a document to enable chat..."
                }
                disabled={!documentId || isLoading}
                className="w-full resize-none rounded-lg bg-white border border-gray-300 px-4 py-3 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
            <button
              type="submit"
              disabled={!documentId || !input.trim() || isLoading}
              className="px-4 py-3 bg-brand-600 text-white rounded-lg hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? "..." : "Send"}
            </button>
          </div>
          <p className="mt-1 text-[0.55rem] uppercase tracking-wide text-neutral-500">
            Enter to send • Shift+Enter for newline
          </p>
        </form>
      </div>
    </div>
  );
}
