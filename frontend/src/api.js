/** Resolve API base for local Vite and Docker (nginx /api proxy). */
export const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchHealth(signal) {
  const res = await fetch(`${API_BASE}/health`, { signal });
  if (!res.ok) {
    throw new Error(`Health check failed (${res.status})`);
  }
  return res.json();
}

export async function createSession() {
  const res = await fetch(`${API_BASE}/sessions`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`Could not create session (${res.status})`);
  }
  return res.json();
}

/**
 * Stream one chat turn from POST /chat/stream.
 * Calls onEvent(payload) for each SSE JSON object.
 */
export async function streamChat({ sessionId, message, signal, onEvent }) {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId || undefined,
      message,
    }),
    signal,
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

      let eventPayload;
      try {
        eventPayload = JSON.parse(dataLines.join("\n"));
      } catch {
        throw new Error("Invalid stream event");
      }

      onEvent(eventPayload);

      if (eventPayload.type === "error") {
        throw new Error(eventPayload.detail || "Streaming failed");
      }
    }
  }
}
