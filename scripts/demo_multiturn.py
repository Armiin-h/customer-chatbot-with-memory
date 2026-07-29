#!/usr/bin/env python3
"""Smoke-demo multi-turn memory + optional SSE against a running API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def request_json(method: str, url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def stream_chat(url: str, payload: dict) -> tuple[str, dict | None]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    tokens: list[str] = []
    done: dict | None = None
    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            if event.get("type") == "token":
                chunk = event.get("content") or ""
                tokens.append(chunk)
                print(chunk, end="", flush=True)
            elif event.get("type") == "done":
                done = event
            elif event.get("type") == "error":
                raise RuntimeError(event.get("detail") or "stream error")
    print()
    return "".join(tokens), done


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo NovaDesk multi-turn chat memory")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="API base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Use /chat/stream for the follow-up turn",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    try:
        health = request_json("GET", f"{base}/health")
    except urllib.error.URLError as exc:
        print(f"API not reachable at {base}: {exc}", file=sys.stderr)
        return 1

    print(f"health: {health}")
    session = request_json("POST", f"{base}/sessions")
    session_id = session["session_id"]
    print(f"session: {session_id}")

    turn1 = request_json(
        "POST",
        f"{base}/chat",
        {
            "session_id": session_id,
            "message": "Hi — I upgraded to the Pro plan yesterday for three seats.",
        },
    )
    print("\n--- turn 1 ---")
    print(turn1["reply"])
    print(f"(message_count={turn1['message_count']})")

    follow_up = "How much does that plan cost per user each month?"
    print("\n--- turn 2 ---")
    if args.stream:
        _, done = stream_chat(
            f"{base}/chat/stream",
            {"session_id": session_id, "message": follow_up},
        )
        count = done.get("message_count") if done else "?"
        print(f"(message_count={count})")
    else:
        turn2 = request_json(
            "POST",
            f"{base}/chat",
            {"session_id": session_id, "message": follow_up},
        )
        print(turn2["reply"])
        print(f"(message_count={turn2['message_count']})")

    info = request_json("GET", f"{base}/sessions/{session_id}")
    print(f"\nsession info: {info}")
    print("\nDemo complete - follow-up should reference Pro / $12 if memory works.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
