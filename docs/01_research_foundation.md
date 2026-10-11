# Gas → Inflation Expectations → ECB → Bund Curve
## Phase 1: Benchmarks, data audit and validity of the thesis

*Prepared 11 Oct 2026. Data as of 9 Oct 2026 close.*

---

## 1. The thesis, stated precisely

> Since the Iran war began (end-Feb 2026), European gas prices have become a main driver of euro-area inflation expectations. Those expectations drive ECB rate-hike expectations. Gas moves should therefore explain, and possibly **predict**, specific moves on the German curve.

This is really two claims, and they need different evidence:

| Claim | What it requires | Difficulty |
|---|---|---|
| **Transmission** (gas co-moves with the curve through an inflation and policy channel) | Contemporaneous regressions, mediation through ILS and OIS, regime dependence | Moderate. Support is already visible in the data (§5) |
| **Predictivity** (gas today tells you about curve moves *later*) | A lead–lag that survives market efficiency, out-of-sample tests, and real-time data | Hard. Daily lead–lag between liquid markets is usually arbitraged away. The more plausible route is gas → *future HICP prints and ECB meetings* → repricing on those dates |

---

## 2. What each benchmark and contract actually is

### 2.1 German government yields (Bundesbank `BBSSY.D.REN.EUR.A6xx…`)

| File code | Tenor | Instrument | History in file |
|---|---|---|---|
| A610 / WT0202 | 2Y | Bundesschatzanweisung (Schatz) | 2014-01 → |
| A620 / WT0505 | 5Y | Bundesobligation (Bobl) | 2006-09 → |
| A607 / WT7070 | 7Y | Bund | 2020-05 → |
| A630 / WT1010 | 10Y | Bund | 2001-10 → |
| A615 / WT1515 | 15Y | Bund | 2020-05 → |
| A612 / WT2020 | 20Y | Bund | **2026-01 →** (only about 180 obs) |
| A640 / WT3030 | 30Y | Bund | 1993-12 → |

- **What it is:** the daily yield of the *current* (on-the-run) federal security in each maturity bucket. It is **not** a constant-maturity or zero-coupon yield. Residual maturity drifts down between new issues, and the series jumps slightly when a new bond becomes "current".
- **Why it matters for the thesis:**
  - The **2Y Schatz** is the market's cleanest Bund-curve proxy for ECB policy expectations over the next roughly 2 years. Even so, it also carries a collateral/scarcity premium (the Schatz asset-swap spread), which moved a lot in 2022–23.
  - **5Y to 10Y** blend expected policy with term premium.
  - **30Y** is dominated by term premium, pension/insurance (ALM) demand, and since March 2025, German fiscal supply. The 5 Mar 2025 +21–22 bp day in the data is the debt-brake reform shock.
- **Unit:** percent, end-of-day. There are no weekend rows. Flags include `Estimated`, `Corrected` and `Provisional` values (a handful).

### 2.2 ICE UK NBP natural gas futures, front month (`NGLNMc1`)

- **What it is:** a continuation of the front-month futures contract on the **UK National Balancing Point** hub, quoted in **pence per therm** (GBp/th).
- **Rough conversion:** 1 therm = 0.1 MMBtu ≈ 0.0293 MWh. So 202.56 p/th (9 Oct 2026) ≈ £69/MWh.
- **Relevance:** NBP is tightly arbitraged with TTF through the interconnectors and LNG. Its monthly changes correlate **0.89** with the IMF EU gas series over 2016–2026. However:
  - It is the **UK** hub, priced in **GBP**. The euro-area inflation benchmark is **Dutch TTF** (EUR/MWh).
  - The UK has little storage, so NBP has its own seasonal and weather basis.
  - `c1` is a **continuation**. It jumps at each roll, especially Sep→Oct and Mar→Apr, when the contract switches between summer and winter delivery. Raw `c1` returns on roll days are not true price moves.
- **Files:** `Price History_20261010_1208.xlsx` (2 years) is a **strict subset** of `Price History_20261010_1208 (1).xlsx` (Nov 2016 → Oct 2026). I verified the two are identical on all 506 overlapping days, so the 2-year file is redundant.

### 2.3 NYMEX Henry Hub natural gas, front month (`NGc1`)

- **What it is:** US gas at the Louisiana hub, in **USD/MMBtu**.
- **Relevance:** it is not a euro-area inflation driver. It is useful only as:
  - a **control**, for global or US-specific gas shocks;
  - the **LNG arbitrage leg**. TTF − (HH × 1.15 + liquefaction + shipping) ≈ the margin pulling US cargoes to Europe.
