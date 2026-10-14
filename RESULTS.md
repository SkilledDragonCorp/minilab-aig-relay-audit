# RESULTS

Local green gate + first green Actions runs on `main` (2026-10-14).

| Check | Result | Detail |
| --- | --- | --- |
| Upstream pin | pass | `git -C upstream rev-parse HEAD` → `5ec95d4cd350f1982c0be71848463b07614e6e9d` |
| Upstream Go build | pass | `go build -o ai-infra-guard ./cmd/cli/main.go` |
| Upstream api_checker pytest | pass | `115 passed, 155 subtests passed in 23.86s` (local); lab-owned CI job green |
| Lab `uv run pytest -q` | pass | `11 passed in 73.90s` local; CI `test` job green |
| Ruff | pass | `uv run ruff check .` + `uv run ruff format --check .` |
| skills-layout | pass | `python3 scripts/check-skills` |
| banned-phrases / upstream-parity | pass | both scripts OK |
| pip-audit | pass | `No known vulnerabilities found` |
| gitleaks | pass | `v8.30.1` / SHA256 `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb` |
| CI run URL | pass | https://github.com/SkilledDragonCorp/minilab-aig-relay-audit/actions/runs/38523950032 |
| Upstream CI run URL | pass | https://github.com/SkilledDragonCorp/minilab-aig-relay-audit/actions/runs/38523950064 |

## Keyless e2e assertions (pinned behavior)

| Path | Profile / algorithm | Exit | Verdict |
| --- | --- | --- | --- |
| Python `run_relay_audit` | `quick` | 1 | `MEDIUM` score `50` (liveness HIGH) |
| Python `run_relay_audit` | `full` | 1 | `HIGH` score `100` |
| HTTP SSE | `algorithm=quick` + allow flags | 1 | `overall_verdict=risk`, `risk_level=high` |
| HTTP SSE | without allow flags | 2 | HTTP 400 for `http://127.0.0.1` mock |

## Tool versions (local)

| Tool | Version |
| --- | --- |
| uv | 0.12.17 |
| Go | go1.27.2 darwin/amd64 |
| Python (lab uv) | 3.14.7 |
| pytest | 9.1.1 |
| ruff | 0.17.0 |
| Upstream | Tencent/AI-Infra-Guard `v4.6.5` @ `5ec95d4cd350f1982c0be71848463b07614e6e9d` |
| Ship SHA | `2ece033e562444b6e4b07d3c209a916d7f599ede` |
