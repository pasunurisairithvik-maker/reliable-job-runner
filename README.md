# Reliable Job Runner

Release 1.0 within its documented scope. See [release and operating notes](RELEASE.md).
A small persistent background task queue in Python: separate API and worker, SQLite state, idempotent submission, bounded retries with exponential backoff, and recovery after a worker lease expires.

## Run: Python 3.11+
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```
Open http://127.0.0.1:8002. In a second terminal, activate the same environment and run:
```bash
python worker.py
```
Keep both terminals in this repository directory so they use the same database. JOBS_DB can set an explicit database path for both processes.

## Two examples
1. Queue word_count with text "hello hello Python". Result: 3 words, 2 unique words.
2. Queue sales_summary with amounts [10.10,20.20]. Result total: "30.30". The docs at /docs let you submit either task.
Select the browser's simulated-failure checkbox with a NEW request key: first attempt fails, retry starts at least 2 seconds later, second succeeds. This is fault injection, not proof of integration with a real flaky service.

## State and reliability
queued -> running -> succeeded. On error: running -> queued until attempt 3, then failed. BEGIN IMMEDIATE serializes claims. Each claim has a unique token; a stale worker cannot replace a newer worker's result. Expired leases recover crashed workers. The same request key returns the same job; a changed payload with that key is rejected.

Execution is AT LEAST ONCE, not exactly once. Leases can cause re-execution. Tasks are pure computations, so duplicates have no external side effects. A real payment/email task would need downstream idempotency. No heartbeat exists; jobs must remain short relative to the 30-second lease. This is not Celery or an AWS service.

## Tests
```bash
python -m unittest discover -s tests -v
```
Tests use controlled clocks for retry timing, simulate crashes and stale completion, check attempt limits, and cover API behavior. No claims of production load or multi-host reliability.

## Limits
Local educational demo; no authentication, rate limit, cancellation, priority, audit history, or arbitrary user-code execution. Payload limits protect individual requests but are not a full public-service resource policy. Money has unspecified currency and uses decimal arithmetic. Word count splits on whitespace, not linguistic tokenization.

AI-assisted initial implementation. Read STUDENT_GUIDE.md and implement an independently understood improvement before describing personal contributions on a resume.
