"use client";

import React, { useRef } from "react";

const DEFAULT_SAMPLE_PROMPTS = [
  "美联储立场如何影响我的 BTC？",
  "分析这条新闻截图",
  "科技板块近期有哪些风险？",
];

interface ChatInputDockProps {
  placeholder?: string;
  onSend?: (text: string) => void;
  /** 点击 + 时触发；若传入 (file) => void 会渲染隐藏的 file input，选图后回调 file */
  onAttach?: () => void | ((file: File) => void);
  disabled?: boolean;
  /** 仅控制发送按钮可用状态，不影响输入框与示例按钮 */
  sendDisabled?: boolean;
  showSamplePrompts?: boolean;
  samplePrompts?: string[];
}

export function ChatInputDock({
  placeholder = "粘贴链接、截图或输入问题",
  onSend,
  onAttach,
  disabled = false,
  showSamplePrompts = true,
  samplePrompts = DEFAULT_SAMPLE_PROMPTS,
  sendDisabled = false,
}: ChatInputDockProps) {
  const [value, setValue] = React.useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAttachClick = () => {
    if (typeof onAttach === "function") {
      if (onAttach.length >= 1) {
        fileInputRef.current?.click();
      } else {
        (onAttach as () => void)();
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && typeof onAttach === "function" && onAttach.length >= 1) {
      (onAttach as (file: File) => void)(file);
    }
    e.target.value = "";
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const t = value.trim();
    if (!t || disabled) return;
    onSend?.(t);
    setValue("");
  };

  const handleSampleClick = (text: string) => {
    setValue(text);
  };

  const extractUrls = (text: string): string[] => {
    const re = /(https?:\/\/[^\s]+)/g;
    const out: string[] = [];
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      out.push(m[1]);
    }
    return Array.from(new Set(out));
  };

  const urls = extractUrls(value);

  return (
    <div className="sticky bottom-0 border-t border-white/5 bg-[#0A0F1E]/80 px-4 py-4 backdrop-blur-xl">
      {typeof onAttach === "function" && onAttach.length >= 1 && (
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          aria-hidden
          onChange={handleFileChange}
        />
      )}
      {showSamplePrompts && samplePrompts.length > 0 && (
        <div className="mx-auto mb-3 flex max-w-2xl flex-wrap justify-center gap-2">
          {samplePrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => handleSampleClick(prompt)}
              disabled={disabled}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-[#9AA0A6] transition-colors hover:border-[#D4AF37]/30 hover:bg-[#D4AF37]/10 hover:text-[#D4AF37] disabled:opacity-50"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}
      <form
        onSubmit={handleSubmit}
        className="mx-auto flex max-w-2xl items-center gap-2 rounded-full border border-white/10 bg-[#0A0F1E]/90 px-4 py-3 shadow-[0_0_20px_rgba(212,175,55,0.15)] backdrop-blur-md transition-colors focus-within:border-[#D4AF37]/40 focus-within:shadow-[0_0_24px_rgba(212,175,55,0.2)]"
      >
        <button
          type="button"
          onClick={handleAttachClick}
          disabled={disabled}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/10 text-[#9AA0A6] transition-colors hover:border-[#D4AF37]/40 hover:bg-[#D4AF37]/10 hover:text-[#D4AF37] disabled:opacity-50"
          title="上传图片、链接或文件"
          aria-label="添加附件"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1 bg-transparent text-sm text-white placeholder:text-[#6B7280] outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim() || sendDisabled}
          title="发送"
          aria-label="发送"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#D4AF37] text-black transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </form>
      {urls.length > 0 && (
        <div className="mx-auto mt-2 max-w-2xl text-[11px] text-[#60A5FA]">
          {urls.map((u) => (
            <span key={u} className="mr-2 underline break-all">
              {u}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
