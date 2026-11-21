# CV1-05 | FirmaBlick private report registry and entitled delivery

**Status:** Code and isolated CI only. Production deployment, payment acceptance and paid-file distribution **DISABLED**. Issue [#43](https://github.com/praneix/FirmaBlickRepo/issues/43). Owner technical standing authority does not grant commercial launch approval.

## Preflight finding: existing infrastructure
Supabase plugin currently exposes **one project named IIA**, status `INACTIVE`. It is unrelated to FirmaBlick. **No tables, storage buckets, migrations, secrets or configuration were installed on IIA.** No dedicated FirmaBlick Supabase project exists in the connected account. A new project would need a separate cost/organization decision. The SQL here is a draft for a future isolated FirmaBlick project and is validated only against an ephemeral Postgres CI service.

The V4 report/sample are owner-only review assets in the user's private ChatGPT Library (folder `FirmaBlick/Energy/V4-Owner-Review`). Neither is committed to this **public** GitHub repository or to Vercel static assets. The registry is metadata only. The report remains editorial-review-unapproved.

## Critical checksum correction (2026-11-21)
A fresh independent SHA-256 inspection of the **current mounted review PDF bytes** revealed that the previous CV1-04 review manifest's PDF and sample digests were stale/inaccurate. The source HTML and XLSX digests still match.

| Artifact | Exact SHA-256 after current-byte verification |
|---|---|
| Full PDF (20 pages) | `1b829c279178f0da6681d28021f2a80dc419288c3d247cb72f9169f5ad10dd82` |
| Sample PDF (5 pages) | `ef7c03259d5017ab6d45e7df3ba59b7d94ec3ef5f5dea80d25f9c342b814abfd` |
| Source HTML | `434f6e127d168d3840c8eb84f442231a8678b5182713c7681628c33077144f79` |
| Investment workbook | `9f914b53c814278d15595e7bc01bf4d27c7ba2266f934ea0059b7bb506856741` |

Current private review candidate is distinguished as **V4-2026-11-21-RC2**; the prior RC1 hash record remains explicitly captured as superseded, without asserting the old bytes were verified. **Neither RC1 nor RC2 is approved or saleable.** The SHA mismatch is a serious preflight finding and must be surfaced to the owner; prevent name-based delivery.

Use `python3 scripts/verify-private-report-assets.py full.pdf sample.pdf` to reject any mismatched local bytes. Upload only after report rights, owner approval, asset checksum and registry consistency all pass.

## Design and implementation
- `product/registry/energy-v4.review.json` is the versioned business/evidence/asset metadata registry. Explicit review status, exact digest, rights, source vintages, sample status and protected storage object path.
- `db/schema/cv1-05-report-registry.sql` creates seven RLS-enabled operational tables: report catalog, immutable report versions, orders, entitlements, SHA-256 token registry, delivery events and singleton global delivery-release flag. Revoke anon/authenticated access. Never grant SELECT to unauthenticated users.
- `public.fb_redeem_report_token` is a **service-role-only** atomic function that locks and consumes an access token after checking all of: token unexpired/unconsumed, entitlement active, order `paid_verified` with timestamp, report/version owner approved, rights verified, both publications marked approved, global release approved. Internal security-definer function is explicitly revoked from public/anon/authenticated. Never accept user-supplied order or report identity at redemption.
- `api/report-access.js` (Vercel serverless) accepts a POST with exactly one high-entropy access token, stores/logs no raw token, hashes the token, calls the service-only DB function, and only on success creates a 60-second signed URL to the private `firmablick-paid-reports` bucket. It does not serve files from GitHub, HTML, public assets or customer-provided paths. It sets no-store/no-referrer headers.
- The Node endpoint is globally **disabled by default** unless `FB_DELIVERY_ENABLED=true` and `FB_OWNER_PUBLICATION_APPROVED=true` are explicitly set in server-only Vercel secrets. The database has an independently disabled global release switch. This is deliberate multi-layer operational safety.
- The signed URL is valid for **up to 60 seconds**, but storage provider signed URLs are bearer links that **cannot be individually revoked** while valid. For a refund or entitlement revocation, further link issuance stops immediately, but a previously issued link can remain valid until expiry. A storage-level object replacement or signing-key rotation can revoke earlier links at broader scope.
- Access tokens must be generated with a cryptographically secure 32-byte random generator by the future **server-side purchase fulfillment service** (#45), stored only by SHA256, and delivered through a private email or similarly controlled channel. The token is single-use and should expire within 15 minutes. Its issuance and email delivery are **not implemented in this issue**.
- If the downstream storage-sign operation fails after the token was consumed atomically, the one-time token cannot be reused. The operational recovery is a controlled reissue, audited by entitlement after a verified order. A durable automatic retry mechanism can be added in #45.
- No user accounts/subscriptions, live payment webhook, invoices or customer emails implemented here; those belong to #45/#46. `/api/report-access` must never be wired to a public CTA before those gates.

## Private bucket and deployment prerequisites
1. Owner authorizes a **dedicated FirmaBlick Supabase project**, with its own organization/plan and separate production vs test environment. Do not reuse or restore the inactive IIA project.
2. Create private `firmablick-paid-reports` bucket; `public=false`. Do not add anonymous storage SELECT policies or public URLs. Enable meaningful backup/revision retention, suitable region/privacy agreements and minimal access permissions.
3. Create a migration in the chosen project's own local CLI history, review the SQL against its actual Supabase release, apply only to FirmaBlick and run SQL advisors and RLS checks. SQL in this repository is **not evidence of live Supabase provision**.
4. In a protected Vercel *preview environment only*, provision server-side `FB_SUPABASE_URL` and `FB_SUPABASE_SECRET_KEY` (service-role authorization; never a client-visible `NEXT_PUBLIC_` key). Keep `FB_DELIVERY_ENABLED=false` and `FB_OWNER_PUBLICATION_APPROVED=false` until all release gates pass. Credential handling and runtime version must be verified against actual deployed platform.
5. On each upload, hash the bytes before and after private storage transfer. Store the object under `reports/<sku>/<revision>/<sha256>.pdf`. Never overwrite an approved hash-addressed object, and use a new revision for corrections. Sample remains a separately approved artefact, not implicitly released merely because its hash exists.
6. Seed review-only V4 metadata with publication false. Do not generate live customer entitlements, records, purchases or raw tokens until #45's provider verification is in place.

## Tests and acceptance
The CI workflow `.github/workflows/cv1-05-private-report-registry.yml` verifies:
- Node endpoint default-deny, no-cache, token format, path validation, unknown paths and wrong-bucket rejection; simulated successful and failed provider calls
- Postgres RLS/role restrictions, unpublished and unpaid refusals, deliberately simulated approved paid grant, atomic one-use/replay, refunded order refusal, expired/revoked entitlement refusal, immutable content checks
- registry and CV1-04 manifest exact latest digest consistency, no paid PDF inside static `site/` or built `dist/`

**A passing mock+ephemeral Postgres workflow is NOT the live Vercel/Supabase end-to-end acceptance.** The latter requires dedicated Supabase and safe environment secrets, real private bucket object, an authorized closed preview, a sandbox purchase from #45 and owner/legal publication approval. #43 remains open until this is demonstrated. No subscription or production activation is assumed.

## Correction and reissue policy (proposed)
- Purchased order pins the exact `report_id + revision + sha256` as its entitlement.
- A factual correction creates a separate immutable revision, documenting reason and original source vintage; past versions stay archived and retired versions stop issuing new links.
- Owner approves the corrected revision and any refund/reissue communication; the buyer receives a newly recorded entitlement only according to approved terms.
- Refund/dispute immediately revokes entitlements and pending tokens. Audit retains only minimum necessary metadata for payment and tax obligations.
- New content and sample are independently gated; ownership and commercial terms reviewed before publication.

## Cross-issue dependencies
- #42: exact approved report asset, source/rights/editorial signoff.
- #39: scope, price and licence owner decisions.
- #47: legal/privacy/tax/transaction notices.
- #45: verified payment webhook, token issuance, sender, refund workflow, live/sandbox flow.
- #48/#54: protected live end-to-end QA and exact-SHA release approval.
- #57: archival resilience beyond a single owner account.

No changes to other ventures or live production services were made.
