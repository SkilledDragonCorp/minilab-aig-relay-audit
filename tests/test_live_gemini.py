"""Optional live baseline against Gemini (skipped without GEMINI_API_KEY)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from relay_audit.cli import main

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.live
def test_baseline_gemini_has_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        # Also try loading .env via CLI helper
        from relay_audit.paths import load_dotenv_if_present

        load_dotenv_if_present()
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        pytest.skip("GEMINI_API_KEY unset")

    monkeypatch.chdir(ROOT)
    rel_out = Path("reports") / "live-gemini-baseline.json"
    abs_out = ROOT / rel_out
    abs_out.parent.mkdir(parents=True, exist_ok=True)
    code = main(
        [
            "baseline",
            "--provider",
            "gemini",
            "--model",
            "gemini-2.0-flash",
            "--profile",
            "quick",
            "--out",
            str(rel_out),
        ]
    )
    assert code == 0
    report = json.loads(abs_out.read_text(encoding="utf-8"))
    assert "verdict" in (report.get("baseline") or {})
