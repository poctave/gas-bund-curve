"""Project configuration: paths, raw-file registry, regimes and event dates."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
TABLES = ROOT / "output" / "tables"
FIGURES = ROOT / "output" / "figures"
for _p in (RAW, CLEAN, TABLES, FIGURES):
    _p.mkdir(parents=True, exist_ok=True)

# Raw files are identified by the RIC printed in the LSEG export header (row 4),
# so the original download names ("Price History_2026...") never matter.
# canonical raw name -> (RIC or source match, clean variable name)
LSEG_FILES = {
    "TFMBMc1": ("lseg_ttf_TFMBMc1.xlsx", "gas_ttf_m1_eurmwh"),
    "LCOc1": ("lseg_brent_LCOc1.xlsx", "oil_brent_m1_usdbbl"),
    "NGLNMc1": ("lseg_nbp_NGLNMc1.xlsx", "gas_nbp_m1_gbppth"),
    "NGc1": ("lseg_hh_NGc1.xlsx", "gas_hh_m1_usdmmbtu"),
    "EUR=": ("lseg_fx_EURUSD.xlsx", "fx_eurusd"),
    "EURGBP=": ("lseg_fx_EURGBP.xlsx", "fx_eurgbp"),
    "EUCPIZ1Y=TWEB": ("lseg_ils_eur_1y_EUCPIZ1Y.xlsx", "ils_eur_1y"),
    "DE5IRS5Y=RR": ("lseg_swapsprd_de5y_DE5IRS5Y.xlsx", "swapsprd_de5y_bp"),
    "EUREST1M=": ("lseg_ois_estr_1m_EUREST1M.xlsx", "ois_estr_1m"),
    "EUREST3M=": ("lseg_ois_estr_3m_EUREST3M.xlsx", "ois_estr_3m"),
    "EUREST1Y=": ("lseg_ois_estr_1y_EUREST1Y.xlsx", "ois_estr_1y"),
    "EUREST2Y=": ("lseg_ois_estr_2y_EUREST2Y.xlsx", "ois_estr_2y"),
}
ILS_1Y1Y_SOURCE = "eur1Y inflation swap.xlsx"  # EUIL1YF1Y=R, a 1y1y forward despite the file name
ILS_1Y1Y_RAW = "lseg_ils_eur_1y1y_EUIL1YF1Y.xlsx"

# Bundesbank code -> tenor
BUND_CODES = {"A610": "2y", "A620": "5y", "A607": "7y", "A630": "10y",
              "A615": "15y", "A612": "20y", "A640": "30y"}

IMF_GAS_SOURCE, IMF_GAS_RAW = "PNGASEUUSDM.csv", "fred_imf_gas_eu_PNGASEUUSDM.csv"
HICP_SOURCE, HICP_RAW = "eurozone_hicp.csv", "hicp_ea_index.csv"

# 1 therm = 0.0293071 MWh
THERM_PER_MWH = 1 / 0.0293071

# Regimes (inclusive). The war began over the weekend of 28 Feb - 1 Mar 2026;
# 2 Mar is the first trading day (NBP +37%, TTF +39%).
WAR_START = pd.Timestamp("2026-03-02")
REGIMES = {
    "R0_pre2021": ("2014-10-01", "2021-06-30"),
    "R1_gas_crisis": ("2021-07-01", "2022-12-31"),
    "R2_normalisation": ("2023-01-01", "2026-02-27"),
    "R3_iran_war": ("2026-03-02", "2026-12-31"),
}
REGIME_LABELS = {
    "R0_pre2021": "2014-21 pre-crisis",
    "R1_gas_crisis": "2021-22 gas crisis",
    "R2_normalisation": "2023-Feb26 normalisation",
    "R3_iran_war": "Iran war (Mar 2026+)",
}

EVENTS = {
    "2026-03-02": "War onset: Hormuz closure / Qatar LNG halt (first trading day)",
    "2026-03-03": "Day 2: TTF +22%, Ras Laffan output halted",
    "2026-04-08": "US-Iran ceasefire",
    "2026-06-11": "ECB hike #1 (DFR 2.00 -> 2.25)",
    "2026-09-10": "ECB hike #2 (DFR 2.25 -> 2.50)",
}


def regime_of(dates: pd.DatetimeIndex) -> pd.Series:
    out = pd.Series(pd.NA, index=dates, dtype="object")
    for name, (a, b) in REGIMES.items():
        out[(dates >= a) & (dates <= b)] = name
    return out
