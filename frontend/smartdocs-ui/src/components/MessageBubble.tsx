import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useMemo } from "react";

/**
 * Internal code renderer to satisfy react-markdown typing without leaking `any` everywhere.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CodeRenderer: React.FC<any> = ({ inline, children, ...rest }) => {
  if (inline) {
    return (
      <code
        className="px-1 py-0.5 rounded bg-gray-200 border border-gray-300 text-[0.75rem] text-gray-800"
        {...rest}
      >
        {children}
      </code>
    );
  }
  return (
    <pre className="my-2 rounded-md border border-gray-300 bg-gray-50 overflow-auto px-3 py-2 text-[0.75rem] leading-snug">
      <code className="font-mono text-gray-800">
        {String(children || "").replace(/\n$/, "")}
      </code>
    </pre>
  );
};

interface Props {
  role: "user" | "assistant";
  content: string;
}

/**
 * Heuristic: If backend does not supply **bold**, promote leading list item "Title:" segment to bold.
 * Examples transformed:
 *  "1. Formation of the Moon: The Moon formed..." -> "1. **Formation of the Moon**: The Moon formed..."
 *  "- Major Factors: These include..." -> "- **Major Factors**: These include..."
 * Will skip if already contains ** in the segment.
 */
function injectListTitleBold(src: string): string {
  const lines = src.split(/\n/).map((l) => {
    return l.replace(
      /^(\s*(?:\d+\.|[-*])\s+)([A-Z][^:\n]{1,80}?)(:)(\s+)/,
      (m, prefix, title, colon, space) => {
        if (/\*\*/.test(title)) return m; // already bold
        return `${prefix}**${title.trim()}**${colon}${space}`;
      }
    );
  });
  return lines.join("\n");
}

/**
 * Chat message bubble with Markdown (GFM) support.
 * Syntax highlighting removed (plain code blocks only).
 */

export function MessageBubble({ role, content }: Props) {
  const isUser = role === "user";
  const processed = useMemo(() => injectListTitleBold(content), [content]);
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} w-full`}>
      <div
        className={`max-w-[70%] rounded-lg px-4 py-2 text-sm leading-relaxed ${
          isUser
            ? "bg-brand-600 text-white"
            : "bg-gray-100 text-gray-900 border border-gray-200"
        } markdown-body`}
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            // Custom code renderer (plain, no syntax highlighting)
            code: CodeRenderer,
            a({ href, children, ...props }) {
              return (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline decoration-brand-500/60 underline-offset-2 hover:text-brand-300"
                  {...props}
                >
                  {children}
                </a>
              );
            },
            strong({ children, ...props }) {
              return (
                <strong className="font-semibold text-gray-900" {...props}>
                  {children}
                </strong>
              );
            },
            em({ children, ...props }) {
              return (
                <em className="text-gray-700 italic" {...props}>
                  {children}
                </em>
              );
            },
            blockquote({ children, ...props }) {
              return (
                <blockquote
                  className="border-l-4 border-brand-600/70 pl-3 ml-0 my-2 text-gray-700 italic"
                  {...props}
                >
                  {children}
                </blockquote>
              );
            },
            ul({ children, ...props }) {
              return (
                <ul
                  className="list-disc pl-5 my-2 space-y-1 marker:text-brand-500"
                  {...props}
                >
                  {children}
                </ul>
              );
            },
            ol({ children, ...props }) {
              return (
                <ol
                  className="list-decimal pl-5 my-2 space-y-1 marker:text-brand-400"
                  {...props}
                >
                  {children}
                </ol>
              );
            },
            li({ children, ...props }) {
              return (
                <li className="leading-snug" {...props}>
                  {children}
                </li>
              );
            },
            table({ children, ...props }) {
              return (
                <div className="my-3 overflow-x-auto">
                  <table
                    className="w-full text-xs border-separate border-spacing-0"
                    {...props}
                  >
                    {children}
                  </table>
                </div>
              );
            },
            thead({ children, ...props }) {
              return (
                <thead className="bg-gray-50 text-gray-700" {...props}>
                  {children}
                </thead>
              );
            },
            th({ children, ...props }) {
              return (
                <th
                  className="px-2 py-1 text-left font-medium border border-gray-300"
                  {...props}
                >
                  {children}
                </th>
              );
            },
            td({ children, ...props }) {
              return (
                <td
                  className="px-2 py-1 align-top border border-gray-300"
                  {...props}
                >
                  {children}
                </td>
              );
            },
            h1({ children, ...props }) {
              return (
                <h1
                  className="mt-2 mb-1 text-lg font-semibold tracking-tight text-brand-600"
                  {...props}
                >
                  {children}
                </h1>
              );
            },
            h2({ children, ...props }) {
              return (
                <h2
                  className="mt-2 mb-1 text-base font-semibold tracking-tight text-brand-600"
                  {...props}
                >
                  {children}
                </h2>
              );
            },
            h3({ children, ...props }) {
              return (
                <h3
                  className="mt-2 mb-1 text-sm font-semibold tracking-tight text-brand-600"
                  {...props}
                >
                  {children}
                </h3>
              );
            },
            p({ children, ...props }) {
              return (
                <p className="my-1 leading-relaxed" {...props}>
                  {children}
                </p>
              );
            },
            hr() {
              return <hr className="my-3 border-gray-300" />;
            }
          }}
        >
          {processed}
        </ReactMarkdown>
      </div>
    </div>
  );
}
