# CV1-17 / Issue #55 — recovered-source retention and restoration record (2026-11-20)

## Outcome to date
**Original authenticated source snapshots preserved in owner-only Google Drive**, independently of short-lived GitHub Actions artifacts.

Restricted Drive folder: https://drive.google.com/drive/folders/1UHz0Yt6f88qCw1WDIMx4sQRzLTuBvS-_

| Archive | Drive file | GitHub artifact | Bytes | SHA256 |
|---|---|---|---:|---|
| Destatis GENESIS 2015–2026 | `1kXx1Y_T8bS2bjCtjjPQ5JRRlvCkiJPcX` | `14613832495` / run `44702970458` | 596015 | `568b6d514643c85a777dc21e9cecf6aa36d2d8fe12bdf4a1e5ebef986a80d3de` |
| Eurostat `sts_inpr_m` comparison | `10aYslK3sl6nQLVqOesRdbQDrGOwBxpFb` | `14612934209` / run `44703565920` | 7978 | `65906eb5bcd853bf1b6f85c60d16d7d9f60fed9eace673daa4c2b5846e30c694` |

GitHub artifact expiry: 2026-12-20 UTC. Google Drive file metadata confirms owner-only access (no public / shared grants). Original zip SHA256 checked on source download and again after an independently fetched Drive raw-file download, with exact byte hashes. Original contained SQLite acquisition metadata and SHA256-addressed raw source objects. Both retained `publication_approved=0`.

## Recover and validate, using only original Drive archives
Download both files from the restricted folder to a controlled local directory; then run:
```bash
python3 scripts/verify-restored-statistical-archives.py \
  destatis-genesis-2015-2026-original-unpublished-2026-11-20.zip \
  eurostat-five-sector-original-unpublished-2026-11-20.zip
```
Expected JSON: `VERIFIED_RESTORED_UNPUBLISHED`, 705 exact matches, 5 sectors, 141 months per industry, and `publication_approved=false`. Script fails on altered outer archive, altered raw objects, wrong dimension definitions or a single mismatched value.

## Engineering limitations / remaining acceptance gate
- Google Drive is **not** write-once immutable (WORM) object storage. The archives have independent retrieval and checksum verification, but malicious deletion or account compromise is still possible.
- For long-term institutional-grade assurance, add an independently administered second backup / versioned-object-store retention policy with tested object lock and restore. This step may require owner approval for additional infrastructure or charges.
- Archive files are private source evidence. Do not add ZIP bytes to public GitHub, customer-facing static sites or automated Vercel deployments.
- The exact 705/705 parity is for the source snapshots as retrieved; it is **not** independent point-in-time historical vintage reconstruction, forecast validation or owner authorization to publish.

**Release:** None. **Issue closure:** block until the repository script has an independently verified test run on a clean checkout and the archival durability acceptance policy is ratified. 
