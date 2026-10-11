# Gas prices and the German yield curve

Do European gas prices drive, and predict, moves on the German Bund curve through inflation expectations and ECB rate-hike expectations?

**Short answer.** Since the Iran war began (first trading day 2 March 2026), a +10% move in Dutch TTF gas has lifted the 2-year Bund yield by about 4bp on the same day, while leaving the 30-year almost unchanged. Gas has driven ECB hike pricing and bear-flattened the curve. The link is regime-specific: it had the opposite sign in 2021-22 and is close to zero in normal times. Gas explains same-day curve moves but does not forecast later ones. Its genuine predictive content is for realised euro-area inflation 6-12 months ahead.

## Read first

| File | What it is |
| --- | --- |
| `output/Gas_Bund_Research_Recap.pdf` | 10-page plain-language recap: the economic story, instruments, data fixes, tests, results, glossary |
| `output/Gas_Bund_Research_Workbook.xlsx` | Full results (29 sheets). Start with `Executive_Summary` |
| `docs/01_research_foundation.md` | Phase 1 memo: benchmark definitions, data audit, validity of the thesis |

## Repository layout

```
data/raw/       source exports under canonical names (Bundesbank, LSEG, FRED, Eurostat HICP)
data/clean/     daily / weekly / monthly panels, data dictionary, data quality log
src/            pipeline code
output/tables/  one CSV per test family
output/figures/ charts (PNG)
docs/           research memo
```

## Pipeline

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cd src
../.venv/bin/python clean.py            # raw -> clean panels, roll and timing flags
../.venv/bin/python econometrics.py     # all tests -> output/tables
../.venv/bin/python figures.py          # charts -> output/figures
../.venv/bin/python build_workbook.py   # results workbook
../.venv/bin/python build_recap_pdf.py  # recap PDF
```

## Data

| Series | Source |
| --- | --- |
| German government yields 2Y-30Y | Bundesbank (BBSSY.D.REN.EUR.A6xx) |
| TTF, Brent, NBP, Henry Hub front-month futures | LSEG (TFMBMc1, LCOc1, NGLNMc1, NGc1) |
| €STR OIS 1M / 3M / 1Y / 2Y | LSEG (EUREST*=) |
| EUR inflation swaps 1Y and 1y1y | LSEG / Tradeweb (EUCPIZ1Y=TWEB, EUIL1YF1Y=R) |
| 5Y swap spread, EUR/USD, EUR/GBP | LSEG (DE5IRS5Y=RR, EUR=, EURGBP=) |
| Euro-area HICP | Eurostat (2025 = 100) |
| IMF EU gas price | FRED (PNGASEUUSDM) |

Key cleaning steps:

- The swap file labelled "1Y" is the 1y1y forward.
- The HICP base splice is removed.
- Futures roll days are detected from open-interest jumps and excluded.
- Bundesbank yields are observed about half a trading day before the LSEG closes. Daily Bund regressions include the previous day's market move, and the full chain is also estimated weekly.

LSEG data are subject to the vendor's licence terms. Keep this repository private unless redistribution is permitted.

## Methods

Every test family has its own sheet in the workbook:

- unit-root tests (ADF, KPSS, Zivot-Andrews) and cointegration (Engle-Granger, Johansen);
- regime regressions with Newey-West HAC errors and Holm correction;
- regime interaction and structural-break tests (Chow, Quandt-Andrews, CUSUM), plus residual diagnostics;
- lead/lag timing tests and block-bootstrap mediation;
- VAR with Granger causality and variance decomposition;
- local projections and out-of-sample forecasts (Clark-West);
- HICP pass-through, curve PCA and an event study.
