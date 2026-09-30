# Release 1.0 — Single-host deterministic task queue

This is a completed release within the scope below. Version 1.0 does not imply public-service readiness, unlimited traffic, security certification or an uptime guarantee.

## Supported use
Single-host deterministic task queue. Start commands and examples are in [README.md](README.md). Use Python 3.11 or newer in a clean virtual environment with the pinned requirements. Browser interfaces are available where documented; the health probe is a command-line tool.

## Verification
9 tests. Run `python -m unittest discover -s tests -v` from this repository. A green result with skipped PostgreSQL tests does not count as PostgreSQL verification; use the isolated database job in CI for that coverage. Never run destructive test fixtures against an operational database.

## Storage and recovery
JOBS_DB shared by API and worker. Retry with the original key after an interrupted submission. Crashed claims recover after lease expiry; exhausted errors, including empty exception messages, remain failed.

For a SQLite database, use Python's `sqlite3.Connection.backup()` to an independent destination rather than copying an open database file. Restore only while all writers are stopped, keep the current database as a fallback, and test the restored copy before replacing it. For PostgreSQL, use a dedicated role and the provider's documented export/restore process. Never commit database copies, tokens, passwords, real customer records or uploaded files.

## Operating boundaries
Local API and worker only. At-least-once execution; no arbitrary code, external email, payments, or multi-host operation.

## Change control
Run the full tests before publishing a change. Keep existing measurements and attribution. A benchmark rerun is a new observation, not permission to replace an unfavorable result. Store secrets in environment variables. Roll back to a known working commit only after checking compatibility with any schema changes; do not force push or erase newer unrelated work.

## Security reports
Never put credentials, private datasets or customer receipts in public issues. A sanitized issue can describe the affected version, expected behavior and a minimal synthetic reproduction. No independent security audit is claimed.
