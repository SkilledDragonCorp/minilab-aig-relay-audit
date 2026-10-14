"""Repo-root helpers and path bounds for CLI outputs."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def repo_root() -> Path:
    """Return the lab repository root (parent of src/)."""
    return Path(__file__).resolve().parents[2]


def upstream_dir() -> Path:
    return repo_root() / "upstream"


def api_checker_dir() -> Path:
    return upstream_dir() / "services" / "api_checker"


def ai_infra_guard_bin() -> Path:
    return upstream_dir() / "ai-infra-guard"


def load_dotenv_if_present() -> None:
    """Load repo-root .env into os.environ without overriding existing values."""
    env_path = repo_root() / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path, override=False)


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"missing required environment variable: {name}", file=sys.stderr)
        raise SystemExit(2)
    return value


def validate_model_id(model: str) -> str:
    model = model.strip()
    if not model:
        raise SystemExit("model id must be non-empty")
    if len(model) > 200:
        raise SystemExit("model id must be <= 200 characters")
    if any(ch.isspace() for ch in model):
        raise SystemExit("model id must not contain whitespace")
    return model


def validate_base_url(base_url: str) -> str:
    url = base_url.strip().rstrip("/")
    allow_local = os.environ.get("RELAY_AUDIT_ALLOW_LOCAL_HTTP", "").strip() == "1"
    if url.startswith("https://"):
        return url
    if allow_local and url.startswith("http://127.0.0.1:"):
        return url
    raise SystemExit(
        "--base-url must be https://... "
        "(http://127.0.0.1:<port> only when RELAY_AUDIT_ALLOW_LOCAL_HTTP=1)"
    )


def validate_out_path(out: str) -> Path:
    root = repo_root().resolve()
    path = Path(out).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f"--out must resolve inside the repo root ({root})") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
