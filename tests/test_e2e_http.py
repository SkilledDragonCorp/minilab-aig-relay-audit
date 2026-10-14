"""Keyless e2e: HTTP SSE path against mock + api-checker serve."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import httpx
import pytest

from conftest import BIN, UPSTREAM, VENV_PY
from relay_audit.cli import main

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RELAY_AUDIT_ALLOW_LOCAL_HTTP", "1")
    monkeypatch.setenv("RELAY_API_KEY", "test-key-not-secret")
    monkeypatch.chdir(ROOT)


@pytest.mark.parametrize("api_checker_server", [True], indirect=True)
def test_run_http_quick_risk(mock_openai, api_checker_server, ensure_upstream_built) -> None:
    rel_out = Path("reports") / "test-http-quick.json"
    abs_out = ROOT / rel_out
    abs_out.parent.mkdir(parents=True, exist_ok=True)
    code = main(
        [
            "run-http",
            "--server",
            api_checker_server["base"],
            "--base-url",
            mock_openai.base_url,
            "--model",
            "gpt-4o",
            "--algorithm",
            "quick",
            "--language",
            "en",
            "--out",
            str(rel_out),
        ]
    )
    assert code == 1
    report = json.loads(abs_out.read_text(encoding="utf-8"))
    result = report["result"]
    assert result["overall_verdict"] == "risk"
    assert result["risk_level"] == "high"
    if abs_out.exists():
        abs_out.unlink()


@pytest.mark.parametrize("api_checker_server", [True], indirect=True)
def test_relay_models_nonempty(api_checker_server, ensure_upstream_built) -> None:
    r = httpx.get(f"{api_checker_server['base']}/api/v1/relay/models", timeout=30.0)
    assert r.status_code == 200
    payload = r.json()
    models = None
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict) and "models" in data:
            models = data["models"]
        elif isinstance(data, list):
            models = data
        elif "models" in payload:
            models = payload["models"]
    assert models is not None
    assert len(models) >= 1


@pytest.mark.parametrize("api_checker_server", [False], indirect=True)
def test_security_control_rejects_private_http(
    mock_openai, api_checker_server, ensure_upstream_built
) -> None:
    rel_out = Path("reports") / "test-http-deny.json"
    abs_out = ROOT / rel_out
    abs_out.parent.mkdir(parents=True, exist_ok=True)
    code = main(
        [
            "run-http",
            "--server",
            api_checker_server["base"],
            "--base-url",
            mock_openai.base_url,
            "--model",
            "gpt-4o",
            "--algorithm",
            "quick",
            "--language",
            "en",
            "--out",
            str(rel_out),
        ]
    )
    assert code == 2
    report = json.loads(abs_out.read_text(encoding="utf-8"))
    assert report.get("status_code") == 400 or report.get("error") == "http_error"
    if abs_out.exists():
        abs_out.unlink()


def test_go_wrapper_list_smoke(ensure_upstream_built) -> None:
    env = os.environ.copy()
    env["AIG_API_CHECKER_PYTHON"] = str(VENV_PY)
    proc = subprocess.run(
        [str(BIN), "api-checker", "list"],
        cwd=str(UPSTREAM),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert proc.returncode == 0
    assert "baseline" in proc.stdout.lower() or "指纹" in proc.stdout or len(proc.stdout) > 0
