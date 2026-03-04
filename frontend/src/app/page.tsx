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

interface DepRef {
  name: string;
  file_path: string | null;
  line_start: number | null;
  line_end: number | null;
  chunk_type: string | null;
}

interface DepsResult {
  target: { name: string; file_path: string; line_start: number; line_end: number };
  calls: DepRef[];
  called_by: DepRef[];
}

type FeatureType = "explain" | "document" | "dependencies" | "business-logic";

// ── Minimal Markdown renderer ───────────────────────────────────────

function renderMarkdown(text: string): string {
  let html = text
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_m, _lang, code) => {
      const escaped = code
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      return `<pre><code>${escaped}</code></pre>`;
    })
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/^---$/gm, "<hr/>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/^\d+\. (.+)$/gm, "<li>$1</li>");
  html = html.replace(/((<li>.*<\/li>\n?)+)/g, "<ul>$1</ul>");
  html = html.replace(
    /^(?!<[hupol]|<li|<hr|<blockquote|<pre)(.+)$/gm,
    "<p>$1</p>"
  );
  return html;
}

// ── SSE streaming helper ────────────────────────────────────────────

async function streamFeature(
  endpoint: string,
  filePath: string,
  functionName: string | null,
  onToken: (text: string) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_URL}/api/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_path: filePath, function_name: functionName }),
    signal,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");
  const decoder = new TextDecoder();
  let buffer = "";
  let accumulated = "";
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
        if (event.type === "token") {
          accumulated += event.token;
          onToken(accumulated);
        }
      } catch { /* skip */ }
    }
  }
}

// ── Feature panel buttons config ────────────────────────────────────

const FEATURES: { type: FeatureType; label: string; color: string; bg: string }[] = [
  { type: "explain", label: "Explain", color: "#93c5fd", bg: "#1e3a5f" },
  { type: "document", label: "Docs", color: "#86efac", bg: "#14532d" },
  { type: "dependencies", label: "Deps", color: "#fbbf24", bg: "#78350f" },
  { type: "business-logic", label: "Business Logic", color: "#c4b5fd", bg: "#3b0764" },
];

// ── Components ──────────────────────────────────────────────────────

