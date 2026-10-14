"""Keyless e2e: in-process run_relay_audit against the mock OpenAI server."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from relay_audit.cli import main

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _allow_local_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RELAY_AUDIT_ALLOW_LOCAL_HTTP", "1")
    monkeypatch.setenv("RELAY_API_KEY", "test-key-not-secret")
    monkeypatch.chdir(ROOT)


def test_run_profile_quick_medium(mock_openai, ensure_upstream_built) -> None:
    rel_out = Path("reports") / "test-quick.json"
    abs_out = ROOT / rel_out
    abs_out.parent.mkdir(parents=True, exist_ok=True)
    code = main(
        [
            "run",
            "--base-url",
            mock_openai.base_url,
            "--model",
            "gpt-4o",
            "--profile",
            "quick",
            "--out",
            str(rel_out),
        ]
    )
    assert code == 1
    report = json.loads(abs_out.read_text(encoding="utf-8"))
    assert report["verdict"] == "MEDIUM"
    assert report["score"] == 50
    probes = [f.get("probe", "") for f in report.get("findings") or []]
    titles = [f.get("title", "") for f in report.get("findings") or []]
    assert "liveness" in probes
    assert any("Relay liveness failed" in t for t in titles) or any(
        f.get("severity") == "HIGH" and f.get("probe") == "liveness"
        for f in report.get("findings") or []
    )
    if abs_out.exists():
        abs_out.unlink()


def test_run_profile_full_high(mock_openai, ensure_upstream_built) -> None:
    rel_out = Path("reports") / "test-full.json"
    abs_out = ROOT / rel_out
    abs_out.parent.mkdir(parents=True, exist_ok=True)
    code = main(
        [
            "run",
            "--base-url",
            mock_openai.base_url,
            "--model",
            "gpt-4o",
            "--profile",
            "full",
            "--out",
            str(rel_out),
        ]
    )
    assert code == 1
    report = json.loads(abs_out.read_text(encoding="utf-8"))
    assert report["verdict"] == "HIGH"
    assert report["score"] == 100
    if abs_out.exists():
        abs_out.unlink()


def test_missing_relay_api_key(monkeypatch: pytest.MonkeyPatch, mock_openai, capsys) -> None:
    monkeypatch.setattr("relay_audit.cli.load_dotenv_if_present", lambda: None)
    monkeypatch.delenv("RELAY_API_KEY", raising=False)
    code = main(
        [
            "run",
            "--base-url",
            mock_openai.base_url,
            "--model",
            "gpt-4o",
            "--profile",
            "quick",
        ]
    )
    assert code == 2
    err = capsys.readouterr().err
    assert "RELAY_API_KEY" in err


def test_unknown_profile_exit_2(mock_openai) -> None:
    code = main(
        [
            "run",
            "--base-url",
            mock_openai.base_url,
            "--model",
            "gpt-4o",
            "--profile",
            "not-a-profile",
        ]
    )
    assert code == 2


def test_api_key_not_in_report(mock_openai, ensure_upstream_built, monkeypatch) -> None:
    key = "super-secret-relay-key-do-not-leak"
    monkeypatch.setenv("RELAY_API_KEY", key)
    rel_out = Path("reports") / "test-no-key.json"
    abs_out = ROOT / rel_out
    abs_out.parent.mkdir(parents=True, exist_ok=True)
    main(
        [
            "run",
            "--base-url",
            mock_openai.base_url,
            "--model",
            "gpt-4o",
            "--profile",
            "quick",
            "--out",
            str(rel_out),
        ]
    )
    text = abs_out.read_text(encoding="utf-8")
    assert key not in text
    if abs_out.exists():
        abs_out.unlink()
    _ = os.environ
