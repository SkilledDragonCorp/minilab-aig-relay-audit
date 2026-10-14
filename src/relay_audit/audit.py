"""In-process Python path: run_relay_audit from upstream api_checker."""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

from relay_audit.paths import (
    api_checker_dir,
    validate_base_url,
    validate_model_id,
    validate_out_path,
)


def _ensure_api_checker_on_path() -> Path:
    checker = api_checker_dir()
    if not checker.is_dir():
        raise RuntimeError(f"missing upstream api_checker at {checker}")
    inserted = str(checker.resolve())
    if inserted not in sys.path:
        sys.path.insert(0, inserted)
    return checker


def import_relay_audit():
    _ensure_api_checker_on_path()
    from algorithms.relay_audit import PROFILES, run_relay_audit  # type: ignore[import-not-found]

    return PROFILES, run_relay_audit


def serialize_result(result: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in result.items():
        if key in {"findings", "probe_results"} and isinstance(value, list):
            out[key] = [
                dataclasses.asdict(item) if dataclasses.is_dataclass(item) else item
                for item in value
            ]
        else:
            out[key] = value
    return out


def run_python_audit(
    *,
    base_url: str,
    api_key: str,
    model: str,
    profile: str,
    out: str | None,
) -> tuple[int, dict[str, Any]]:
    base_url = validate_base_url(base_url)
    model = validate_model_id(model)
    try:
        profiles, run_relay_audit = import_relay_audit()
    except Exception as exc:  # noqa: BLE001 — surface import failures as exit 2
        raise SystemExit(f"failed to import upstream run_relay_audit: {exc}") from exc

    if profile not in profiles:
        raise SystemExit(f"unknown --profile {profile!r}; allowed: {', '.join(sorted(profiles))}")

    try:
        raw = run_relay_audit(base_url, api_key, model, profile=profile)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"run_relay_audit failed: {exc}") from exc

    report = serialize_result(raw)
    # Never write the API key into the report.
    report.pop("api_key", None)
    report["base_url"] = base_url
    report["model"] = model
    report["profile"] = profile

    if out:
        path = validate_out_path(out)
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    verdict = str(report.get("verdict", "")).upper()
    findings = report.get("findings") or []
    if verdict == "LOW" and not findings:
        return 0, report
    if verdict in {"MEDIUM", "HIGH"} or findings:
        return 1, report
    return 2, report
