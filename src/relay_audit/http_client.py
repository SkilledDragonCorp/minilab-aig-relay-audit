"""HTTP SSE path: POST /api/v1/relay/check/stream against a local api-checker serve."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from relay_audit.paths import validate_base_url, validate_model_id, validate_out_path

ALGORITHMS = frozenset({"quick", "full"})
LANGUAGES = frozenset({"en", "zh"})


def _validate_server(server: str) -> str:
    server = server.strip().rstrip("/")
    parsed = urlparse(server)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit("--server must be an http(s) URL")
    return server


def parse_sse_events(text: str) -> list[tuple[str, dict[str, Any]]]:
    """Parse SSE text into (event, data_dict) pairs."""
    events: list[tuple[str, dict[str, Any]]] = []
    event_name = "message"
    data_lines: list[str] = []
    for line in text.splitlines():
        if not line:
            if data_lines:
                payload = "\n".join(data_lines)
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    data = {"raw": payload}
                events.append((event_name, data if isinstance(data, dict) else {"raw": data}))
            event_name = "message"
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[len("event:") :].strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line[len("data:") :].lstrip())
    if data_lines:
        payload = "\n".join(data_lines)
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = {"raw": payload}
        events.append((event_name, data if isinstance(data, dict) else {"raw": data}))
    return events


def run_http_audit(
    *,
    server: str,
    base_url: str,
    api_key: str,
    model: str,
    algorithm: str,
    language: str,
    out: str | None,
    timeout_s: float = 180.0,
) -> tuple[int, dict[str, Any]]:
    server = _validate_server(server)
    base_url = validate_base_url(base_url)
    model = validate_model_id(model)
    if algorithm not in ALGORITHMS:
        raise SystemExit(f"unknown --algorithm {algorithm!r}; allowed: quick, full")
    if language not in LANGUAGES:
        raise SystemExit(f"unknown --language {language!r}; allowed: en, zh")

    body = {
        "algorithm": algorithm,
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "language": language,
    }
    url = f"{server}/api/v1/relay/check/stream"
    try:
        with httpx.Client(timeout=timeout_s) as client:
            with client.stream(
                "POST",
                url,
                json=body,
                headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
            ) as response:
                if response.status_code >= 400:
                    detail = response.read().decode("utf-8", errors="replace")
                    report = {
                        "error": "http_error",
                        "status_code": response.status_code,
                        "detail": detail[:2000],
                        "server": server,
                        "base_url": base_url,
                        "model": model,
                        "algorithm": algorithm,
                    }
                    if out:
                        validate_out_path(out).write_text(
                            json.dumps(report, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8",
                        )
                    return 2, report
                chunks: list[str] = []
                deadline = time.monotonic() + timeout_s
                for chunk in response.iter_text():
                    chunks.append(chunk)
                    if time.monotonic() > deadline:
                        report = {"error": "timeout", "server": server}
                        if out:
                            validate_out_path(out).write_text(
                                json.dumps(report, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8",
                            )
                        return 2, report
                text = "".join(chunks)
    except httpx.HTTPError as exc:
        report = {"error": "http_error", "detail": str(exc), "server": server}
        if out:
            validate_out_path(out).write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        return 2, report

    events = parse_sse_events(text)
    result_payload: dict[str, Any] | None = None
    for name, data in events:
        if name == "result":
            # Upstream wraps as {data: {...}} or may be the data itself.
            if isinstance(data.get("data"), dict):
                result_payload = data["data"]
            else:
                result_payload = data

    if result_payload is None:
        report = {
            "error": "missing_result_event",
            "events": [{"event": n, "keys": sorted(d.keys())} for n, d in events],
            "server": server,
            "base_url": base_url,
            "model": model,
            "algorithm": algorithm,
        }
        if out:
            validate_out_path(out).write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        return 2, report

    report = {
        "result": result_payload,
        "server": server,
        "base_url": base_url,
        "model": model,
        "algorithm": algorithm,
        "language": language,
    }
    if out:
        validate_out_path(out).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    verdict = str(result_payload.get("overall_verdict", "")).lower()
    if verdict == "pass":
        return 0, report
    if verdict == "risk":
        return 1, report
    return 2, report
