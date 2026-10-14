"""Skill frontmatter layout smoke."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_audit_model_relay_skill_exists() -> None:
    skill = ROOT / ".claude" / "skills" / "audit-model-relay" / "SKILL.md"
    assert skill.is_file()
    text = skill.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "name: audit-model-relay" in text
    assert "description:" in text
