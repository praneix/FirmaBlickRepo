# CV1-07 sandbox purchase and protected delivery: implementation boundary

## Scope and status

**Sandbox reference engine implemented, not a live payment provider integration.** Source: `commerce/sandbox-fulfillment.mjs`. Test: `tests/sandbox-fulfillment.test.mjs`. SKU `FB-ENERGY-DE-2026-01`; approved flagship price EUR 990 excluding taxes, represented as 99000 minor units (catalogue 2026-11-24; EUR149 superseded). The fixture PDF is deliberately synthetic and never sold.

The engine models buyer order creation, exact amount/currency/SKU reconciliation, HMAC-signed sandbox webhook events, duplicate event idempotency, payment capture, cancellation, failure, refund, entitlement, signed time-limited download claims, PDF magic-byte check, and post-refund access revocation. Tests must pass on the exact PR SHA.

## Nonproduction-only limitations / release blockers

1. `Map`/`Set` in-memory store is **not durable or safe for horizontally scaled/serverless production**. Replace with transactional database (unique order ID and provider event ID, row locks or conditional updates, immutable payment audit log, outbox for notifications). Race-safe idempotency must be proven under concurrent duplicate webhook delivery.
2. The event types and HMAC signature are a **synthetic provider contract**. They are not Razorpay/Skydo wire formats or proof of actual payment. Implement real provider signature validation and independently retrieve captured status/amount/currency/order from the approved processor before issuing an entitlement.
3. The private asset adapter is injected. Supply approved 20-page report from authenticated private object storage with immutable revision/hash, never from public `dist/`. Approved five-page sample can be public after editorial/source rights approval.
4. Build actual Vercel serverless endpoints for create order, hosted checkout redirect, raw webhook, order status and authenticated/one-time download. Add server-side secret management, secure cookies or bound email claim, throttling, buyer identity verification and expiring token rotation.
5. Create compliant invoice/receipt, refunds/chargebacks and customer service notification workflows after qualified India/EU legal and cross-border tax review.
6. Perform real provider **test-mode** payment success/cancel/fail/refund, replay/concurrency, storage and email delivery tests. Archive redacted evidence, exact SHA and report file hash. Public production checkout remains blocked.
7. The release-copy audit must pass on all customer-facing assets, emails and checkout pages. The current protected editorial page intentionally contains internal review notices, and must be cleaned only at the final approved release boundary.

## Test command

`node --test tests/sandbox-fulfillment.test.mjs` (also included in `npm test` and GitHub CI).

## Next engineering integration

Implement durable sandbox persistence + private report storage + provider test-mode adapter. Validate processor eligibility and account configuration first. If credentials or legal approval are missing, continue with deterministic mock sandbox while retaining the fail-closed production gate. **Never substitute simulated capture for a real transaction.**
