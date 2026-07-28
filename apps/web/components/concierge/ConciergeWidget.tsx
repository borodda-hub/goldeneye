"use client";

/**
 * The Concierge (Phase C) — floating grounded assistant on every app screen.
 *
 * Guide · teacher · explainer · research assistant. Replies come from
 * POST /v1/concierge/chat, which answers ONLY from the curated knowledge pack
 * + a live server-assembled context (price, ensemble view, range band, fresh
 * headlines) and passes the standard safety scan. Suggestions are
 * server-derived from a fixed route map — the widget never builds links from
 * model text. Rendered with InlineMarkdown (injection-safe).
 *
 * Mounted OUTSIDE <main> in the app layout: it is an intentional overlay, not
 * page content — the ui-audit detectors scan within <main> only.
 */

import { InlineMarkdown } from "@/components/InlineMarkdown";
import {
  type ConciergeSuggestion,
  type ConciergeTurn,
  postConciergeChat,
} from "@/lib/api";
import { clerkEnabled } from "@/lib/clerk";
import { useActiveInstrument } from "@/lib/useActiveInstrument";
import { useUser } from "@clerk/nextjs";
import { useMutation } from "@tanstack/react-query";
import { Send, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  suggestions?: ConciergeSuggestion[];
  error?: boolean;
}

const DEFAULT_GREETING =
  "Welcome to Goldeneye. I can explain any screen, teach the methodology, or synthesize the latest headlines against the current market read. What would you like to explore?";

function ClerkGreetingName({ onName }: { onName: (n: string) => void }) {
  const { user } = useUser();
  const first = user?.firstName;
  useEffect(() => {
    if (first) onName(first);
  }, [first, onName]);
  return null;
}

export function ConciergeWidget() {
  const pathname = usePathname();
  const { activeSymbol } = useActiveInstrument();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [firstName, setFirstName] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const threadRef = useRef<HTMLDivElement>(null);

  const greeting = firstName
    ? `Welcome back, ${firstName}. ${DEFAULT_GREETING}`
    : DEFAULT_GREETING;

  const chat = useMutation({
    mutationFn: (message: string) => {
      const history: ConciergeTurn[] = messages
        .filter((m) => !m.error)
        .slice(-8)
        .map((m) => ({ role: m.role, content: m.content }));
      return postConciergeChat({
        message,
        history,
        symbol: activeSymbol,
        route: pathname ?? undefined,
      });
    },
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply,
          suggestions: data.suggestions,
        },
      ]);
    },
    onError: (err: Error) => {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: /429/.test(err.message)
            ? "The concierge is rate-limited for now — please try again in a little while."
            : "The concierge couldn't answer that just now. Try rephrasing — note it never gives trading advice.",
          error: true,
        },
      ]);
    },
  });

  const send = () => {
    const message = input.trim();
    if (!message || chat.isPending) return;
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    chat.mutate(message);
  };

  // Keep the newest message in view — runs each render (the thread is tiny).
  useEffect(() => {
    const el = threadRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  });

  return (
    <>
      {clerkEnabled && <ClerkGreetingName onName={setFirstName} />}

      {/* Launcher */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={open ? "Close concierge" : "Open concierge"}
        className="fixed bottom-16 right-4 z-40 inline-flex items-center gap-2 border border-accent bg-surface-2 px-3 py-2.5 font-mono text-[11px] uppercase tracking-eyebrow text-accent hover:bg-accent hover:text-bg transition-colors shadow-lg"
      >
        {open ? (
          <X size={14} strokeWidth={1.5} aria-hidden />
        ) : (
          <Sparkles size={14} strokeWidth={1.5} aria-hidden />
        )}
        <span className="hidden sm:inline">Concierge</span>
      </button>

      {/* Panel */}
      {open && (
        <section
          aria-label="Goldeneye concierge"
          className="fixed bottom-28 right-4 z-40 flex w-[380px] max-w-[calc(100vw-2rem)] flex-col border border-line-2 bg-surface-1 shadow-2xl"
          style={{ height: "min(520px, calc(100vh - 10rem))" }}
        >
          <div className="flex items-center gap-2 border-b border-line-1 px-3 py-2.5">
            <Sparkles
              size={12}
              strokeWidth={1.5}
              aria-hidden
              className="text-accent"
            />
            <span className="font-mono text-[11px] uppercase tracking-eyebrow text-accent">
              Concierge
            </span>
            <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.14em] text-ink-4">
              {activeSymbol} · grounded
            </span>
          </div>

          <div
            ref={threadRef}
            aria-live="polite"
            className="flex-1 overflow-y-auto px-3 py-3 flex flex-col gap-3"
          >
            <Bubble from="assistant" content={greeting} />
            {messages.map((m, i) => (
              <Bubble
                key={`${i}-${m.role}-${m.content.slice(0, 16)}`}
                from={m.role}
                content={m.content}
                suggestions={m.suggestions}
                error={m.error}
              />
            ))}
            {chat.isPending && (
              <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-4 animate-pulse">
                Thinking…
              </p>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
            className="flex items-center gap-2 border-t border-line-1 px-3 py-2.5"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              maxLength={2000}
              placeholder="Ask about any screen, the methodology, or the latest news…"
              aria-label="Message the concierge"
              className="min-w-0 flex-1 bg-transparent text-xs text-ink-1 placeholder:text-ink-4 focus:outline-none"
            />
            <button
              type="submit"
              disabled={!input.trim() || chat.isPending}
              aria-label="Send"
              className="text-accent disabled:text-ink-4 hover:text-accent-bright transition-colors"
            >
              <Send size={14} strokeWidth={1.5} aria-hidden />
            </button>
          </form>

          <p className="border-t border-line-1 px-3 py-1.5 font-mono text-[10px] tracking-[0.08em] text-ink-4">
            Explains the platform &amp; its data — never financial advice.
          </p>
        </section>
      )}
    </>
  );
}

function Bubble({
  from,
  content,
  suggestions,
  error,
}: {
  from: "user" | "assistant";
  content: string;
  suggestions?: ConciergeSuggestion[];
  error?: boolean;
}) {
  if (from === "user") {
    return (
      <div className="self-end max-w-[85%] border border-line-2 bg-surface-2 px-3 py-2 text-xs leading-relaxed text-ink-1">
        {content}
      </div>
    );
  }
  return (
    <div className="self-start max-w-[92%] flex flex-col gap-2">
      <div
        className={`border-l-2 pl-3 py-0.5 text-xs leading-relaxed ${
          error ? "border-down text-ink-3" : "border-accent-deep text-ink-2"
        }`}
      >
        <InlineMarkdown text={content} />
      </div>
      {suggestions && suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pl-3">
          {suggestions.map((s) => (
            <Link
              key={s.route}
              href={s.route}
              className="border border-line-2 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-3 hover:border-accent hover:text-accent transition-colors"
            >
              {s.label} →
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
