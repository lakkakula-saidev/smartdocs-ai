/* Lightweight module declarations for react-syntax-highlighter (Prism build) to silence TS + lint.
   Replace with official types if published later. */

declare module "react-syntax-highlighter" {
  import * as React from "react";

  interface SyntaxHighlighterProps extends React.HTMLAttributes<HTMLElement> {
    language?: string;
    /* Theme object (do NOT confuse with regular inline style prop coming from HTMLAttributes) */
    customStyle?: React.CSSProperties;
    wrapLongLines?: boolean;
    PreTag?: string | React.ComponentType<unknown>;
    children?: string;
  }

  export const Prism: React.FC<SyntaxHighlighterProps>;
}

declare module "react-syntax-highlighter/dist/esm/styles/prism" {
  export const oneDark: Record<string, unknown>;
}
