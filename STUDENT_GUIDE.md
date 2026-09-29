# Student walkthrough
Read validate, enqueue, claim, execute, finish, work_once in app/jobs.py; then app/main.py and worker.py.
Explain why an HTTP request returns before work completes, why retries wait, and why a lease and claim token are different.

## Two independent improvements
- Add cancellation for queued jobs and test that cancelled jobs cannot be claimed.
- Add heartbeat renewal for running jobs; test a long job, expiry, and stale heartbeat rejection.

## Interview questions
What is a state machine? Why use BEGIN IMMEDIATE? What is an idempotency key? What does at-least-once mean? Why must external side effects be idempotent? Why doesn't a retry fix a permanent error? How would Redis or SQS change this design?

Do not claim AWS, distributed workers, production customers, or exactly-once execution. Explain AI assistance and describe your own implemented changes accurately.
