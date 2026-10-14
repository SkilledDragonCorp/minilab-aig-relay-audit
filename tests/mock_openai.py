"""Stdlib mock OpenAI-compatible server for keyless e2e tests."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

FIXED_TEXT = "I am a deterministic fake model."


class MockOpenAIHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            data = {}
        return data if isinstance(data, dict) else {}

    def _send(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/v1/models", "/models"}:
            payload = {"data": [{"id": "gpt-4o", "object": "model"}]}
            self._send(200, json.dumps(payload).encode("utf-8"))
            return
        self._send(404, b'{"error":"not found"}')

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in {"/v1/chat/completions", "/chat/completions"}:
            self._send(404, b'{"error":"not found"}')
            return
        req = self._read_json()
        if req.get("stream"):
            # Minimal SSE chat completion stream.
            chunks = [
                {
                    "id": "chatcmpl-mock",
                    "object": "chat.completion.chunk",
                    "model": req.get("model", "gpt-4o"),
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant", "content": FIXED_TEXT},
                            "finish_reason": None,
                        }
                    ],
                },
                {
                    "id": "chatcmpl-mock",
                    "object": "chat.completion.chunk",
                    "model": req.get("model", "gpt-4o"),
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                },
            ]
            body_parts = [f"data: {json.dumps(c)}\n\n".encode() for c in chunks]
            body_parts.append(b"data: [DONE]\n\n")
            body = b"".join(body_parts)
            self._send(200, body, content_type="text/event-stream")
            return

        payload = {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "model": req.get("model", "gpt-4o"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": FIXED_TEXT},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        self._send(200, json.dumps(payload).encode("utf-8"))


class MockOpenAIServer:
    def __init__(self) -> None:
        self._httpd = HTTPServer(("127.0.0.1", 0), MockOpenAIHandler)
        self.port = int(self._httpd.server_address[1])
        self.base_url = f"http://127.0.0.1:{self.port}/v1"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._httpd.shutdown()
        self._thread.join(timeout=5)
