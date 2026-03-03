"use client";

import { useState, useRef, useCallback, FormEvent } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ───────────────────────────────────────────────────────────

interface Source {
  content: string;
  file_path: string;
  line_start: number;
  line_end: number;
  chunk_type: string;
  language: string;
  function_name: string | null;
  parent_section: string | null;
  parent_division: string | null;
  score: number;
}

// ── Minimal Markdown renderer ───────────────────────────────────────

function renderMarkdown(text: string): string {
  let html = text
    // Code blocks (``` ... ```)
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_m, _lang, code) => {
      const escaped = code
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      return `<pre><code>${escaped}</code></pre>`;
    })
    // Inline code
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    // Bold
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    // Italic
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // Headers
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    // Horizontal rule
    .replace(/^---$/gm, "<hr/>")
    // Unordered lists
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    // Ordered lists
    .replace(/^\d+\. (.+)$/gm, "<li>$1</li>");

  // Wrap consecutive <li> in <ul>
  html = html.replace(/((<li>.*<\/li>\n?)+)/g, "<ul>$1</ul>");
  // Paragraphs: wrap lines that aren't already block elements
  html = html.replace(
    /^(?!<[hupol]|<li|<hr|<blockquote|<pre)(.+)$/gm,
    "<p>$1</p>"
  );
  return html;
}

// ── Components ──────────────────────────────────────────────────────

