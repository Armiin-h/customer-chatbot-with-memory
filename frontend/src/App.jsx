import { useEffect, useState } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

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

  return (
    <div className="page">
      <header className="header">
        <p className="brand">NovaDesk Support</p>
        <h1>Customer Chatbot</h1>
        <p className="subtitle">
          Multi-turn support agent with conversation memory. Chat UI arrives in a later day.
        </p>
      </header>

      <section className="status-panel" aria-live="polite">
        <h2>API status</h2>
        {error && <p className="status error">Offline — {error}</p>}
        {health && !error && (
          <p className="status ok">
            Online — {health.service} · model {health.ollama_model}
          </p>
        )}
        {!health && !error && <p className="status">Checking…</p>}
      </section>
    </div>
  );
}