- **Data issue:** the −64% move on 29 Jan 2026 is a contract roll after the late-January spike, not a price crash. It must be roll-adjusted.
- Only 2 years of history.

### 2.4 IMF "Global price of Natural Gas, EU" (FRED `PNGASEUUSDM`)

- Monthly **average**, USD/MMBtu, 2014-01 → 2026-07 (lags about 2–3 months).
- The IMF does not formally name the hub in its FRED metadata. Third parties describe it as TTF-based in recent years, spliced to an older oil-indexed German border price. **Treat the early history with care.**
- It is in USD, so EUR/USD moves contaminate it as a euro-area cost measure.
- **FRED revises recent months.** For example, the March 2026 figure of 17.67 has differed between vintages.

### 2.5 EUR inflation swap: `EUIL1YF1Y=R` (file named "eur1Y inflation swap")

- ⚠️ **This is not the 1Y spot inflation swap.** By LSEG naming convention, `1YF1Y` is the **1-year rate, 1 year forward (1y1y)**: expected HICPxT inflation from about Oct 2027 to Oct 2028. The earlier analysis labelled it "1Y swap".
- **Underlying:** euro-area HICP **ex-tobacco** (HICPxT), with a 3-month indexation lag.
- **Why 1y1y matters:** the spot 1Y swap is largely *mechanical*, pinned by energy prices already in the pipeline. 1y1y measures whether the market thinks the shock **persists into the ECB's policy horizon**, which is the right object for the thesis. The 2026 data show 1y1y rising from 1.74% (27 Feb) to 2.28% (22 Jul).
- **Caveat:** EUR ILS also embeds an inflation risk premium and liquidity effects, and the front end is very oil-sensitive.

### 2.6 Euro-area HICP (`eurozone_hicp.csv`)

- Monthly index, **not seasonally adjusted**.
- ⚠️ **Two index bases are spliced.** Rows to Nov 1999 are on an old base (around 83–86). From Dec 1999 the series is on **2025 = 100**, Eurostat's new reference year since the January 2026 release; the 2025 average in the file is exactly 100.00. This creates a fake **−34% month in Dec 1999**, and every YoY figure through Nov 2000 is garbage.
- Dates are mid-month stamps. They need to be normalised to the **reference month**, and for predictive work, to the **release date**: flash at end of month, final mid-month after.

### 2.7 `stock_data.csv`: recommend **discarding**

