# FirmaBlick first-cut website brief

## Objective
Create a polished first-cut **responsive website prototype**, with a Vercel preview available from a GitHub pull request. Prioritize visuals and a working preview. The modelling engine, private customer datasets, authentication, payment integrations and live datasets are separate milestones.

## Brand and design
- Brand: FirmaBlick. No trademark symbols anywhere.
- Tagline: STRUCTURE. PERSPECTIVE. IMPACT.
- Deep navy `#10283D`, warm ivory `#FAF9F6`, white `#FFFFFF`, restrained red accent `#B84A42`.
- Editorial research institution quality, premium serif headlines + highly legible sans-serif body.
- **Approved Google Stitch export is source of truth** if present in the repository under `stitch-export/`. Preserve imagery and layout; make componentized, responsive and accessible.

## First-cut pages
1. Home: editorial headline, European industrial economics focus, featured insight, dynamic demo preview, research teasers and contact call to action.
2. Intelligence: interactive demo for German industrial outlook to 2030 with three scenarios (Central, Resilience, Transformation), productivity slider 0–5%, start 2027/2028/2029, energy price deviation -3% to +3%, comparison selector. Demo values must be labelled **illustrative**. Make controls responsive and functional, without pretending to use official data.
3. Research: browsable preview catalogue with placeholder reports clearly labelled as examples.
4. Methodology: official historical vs provisional vs estimated vs forecast, traceability and calibration principles.
5. Contact: accessible form UI (no false claim of sending unless backend is wired).
6. Footer: Privacy, Terms, Imprint, Disclaimer placeholders clearly marked pending legal review; disclose FirmaBlick as a brand operated by DesiPlat, India.

## Engineering
- Prefer Next.js + TypeScript + Tailwind when an app skeleton is needed.
- Mobile / tablet / desktop responsive; semantic HTML; accessible labels and keyboard focus.
- No invented historical official statistics, references, or working backend claims.
- No connected customer upload, real data processing, authentication or external API keys in this prototype.
- Provide clear README setup, list working pages, note limitations.
- No changes to other projects.
