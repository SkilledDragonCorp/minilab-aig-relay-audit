---
name: audit-model-relay
description: Before adding a third-party model relay to an agent config, run relay-audit full profile and block on exit 1 or 2.
---

# audit-model-relay

Use this skill whenever an agent config, MCP bridge, or IDE setting points at a third-party OpenAI-compatible relay.

## Procedure

1. Confirm the relay base URL includes the version prefix (`…/v1`).
2. Export `RELAY_API_KEY` for that relay (spend-capped). Never paste the key into chat or commit it.
3. Run:

```bash
uv run relay-audit run --base-url <relay>/v1 --model <id> --profile full --out reports/relay-audit.json
```

4. Interpret exit codes:
   - `0` — verdict `LOW` and no findings; safe to proceed.
   - `1` — findings or verdict `MEDIUM`/`HIGH`; **block the config change**.
   - `2` — tool error or invalid inputs; **block** and fix the audit setup.

5. Optional known-good control (requires `GEMINI_API_KEY`):

```bash
uv run relay-audit baseline --provider gemini --model gemini-2.0-flash --profile quick --out reports/gemini-baseline.json --relay-report reports/relay-audit.json
```

## HTTP path

When exercising the upstream SSE server locally:

```bash
cd upstream
export AIG_API_CHECKER_PYTHON="$PWD/services/api_checker/.venv/bin/python"
export HOST=127.0.0.1 PORT=8000
./ai-infra-guard api-checker serve
```

```bash
uv run relay-audit run-http --server http://127.0.0.1:8000 --base-url <relay>/v1 --model <id> --algorithm quick --language en --out reports/relay-http.json
```

Do not set `AIG_API_CHECKER_ALLOW_HTTP` or `AIG_API_CHECKER_ALLOW_PRIVATE_TARGETS` against real relays.
