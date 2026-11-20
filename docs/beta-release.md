# FirmaBlick V1 beta readiness, security and release decision (Issue #17)

## Preflight findings
- GitHub permissions support an isolated PR into `agent/prototype-2-44525788542`; PR #28 from Issue #16 is already integrated.
- Existing CI tests Node, Python and real Chromium desktop/mobile behavior. This issue adds independent static client security, formal no-release checks, broader browser E2E, and a CI-linked candidate manifest.
- Authenticated GENESIS acquisition and independent real-value verification for Issues #10–12 remain outstanding. Flagship forecast and sector validation for Issues #14 and #16 remain unpublished.
- The Vercel preview is protected by authentication, preventing previously attempted external browser access. GitHub's built `dist/` can be checked in local Chromium CI, but **this is not a claim of a tested authenticated Vercel preview**. The actual preview must be reviewed with authorized access before beta signoff.
- No new infrastructure, service tokens, billing, customer data, IIA/SER resources, production merge or DNS changes are authorized.

## Release manifest, evidence and approval
`release/beta-manifest.v1.json` is a versioned, deliberately BLOCKED **candidate** recording release ID, Git commit, source dataset/vintage and file hashes, five-industry official spot checks, model/version/holdout evidence, four independent sector release flags, CI run/SHA and browser/security results, preview URL/reviewer/approval, named manual approver and authorization scope, privacy safeguards and production/DNS approvals.

The current committed manifest keeps source vintage, Git SHA, test-run evidence and manual approver unset because those approvals do not yet exist. CI generates a separately retained `release-artifacts/beta-candidate.json` carrying the actual tested PR head SHA and GitHub Actions run URL while recording the pipeline status **running_not_yet_approved**. This artifact is **not** a self-attestation of success or permission to deploy. PR-linked job results must be verified against the precise SHA externally; the final environment approval must come through GitHub's protected manual approval controls.

`scripts/beta-release-gate.mjs` independently inspects the committed historical and sector release files. It blocks on absent source data, integrity/metadata mismatch, missing authenticated golden value evidence, unapproved aggregate forecast, independently unverified CI run, untested protected Vercel preview, missing protected manual approval, security checks or any attempted production/DNS authorization. The gate's current CI assertion must pass only when it **correctly blocks publication**. For genuine future release the gate has a separate `--require-preview-approved` action that exits nonzero until independently verified evidence is supplied. Do not write a CI job that declares release success based solely on booleans in JSON.

**No beta activation** should proceed without:
1. Owner secure GENESIS token; authentic source acquisition and preserved raw source bytes; confirmed WZ2008, unit/base, adjustment and status mappings.
2. Independent official published-value spot checks covering all five series, with source URLs, months, exact matching values, reviewer and immutable raw-file digests.
3. A complete validated historical-data release file with source-vintage information and a separately authorized published manufacturing forecast, or a specific approved revision to the proposed beta scope.
4. CI and browser checks green on the exact candidate Git SHA; independent review of secrets, external-resource disclosures and licence/usage rights.
5. Vercel authenticated preview tested and accepted by the owner (including screenshot/accessibility and live static response headers); protected environment approval and named manual release sign-off.
6. Legal completion: operator's legally required identity and contact details, privacy and terms review for Germany/EU access, rights to remote imagery, and hosting/subprocessor disclosures.

## Security/monitoring/observability
Static Vercel config adds Content-Security-Policy, no-sniff, anti-framing, conservative referrer and browser permissions restrictions. The policy allows only same-origin scripts/connect requests and the existing Google Fonts / Google-hosted imagery domains. This is a hardened **prototype** policy; deployment response headers must be independently checked on the protected preview before public access.

`scripts/security-audit.mjs` scans all publicly bundled text for secret signatures, dangerous credential file names, unsafe external API requests, unexpected resource origins and misleading copy. It verifies required policy headers and the current transparent disclosures. It does **not** replace dynamic penetration testing, dependency review, Vercel runtime verification or a comprehensive privacy/security audit. The existing static site has no server-side customer intake or telemetry. Its browser controls operate locally, and a sample enquiry sends nothing. Google resources and hosting services can receive standard network requests/access logs, disclosed in the footer.

Current observability is deliberately **privacy-minimal**: GitHub Actions run and screenshot artifacts, source-acquisition failure/quarantine reports, and Vercel's own infrastructure logs when deployment is authorized. No analytics SDK, hidden tracker or live end-user data collection is introduced. Planned operational monitoring after a dedicated infrastructure decision: acquisition job status, stale source-vintage threshold (120 days), checksum failures and quarantine counts, CI/preview failures, protected-release approval and incident owner. Do not create scheduled background checks or log raw credentials.

## Browser and source QA
The pinned Playwright Chromium CI now includes `tests/beta-browser.mjs` on desktop 1365×900 and mobile 390×844, verifying navigation fragments and accessibility landmarks, the full five-industry selection, actual no-data empty states, contact native email validation, footer provenance/disclosure text, a deliberately forged historical-data payload being rejected, and a valid **test-intercept-only** source citation/accessible data table.

Existing `tests/historical-browser.mjs` and `tests/scenario-browser.mjs` continue testing mobile layout, source provenance, missing values, scenario values and multi-turn invalid instructions. Mocked values in Chromium tests are synthetic and are **never copied to the published historical JSON**. A genuine Destatis golden-file spot check is outstanding, so no official statistical correctness is asserted.

## Legal and publication boundary
The footer replaces unfinished placeholders with accurate prototype disclosures on remote resources, local-only demo input, example analysis, economic-model limitations, and the DesiPlat operator identity. These disclosures **do not constitute final EU legal compliance**. Full operator contact details, GDPR/privacy obligations, relevant licence and business imprint information require owner/legal completion.

All engineering changes are confined to the prototype feature PR and merged prototype integration branch after CI. No production `main`, DNS or public-release action is authorized here. GitHub green CI is **engineering readiness**, while real-data parity, protected Vercel preview and explicit manual approval remain release blockers.

## Commands
```sh
npm ci --ignore-scripts
npm run build
npm test
node scripts/security-audit.mjs
node scripts/beta-release-gate.mjs --assert-blocked
node scripts/beta-release-gate.mjs --require-preview-approved  # expected nonzero until approval
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Sources: Epic #5, issues #7–17; `docs/source-registry.md`, `docs/historical-industry-views.md`, `docs/forecast-evaluation.md`, `docs/sector-forecast-gates.md`. 