function SourceCard({ source, index }: { source: Source; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const shortPath = source.file_path.replace(/^.*?data\/gnucobol\//, "");
  const codePreview = expanded
    ? source.content
    : source.content.slice(0, 600) + (source.content.length > 600 ? "..." : "");

  return (
    <div
      style={{
        background: "var(--card)",
        border: "1px solid var(--card-border)",
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px",
          borderBottom: "1px solid var(--card-border)",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              background: "var(--accent)",
              color: "#fff",
              borderRadius: 4,
              padding: "2px 6px",
              flexShrink: 0,
            }}
          >
            {index + 1}
          </span>
          <span
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: 13,
              fontWeight: 500,
              color: "#f4f4f5",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {shortPath}:{source.line_start}-{source.line_end}
          </span>
        </div>
        <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
          {source.function_name && (
            <span
              style={{
                fontSize: 11,
                background: "#1e293b",
                color: "#94a3b8",
                borderRadius: 4,
                padding: "2px 8px",
                fontFamily: "var(--font-geist-mono), monospace",
              }}
            >
              {source.function_name}
            </span>
          )}
          <span
            style={{
              fontSize: 11,
              background: "#14532d",
              color: "#86efac",
              borderRadius: 4,
              padding: "2px 8px",
            }}
          >
            {source.chunk_type}
          </span>
          <span
            style={{
              fontSize: 11,
              background: "#1e1b4b",
              color: "#a5b4fc",
              borderRadius: 4,
              padding: "2px 8px",
            }}
          >
            {(source.score * 100).toFixed(1)}%
          </span>
        </div>
      </div>
      {/* Code */}
      <div style={{ position: "relative" }}>
        <pre
          style={{
            margin: 0,
            padding: 14,
            fontSize: 12,
            lineHeight: 1.6,
            background: "var(--code-bg)",
            overflow: "auto",
            maxHeight: expanded ? "none" : 200,
            fontFamily: "var(--font-geist-mono), monospace",
            color: "#a1a1aa",
          }}
        >
          <code>{codePreview}</code>
        </pre>
        {source.content.length > 600 && (
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              position: expanded ? "relative" : "absolute",
              bottom: 0,
              left: 0,
              right: 0,
              width: "100%",
              padding: "6px 0",
              fontSize: 12,
              color: "var(--accent)",
              background: expanded
                ? "var(--code-bg)"
                : "linear-gradient(transparent, var(--code-bg) 50%)",
              border: "none",
              cursor: "pointer",
              textAlign: "center",
            }}
          >
            {expanded ? "Show less" : "Show more"}
          </button>
        )}
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--muted)" }}>
      <svg width="20" height="20" viewBox="0 0 24 24" style={{ animation: "spin 1s linear infinite" }}>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" strokeDasharray="30 70" />
      </svg>
      <span style={{ fontSize: 14 }}>Searching codebase and generating answer...</span>
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────

export default function Home() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleSubmit = useCallback(
    async (e?: FormEvent) => {
      e?.preventDefault();
      const trimmed = query.trim();
      if (!trimmed || loading) return;

      // Reset
      setAnswer("");
      setSources([]);
      setError(null);
      setLatencyMs(null);
      setLoading(true);

      // Abort previous request if any
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch(`${API_URL}/api/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: trimmed, top_k: 5, stream: true }),
          signal: controller.signal,
        });

        if (!res.ok) {
          throw new Error(`API error: ${res.status} ${res.statusText}`);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";
        let accumulatedAnswer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;

            try {
              const event = JSON.parse(jsonStr);
              if (event.type === "sources") {
                setSources(event.sources);
              } else if (event.type === "token") {
                accumulatedAnswer += event.token;
                setAnswer(accumulatedAnswer);
              } else if (event.type === "done") {
                setLatencyMs(event.latency_ms);
              }
            } catch {
              // Skip malformed events
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(
          err instanceof Error
            ? err.message
            : "Failed to connect to the API. Is the backend running?"
        );
      } finally {
        setLoading(false);
      }
    },
    [query, loading]
  );

  const hasResults = answer || sources.length > 0;

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      {/* Header */}
      <header
        style={{
          width: "100%",
          borderBottom: "1px solid var(--card-border)",
          padding: "16px 24px",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <h1
          style={{
            fontSize: 20,
            fontWeight: 700,
            letterSpacing: "-0.02em",
            margin: 0,
          }}
        >
          LegacyLens
        </h1>
        <span style={{ fontSize: 13, color: "var(--muted)" }}>
          RAG-powered exploration of the GnuCOBOL codebase
        </span>
      </header>

      {/* Main */}
      <main
        style={{
          width: "100%",
          maxWidth: 860,
          padding: "0 24px",
          flex: 1,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Search bar */}
        <form
          onSubmit={handleSubmit}
          style={{
            position: "sticky",
            top: 0,
            zIndex: 10,
            background: "var(--background)",
            paddingTop: hasResults ? 16 : 0,
            paddingBottom: 16,
            marginTop: hasResults ? 0 : "20vh",
            transition: "margin-top 0.3s ease",
          }}
        >
          {!hasResults && !loading && (
            <h2
              style={{
                fontSize: 28,
                fontWeight: 700,
                marginBottom: 8,
                letterSpacing: "-0.02em",
              }}
            >
              Ask about the GnuCOBOL codebase
            </h2>
          )}
          <div
            style={{
              display: "flex",
              gap: 8,
              background: "var(--card)",
              border: "1px solid var(--card-border)",
              borderRadius: 10,
              padding: 4,
            }}
          >
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder='e.g. "Where is the main entry point?" or "Show me error handling patterns"'
              style={{
                flex: 1,
                padding: "10px 14px",
                fontSize: 15,
                background: "transparent",
                border: "none",
                outline: "none",
                color: "var(--foreground)",
                fontFamily: "inherit",
              }}
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              style={{
                padding: "10px 20px",
                fontSize: 14,
                fontWeight: 600,
                background: loading || !query.trim() ? "var(--card-border)" : "var(--accent)",
                color: "#fff",
                border: "none",
                borderRadius: 7,
                cursor: loading || !query.trim() ? "not-allowed" : "pointer",
                transition: "background 0.15s",
              }}
              onMouseEnter={(e) => {
                if (!loading && query.trim())
                  (e.target as HTMLButtonElement).style.background = "var(--accent-hover)";
              }}
              onMouseLeave={(e) => {
                if (!loading && query.trim())
                  (e.target as HTMLButtonElement).style.background = "var(--accent)";
              }}
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </div>
          {!hasResults && !loading && (
            <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
              {[
                "Where is the main entry point?",
                "Find all file I/O operations",
                "Show me error handling patterns",
              ].map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => {
                    setQuery(q);
                    // Submit after setting query
                    setTimeout(() => {
                      const form = document.querySelector("form");
                      form?.requestSubmit();
                    }, 0);
                  }}
                  style={{
                    fontSize: 12,
                    padding: "6px 12px",
                    background: "transparent",
                    border: "1px solid var(--card-border)",
                    borderRadius: 6,
                    color: "var(--muted)",
                    cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                  onMouseEnter={(e) => {
                    (e.target as HTMLButtonElement).style.borderColor = "var(--accent)";
                    (e.target as HTMLButtonElement).style.color = "var(--accent)";
                  }}
                  onMouseLeave={(e) => {
                    (e.target as HTMLButtonElement).style.borderColor = "var(--card-border)";
                    (e.target as HTMLButtonElement).style.color = "var(--muted)";
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          )}
        </form>

        {/* Error */}
        {error && (
          <div
            style={{
              background: "#2d1215",
              border: "1px solid #7f1d1d",
              borderRadius: 8,
              padding: "12px 16px",
              marginBottom: 16,
              color: "#fca5a5",
              fontSize: 14,
            }}
          >
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && !answer && (
          <div style={{ marginBottom: 24 }}>
            <LoadingSpinner />
          </div>
        )}

        {/* Answer */}
        {answer && (
          <div style={{ marginBottom: 24 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 10,
              }}
            >
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--muted)", margin: 0 }}>
                Answer
              </h3>
              {latencyMs !== null && (
                <span style={{ fontSize: 12, color: "var(--muted)" }}>
                  {(latencyMs / 1000).toFixed(1)}s
                </span>
              )}
            </div>
            <div
              style={{
                background: "var(--card)",
                border: "1px solid var(--card-border)",
                borderRadius: 8,
                padding: "16px 20px",
              }}
            >
              <div
                className="markdown-content"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(answer) }}
              />
              {loading && (
                <span
                  style={{
                    display: "inline-block",
                    width: 6,
                    height: 16,
                    background: "var(--accent)",
                    marginLeft: 2,
                    animation: "blink 1s step-end infinite",
                    verticalAlign: "text-bottom",
                  }}
                >
                  <style>{`@keyframes blink { 50% { opacity: 0; } }`}</style>
                </span>
              )}
            </div>
          </div>
        )}

        {/* Sources */}
        {sources.length > 0 && (
          <div style={{ marginBottom: 48 }}>
            <h3
              style={{
                fontSize: 14,
                fontWeight: 600,
                color: "var(--muted)",
                marginBottom: 10,
              }}
            >
              Sources ({sources.length} chunks)
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {sources.map((s, i) => (
                <SourceCard key={`${s.file_path}-${s.line_start}-${i}`} source={s} index={i} />
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
