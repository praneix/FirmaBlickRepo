# ARIE research jobs: contract v1

This is an isolated, vendor-neutral, **nonproduction reference**, not a database
adapter or provider integration. The assigned draft PR is based on `main`
(`99054e0`); the separate integration branch and PR #77 are not incorporated.
This checkout has no root JavaScript test configuration, so the synthetic tests
use Node's built-in test runner and require Node 18 or later. No dependencies,
credentials, database, schema changes, or network access are required:

```sh
node --test tests/arie/jobs.test.mjs
```

## Contract

`ResearchJobs` is a synchronous, single-instance model. Supply `clock`, a
function returning nonnegative safe-integer epoch milliseconds. The caller must
provide a nondecreasing clock; production persistence must instead use a
consistent authoritative database clock. `create` takes `id`, `commissionId`,
`idempotencyKey`, `taskKind`, JSON-compatible `payload`, integer `priority`,
and `maxAttempts` (1–10). IDs and keys are nonempty strings; real UUID format
validation belongs to a later adapter. The returned job contains `version: 1`,
the supplied fields, state, attempt count, lease owner/expiry, and update time.
The `(commissionId, idempotencyKey)` pair and job ID are unique per instance:
duplicates are rejected, not silently replaced or replayed. Keys are retained
in all terminal states. Returned jobs and stored payload/results are copies.
Priority is metadata; selection and scheduling are outside this model.

`claim(id, owner, leaseMs)` grants a queued or expired lease, increments
`attemptCount`, and returns `{jobId, owner, attempt}` as the fencing handle.
Duration is an integer from 1 ms to 24 hours. An unexpired lease cannot be
claimed. Expiry is inclusive (`now >= leaseExpiresAt`). At the attempt limit an
expired lease becomes `failed` when claim is next attempted; no extra attempt
is granted. `complete(handle, result)` accepts only a current, unexpired handle
and returns `{accepted: true}` once, then `{accepted: false}` for duplicates
and stale handles. The accepted result is stored in this model. `fail(handle)`
requeues a current unexpired attempt if attempts remain; otherwise it marks it
failed. Expired handles cannot fail or complete. `stop(id, 'blocked' |
'cancelled')` terminates a queued or leased job and invalidates the lease;
terminal jobs cannot be claimed or restarted here. Unknown IDs throw.

`canDispatch(handle, evidence)` is a **stub precondition**, not a dispatcher:
it returns true only for a current, unexpired lease and exact `true` values for
`eligibilityVerified`, `budgetReserved`, `regionVerified`, and
`nonproductionAuthorized`. It performs no external call and does not verify
these assertions. A later authorized integration must independently verify
and bind all evidence to the job, attempt, permitted region, budget and
nonproduction scope, ensure it remains valid at dispatch, and fail closed.
A boolean supplied by an untrusted caller is not authorization. Neither a
successful check nor this contract authorizes provider access or spending.

## Separately approved persistence integration

The in-memory tests cannot prove cross-worker or database atomicity. A future,
separately approved Supabase adapter must use transactions and real concurrent
database tests before claiming such guarantees. At minimum:

* Enforce the database unique `(commission_id, idempotency_key)` constraint and
  unique job ID. Handle uniqueness conflicts without creating a second job.
* In one transaction select an eligible queued or expired row with
  `FOR UPDATE SKIP LOCKED`, using a database time source, and atomically check
  the attempt limit, increment `attempt_count`, and write lease owner, expiry,
  state and update time. Exhausted expired rows must be transitioned to failed
  without dispatch. Commit before the worker acts.
* Complete, fail, block and cancel with transaction-scoped compare-and-set.
  Completion/failure must match job ID, `state = leased`, owner, the captured
  attempt count, and an unexpired lease against database time. Do not reset
  attempt counts or reuse a job ID; the attempt is the fencing generation even
  when the same owner reclaims. Atomically persist the accepted result with
  completion and prevent a second accepted result. The listed staging fields
  do not specify a result store: its durable design needs separate approval.
* Test overlapping transactions, expiry, cancellation and stale completions
  against the actual database, including rollback and uniqueness conflicts.
  A check followed by a separate update is not sufficient. A lease also cannot
  undo an already-started external side effect; provider-side idempotency and
  the independent dispatch gates require separate design and approval.
