"""Known-good Gemini OpenAI-compatible baseline + optional relay diff."""

from __future__ import annotations

import json
import os
from typing import Any

from relay_audit.audit import run_python_audit
from relay_audit.paths import require_env, validate_out_path

GEMINI_OPENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"


def _probe_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in report.get("probe_results") or []:
        name = item.get("name")
        if name:
            out[str(name)] = {
                "ok": item.get("ok"),
                "latency_ms": item.get("latency_ms"),
                "error": item.get("error"),
            }
    return out


def run_baseline(
    *,
    provider: str,
    model: str,
    profile: str,
    out: str | None,
    relay_report_path: str | None,
) -> int:
    if provider != "gemini":
        raise SystemExit(f"unsupported --provider {provider!r}; only gemini is implemented")

    api_key = require_env("GEMINI_API_KEY")
    # Temporarily point RELAY_API_KEY semantics: Gemini key is the auth for the control.
    code, baseline = run_python_audit(
        base_url=GEMINI_OPENAI_BASE,
        api_key=api_key,
        model=model,
        profile=profile,
        out=None,
    )

    diff: dict[str, Any] | None = None
    if relay_report_path:
        path = validate_out_path(relay_report_path)
        if not path.is_file():
            raise SystemExit(f"relay report not found: {path}")
        relay = json.loads(path.read_text(encoding="utf-8"))
        base_probes = _probe_index(baseline)
        relay_probes = _probe_index(relay)
        names = sorted(set(base_probes) | set(relay_probes))
        per_probe = []
        for name in names:
            per_probe.append(
                {
                    "probe": name,
                    "baseline": base_probes.get(name),
                    "relay": relay_probes.get(name),
                }
            )
        diff = {
            "baseline_verdict": baseline.get("verdict"),
            "baseline_score": baseline.get("score"),
            "relay_verdict": relay.get("verdict"),
            "relay_score": relay.get("score"),
            "probes": per_probe,
        }

    report = {
        "provider": provider,
        "model": model,
        "profile": profile,
        "baseline": baseline,
        "diff": diff,
        "gemini_base_url": GEMINI_OPENAI_BASE,
        "run_exit_code": code,
        # Preserve env name presence only (never the value).
        "gemini_api_key_set": bool(os.environ.get("GEMINI_API_KEY")),
    }
    if out:
        validate_out_path(out).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps({"verdict": baseline.get("verdict"), "score": baseline.get("score")}))
    return 0 if baseline.get("verdict") else 2
