# Issue #8 | Read-only GENESIS ingestion

**State:** production-ready acquisition code with a deliberately unverified live provider connection. No source values may be published until live metadata, adjustment and quality-status semantics are confirmed.

## Verified provider contract

Primary provider: [Destatis GENESIS-Online](https://genesis.destatis.de/datenbank/online/statistic/42153), tables [42153-0001](https://genesis.destatis.de/datenbank/online/table/42153-0001) (manufacturing aggregate) and [42153-0002](https://genesis.destatis.de/datenbank/online/statistic/42153) (two-digit manufacturing divisions).

The [official Destatis REST example repository](https://github.com/StatistischesBundesamt/GENESIS-Online) and [POST example documentation](https://genesis.destatis.de/datenbank/online/docs/20250505_python_post_logincheck_tablefile_cubefile.pdf) confirm:
- API base: https://genesis.destatis.de/genesisWS/rest/2020/
- **POST only**, never GET (changed in 2025).
- Place read-only **GENESIS personal API token in HTTP header** as \`username\`, with empty \`password\`; send form-encoded **request body**, no credentials in URLs.
- \`metadata/table\` returns JSON (status must be validated); \`data/tablefile\` with \`format=ffcsv\` returns a ZIP containing a semicolon-delimited flat-file CSV.
- Error payloads, including failures on HTTP 200, may return a GENESIS JSON status instead of ZIP.
- Values and timestamps remain raw for Issue #8. Quality flags and full raw dimensions are preserved as evidence.
- API access requires a registered GENESIS account and personal token; account and API access are free, subject to published attribution and terms.

**Token setup:** Sign up at https://genesis.destatis.de/ , open Webservice (API) in your account, generate a personal token, then store it in a local environment variable \`GENESIS_TOKEN\` (or a protected CI secret). Never paste a token in a GitHub issue, PR, log, chat or committed file.

## Commands

No package installation necessary (Python 3.11+ standard library):

\`\`\`bash
python3 -m unittest discover -s tests -p 'test_genesis.py' -v
python3 -m ingestion.genesis logincheck
python3 -m ingestion.genesis fetch --startyear 2021 --endyear 2026 --output artifacts/genesis
\`\`\`

With no token, the command fails with code **2** and a specific setup instruction. With a rejected token, it similarly fails rather than generating or silently substituting synthetic observations. Temporary source errors retry at most 3 times. A malformed archive, invalid metadata JSON, missing sector, inconsistent base-year or unknown field structure fails closed.

**Gated live smoke test** (requires authenticated access and explicit external call):

\`\`\`bash
GENESIS_LIVE_SMOKE=1 python3 -m ingestion.genesis live-smoke
\`\`\`

This checks remote authentication but does not claim five-series coverage. A full \`fetch\` validates coverage after acquisition. Leave the live test absent from normal public pull-request CI to prevent token exposure and surprise external requests.

## Inventory and provenance

One \`fetch\` retrieves metadata and raw ZIPs for each of two tables and creates separate acquisition folders containing:
- \`metadata.json\`: unmodified GENESIS response bytes
- \`tablefile.zip\`: unmodified compressed flat-file CSV bytes
- \`manifest.json\`: acquisition UTC, source endpoint, request filters, table ID, safe HTTP metadata (status/content-type/ETag/last-modified), SHA-256 of each raw artifact and source code coverage by table

The ZIP is inspected in memory, with max-file limits, and the five target industry codes are matched **exactly** (C; WZ divisions 20, 24, 28, 29) to avoid accidentally interpreting C281, C202 or similarly prefixed sub-divisions as full division results. Original dimension codes, periods and sample source quality flags remain in the inventory.

Index base-year is read from the source CSV's value unit or value-variable label, and cannot silently combine 2021=100 with another basis. Coverage and base-year checks are **discovery-only**, not the historical release gate: source adjustments and quality statuses may still include multiple series within each industry. Issue #10 will validate selected measures and normalize source data to the v1 observation schema.

The software does not invent official series, issue public statistical forecasts, or write to a database. Acquired raw artifacts are local and excluded from Git. Issue #9 will add immutable versioned storage.

## Fixture accuracy and limitations

Tests generate **synthetic values in the official documented flat-file CSV column pattern**, wrapped in ZIP bytes. They test structural compliance, complete industry detection and deterministic failure behaviour. These are *official-format test fixtures*, not copies of official response bytes and not evidence of successful live API authentication.

A first actual live acquisition must inspect the downloaded metadata and confirm:
1. How WZ2008 divisions and the manufacturing aggregate are coded within GENESIS tablefile rows.
2. Which original, calendar-adjusted, or seasonally-adjusted series should be selected.
3. Which quality signs correspond to provisional/revised/suppressed values.
4. The effective base year and release date for the downloaded vintage.

If an actual producer response differs from the documented format, fix the adapter and extend its test fixture from a **sanitized** official response sample before accepting the live smoke result. Preserve source raw bytes, never claim a successful normalized dataset merely because downloading succeeded.

## References

- https://github.com/StatistischesBundesamt/GENESIS-Online
- https://genesis.destatis.de/datenbank/online/docs/20250505_python_post_logincheck_tablefile_cubefile.pdf
- https://genesis.destatis.de/genesisWS/swagger-ui/index.html
- https://genesis.destatis.de/datenbank/online/statistic/42153
- https://www.destatis.de/EN/Service/OpenData/api-webservice.html
