"""Shared fixtures: mock OpenAI server + optional built upstream binary."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from mock_openai import MockOpenAIServer

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream"
BIN = UPSTREAM / "ai-infra-guard"
API_CHECKER = UPSTREAM / "services" / "api_checker"
VENV_PY = API_CHECKER / ".venv" / "bin" / "python"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def mock_openai() -> Iterator[MockOpenAIServer]:
    server = MockOpenAIServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def ensure_upstream_built() -> Path:
    """Build upstream Go binary + api_checker venv once per session if missing."""
    if not VENV_PY.is_file():
        subprocess.run(
            ["python3", "-m", "venv", str(API_CHECKER / ".venv")],
            check=True,
            cwd=str(UPSTREAM),
        )
        subprocess.run(
            [
                str(VENV_PY),
                "-m",
                "pip",
                "install",
                "-r",
                str(API_CHECKER / "requirements.txt"),
            ],
            check=True,
            cwd=str(UPSTREAM),
        )
    if not BIN.is_file():
        subprocess.run(
            ["go", "build", "-o", "ai-infra-guard", "./cmd/cli/main.go"],
            check=True,
            cwd=str(UPSTREAM),
        )
    os.environ.setdefault("AIG_API_CHECKER_PYTHON", str(VENV_PY))
    return BIN


@pytest.fixture
def api_checker_server(ensure_upstream_built: Path, request: pytest.FixtureRequest):
    """Start api-checker serve on a free port. Param: allow_private (bool)."""
    allow = getattr(request, "param", True)
    port = _free_port()
    env = os.environ.copy()
    env["HOST"] = "127.0.0.1"
    env["PORT"] = str(port)
    env["AIG_API_CHECKER_PYTHON"] = str(VENV_PY)
    if allow:
        env["AIG_API_CHECKER_ALLOW_HTTP"] = "1"
        env["AIG_API_CHECKER_ALLOW_PRIVATE_TARGETS"] = "1"
    else:
        env.pop("AIG_API_CHECKER_ALLOW_HTTP", None)
        env.pop("AIG_API_CHECKER_ALLOW_PRIVATE_TARGETS", None)

    log_path = ROOT / "reports" / f"api-checker-serve-{port}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [str(ensure_upstream_built), "api-checker", "serve"],
        cwd=str(UPSTREAM),
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 180
    last_err = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            log_fh.close()
            err = log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"api-checker serve exited early: {err}")
        try:
            r = httpx.get(f"{base}/healthz", timeout=2.0)
            if r.status_code == 200:
                break
        except httpx.HTTPError as exc:
            last_err = str(exc)
        time.sleep(0.5)
    else:
        proc.kill()
        log_fh.close()
        err_tail = log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
        raise RuntimeError(f"api-checker serve healthz timeout: {last_err}; log={err_tail}")

    def _cleanup() -> None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_fh.close()

    request.addfinalizer(_cleanup)

    yield {"base": base, "port": port, "proc": proc, "allow": allow}