function FeaturePanel({
  source,
  feature,
  onClose,
}: {
  source: Source;
  feature: FeatureType;
  onClose: () => void;
}) {
  const [content, setContent] = useState("");
  const [deps, setDeps] = useState<DepsResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Run on mount
  useState(() => {
    const controller = new AbortController();
    abortRef.current = controller;

    if (feature === "dependencies") {
      fetch(`${API_URL}/api/dependencies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_path: source.file_path,
          function_name: source.function_name,
        }),
        signal: controller.signal,
      })
        .then((res) => {
          if (!res.ok) throw new Error(`API error: ${res.status}`);
          return res.json();
        })
        .then((data) => {
          setDeps(data);
          setLoading(false);
        })
        .catch((err) => {
          if (err.name !== "AbortError") {
            setError(err.message);
            setLoading(false);
          }
        });
    } else {
      streamFeature(
        feature,
        source.file_path,
        source.function_name,
        (text) => setContent(text),
        controller.signal
      )
        .then(() => setLoading(false))
        .catch((err) => {
          if (err.name !== "AbortError") {
            setError(err.message);
            setLoading(false);
          }
        });
    }

    return undefined;
  });

  const featureMeta = FEATURES.find((f) => f.type === feature)!;

  return (
    <div
      style={{
        borderTop: `2px solid ${featureMeta.bg}`,
        background: "#111218",
        padding: "14px 16px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 10,
        }}
      >
        <span
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: featureMeta.color,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          {featureMeta.label}
        </span>
        <button
          onClick={() => {
            abortRef.current?.abort();
            onClose();
          }}
          style={{
            background: "none",
            border: "none",
            color: "var(--muted)",
            cursor: "pointer",
            fontSize: 16,
            padding: "0 4px",
          }}
        >
          x
        </button>
      </div>

      {error && (
        <div style={{ color: "#fca5a5", fontSize: 13 }}>{error}</div>
      )}

      {feature === "dependencies" && deps && (
        <div style={{ fontSize: 13, lineHeight: 1.7 }}>
          <div style={{ marginBottom: 10 }}>
            <strong style={{ color: "#f4f4f5" }}>Calls ({deps.calls.length}):</strong>
            {deps.calls.length === 0 && (
              <span style={{ color: "var(--muted)", marginLeft: 8 }}>None detected</span>
            )}
            {deps.calls.map((c, i) => (
              <div
                key={i}
                style={{
                  padding: "4px 0 4px 12px",
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: 12,
                  color: c.file_path ? "#93c5fd" : "var(--muted)",
                }}
              >
                {c.name}
                {c.file_path && (
                  <span style={{ color: "var(--muted)" }}>
                    {" "}
                    - {c.file_path.replace(/^.*?data\/gnucobol\//, "")}:{c.line_start}
                  </span>
                )}
              </div>
            ))}
          </div>
          <div>
            <strong style={{ color: "#f4f4f5" }}>Called by ({deps.called_by.length}):</strong>
            {deps.called_by.length === 0 && (
              <span style={{ color: "var(--muted)", marginLeft: 8 }}>None found</span>
            )}
            {deps.called_by.map((c, i) => (
              <div
                key={i}
                style={{
                  padding: "4px 0 4px 12px",
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: 12,
                  color: "#fbbf24",
                }}
              >
                {c.name}
                {c.file_path && (
                  <span style={{ color: "var(--muted)" }}>
                    {" "}
                    - {c.file_path.replace(/^.*?data\/gnucobol\//, "")}:{c.line_start}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {feature !== "dependencies" && content && (
        <div
          className="markdown-content"
          style={{ fontSize: 13 }}
          dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
        />
      )}

      {loading && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--muted)" }}>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            style={{ animation: "spin 1s linear infinite" }}
          >
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            <circle
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="3"
              fill="none"
              strokeDasharray="30 70"
            />
          </svg>
          <span style={{ fontSize: 12 }}>
            {feature === "dependencies" ? "Analyzing dependencies..." : "Generating..."}
          </span>
        </div>
      )}
    </div>
  );
}

function SourceCard({ source, index }: { source: Source; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const [activeFeature, setActiveFeature] = useState<FeatureType | null>(null);
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
      {/* Action buttons */}
      <div
        style={{
          display: "flex",
          gap: 6,
          padding: "8px 14px",
          borderTop: "1px solid var(--card-border)",
          background: "var(--card)",
        }}
      >
        {FEATURES.map((f) => (
          <button
            key={f.type}
            onClick={() =>
              setActiveFeature(activeFeature === f.type ? null : f.type)
            }
            style={{
              fontSize: 11,
              padding: "4px 10px",
              background: activeFeature === f.type ? f.bg : "transparent",
              border: `1px solid ${activeFeature === f.type ? f.color : "var(--card-border)"}`,
              borderRadius: 5,
              color: activeFeature === f.type ? f.color : "var(--muted)",
              cursor: "pointer",
              transition: "all 0.15s",
              fontWeight: activeFeature === f.type ? 600 : 400,
            }}
          >
            {f.label}
          </button>
        ))}
      </div>
      {/* Feature panel */}
      {activeFeature && (
        <FeaturePanel
          key={activeFeature}
          source={source}
          feature={activeFeature}
          onClose={() => setActiveFeature(null)}
        />
      )}
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

// ── Code Understanding Section ──────────────────────────────────────

function CodeUnderstanding() {
  const [filePath, setFilePath] = useState("");
  const [functionName, setFunctionName] = useState("");
  const [selectedFeature, setSelectedFeature] = useState<FeatureType>("explain");
  const [content, setContent] = useState("");
  const [deps, setDeps] = useState<DepsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleRun = useCallback(async () => {
    if (!filePath.trim()) return;
    setContent("");
    setDeps(null);
    setError(null);
    setLoading(true);

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const fn = functionName.trim() || null;

    try {
      if (selectedFeature === "dependencies") {
        const res = await fetch(`${API_URL}/api/dependencies`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file_path: filePath.trim(), function_name: fn }),
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        setDeps(await res.json());
      } else {
        await streamFeature(
          selectedFeature,
          filePath.trim(),
          fn,
          (text) => setContent(text),
          controller.signal
        );
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }, [filePath, functionName, selectedFeature]);

  const featureMeta = FEATURES.find((f) => f.type === selectedFeature)!;

  return (
    <div
      style={{
        background: "var(--card)",
        border: "1px solid var(--card-border)",
        borderRadius: 8,
        padding: 16,
      }}
    >
      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <input
          type="text"
          value={filePath}
          onChange={(e) => setFilePath(e.target.value)}
          placeholder="File path (e.g. cobc/cobc.c)"
          style={{
            flex: 2,
            padding: "8px 12px",
            fontSize: 13,
            background: "var(--code-bg)",
            border: "1px solid var(--card-border)",
            borderRadius: 6,
            color: "var(--foreground)",
            fontFamily: "var(--font-geist-mono), monospace",
            outline: "none",
            minWidth: 180,
          }}
        />
        <input
          type="text"
          value={functionName}
          onChange={(e) => setFunctionName(e.target.value)}
          placeholder="Function name (optional)"
          style={{
            flex: 1,
            padding: "8px 12px",
            fontSize: 13,
            background: "var(--code-bg)",
            border: "1px solid var(--card-border)",
            borderRadius: 6,
            color: "var(--foreground)",
            fontFamily: "var(--font-geist-mono), monospace",
            outline: "none",
            minWidth: 140,
          }}
        />
      </div>
      <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
        {FEATURES.map((f) => (
          <button
            key={f.type}
            onClick={() => setSelectedFeature(f.type)}
            style={{
              fontSize: 12,
              padding: "5px 12px",
              background: selectedFeature === f.type ? f.bg : "transparent",
              border: `1px solid ${selectedFeature === f.type ? f.color : "var(--card-border)"}`,
              borderRadius: 5,
              color: selectedFeature === f.type ? f.color : "var(--muted)",
              cursor: "pointer",
              fontWeight: selectedFeature === f.type ? 600 : 400,
            }}
          >
            {f.label}
          </button>
        ))}
        <button
          onClick={handleRun}
          disabled={loading || !filePath.trim()}
          style={{
            marginLeft: "auto",
            fontSize: 12,
            padding: "5px 16px",
            fontWeight: 600,
            background:
              loading || !filePath.trim() ? "var(--card-border)" : "var(--accent)",
            color: "#fff",
            border: "none",
            borderRadius: 5,
            cursor: loading || !filePath.trim() ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Running..." : "Run"}
        </button>
      </div>

      {error && (
        <div style={{ color: "#fca5a5", fontSize: 13, marginBottom: 8 }}>{error}</div>
      )}

      {loading && !content && !deps && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--muted)" }}>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            style={{ animation: "spin 1s linear infinite" }}
          >
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            <circle
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="3"
              fill="none"
              strokeDasharray="30 70"
            />
          </svg>
          <span style={{ fontSize: 12 }}>
            {selectedFeature === "dependencies"
              ? "Analyzing dependencies..."
              : "Generating..."}
          </span>
        </div>
      )}

      {content && (
        <div
          style={{
            background: "var(--code-bg)",
            borderRadius: 6,
            padding: "12px 16px",
            borderLeft: `3px solid ${featureMeta.color}`,
          }}
        >
          <div
            className="markdown-content"
            style={{ fontSize: 13 }}
            dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
          />
          {loading && (
            <span
              style={{
                display: "inline-block",
                width: 6,
                height: 14,
                background: featureMeta.color,
                animation: "blink 1s step-end infinite",
                verticalAlign: "text-bottom",
              }}
            >
              <style>{`@keyframes blink { 50% { opacity: 0; } }`}</style>
            </span>
          )}
        </div>
      )}

      {deps && (
        <div
          style={{
            background: "var(--code-bg)",
            borderRadius: 6,
            padding: "12px 16px",
            borderLeft: "3px solid #fbbf24",
            fontSize: 13,
            lineHeight: 1.7,
          }}
        >
          <div style={{ marginBottom: 10 }}>
            <strong style={{ color: "#f4f4f5" }}>Calls ({deps.calls.length}):</strong>
            {deps.calls.length === 0 && (
              <span style={{ color: "var(--muted)", marginLeft: 8 }}>None detected</span>
            )}
            {deps.calls.map((c, i) => (
              <div
                key={i}
                style={{
                  padding: "3px 0 3px 12px",
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: 12,
                  color: c.file_path ? "#93c5fd" : "var(--muted)",
                }}
              >
                {c.name}
                {c.file_path && (
                  <span style={{ color: "var(--muted)" }}>
                    {" "}
                    - {c.file_path.replace(/^.*?data\/gnucobol\//, "")}:{c.line_start}
                  </span>
                )}
              </div>
            ))}
          </div>
          <div>
            <strong style={{ color: "#f4f4f5" }}>Called by ({deps.called_by.length}):</strong>
            {deps.called_by.length === 0 && (
              <span style={{ color: "var(--muted)", marginLeft: 8 }}>None found</span>
            )}
            {deps.called_by.map((c, i) => (
              <div
                key={i}
                style={{
                  padding: "3px 0 3px 12px",
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: 12,
                  color: "#fbbf24",
                }}
              >
                {c.name}
                {c.file_path && (
                  <span style={{ color: "var(--muted)" }}>
                    {" "}
                    - {c.file_path.replace(/^.*?data\/gnucobol\//, "")}:{c.line_start}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────

export default function Home() {
  const [activeTab, setActiveTab] = useState<"search" | "understand">("search");
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

      setAnswer("");
      setSources([]);
      setError(null);
      setLatencyMs(null);
      setLoading(true);

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
              // skip
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
          padding: "12px 24px",
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
        <span style={{ fontSize: 13, color: "var(--muted)", marginRight: "auto" }}>
          RAG-powered exploration of the GnuCOBOL codebase
        </span>
        <div style={{ display: "flex", gap: 4 }}>
          {(["search", "understand"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: "6px 14px",
                fontSize: 13,
                fontWeight: activeTab === tab ? 600 : 400,
                background: activeTab === tab ? "var(--accent)" : "transparent",
                color: activeTab === tab ? "#fff" : "var(--muted)",
                border: "none",
                borderRadius: 6,
                cursor: "pointer",
              }}
            >
              {tab === "search" ? "Search" : "Code Understanding"}
            </button>
          ))}
        </div>
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
        {activeTab === "understand" && (
          <div style={{ marginTop: 24 }}>
            <h2
              style={{
                fontSize: 18,
                fontWeight: 600,
                marginBottom: 12,
                letterSpacing: "-0.01em",
              }}
            >
              Code Understanding
            </h2>
            <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 16 }}>
              Enter a file path and optional function name to analyze any function in the
              GnuCOBOL codebase. File paths match what&apos;s stored in Pinecone (e.g.
              paths containing data/gnucobol/).
            </p>
            <CodeUnderstanding />
          </div>
        )}

        {activeTab === "search" && (
          <>
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
                    background:
                      loading || !query.trim()
                        ? "var(--card-border)"
                        : "var(--accent)",
                    color: "#fff",
                    border: "none",
                    borderRadius: 7,
                    cursor:
                      loading || !query.trim() ? "not-allowed" : "pointer",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) => {
                    if (!loading && query.trim())
                      (e.target as HTMLButtonElement).style.background =
                        "var(--accent-hover)";
                  }}
                  onMouseLeave={(e) => {
                    if (!loading && query.trim())
                      (e.target as HTMLButtonElement).style.background =
                        "var(--accent)";
                  }}
                >
                  {loading ? "Searching..." : "Search"}
                </button>
              </div>
              {!hasResults && !loading && (
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    marginTop: 12,
                    flexWrap: "wrap",
                  }}
                >
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
                        (e.target as HTMLButtonElement).style.borderColor =
                          "var(--accent)";
                        (e.target as HTMLButtonElement).style.color =
                          "var(--accent)";
                      }}
                      onMouseLeave={(e) => {
                        (e.target as HTMLButtonElement).style.borderColor =
                          "var(--card-border)";
                        (e.target as HTMLButtonElement).style.color =
                          "var(--muted)";
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
                  <h3
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color: "var(--muted)",
                      margin: 0,
                    }}
                  >
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
                    dangerouslySetInnerHTML={{
                      __html: renderMarkdown(answer),
                    }}
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
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                  }}
                >
                  {sources.map((s, i) => (
                    <SourceCard
                      key={`${s.file_path}-${s.line_start}-${i}`}
                      source={s}
                      index={i}
                    />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
