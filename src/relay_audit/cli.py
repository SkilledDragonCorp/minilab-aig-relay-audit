"""relay-audit CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys

from relay_audit.paths import load_dotenv_if_present, require_env


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="relay-audit",
        description="Audit OpenAI-compatible model relays with AI-Infra-Guard api-checker",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Check upstream binary, python, list, and imports")

    run_p = sub.add_parser("run", help="In-process run_relay_audit (Python path)")
    run_p.add_argument("--base-url", required=True)
    run_p.add_argument("--model", required=True)
    run_p.add_argument("--profile", required=True, choices=["quick", "standard", "full"])
    run_p.add_argument("--out", default=None)

    http_p = sub.add_parser("run-http", help="HTTP SSE path via api-checker serve")
    http_p.add_argument("--server", default="http://127.0.0.1:8000")
    http_p.add_argument("--base-url", required=True)
    http_p.add_argument("--model", required=True)
    http_p.add_argument("--algorithm", required=True, choices=["quick", "full"])
    http_p.add_argument("--language", default="en", choices=["en", "zh"])
    http_p.add_argument("--out", default=None)

    base_p = sub.add_parser("baseline", help="Known-good Gemini control baseline")
    base_p.add_argument("--provider", required=True, choices=["gemini"])
    base_p.add_argument("--model", required=True)
    base_p.add_argument("--profile", default="quick", choices=["quick", "standard", "full"])
    base_p.add_argument("--out", default=None)
    base_p.add_argument(
        "--relay-report",
        default=None,
        help="Optional prior relay-audit run report.json to diff against",
    )

    return parser


def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "doctor":
        from relay_audit.doctor import run_doctor

        return run_doctor()

    if args.command == "run":
        from relay_audit.audit import run_python_audit

        api_key = require_env("RELAY_API_KEY")
        code, report = run_python_audit(
            base_url=args.base_url,
            api_key=api_key,
            model=args.model,
            profile=args.profile,
            out=args.out,
        )
        print(
            json.dumps(
                {
                    "verdict": report.get("verdict"),
                    "score": report.get("score"),
                    "findings": len(report.get("findings") or []),
                }
            )
        )
        return code

    if args.command == "run-http":
        from relay_audit.http_client import run_http_audit

        api_key = require_env("RELAY_API_KEY")
        code, report = run_http_audit(
            server=args.server,
            base_url=args.base_url,
            api_key=api_key,
            model=args.model,
            algorithm=args.algorithm,
            language=args.language,
            out=args.out,
        )
        result = report.get("result") or {}
        print(
            json.dumps(
                {
                    "overall_verdict": result.get("overall_verdict"),
                    "risk_level": result.get("risk_level"),
                    "score": result.get("score"),
                }
            )
        )
        return code

    if args.command == "baseline":
        from relay_audit.baseline import run_baseline

        return run_baseline(
            provider=args.provider,
            model=args.model,
            profile=args.profile,
            out=args.out,
            relay_report_path=args.relay_report,
        )

    print(f"unknown command {args.command}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_present()
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return _dispatch(args)
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
            return 2
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
