import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [messageCount, setMessageCount] = useState(0);
  const bottomRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`);
        if (!res.ok) {
          throw new Error(`Health check failed (${res.status})`);
        }
        const data = await res.json();
        if (!cancelled) {
          setHealth(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not reach API");
          setHealth(null);
        }
      }
    }

    checkHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  async function resetSession() {
    setMessages([]);
    setMessageCount(0);

    try {
      const res = await fetch(`${API_BASE}/sessions`, { method: "POST" });
      if (!res.ok) {
        throw new Error(`Could not create session (${res.status})`);
      }
      const payload = await res.json();
      setSessionId(payload.session_id || "");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create session");
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const message = input.trim();
    if (!message || isStreaming) {
      return;
    }

    setInput("");
    setIsStreaming(true);
    setError(null);

    const userMessage = { role: "user", content: message };
    const assistantMessage = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, userMessage, assistantMessage]);

    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId || undefined,
          message,
        }),
      });

      if (!res.ok || !res.body) {
        throw new Error(`Stream request failed (${res.status})`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventBlock of events) {
          const dataLines = eventBlock
            .split("\n")
            .filter((line) => line.startsWith("data: "))
            .map((line) => line.slice(6));

          if (!dataLines.length) {
            continue;
          }

          try {
            const eventPayload = JSON.parse(dataLines.join("\n"));

            if (eventPayload.type === "session" && eventPayload.session_id) {
              setSessionId(eventPayload.session_id);
              continue;
            }

            if (eventPayload.type === "token") {
              setMessages((prev) => {
                const next = [...prev];
                for (let i = next.length - 1; i >= 0; i -= 1) {
                  if (next[i].role === "assistant") {
                    next[i] = {
                      ...next[i],
                      content: `${next[i].content}${eventPayload.content || ""}`,
                    };
                    break;
                  }
                }
                return next;
              });
              continue;
            }

            if (eventPayload.type === "done") {
              setMessageCount(eventPayload.message_count || 0);
              continue;
            }

            if (eventPayload.type === "error") {
              throw new Error(eventPayload.detail || "Streaming failed");
            }
          } catch (parseErr) {
            throw new Error(
              parseErr instanceof Error ? parseErr.message : "Invalid stream event",
            );
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed");
      setMessages((prev) => {
        if (!prev.length) {
          return prev;
        }
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant" && !last.content) {
          next[next.length - 1] = {
            role: "assistant",
            content: "I could not generate a reply. Please try again.",
          };
        }
        return next;
      });
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <p className="brand">NovaDesk Support</p>
        <h1>Customer Chatbot</h1>
        <p className="subtitle">Multi-turn support with memory and streaming replies.</p>
      </header>

      <section className="status-panel" aria-live="polite">
        <h2>API status</h2>
        {error && <p className="status error">Issue — {error}</p>}
        {health && !error && (
          <p className="status ok">
            Online — {health.service} · model {health.ollama_model}
          </p>
        )}
        {!health && !error && <p className="status">Checking…</p>}
      </section>

      <section className="chat-shell">
        <div className="chat-toolbar">
          <div className="session">
            <span className="session-label">Session</span>
            <code className="session-id">{sessionId || "will be created on first message"}</code>
          </div>
          <button type="button" className="btn-secondary" onClick={resetSession} disabled={isStreaming}>
            New chat
          </button>
        </div>

        <div className="chat-log" aria-live="polite">
          {messages.length === 0 && (
            <p className="empty">
              Ask about plans, refunds, billing, or exports. Follow-up questions will use memory.
            </p>
          )}

          {messages.map((msg, index) => (
            <div key={`${msg.role}-${index}`} className={`bubble ${msg.role}`}>
              <p>{msg.content || (msg.role === "assistant" ? "…" : "")}</p>
            </div>
          ))}

          {isStreaming && <p className="typing">Assistant is typing…</p>}
          <div ref={bottomRef} />
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Type your support question..."
            value={input}
            onChange={(event) => setInput(event.target.value)}
            disabled={isStreaming}
          />
          <button type="submit" className="btn-primary" disabled={isStreaming || !input.trim()}>
            Send
          </button>
        </form>

        <p className="footnote">Stored messages in this session: {messageCount}</p>
      </section>
    </div>
  );
}
