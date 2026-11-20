# FirmaBlick n8n API diagnostics bridge (initial, read-only)

Purpose: inspect known live n8n workflow IDs and recent execution states from GitHub Actions without manually copying stack traces or using n8n Assistant credits.

The public n8n API is available **only on paid Cloud plans** (including Starter); unavailable on the free Cloud trial as of 2026-11-20. See https://docs.n8n.io/connect/n8n-api/authentication/.

## User one-time setup
1. Subscribe to n8n Cloud Starter, unless the trial API restriction is lifted.
2. n8n Settings > n8n API > Create API key. Limit scopes to `workflow:read`, `execution:read`, and `execution:list` if available. Set expiration. Do not share the key in chat.
3. Add GitHub Actions repository secrets under `praneix/FirmaBlickRepo`:
   - `N8N_BASE_URL`: `https://<workspace>.app.n8n.cloud`
   - `N8N_API_KEY`: n8n's API key.
4. Run **FirmaBlick n8n Read-only Diagnostics** from Actions on this feature branch.

This pilot makes GET requests only. It never publishes or updates workflows or accesses credential values.
The diagnostics summary reports workflow IDs, node counts and recent execution IDs/statuses.
Sensitive full workflow definitions and execution payloads stay in memory on the ephemeral runner, never written to GitHub logs or artifacts.

## Future engineering access
After read-only diagnostics is validated, workflow updates can be supported by a separate explicitly gated GitHub Actions operation that backs up existing definitions, drafts modifications and verifies behavior. Do not enable write access to this diagnostic key unless separately authorized. 
