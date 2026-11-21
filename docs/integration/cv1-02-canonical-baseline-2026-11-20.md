# CV1-02 | Canonical nonproduction integration baseline

Date: 2026-11-20
Branch: `agent/fb-v1-integration-20261120`
Issue: [#40](https://github.com/praneix/FirmaBlickRepo/issues/40)

## Safety and authority

- `main` is the default/production branch and must not be modified or merged without the owner's explicit production release decision.
- This **nonproduction** integration branch is the single engineering basis for subsequent commercial V1 work.
- Maintain Vercel Authentication protection for previews. No custom-domain, DNS, environment secret, paid subscription, or published report changes.
- GitHub Actions green = code checks only; official-source, forecast, economic evidence, contact/payment and legal gates remain separate.
- The current official historical public JSON intentionally says `unavailable`. Any preview-only verified observations remain restricted to separate authenticated protected preview jobs.

## Exact integration ancestry

- PR #4 carries the static website and V1 test suite against `main`. It remains a **draft and unmerged**. `main` has unrelated workflow commits and is not a valid website deployment baseline.
- PR #31 `agent/verified-source-execution-plan-20261120` introduces the evidence execution plan and archive risk notes.
- PR #32 `agent/genesis-extended-history-20261120` introduces authenticated source-acquisition evidence. This branch and PR #31 **diverge in commit ancestry** (one prior commit not shared) even though file diff is limited to GENESIS workflow and extended-history evidence. Do not assert that every commit in both branches is integrated merely from apparent file completeness.
- PR #33 `agent/eurostat-live-comparator-20261120` builds on the GENESIS extended branch and records 705/705 parity, revision-aware forecast failure and legal preflight.
- PR #34 `agent/verified-historical-vercel-preview-20261120` adds an independently verified **protected-preview-only** five-series historical JSON generator and UI validator.
- PR #35 `agent/energy-flagship-evidence-20261120` adds verified SMARD and industrial tariff source code/records.
- PR #56 `agent/cv1-17-statistical-source-retention-20261120` adds independent raw source backup and restoration verifier after PR #35.
- PR #36 `agent/n8n-readonly-diagnostics-20261120` adds three read-only n8n files after PR #35. These are **copied exactly** into the integration branch based on PR #56.
- Existing main GitHub workflow-only commits are not automatically included. Resolve them separately before an eventual reviewed production merge, following verified intent. No history rewriting.

## Canonical integration contents

- Public prototype site, official data source contracts, ingestion/normalization with fail-closed source gates, analytic and forecast **candidate** modules, baseline CI and Chromium browser checks
- Restricted source acquisition/reconciliation/preview workflows and source-record evidence
- Energy primary-source acquisition and hourly verification
- Restore verifier and retention documentation, with owner-only Drive backups (do not place raw ZIP archives into public repository)
- n8n API read-only diagnostics bridge, **no active integration** to the user's n8n Cloud workspace until credentials are configured
- Commercial backlog and independent owner publication gate remain explicit

## Release facts and limitations

1. **No public official historical data:** `site/data/historical.json` status is `unavailable`; protected source-backed preview generation exists and was source verified but deployment initially failed for Vercel build quota. Promote through separate issue #41 and independent release assurance.
2. **No public forecast:** Candidate did not meet locked holdout performance. Industry-level gates remain closed, see #49.
3. **No real customer or revenue flow:** sample contact form is disabled, catalogue example reports have no checkout, no digital fulfillment or commercial operator notice. These are issues #42–#48.
4. **No production authorization:** all beta gates must stay `BLOCK_RELEASE`, no DNS or trademark status changes.
5. Research and archive commits are evidence, not complete public-report renderings.

## Vercel build economy policy

The Vercel Project's `commandForIgnoringBuildStep` skips Git push auto-preview deployment except on this integration branch, and on this branch only triggers a build when website/build-relevant files change. A docs, n8n, acquisition or workflow-only commit should be skipped by the ignored build step. The current project has no owner-authorized public production route; `main` is deliberately suppressed until an explicit owner release. Do not rely on this alone as a deployment security boundary.

Production domain, service credentials and authenticated preview remain controlled separately. Manual CLI deployments, if ever approved, require their own safety check.

## Ongoing engineering workflow

1. New issue → branch from `agent/fb-v1-integration-20261120`, not from `main`.
2. Make a focused PR back into integration. Green GitHub Actions checks, human/automated review as applicable and exact SHA pinned.
3. Merge only into nonproduction integration when all relevant checks pass and no release guard bypass occurs.
4. Run optional protected Vercel preview only for UI changes; verified source-backed previews require authenticated source injection via owner-approved workflow.
5. Release branch → comprehensive QA manifest, owner reviews protected preview and explicitly approves `main`/production and `firmablick.com` DNS.

## Verification

```sh
npm ci --ignore-scripts
npm run build
npm test
node scripts/security-audit.mjs
node scripts/beta-release-gate.mjs --assert-blocked
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

PR CI must confirm exact SHA status. An OK Vercel build or static source document alone never certifies correctness.
