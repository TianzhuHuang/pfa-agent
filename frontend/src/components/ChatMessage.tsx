"use client";

import React from "react";
import ReactMarkdown from "react-markdown";

const markdownComponents = {
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="mb-6 leading-relaxed">{children}</p>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="mb-5 pl-6 list-disc">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="mb-5 pl-6 list-decimal">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="mb-2">{children}</li>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold">{children}</strong>
  ),
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className="mb-4 text-lg font-semibold">{children}</h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="mb-3 mt-6 text-base font-semibold">{children}</h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="mb-2 mt-4 text-sm font-semibold">{children}</h3>
  ),
  hr: () => <hr className="my-6 border-white/10" />,
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote className="border-l-4 border-[#1976d2]/50 pl-4 my-4 text-[#b1bad3]">
      {children}
    </blockquote>
  ),
};

interface ChatMessageProps {
  content: string;
  role: "user" | "assistant";
  isStreaming?: boolean;
}

export function ChatMessage({ content, role, isStreaming }: ChatMessageProps) {
  const isUser = role === "user";

  if (isUser) {
    return (
      <div className="rounded-xl px-4 py-3 text-sm ml-8 bg-[#1a1a1a] text-white max-w-[90%]">
        {content}
      </div>
    );
  }

  const displayContent = content || (isStreaming ? "思考中..." : "");

  if (!content && isStreaming) {
    return (
      <div className="rounded-xl px-4 py-3 text-sm mr-8 bg-transparent text-[#888888] max-w-[90%]">
        思考中...
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl px-4 py-3 text-sm mr-8 bg-transparent text-[#b1bad3] w-[90%] max-w-[90%] prose prose-invert max-w-none prose-p:leading-relaxed prose-ul:mb-5 prose-ul:pl-6 prose-ol:mb-5 prose-ol:pl-6 prose-li:mb-2 prose-strong:font-semibold ${
        isStreaming ? "prose-streaming" : ""
      }`}
    >
      <ReactMarkdown components={markdownComponents}>
        {displayContent.replace(/\n\n+/g, "\n\n")}
      </ReactMarkdown>
    </div>
  );
}
