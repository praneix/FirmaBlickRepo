# CV1-04 | Energy Flagship V4 editorial candidate and evidence assurance

**Status:** Nonpublic owner review. **Publication:** BLOCKED. **Date:** 2026-11-21. **Issue:** [#42](https://github.com/praneix/FirmaBlickRepo/issues/42).

## Actual editorial deliverables
The owner review package is created outside the **public** GitHub repository, comprising:
- 20-page report PDF and HTML: `FirmaBlick_Energy_Flagship_V4_Candidate.*`
- Five-page free executive sample PDF and HTML: `FirmaBlick_Energy_V4_Executive_Sample.*`
- Formula-preserving V4 investment-model workbook: `FirmaBlick_Energy_V4_Deterministic_Investment_Model.xlsx`
- A reproducible editorial script retained in the private owner's review package
- This public numerical verifier, source register, checksum manifest, and the explicit remaining release gates

**Do not commit the complete paid report or its source HTML to this public repository.** The report is a prospective commercial digital product. It must be stored in a future authenticated report registry (#43). This GitHub tree contains verification code and digest evidence, not distributable paid copies.

## V3 → V4 editorial decisions
- Preserve the authored designs, SVG macro exhibits and primary-source graphs, but reorder original V3 pages into a coherent 20-page narrative: executive framing → Q3 market observations → 2025 price microstructure → delivered-tariff definitions and EU comparisons → EBITDA and plant archetypes → grid and policy → procurement and BESS capital discipline → location and scenario choices → management agenda → claim-level assurance.
- Remove three overlapping V3 pages, including redundant storage summary and stand-alone commercial-offer copy; retain the four mandate executive conversion flow in the management section.
- Retain observed 2025/2026 labels; 2026-S1 Eurostat industrial consumption bands IC–IG are fully separated from wholesale day-ahead and site delivered energy.
- Correct 'DE less FR/ES' label to 'DE minus FR/ES'; retain Germany provisional `p`.
- Use **573** for the official 2025 published negative-price-hour count; **576** represents FirmaBlick's recalculated negative *hourly means* from 15-/60-minute mixed price records. These are distinct measures and still differ by three; DO NOT call them reconciled or treat them as a time series.
- NPV (€69,938) and 20%/30% downside cases independently reproduce formula-based Excel results. All BESS inputs are illustrative with no customer deployment or dispatch feasibility claim.
- Conform all footer dates to 21 November 2026 and re-number exhibits in reading order.
- Primary source register links go to exact SMARD Q3 2026, SMARD 2025, Fraunhofer market API, Eurostat table and TSO provisional tariff release. Policy claims remain subject to point-of-publication freshness review.

## Proof available in GitHub
`python3 research/energy/v4_assurance.py` requires no credentials, checks original 15,387 intervals, exact 2025 wholesale mean and 573-vs-576 distinction, all fifteen H1 2026 IC-IG / DE-FR-ES Eurostat cells and German provisional flags, BESS discounted cash flows, 40 GWh bill and EBITDA arithmetic, source metadata and publication gate. The CI workflow runs this and existing baseline checks on a draft PR.

## Acceptance and what has NOT passed
- **Passed:** internal deterministic calculations and Eurostat source definitions, manuscript pagination and representative vector exhibit visual inspection, coherent report sequence and an owner-downloadable candidate and sample.
- **Pending:** per-claim exact source passage audit for every policy and macro assertion, native Chromium-print PDF parity (WeasyPrint renderer checked; client browser compatibility still outstanding), owner/editorial signoff, licensed asset rights, any residual 573/576 source-method reconciliation and protected report registry / purchase handling. Historical publication/forecast gates stay blocked.
- This is a **candidate** release, not a fully validated commercial edition. Do not close #42 until owner-approved distribution artifact and source rights are evidenced.

## Principal sources
- SMARD 2025 https://www.smard.de/page/en/topic-article/5892/219038/record-high-for-solar-generation-in-each-quarter
- SMARD Q3 2026 https://www.smard.de/page/en/topic-article/5892/222056/higher-generation-and-exports
- Fraunhofer Energy-Charts 2025 interval series https://api.energy-charts.info/price?bzn=DE-LU&start=2025-01-01&end=2025-12-31
- Eurostat `nrg_pc_205` https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_205/default/table
- German transmission tariffs 2027 https://www.amprion.net/Press/Press-Detail-Page_100352.html
