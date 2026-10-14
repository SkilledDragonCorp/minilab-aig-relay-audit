# Security Policy

**Built by [SkilledDragon LLC](https://skilleddragon.com)**

This is a **SkilledDragon educational minilab**, not a production product. We do **not** maintain these repos on a regular schedule and we do **not** operate a vulnerability response program for them.

## Contact

General questions: **hello@skilleddragon.com**  
Do not use a dedicated security mailbox for this repo — none exists.

## If you find an issue

- Prefer reporting **upstream** when the issue is in [Tencent/AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard).
- For something specific to this minilab’s CLI wrapper or CI, you may email hello@skilleddragon.com. There is **no SLA**, and we may not patch or reply quickly.

## Supported versions

Only the commit currently on `main` is considered current for this educational lab.

## Secret handling

- Never commit `.env`, API keys, or tokens.
- Secrets are read from environment variables (local `.env` loaded at startup; GitHub Actions secrets in CI).
- Required for `relay-audit run` / `run-http`: `RELAY_API_KEY` (validated at startup; never logged or written into reports).
- Optional `GEMINI_API_KEY` enables the known-good Gemini baseline slice.
- Minimum scopes: Google AI Studio free-tier key for Gemini; a spend-capped relay key able to call `/v1/models` and `/v1/chat/completions` for your own relay.

## Tooling pins

| Control | Pin |
| --- | --- |
| Upstream | `Tencent/AI-Infra-Guard` @ `5ec95d4cd350f1982c0be71848463b07614e6e9d` (tag `v4.6.5`, Apache-2.0) |
| gitleaks | `v8.30.1` (pre-commit hook + CI binary with SHA256 verify) |
| Dependency audit | `uv export --frozen --format requirements-txt --no-emit-project > /tmp/req.txt` then `uvx pip-audit --strict -r /tmp/req.txt` |

## Upstream license

`Tencent/AI-Infra-Guard` is Apache-2.0. The api-checker HTTP server rejects `http://` and private targets unless `AIG_API_CHECKER_ALLOW_HTTP=1` and `AIG_API_CHECKER_ALLOW_PRIVATE_TARGETS=1` are set; this lab enables those flags only in keyless tests against `127.0.0.1`.

Use at your own risk. Pin versions, review the code, and treat this as sample material.
