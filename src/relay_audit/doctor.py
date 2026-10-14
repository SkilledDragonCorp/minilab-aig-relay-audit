"""relay-audit doctor: JSON health check of upstream build + imports."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from relay_audit.paths import ai_infra_guard_bin, api_checker_dir, upstream_dir


def run_doctor() -> int:
    report: dict[str, Any] = {
        "ok": False,
        "upstream_bin": str(ai_infra_guard_bin()),
        "bin_exists": False,
        "aig_api_checker_python": os.environ.get("AIG_API_CHECKER_PYTHON", ""),
        "python_executable": False,
        "list_exit_code": None,
        "list_stdout_head": "",
        "import_ok": False,
        "import_error": None,
        "profiles": [],
    }

    bin_path = ai_infra_guard_bin()
    report["bin_exists"] = bin_path.is_file() and os.access(bin_path, os.X_OK)

    py = os.environ.get("AIG_API_CHECKER_PYTHON", "").strip()
    if not py:
        venv_py = api_checker_dir() / ".venv" / "bin" / "python"
        if venv_py.is_file():
            py = str(venv_py)
            report["aig_api_checker_python"] = py
    report["python_executable"] = bool(py) and Path(py).is_file() and os.access(py, os.X_OK)

    if report["bin_exists"]:
        env = os.environ.copy()
        if py:
            env["AIG_API_CHECKER_PYTHON"] = py
        try:
            proc = subprocess.run(
                [str(bin_path), "api-checker", "list"],
                cwd=str(upstream_dir()),
                env=env,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            report["list_exit_code"] = proc.returncode
            report["list_stdout_head"] = (proc.stdout or "")[:500]
        except (OSError, subprocess.TimeoutExpired) as exc:
            report["list_exit_code"] = 2
            report["list_stdout_head"] = str(exc)

    try:
        from relay_audit.audit import import_relay_audit

        profiles, _ = import_relay_audit()
        report["import_ok"] = True
        report["profiles"] = sorted(profiles.keys())
    except Exception as exc:  # noqa: BLE001
        report["import_ok"] = False
        report["import_error"] = str(exc)

    report["ok"] = bool(
        report["bin_exists"]
        and report["python_executable"]
        and report["list_exit_code"] == 0
        and report["import_ok"]
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1