- 24 rows, source unknown. It looks like Henry Hub (3.20 vs NGc1's 3.22 on 9 Oct), but it does not match NGc1 closes on other days (8 Oct: 3.13 vs 3.168).
- It contains weekend rows (e.g. 3–4 Oct, 26–27 Sep) that duplicate Friday rows.
- Some rows have High < Open (25–26 Sep: Open 3.30, High 3.23).
- It is not reliable or needed.

---

## 3. Is the economic logic valid?

### 3.1 The chain and the 2026 evidence

```
Gas supply shock (Hormuz / Qatar LNG)
   │  direct: retail gas & electricity tariffs (lags 1–12m, country-specific regulation)
   │  indirect: industry costs, fertiliser → food
   ▼
Euro-area inflation (HICP energy)  ──►  market inflation expectations (ILS 1y, 1y1y)
                                              ▼
                                   ECB reaction function → €STR OIS → 2Y Schatz
                                              ▼
                               Curve: front end ↑ more than long end = BEAR FLATTENING
```

The 2026 narrative supports every link:

- **Gas.** TTF went from about €32/MWh before the war to more than €60 in early March, after Qatar halted LNG output following strikes on Ras Laffan and Hormuz was disrupted. It fell more than 15% on the 8 April ceasefire, then rose again in July. Kpler reports the front-month at $20.91/MMBtu on 22 Jul, the highest since Jan 2023.
- **Inflation.** Euro-area HICP was 3.3% YoY in August, with energy at +14.3%.
- **ECB.** The ECB hiked in **June** (first hike since 2023, deposit rate to 2.25%) and **September** (to 2.50%). Markets were pricing 2–3 more hikes by end-2027.
- **Curve.** The curve bear-flattened. Your Bundesbank data show:

| Date | 2Y | 5Y | 10Y | 30Y | NBP (p/th) | 1y1y ILS |
|---|---|---|---|---|---|---|
| 27 Feb 2026 (pre-war) | 2.03 | 2.28 | 2.69 | 3.36 | 78.6 | 1.74 |
| 31 Mar 2026 | 2.62 | 2.73 | 3.03 | 3.48 | 128.1 | 2.21 |
| 8 Apr 2026 (ceasefire) | 2.50 | 2.62 | 2.92 | 3.45 | 114.3 | 2.09 |
| 22 Jul 2026 (re-escalation) | 2.81 | 2.92 | 3.17 | 3.66 | 151.4 | 2.28 |
| 9 Oct 2026 | 3.09 | 3.23 | 3.47 | 3.85 | 202.6 | 2.21 |

Since the war began, the 2Y is up **+106 bp** and the 30Y **+49 bp**, so 2s30s has flattened by about 57 bp. The thesis is coherent with the observed price action.

### 3.2 A quick regime check (weekly changes, NBP roll days removed)

| Regime | Weeks | corr(gas, 1y1y) | corr(gas, 2Y) | corr(gas, 10Y) | corr(gas, 30Y) | corr(gas, 2s10s) | 2Y bp per +10% gas |
|---|---|---|---|---|---|---|---|
| 2017–19 calm | 156 | +0.05 | +0.11 | +0.15 | +0.17 | +0.11 | +0.6 |
| Jul 2021–2022 gas crisis | 79 | −0.00 | **−0.31** | −0.28 | −0.28 | +0.08 | **−2.2** |
| 2023 – Feb 2026 | 165 | +0.09 | +0.17 | +0.05 | −0.02 | −0.21 | +2.1 |
| **Iran war, Mar 2026 →** | 32 | **+0.52** | **+0.52** | +0.40 | +0.22 | **−0.48** | **+6.4** |

**Reading:** the relationship is strongly **regime-dependent**.

- Only in the 2026 regime does gas load on the front end with the expected sign, flattening the curve.
- In 2022, gas spikes were met with *lower* weekly yields. The likely causes are flight-to-quality into Bunds, a growth/recession shock, and an ECB still seen as behind the curve.

This is a key result in itself. The thesis holds **conditionally**: when the central bank is seen as *reactive* to energy inflation. It does not hold unconditionally.

*Caveat: 32 weekly observations is a small sample. These are indicative correlations, not inference.*

### 3.3 Threats to validity

1. **Oil is the main confounder.** Hormuz hits oil and gas at the same time, and EUR inflation swaps are historically driven by **Brent** more than by gas. Without a Brent control, a "gas beta" largely picks up oil. **This is the most important gap.**
2. **Gas supply shocks are stagflationary.** Higher inflation pushes yields up, but weaker growth and flight-to-quality push Bund yields down. The net sign depends on the regime, as §3.2 shows. Model it with regime interactions; do not assume a constant beta.
3. **LNG vs pipeline shocks differ.** ECB WP 3227 (May 2026) finds that **LNG supply shocks affect inflation expectations less** than pipeline shocks, even though both raise gas prices and realised inflation. The Iran war is primarily an *LNG* shock. This is a direct counterpoint to address: the strong 2026 co-movement may run through oil, or through a perceived ECB reaction function, rather than through ILS alone.
4. **A common news factor.** Gas and yields may both be reacting to the same geopolitical headlines, with no causal path through inflation expectations. Event studies (2 Mar, 8 Apr, July re-escalation) and mediation tests help separate the two.
5. **The 2Y Bund is not equal to rate expectations.** It also carries a scarcity/collateral premium and flight-to-quality bid. To test the "rate-hike expectations" link directly, you need **€STR OIS**, either ECB-meeting-dated or 1Y / 1y1y.
6. **German-specific long-end drivers.** Fiscal expansion since March 2025, Bund supply, and the end of QT dynamics drive 10Y–30Y independently of gas. Use slopes and PCA factors, not raw long-end levels.
7. **Predictivity and look-ahead bias.**
   - HICP is published with a lag.
   - FRED gas data are revised.
   - Monthly *averages* of gas against monthly *averages* of yields create spurious smoothing and autocorrelation.
   - Any predictive test must use **real-time data** and **out-of-sample** evaluation.

### 3.4 Problems in the earlier analysis (`gas_yield_analysis.py`)

The earlier conclusions should **not** be relied on:

- **Mislabelled swap.** It treats the 1y1y swap as the "1Y" swap.
- **YoY across the HICP break.** It computes HICP YoY across the base-splice break.
- **Fake zero returns.** `fillna(0)` on gas returns turns missing data into "no move" observations.
- **Bad controls.** It controls for inflation and ILS, which are the **mediators** of the channel being tested. This absorbs exactly the effect the thesis predicts.
- **Odd lag structure.** Gas is lagged by the *same* number of months as the forecast horizon, which is not a standard predictive design.
- **Unadjusted standard errors.** Horizons overlap (3, 6 and 12 months) but there are no HAC (Newey–West) standard errors. The reported p-values are overstated.
- **Smoothing.** It uses monthly-average yields against monthly-average gas.
- **Wrong environment.** The anaconda environment is broken (NumPy 1/2 ABI clash). I installed `pandas`, `statsmodels`, `openpyxl` and `matplotlib` into the project `.venv`; use `.venv/bin/python`.

---

## 4. Data gaps to fill

In priority order. LSEG RICs are given where I'm confident; verify them in the terminal.

| # | Series | Why | Suggested source |
|---|---|---|---|
| 1 | **TTF front-month, daily** (ICE Endex Dutch TTF, EUR/MWh) + ideally **TTF Cal-27** | *The* euro-area gas benchmark. Cal-27 captures the persistence the 1y1y and ECB care about | LSEG `TFMBMc1`; Cal strip from ICE Endex |
| 2 | **Brent front-month, daily** | Main confounder (§3.3.1) | LSEG `LCOc1` |
| 3 | **€STR OIS**: 1Y, 2Y, 1y1y (or ECB meeting-dated OIS) | Direct measure of rate-hike expectations, the middle link | LSEG / Bloomberg / ECB |
| 4 | **EUR ILS 1Y spot** and **5y5y** | Spot = mechanical near-term pass-through. 5y5y = de-anchoring / long-end channel | LSEG |
| 5 | **EUR/GBP, EUR/USD** | To convert NBP/IMF into EUR/MWh | ECB SDW reference rates |
| 6 | **VSTOXX or similar** | Risk-off / flight-to-quality control | |
| 7 | **HICP flash release dates + consensus**, **ECB meeting dates** | Event studies and predictive tests through data surprises | Eurostat calendar, ECB |
| 8 | *Optional:* Bundesbank **zero-coupon term structure** (daily, constant maturity) | Removes on-the-run roll effects from curve and PCA work | Bundesbank BBSIS dataset |

The analysis can start with what you have, using NBP as a TTF proxy and 1y1y as the expectations measure. Items 1–3, however, are what make the result defensible.

---

## 5. Proposed cleaning and naming conventions (Phase 2)

**Folder layout**

```
data/raw/        originals, untouched
data/clean/      tidy daily + monthly panels (parquet + csv)
docs/            this memo, data dictionary
src/             loaders, cleaning, analysis modules
output/          tables & charts
```

**Variable naming:** `<asset>_<instrument>_<tenor>_<unit>`

| Clean name | Source | Notes |
|---|---|---|
| `bund_2y`, `bund_5y`, `bund_7y`, `bund_10y`, `bund_15y`, `bund_20y`, `bund_30y` | Bundesbank BBSSY | %, keep quality flags in `*_flag` |
| `slope_2s10s`, `slope_2s30s`, `slope_5s30s`, `fly_2s5s10s` | derived | bp |
| `gas_nbp_m1_gbppth` | NGLNMc1 | plus `gas_nbp_m1_ret_rolladj` |
| `gas_hh_m1_usdmmbtu` | NGc1 | roll-adjusted returns |
| `gas_eu_imf_usdmmbtu_mavg` | FRED PNGASEUUSDM | monthly only |
| `ils_eur_1y1y` | EUIL1YF1Y=R | % |
| `hicp_ea_idx_2025` and `hicp_ea_yoy` | eurozone_hicp | post-Dec-1999 only, reference-month dated |
| `regime_war` | dummy | 1 from 2026-03-02 (first trading day after the war began); exact start date to confirm |

**Cleaning rules**

- Business-day calendar (TARGET2).
- No forward-filling of prices for returns. Missing stays missing.
- Remove roll-day returns or build ratio-adjusted continuations.
- Log returns for gas; bp changes for yields.
- Flag `Estimated` / `Corrected` values.
- Trim the HICP splice.
- Drop `stock_data.csv`.
- Use the long NBP file only.

---

## 6. Proposed empirical design (Phase 3)

1. **Event study.**
   - Events: 2 Mar 2026 (war onset), 8 Apr (ceasefire), July re-escalation, ECB 11 Jun and 10 Sep, HICP flash dates.
   - Measure: 1–2 day changes across the curve and in 1y1y.
2. **Transmission regressions (daily and weekly).**
   - Δ2Y, Δ5Y, … on Δlog gas, Δlog Brent, ΔFX and risk.
   - Interacted with `regime_war`, using HAC standard errors and rolling betas.
3. **Mediation.**
   - Gas → Δ1y1y ILS → ΔOIS → Δ2Y.
   - Tests whether the gas effect on the curve runs through expectations.
4. **Curve shape.**
   - Regress level, slope and curvature (PCA on 2Y–30Y) on gas.
   - Hypothesis: gas loads on **slope (flattening)** in the war regime.
5. **Predictivity.**
   - Jordà local projections at horizons h = 1–20 days and 1–6 months.
   - Gas → future HICP-energy surprises → ECB repricing.
   - Out-of-sample R² vs a random walk.
   - Strictly real-time data.

---

## Sources

- Kpler: [Hormuz crisis drives TTF to highest level since 2023](https://www.kpler.com/blog/global-lng-and-natural-gas-prices-surge-as-us-and-iran-resume-hot-war)
- CNBC: [Middle East war sends natural gas prices soaring](https://www.cnbc.com/2026/03/03/middle-east-war-gas-energy-lng-drone-qatar-strait-hormuz-price-shock.html)
- Trading Economics: [TTF prices plunge on US-Iran ceasefire](https://tradingeconomics.com/commodity/eu-natural-gas/news/540028)
- Trading Economics: [Bund yields plunge as US-Iran ceasefire eases ECB hike expectations](https://tradingeconomics.com/germany/government-bond-yield/news/540079)
- EIA: [International LNG prices rise amid Strait of Hormuz closure](https://www.eia.gov/todayinenergy/detail.php?id=67604)
- EUI FSR: [How the war with Iran is reshaping Europe's gas security](https://fsr.eui.eu/how-the-war-with-iran-is-reshaping-europes-gas-security/)
- CNBC: [ECB hikes for first time since 2023 (11 Jun 2026)](https://www.cnbc.com/2026/06/11/ecb-hikes-interest-rates.html)
- CNBC: [ECB hikes rates as expected (10 Sep 2026)](https://www.cnbc.com/2026/09/10/ecb-interest-rate-hike-lagarde-iran.html)
- CNBC: [Traders see September hike as ECB mulls energy spike](https://www.cnbc.com/2026/07/23/interest-rate-hike-iran-european-central-bank.html)
- Euronews: [Bond yields surge as Iran war stirs inflation fears](https://www.euronews.com/business/2026/03/26/bond-yields-surge-as-iran-war-stirs-inflation-fears-almost-a-month-into-the-conflict)
- CNBC: [European bond yields at 15-year highs](https://www.cnbc.com/2026/03/27/european-bond-yields-inflation-rate-hikes.html)
- InterCapital: [Bear flattening and broken supply chains](https://inter.capital/bear-flattening-and-broken-supply-chains-the-iran-wars-divergent-impact-on-us-and-european-markets-2/)
- ABN AMRO: [Rates conviction, Middle East conflict update (12 Mar 2026)](https://assets.ctfassets.net/1u811bvgvthc/1WqQjioRIw1DQ4guOC8y40/3419c4f7b03235328f38e4b3aa81a1c1/20260312_ABN_AMRO_Rates_Conviction_-_Update_Middle_East_Conflict.pdf)
- ECB WP 3227: [Gas market shocks: tracing the effect on euro area inflation expectations](https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp3227~2a32fe33b7.en.pdf)
- ECB WP 2905: [Gas price shocks and euro area inflation](https://ECB.eu/pub/pdf/scpwps/ecb.wp2905~6b246d6bf4.en.pdf)
- ECB WP 2968: [The pass-through to inflation of gas price shocks](https://ecb.europa.eu/pub/pdf/scpwps/ecb.wp2968~e514c92723.en.pdf)
- FRED: [PNGASEUUSDM](https://fred.stlouisfed.org/series/PNGASEUUSDM)
- Bundesbank: [Capital market indicators (rendbund)](https://www.bundesbank.de/resource/blob/772218/f2dacb4a7ceed9e6dec3e91c9bab284a/472B63F073F071307366337C94F8C870/rendbund-data.pdf)
- NTMA: [HICP rebasing notice, March 2026](https://www.ntma.ie/uploads/general/HICP-Rebasing-Notice-March-2026.pdf); AFT: [New HICP reference year](https://www.aft.gouv.fr/en/node/13675)
- ECB Economic Bulletin 5/2025: [ILS forward naming and LSEG data](https://www.ecb.europa.eu/press/economic-bulletin/articles/2025/html/ecb.ebart202505_02~b0c28fc22e.en.html)
