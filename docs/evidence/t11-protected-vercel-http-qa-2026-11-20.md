# T11 | Protected Vercel preview: direct authenticated response QA (20 November 2026)

**Existing protected prototype:** `dpl_3JqPntmmAE9FfvJu9NY7uzz97CSv`, Git SHA `ba5de0e821b3b86ca6c3c7708a9a7b090bbb7f20`, `agent/prototype-2-44525788542`. URL `https://firmablickrepo-lezcw5iac-firma-blick.vercel.app/`. No production or DNS action.

## Direct verified responses
Via the connected Vercel account's protected deployment fetch capability:
- Root `/`: HTTP 200, actual HTML includes title `FirmaBlick | European Industrial Intelligence`, five-industry historical navigation, distinctive synthetic scenario disclosure and static locally processed enquiry.
- `/data/historical.json`: HTTP 200, `schema_version=1.0.0`, `status=unavailable`, `series=[]`. This is the correct **production-safe** state for the currently deployed prototype, even though a newer 705/705 verified source dataset exists in separate unpublished engineering evidence.
- `/data/sector-forecast-status.json`: HTTP 200, `status=historical_only`, `publication_approved=false`, `aggregate_release_transfer_permitted=false`, sector release flags `20,24,28,29 = false`. This is also the correct no-unsupported-forecast state.
- Actual static-response headers contain: `Content-Security-Policy` (same-origin scripts/connections, no frame ancestors, constrained external fonts/images); `Strict-Transport-Security` with `max-age=63072000`; `X-Content-Type-Options=nosniff`; `X-Frame-Options=DENY`; `Referrer-Policy=strict-origin-when-cross-origin`; `Permissions-Policy` disabling camera/microphone/geolocation/payment; `X-Robots-Tag=noindex`.
- Vercel project metadata: `ssoProtection.enabled=true`, `deploymentType=all_except_custom_domains`. Protected access was verified through the platform account; ordinary visitors without an access grant have not been used to test every access path.

## Current limitations
- These are **authenticated HTTP response and content checks**, not browser E2E rendering, screenshot, or keyboard/accessibility confirmation. Prior GitHub Chromium CI tests exercise the current prototype and synthetic intercepted data, rather than certified five-series live display.
- Preview has **not yet received** actual 705-record chart data. A stand-alone private HTML chart preview was generated from independently matched official archives, but is not deployed to Vercel.
- The existing HTML legal notice acknowledges missing full operator contact/imprint and privacy document completion. External Google Fonts and Google-hosted imagery rights/data-transfer review is incomplete. Current footer correctly says DesiPlat operates FirmaBlick in India, with no EU trademark registration assertion.
- **No public release authorization.** Model numerical diagnostics fail all-horizon gate; public forecast flags must remain false.

## Acceptance state
Protected preview connectivity and static HTTP-security header inspection: PASS.
Protected five historical chart acceptance, live accessibility and final legal approval: OPEN.
No modifications to production, DNS or domains.
