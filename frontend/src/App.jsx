import { useEffect, useRef, useState } from "react";
import { API_BASE, createSession, fetchHealth, streamChat } from "./api";
import { markdownToHtml } from "./markdown";
import "./App.css";

export default function App() {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(null);
  const [chatError, setChatError] = useState(null);
  const [sessionId, setSessionId] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [messageCount, setMessageCount] = useState(0);
  const [lastFailedMessage, setLastFailedMessage] = useState("");
  const bottomRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function checkHealth() {
      try {
        const data = await fetchHealth(controller.signal);
        if (!cancelled) {
          setHealth(data);
          setHealthError(null);
        }
      } catch (err) {
        if (!cancelled && err?.name !== "AbortError") {
          setHealth(null);
          setHealthError(err instanceof Error ? err.message : "Could not reach API");
        }
      }
    }

    checkHealth();
    const timer = setInterval(checkHealth, 30000);

    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  async function resetSession() {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }

    setMessages([]);
    setMessageCount(0);
    setChatError(null);
    setLastFailedMessage("");
    setIsStreaming(false);

    try {
      const payload = await createSession();
      setSessionId(payload.session_id || "");
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Could not create session");
    }
  }

  function appendToken(token) {
    setMessages((prev) => {
      const next = [...prev];
      for (let i = next.length - 1; i >= 0; i -= 1) {
        if (next[i].role === "assistant") {
          next[i] = {
            ...next[i],
            content: `${next[i].content}${token || ""}`,
          };
          break;
        }
      }
      return next;
    });
  }

  async function sendMessage(rawMessage) {
    const message = rawMessage.trim();
    if (!message || isStreaming) {
      return;
    }

    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    setInput("");
    setIsStreaming(true);
    setChatError(null);
    setLastFailedMessage("");

    setMessages((prev) => [
      ...prev,
      { role: "user", content: message },
      { role: "assistant", content: "" },
    ]);

    try {
      await streamChat({
        sessionId,
        message,
        signal: controller.signal,
        onEvent: (eventPayload) => {
          if (eventPayload.type === "session" && eventPayload.session_id) {
            setSessionId(eventPayload.session_id);
          } else if (eventPayload.type === "token") {
            appendToken(eventPayload.content);
          } else if (eventPayload.type === "done") {
            setMessageCount(eventPayload.message_count || 0);
          }
        },
      });
    } catch (err) {
      if (err?.name === "AbortError") {
        return;
      }
      const detail = err instanceof Error ? err.message : "Chat request failed";
      setChatError(detail);
      setLastFailedMessage(message);
      setMessages((prev) => {
        if (!prev.length) {
          return prev;
        }
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant" && !last.content) {
          next[next.length - 1] = {
            role: "assistant",
            content: "I could not generate a reply. Use **Retry** below or send a new message.",
          };
        }
        return next;
      });
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
      }
      setIsStreaming(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendMessage(input);
  }

  function handleRetry() {
    if (!lastFailedMessage || isStreaming) {
      return;
    }
    const message = lastFailedMessage;
    // Drop the failed user+assistant pair, then resend after state settles
    setMessages((prev) => (prev.length >= 2 ? prev.slice(0, -2) : prev));
    setTimeout(() => {
      sendMessage(message);
    }, 0);
  }

  function handleStop() {
    abortRef.current?.abort();
    setIsStreaming(false);
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
        {healthError && <p className="status error">Offline — {healthError}</p>}
        {health && !healthError && (
          <p className="status ok">
            Online — {health.service} · model {health.ollama_model} · {API_BASE}
          </p>
        )}
        {!health && !healthError && <p className="status">Checking…</p>}
      </section>

      {chatError && (
        <div className="error-banner" role="alert">
          <p>{chatError}</p>
          <div className="error-actions">
            {lastFailedMessage && (
              <button type="button" className="btn-secondary" onClick={handleRetry} disabled={isStreaming}>
                Retry
              </button>
            )}
            <button type="button" className="btn-secondary" onClick={() => setChatError(null)}>
              Dismiss
            </button>
          </div>
        </div>
      )}

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
              {msg.role === "assistant" ? (
                <div
                  className="md"
                  dangerouslySetInnerHTML={{
                    __html: markdownToHtml(msg.content || (isStreaming ? "…" : "")),
                  }}
                />
              ) : (
                <p>{msg.content}</p>
              )}
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
            aria-label="Message"
          />
          {isStreaming ? (
            <button type="button" className="btn-secondary" onClick={handleStop}>
              Stop
            </button>
          ) : (
            <button type="submit" className="btn-primary" disabled={!input.trim()}>
              Send
            </button>
          )}
        </form>

        <p className="footnote">Stored messages in this session: {messageCount}</p>
      </section>
    </div>
  );
}
