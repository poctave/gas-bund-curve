"""Econometric test battery: gas -> inflation expectations -> ECB pricing -> Bund curve.

Conventions
  rates / spreads : daily changes in bp       (d_*)
  prices          : 100 x log change, in %    (r_*)
  => a gas beta is "bp per 1% TTF move"; x9.53 gives "bp per +10% TTF".
  Inference uses Newey-West HAC standard errors throughout.

Every table is written to output/tables/<name>.csv and collected in RESULTS for the workbook.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import (acorr_breusch_godfrey, acorr_ljungbox, breaks_cusumolsresid,
                                          het_arch, het_breuschpagan, het_white, linear_reset)
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson, jarque_bera
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller, coint, kpss, zivot_andrews
from statsmodels.tsa.vector_ar.vecm import coint_johansen

from config import CLEAN, EVENTS, REGIME_LABELS, REGIMES, TABLES

warnings.filterwarnings("ignore")
RESULTS: dict[str, pd.DataFrame] = {}
PER10 = 100 * np.log(1.1)  # converts bp-per-1% into bp-per-+10%

GAS, OIL, FX = "r_gas_ttf_m1_eurmwh", "r_oil_brent_m1_usdbbl", "r_fx_eurusd"
CONTROLS = [OIL, FX]
Y_LABELS = {
    "d_bund_2y": "Bund 2Y", "d_bund_5y": "Bund 5Y", "d_bund_7y": "Bund 7Y", "d_bund_10y": "Bund 10Y",
    "d_bund_15y": "Bund 15Y", "d_bund_30y": "Bund 30Y",
    "d_slope_2s5s": "Slope 2s5s", "d_slope_2s10s": "Slope 2s10s", "d_slope_5s10s": "Slope 5s10s",
    "d_slope_10s30s": "Slope 10s30s", "d_slope_2s30s": "Slope 2s30s", "d_slope_5s30s": "Slope 5s30s",
    "d_fly_2s5s10s": "Fly 2s5s10s",
    "d_ois_estr_1y": "€STR OIS 1Y", "d_ois_estr_2y": "€STR OIS 2Y", "d_ois_estr_1y1y": "€STR OIS 1y1y",
    "d_ils_eur_1y": "Infl. swap 1Y", "d_ils_eur_1y1y": "Infl. swap 1y1y",
    "d_swapsprd_de5y_bp": "5Y swap spread (IRS-Bund)", "d_sprd_bund2y_ois2y": "Bund2Y - OIS2Y",
}
REGIME_ORDER = ["R0_pre2021", "R1_gas_crisis", "R2_normalisation", "R3_iran_war"]


def save(name: str, df: pd.DataFrame) -> pd.DataFrame:
    df.to_csv(TABLES / f"{name}.csv", index=False)
    RESULTS[name] = df
    return df


def nw_lags(n: int) -> int:
    return int(np.floor(4 * (n / 100) ** (2 / 9)))


def ols(y: pd.Series, X: pd.DataFrame, hac_lags: int | None = None):
    data = pd.concat([y, X], axis=1).dropna()
    yy, XX = data.iloc[:, 0], sm.add_constant(data.iloc[:, 1:])
    lags = nw_lags(len(data)) if hac_lags is None else hac_lags
    return sm.OLS(yy, XX).fit(cov_type="HAC", cov_kwds={"maxlags": lags}), data


BBK_DEPS = ("d_bund_", "d_slope_", "d_fly_", "d_sprd_bund2y")


def is_bbk(dep: str) -> bool:
    """Dependent variables built from Bundesbank yields (snapshot ~half a day before LSEG closes)."""
    return dep.startswith(BBK_DEPS)


def market_X(d: pd.DataFrame, dep: str) -> pd.DataFrame:
    """Gas, Brent, EURUSD at t; for Bundesbank-based targets also at t-1 (Dimson adjustment)."""
    X = d[[GAS] + CONTROLS].copy()
    if is_bbk(dep):
        for c in [GAS] + CONTROLS:
            X[c + "_l1"] = d[c].shift(1)
    return X


def total_effect(res, var: str) -> tuple[float, float, float]:
    """beta_t (+ beta_t-1 if present): point, HAC se, p-value."""
    names = [var] + ([var + "_l1"] if var + "_l1" in res.params else [])
    w = np.zeros(len(res.params))
    for nm in names:
        w[list(res.params.index).index(nm)] = 1
    t = res.t_test(w)
    return float(np.squeeze(t.effect)), float(np.squeeze(t.sd)), float(np.squeeze(t.pvalue))


def load():
    lv = pd.read_csv(CLEAN / "daily_levels.csv", index_col=0, parse_dates=True)
    d = pd.read_csv(CLEAN / "daily_changes.csv", index_col=0, parse_dates=True)
    w = pd.read_csv(CLEAN / "weekly_changes.csv", index_col=0, parse_dates=True)
    m = pd.read_csv(CLEAN / "monthly_panel.csv", index_col=0, parse_dates=True)
    d = d[d.index >= "2014-10-13"]
    w = w[w.index >= "2014-10-17"]
    return lv, d, w, m


# =========================================================================== 1. data properties
def descriptive(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    cols = [GAS, OIL, "d_ils_eur_1y1y", "d_ois_estr_1y1y", "d_bund_2y", "d_bund_10y", "d_bund_30y",
            "d_slope_2s10s"]
    for reg in ["ALL"] + REGIME_ORDER:
        sub = d if reg == "ALL" else d[d.regime == reg]
        for c in cols:
            s = sub[c].dropna()
            if len(s) < 30:
                continue
            jb, jbp, sk, ku = jarque_bera(s)
            lb = acorr_ljungbox(s, lags=[10], return_df=True)["lb_pvalue"].iloc[0]
            arch_p = het_arch(s - s.mean(), nlags=5)[1]
            rows.append({"regime": REGIME_LABELS.get(reg, "Full sample"), "series": c, "n": len(s),
                         "mean": s.mean(), "std": s.std(), "skew": sk, "excess_kurtosis": ku - 3,
                         "min": s.min(), "max": s.max(), "acf_lag1": s.autocorr(1),
                         "jarque_bera_p": jbp, "ljung_box_q10_p": lb, "arch_lm5_p": arch_p})
    return save("01_descriptive_stats", pd.DataFrame(rows))


def unit_roots(lv: pd.DataFrame) -> pd.DataFrame:
    series = {
        "bund_2y": lv.bund_2y, "bund_10y": lv.bund_10y, "bund_30y": lv.bund_30y,
        "slope_2s10s": lv.slope_2s10s, "ln_ttf": np.log(lv.gas_ttf_m1_eurmwh),
        "ln_brent": np.log(lv.oil_brent_m1_usdbbl), "ils_eur_1y1y": lv.ils_eur_1y1y,
        "ois_estr_1y1y": lv.ois_estr_1y1y, "ois_estr_2y": lv.ois_estr_2y,
        "swapsprd_de5y_bp": lv.swapsprd_de5y_bp,
    }
    rows = []
    for name, s in series.items():
        s = s[s.index >= "2014-10-13"].dropna()
        # weekly sampling keeps Zivot-Andrews tractable and is standard for unit-root work
        s = s.resample("W-FRI").last().dropna()
        for form, x in [("level", s), ("first difference", s.diff().dropna())]:
            adf = adfuller(x, autolag="AIC")
            kp = kpss(x, regression="c", nlags="auto")
            za = zivot_andrews(x, regression="c", autolag="AIC")
            verdict = ("stationary" if adf[1] < 0.05 and kp[1] > 0.05 else
                       "unit root" if adf[1] > 0.05 and kp[1] < 0.05 else "mixed / borderline")
            rows.append({"series": name, "form": form, "n_weeks": len(x),
                         "adf_stat": adf[0], "adf_p": adf[1], "kpss_stat": kp[0], "kpss_p": kp[1],
                         "za_stat": za[0], "za_p": za[1], "za_break_date": x.index[za[4]].date(),
                         "verdict": verdict})
    return save("02_unit_roots", pd.DataFrame(rows))


def cointegration(lv: pd.DataFrame) -> pd.DataFrame:
    wk = lv.select_dtypes("number").resample("W-FRI").last()
    wk["ln_ttf"] = np.log(wk.gas_ttf_m1_eurmwh)
    wk["ln_brent"] = np.log(wk.oil_brent_m1_usdbbl)
    pairs = [("bund_2y", "ln_ttf"), ("ils_eur_1y1y", "ln_ttf"), ("ils_eur_1y1y", "ln_brent"),
             ("ois_estr_1y1y", "ils_eur_1y1y"), ("bund_2y", "ois_estr_2y"), ("bund_2y", "ils_eur_1y1y")]
    rows = []
    for a, b in pairs:
        x = wk[[a, b]].dropna()
        t, p, _ = coint(x[a], x[b])
        rows.append({"test": "Engle-Granger", "system": f"{a} ~ {b}", "n_weeks": len(x),
                     "stat": t, "p_value": p, "rank_at_5pct": int(p < 0.05),
                     "verdict": "cointegrated" if p < 0.05 else "no cointegration"})
    for sysvars in [["bund_2y", "ils_eur_1y1y", "ln_ttf", "ln_brent"],
                    ["bund_2y", "ois_estr_1y1y", "ils_eur_1y1y", "ln_ttf"]]:
        x = wk[sysvars].dropna()
        j = coint_johansen(x, det_order=0, k_ar_diff=2)
        rank = int(np.sum(j.lr1 > j.cvt[:, 1]))  # sequential trace test at 5%
        rows.append({"test": "Johansen trace", "system": " , ".join(sysvars), "n_weeks": len(x),
                     "stat": j.lr1[0], "p_value": np.nan, "rank_at_5pct": rank,
                     "verdict": f"rank {rank} (trace r=0: {j.lr1[0]:.1f} vs 5% cv {j.cvt[0, 1]:.1f})"})
    return save("03_cointegration", pd.DataFrame(rows))


# =========================================================================== 2. transmission
TRANSMISSION_Y = ["d_ils_eur_1y", "d_ils_eur_1y1y", "d_ois_estr_1y", "d_ois_estr_1y1y", "d_ois_estr_2y",
                  "d_bund_2y", "d_bund_5y", "d_bund_7y", "d_bund_10y", "d_bund_15y", "d_bund_30y",
                  "d_slope_2s5s", "d_slope_2s10s", "d_slope_5s10s", "d_slope_10s30s", "d_slope_2s30s",
                  "d_slope_5s30s", "d_fly_2s5s10s",
                  "d_swapsprd_de5y_bp", "d_sprd_bund2y_ois2y"]


def transmission(d: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Daily: Bundesbank-based targets regress on t and t-1 market moves; total = sum (Dimson).
       Weekly: Friday-to-Friday; Bundesbank targets use market returns lagged one business day."""
    rows = []
    min_n = 25 if freq == "weekly" else 60
    for y in TRANSMISSION_Y:
        for reg in REGIME_ORDER + ["ALL"]:
            sub = d if reg == "ALL" else d[d.regime == reg]
            if sub[y].notna().sum() < min_n:
                continue
            if freq == "daily":
                X = market_X(sub, y)
            else:
                sfx = "_lag1d" if is_bbk(y) else ""
                X = sub[[GAS + sfx, OIL + sfx, FX + sfx]]
                X.columns = [GAS, OIL, FX]
            res, data = ols(sub[y], X)
            if len(data) < min_n:
                continue
            g, gse, gp = total_effect(res, GAS)
            o, ose, op = total_effect(res, OIL)
            rows.append({"frequency": freq, "dependent": Y_LABELS[y], "dep_var": y,
                         "regime": REGIME_LABELS.get(reg, "Full sample"), "n": int(res.nobs),
                         "async_adjusted": bool(is_bbk(y)),
                         "beta_ttf_total": g, "t_ttf": g / gse, "p_ttf": gp, "bp_per_10pct_ttf": g * PER10,
                         "beta_ttf_same_day": res.params[GAS],
                         "beta_ttf_prev_day": res.params.get(GAS + "_l1", np.nan),
                         "beta_brent_total": o, "t_brent": o / ose, "p_brent": op, "bp_per_10pct_brent": o * PER10,
                         "r2": res.rsquared})
    out = pd.DataFrame(rows)
    # Holm correction across the dependent variables within each regime (family = one regime)
    # Holm correction within each regime: (i) across all dependent variables (strictest);
    # (ii) within its family - rate levels & spreads vs curve shape (slopes, fly)
    out["family"] = np.where(out.dep_var.str.startswith(("d_slope_", "d_fly_")), "curve shape", "rates & spreads")
    out["p_ttf_holm"] = np.nan
    out["p_ttf_holm_family"] = np.nan
    for reg, g in out.groupby("regime"):
        out.loc[g.index, "p_ttf_holm"] = multipletests(g.p_ttf, method="holm")[1]
        for fam, gf in g.groupby("family"):
            out.loc[gf.index, "p_ttf_holm_family"] = multipletests(gf.p_ttf, method="holm")[1]
    return save(f"04_transmission_{freq}", out)


def regime_interaction(d: pd.DataFrame) -> pd.DataFrame:
    """Pooled daily model with regime-specific slopes (R1 gas crisis, R3 war vs base R0+R2).
    H0: total TTF effect in regime = base total effect (one linear restriction, HAC)."""
    rows = []
    for y in ["d_ils_eur_1y", "d_ils_eur_1y1y", "d_ois_estr_1y1y", "d_ois_estr_2y", "d_bund_2y", "d_bund_10y",
              "d_bund_30y", "d_slope_2s5s", "d_slope_2s10s", "d_slope_5s10s", "d_slope_10s30s", "d_slope_2s30s",
              "d_slope_5s30s", "d_swapsprd_de5y_bp"]:
        base = market_X(d, y)
        sub = pd.concat([d[[y, "regime"]], base], axis=1).dropna()
        X = sub[base.columns].copy()
        for r in ["R1_gas_crisis", "R3_iran_war"]:
            dummy = (sub.regime == r).astype(float)
            for c in base.columns:
                X[f"{c}:{r}"] = sub[c] * dummy
            X[f"const:{r}"] = dummy
        if X[[c for c in X if c.endswith("R1_gas_crisis")]].abs().sum().sum() == 0:
            X = X[[c for c in X if not c.endswith("R1_gas_crisis")]]
        res, _ = ols(sub[y], X)
        gnames = [c for c in base.columns if c.startswith(GAS)]
        for r in ["R1_gas_crisis", "R3_iran_war"]:
            if f"{GAS}:{r}" not in res.params:
                continue
            w_base = np.array([1.0 if p in gnames else 0.0 for p in res.params.index])
            w_diff = np.array([1.0 if p in [f"{g}:{r}" for g in gnames] else 0.0 for p in res.params.index])
            tb, td = res.t_test(w_base), res.t_test(w_diff)
            rows.append({"dependent": Y_LABELS[y], "regime_vs_base": REGIME_LABELS[r],
                         "base_bp_per_10pct": float(np.squeeze(tb.effect)) * PER10,
                         "regime_bp_per_10pct": float(np.squeeze(tb.effect) + np.squeeze(td.effect)) * PER10,
                         "difference_bp_per_10pct": float(np.squeeze(td.effect)) * PER10,
                         "wald_t": float(np.squeeze(td.tvalue)), "wald_p": float(np.squeeze(td.pvalue)),
                         "n": int(res.nobs)})
    return save("05_regime_interaction", pd.DataFrame(rows))


# =========================================================================== 3. diagnostics
def residual_diagnostics(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in ["d_ils_eur_1y1y", "d_ois_estr_1y1y", "d_bund_2y", "d_bund_10y", "d_bund_30y", "d_slope_2s10s"]:
        for reg in ["ALL", "R3_iran_war"]:
            sub = d if reg == "ALL" else d[d.regime == reg]
            Xm = market_X(sub, y)
            data = pd.concat([sub[y], Xm], axis=1).dropna()
            X = sm.add_constant(data[Xm.columns])
            res = sm.OLS(data[y], X).fit()
            e = res.resid
            bp = het_breuschpagan(e, X)[1]
            wh = het_white(e, X)[1]
            bg = acorr_breusch_godfrey(res, nlags=5)[1]
            lb = acorr_ljungbox(e, lags=[10], return_df=True)["lb_pvalue"].iloc[0]
            arch = het_arch(e, nlags=5)[1]
            jb = jarque_bera(e)[1]
            reset = float(linear_reset(res, power=3, use_f=True).pvalue)
            vif_g = variance_inflation_factor(X.values, list(X.columns).index(GAS))
            vif_o = variance_inflation_factor(X.values, list(X.columns).index(OIL))
            cusum_p = breaks_cusumolsresid(e.values, ddof=X.shape[1])[1]
            issues = []
            if bg < 0.05 or lb < 0.05:
                issues.append("serial correlation")
            if bp < 0.05 or wh < 0.05:
                issues.append("heteroskedasticity")
            if arch < 0.05:
                issues.append("ARCH")
            if jb < 0.05:
                issues.append("fat tails")
            if reset < 0.05:
                issues.append("functional form")
            if cusum_p < 0.05:
                issues.append("parameter instability")
            rows.append({"dependent": Y_LABELS[y], "sample": REGIME_LABELS.get(reg, "Full sample"),
                         "n": int(res.nobs), "durbin_watson": durbin_watson(e),
                         "breusch_godfrey_5_p": bg, "ljung_box_10_p": lb, "breusch_pagan_p": bp,
                         "white_p": wh, "arch_lm5_p": arch, "jarque_bera_p": jb, "reset_p": reset,
                         "cusum_p": cusum_p, "vif_ttf": vif_g, "vif_brent": vif_o,
                         "corr_ttf_brent": data[GAS].corr(data[OIL]),
                         "issues": ", ".join(issues) or "none",
                         "remedy": "Newey-West HAC SEs (robust to heteroskedasticity + autocorrelation); "
                                   "regime split for instability" if issues else "OLS SEs valid"})
    return save("06_residual_diagnostics", pd.DataFrame(rows))


# =========================================================================== 4. structural breaks
ANDREWS_CV_P1_15 = {"10%": 7.12, "5%": 8.68, "1%": 12.16}  # Andrews (1993) Table 1, p=1, pi0=0.15


def _gas_shift_wald(y: pd.Series, Xm: pd.DataFrame, post: np.ndarray) -> tuple[float, float, float]:
    """HAC Wald on H0: total TTF effect (t [+ t-1]) unchanged after `post` begins (one restriction)."""
    X = Xm.copy()
    gcols = [c for c in Xm.columns if c.startswith(GAS)]
    for c in gcols:
        X[c + "_post"] = Xm[c].values * post
    X["post"] = post.astype(float)
    r = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": nw_lags(len(y))})
    w = np.array([1.0 if p in [c + "_post" for c in gcols] else 0.0 for p in r.params.index])
    t = r.t_test(w)
    return float(np.squeeze(t.effect)), float(np.squeeze(t.tvalue)) ** 2, float(np.squeeze(t.pvalue))


def structural_breaks(d: pd.DataFrame) -> pd.DataFrame:
    """(a) Chow F at the known war date (all coefficients, classical);
       (b) HAC Wald for a shift in the total TTF effect at the war date;
       (c) Quandt-Andrews sup-Wald for an unknown break date in the total TTF effect (15% trimming)."""
    from scipy.stats import f as fdist
    rows = []
    for y in ["d_bund_2y", "d_bund_10y", "d_slope_2s5s", "d_slope_2s10s", "d_slope_2s30s", "d_ils_eur_1y1y", "d_ois_estr_1y1y",
              "d_ois_estr_2y"]:
        Xm_all = market_X(d, y)
        data = pd.concat([d[y], Xm_all], axis=1).loc["2023-01-01":].dropna()
        yy, Xm = data[y], data[Xm_all.columns]
        X = sm.add_constant(Xm)
        n, k = X.shape
        post = (data.index >= "2026-03-02")
        ssr_p = sm.OLS(yy, X).fit().ssr
        ssr_1 = sm.OLS(yy[~post], X[~post]).fit().ssr
        ssr_2 = sm.OLS(yy[post], X[post]).fit().ssr
        F = ((ssr_p - ssr_1 - ssr_2) / k) / ((ssr_1 + ssr_2) / (n - 2 * k))
        shift, _, wald_p = _gas_shift_wald(yy, Xm, post)
        lo, hi = int(0.15 * n), int(0.85 * n)
        best = (0.0, None)
        for i in range(lo, hi, 2):
            _, wstat, _ = _gas_shift_wald(yy, Xm, np.arange(n) >= i)
            if wstat > best[0]:
                best = (wstat, data.index[i])
        sig = ("1%" if best[0] > ANDREWS_CV_P1_15["1%"] else "5%" if best[0] > ANDREWS_CV_P1_15["5%"]
               else "10%" if best[0] > ANDREWS_CV_P1_15["10%"] else "not significant")
        rows.append({"dependent": Y_LABELS[y], "sample": f"{data.index[0]:%Y-%m-%d} to {data.index[-1]:%Y-%m-%d}",
                     "n": n, "chow_F_at_2026_03_02": F, "chow_p": 1 - fdist.cdf(F, k, n - 2 * k),
                     "ttf_effect_shift_bp_per_10pct": shift * PER10, "robust_wald_p": wald_p,
                     "sup_wald_stat": best[0], "sup_wald_break_date": best[1].date(),
                     "sup_wald_cv_5pct": ANDREWS_CV_P1_15["5%"], "sup_wald_significance": sig,
                     "searchable_window": f"{data.index[lo]:%Y-%m-%d} to {data.index[hi]:%Y-%m-%d}"})
    return save("07_structural_breaks", pd.DataFrame(rows))


def rolling_betas(d: pd.DataFrame, window: int = 120) -> pd.DataFrame:
    """120-business-day rolling total TTF effect (HAC 95% band), stepped weekly."""
    out = []
    for y in ["d_bund_2y", "d_ils_eur_1y1y", "d_ois_estr_1y1y", "d_slope_2s10s"]:
        Xm = market_X(d, y)
        sub = pd.concat([d[y], Xm], axis=1).loc["2016-01-01":].dropna()
        for end in range(window, len(sub) + 1, 5):
            w = sub.iloc[end - window:end]
            r = sm.OLS(w[y], sm.add_constant(w[Xm.columns])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
            b, se, _ = total_effect(r, GAS)
            out.append({"date": w.index[-1], "dependent": Y_LABELS[y], "bp_per_10pct_ttf": b * PER10,
                        "lo95_bp10": (b - 1.96 * se) * PER10, "hi95_bp10": (b + 1.96 * se) * PER10})
    return save("08_rolling_betas_120d", pd.DataFrame(out))


# =========================================================================== 5. timing
def lead_lag(d: pd.DataFrame) -> pd.DataFrame:
    """Two diagnostics of data timing:
       (i) Bund vs OIS (both rates): which day's OIS move does the Bundesbank yield load on?
       (ii) TTF at t-1, t, t+1 -> target (Dimson)."""
    rows = []
    for y, x in [("d_bund_2y", "d_ois_estr_2y"), ("d_bund_10y", "d_ois_estr_2y"),
                 ("d_ils_eur_1y1y", "d_ois_estr_2y")]:
        sub = d.loc["2019-10-03":]
        X = pd.DataFrame({"x_t-1": sub[x].shift(1), "x_t": sub[x], "x_t+1": sub[x].shift(-1)})
        res, _ = ols(sub[y], X)
        rows.append({"test": "timing vs OIS 2Y (LSEG close)", "dependent": Y_LABELS[y], "regressor": Y_LABELS[x],
                     "sample": "Oct 2019 - Oct 2026", "n": int(res.nobs),
                     "beta_t-1": res.params["x_t-1"], "p_t-1": res.pvalues["x_t-1"],
                     "beta_t": res.params["x_t"], "p_t": res.pvalues["x_t"],
                     "beta_t+1": res.params["x_t+1"], "p_t+1": res.pvalues["x_t+1"], "r2": res.rsquared})
    for y in ["d_bund_2y", "d_bund_10y", "d_ils_eur_1y1y", "d_ois_estr_1y1y", "d_slope_2s10s"]:
        for reg in ["ALL", "R3_iran_war"]:
            sub = d if reg == "ALL" else d[d.regime == reg]
            X = pd.DataFrame({"x_t-1": sub[GAS].shift(1), "x_t": sub[GAS], "x_t+1": sub[GAS].shift(-1),
                              OIL: sub[OIL], FX: sub[FX]})
            res, _ = ols(sub[y], X)
            b = res.params[["x_t-1", "x_t", "x_t+1"]]
            w = np.array([1.0 if p in b.index else 0.0 for p in res.params.index])
            ts = res.t_test(w)
            row = {"test": "Dimson TTF lead/lag", "dependent": Y_LABELS[y], "regressor": "TTF",
                   "sample": REGIME_LABELS.get(reg, "Full sample"), "n": int(res.nobs),
                   "beta_t-1": b["x_t-1"], "p_t-1": res.pvalues["x_t-1"], "beta_t": b["x_t"], "p_t": res.pvalues["x_t"],
                   "beta_t+1": b["x_t+1"], "p_t+1": res.pvalues["x_t+1"], "r2": res.rsquared,
                   "dimson_sum_bp_per_10pct": b.sum() * PER10, "dimson_sum_p": float(np.squeeze(ts.pvalue))}
            for k in range(-3, 4):
                row[f"xcorr_gas(t{k:+d})"] = sub[y].corr(sub[GAS].shift(-k))
            rows.append(row)
    return save("09_lead_lag_timing", pd.DataFrame(rows))


# =========================================================================== 6. mediation
def _block_boot(data: np.ndarray, fn, n_boot: int, block: int, rng) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    point = fn(data)
    n = len(data)
    nb = int(np.ceil(n / block))
    boots = np.empty((n_boot, len(point)))
    for i in range(n_boot):
        starts = rng.integers(0, n - block + 1, nb)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        boots[i] = fn(data[idx])
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
    return point, lo, hi


def _serial3(a: np.ndarray) -> np.ndarray:
    """cols: X, Brent, FX, M1, M2, Y.  M1 = a1 X ; M2 = a2 X + d21 M1 ; Y = c' X + b1 M1 + b2 M2."""
    X, O, F, M1, M2, Y = (a[:, i] for i in range(6))
    c = np.ones(len(a))
    b_m1 = np.linalg.lstsq(np.c_[c, X, O, F], M1, rcond=None)[0]
    b_m2 = np.linalg.lstsq(np.c_[c, X, M1, O, F], M2, rcond=None)[0]
    b_y = np.linalg.lstsq(np.c_[c, X, M1, M2, O, F], Y, rcond=None)[0]
    b_tot = np.linalg.lstsq(np.c_[c, X, O, F], Y, rcond=None)[0]
    a1, a2, d21, cp, b1, b2 = b_m1[1], b_m2[1], b_m2[2], b_y[1], b_y[2], b_y[3]
    i1, i2, i12 = a1 * b1, a2 * b2, a1 * d21 * b2
    return np.array([b_tot[1], cp, i1, i2, i12, i1 + i2 + i12, a1, a2, d21, b1, b2])


def _simple(a: np.ndarray) -> np.ndarray:
    """cols: X, Brent, FX, M, Y.  M = a X ; Y = c' X + b M."""
    X, O, F, M, Y = (a[:, i] for i in range(5))
    c = np.ones(len(a))
    b_m = np.linalg.lstsq(np.c_[c, X, O, F], M, rcond=None)[0]
    b_y = np.linalg.lstsq(np.c_[c, X, M, O, F], Y, rcond=None)[0]
    b_tot = np.linalg.lstsq(np.c_[c, X, O, F], Y, rcond=None)[0]
    return np.array([b_tot[1], b_y[1], b_m[1] * b_y[2], b_m[1], b_y[2]])


def mediation(d: pd.DataFrame, w: pd.DataFrame, n_boot: int = 2000, seed: int = 7) -> pd.DataFrame:
    """Two layers, each at the frequency where its variables are synchronous:
       A. DAILY, LSEG-only link  TTF -> inflation swap -> €STR OIS 1y1y (expected policy path)
       B. WEEKLY full chain      TTF -> ILS -> OIS 1y1y -> Bund 2Y (Bundesbank timing washes out)
       Controls Brent & EURUSD.  95% CIs: moving-block bootstrap (block 10 days / 4 weeks)."""
    rng = np.random.default_rng(seed)
    rows = []

    def emit(freq, sample, n, names, point, lo, hi, n_effects, mediator):
        for k, nm in enumerate(names):
            is_eff = k < n_effects
            rows.append({"frequency": freq, "sample": sample, "mediator": mediator, "n": n, "effect": nm,
                         "estimate": point[k], "ci95_lo": lo[k], "ci95_hi": hi[k],
                         "significant_95": bool(lo[k] > 0 or hi[k] < 0),
                         "bp_per_10pct_ttf": point[k] * PER10 if is_eff else np.nan,
                         "share_of_total": point[k] / point[0] if is_eff and k < n_effects and point[0] != 0
                         else np.nan})

    # A. daily, LSEG-synchronous
    for sample, sub in [(REGIME_LABELS["R3_iran_war"], d[d.regime == "R3_iran_war"]),
                        ("Oct 2019 - Oct 2026", d.loc["2019-10-03":]),
                        ("Apr 2022 - Oct 2026", d.loc["2022-04-11":])]:
        for m in ["d_ils_eur_1y1y", "d_ils_eur_1y"]:
            data = sub[[GAS, OIL, FX, m, "d_ois_estr_1y1y"]].dropna().values
            if len(data) < 60:
                continue
            p, lo, hi = _block_boot(data, _simple, n_boot, 10, rng)
            names = ["Total: TTF -> OIS 1y1y", "Direct: TTF -> OIS 1y1y (not via ILS)",
                     f"Indirect: TTF -> {Y_LABELS[m]} -> OIS 1y1y",
                     f"path a: TTF -> {Y_LABELS[m]} (bp per 1%)", f"path b: {Y_LABELS[m]} -> OIS 1y1y (bp per bp)"]
            emit("daily", sample, len(data), names, p, lo, hi, 3, Y_LABELS[m])

    # B. weekly, full chain to Bund 2Y. Bund targets: market returns lagged one business day
    wk = w.copy()
    for sample, sub in [("Oct 2019 - Oct 2026 (weekly)", wk.loc["2019-10-04":]),
                        ("Apr 2022 - Oct 2026 (weekly)", wk.loc["2022-04-15":]),
                        (REGIME_LABELS["R3_iran_war"] + " (weekly)", wk[wk.regime == "R3_iran_war"])]:
        data = sub[[GAS, OIL, FX, "d_ils_eur_1y1y", "d_ois_estr_1y1y", "d_bund_2y"]].dropna().values
        p, lo, hi = _block_boot(data, _serial3, n_boot, 4, rng)
        names = ["Total: TTF -> Bund 2Y", "Direct: TTF -> Bund 2Y (not via ILS/OIS)",
                 "Indirect: TTF -> ILS 1y1y -> Bund 2Y", "Indirect: TTF -> OIS 1y1y -> Bund 2Y",
                 "Indirect: TTF -> ILS 1y1y -> OIS 1y1y -> Bund 2Y", "Total indirect",
                 "a1: TTF -> ILS 1y1y (bp per 1%)", "a2: TTF -> OIS 1y1y direct (bp per 1%)",
                 "d21: ILS 1y1y -> OIS 1y1y (bp per bp)", "b1: ILS 1y1y -> Bund 2Y (bp per bp)",
                 "b2: OIS 1y1y -> Bund 2Y (bp per bp)"]
        emit("weekly", sample, len(data), names, p, lo, hi, 6, "ILS 1y1y + OIS 1y1y")
    return save("10_mediation", pd.DataFrame(rows))


# =========================================================================== 7. VAR / Granger
def _run_var(data: pd.DataFrame, label: str, freq: str, maxlags: int, orderings: dict[str, list[str]]):
    model = VAR(data.reset_index(drop=True))
    sel = model.select_order(maxlags=maxlags)
    p = max(1, int(sel.selected_orders["bic"]))
    res = model.fit(p)
    names = list(data.columns)
    wn = res.test_whiteness(nlags=max(p + 5, 10))
    diag = {"frequency": freq, "sample": label, "variables": ", ".join(names), "n": res.nobs,
            "lag_order_bic": p, "lag_aic": sel.selected_orders["aic"], "lag_hqic": sel.selected_orders["hqic"],
            "stable": bool(res.is_stable()), "max_root_modulus": float(np.max(np.abs(1 / res.roots))),
            "portmanteau_p": wn.pvalue, "normality_p": res.test_normality().pvalue}
    gr = []
    for causing in names:
        for caused in names:
            if causing == caused:
                continue
            t = res.test_causality(caused, [causing], kind="f")
            gr.append({"frequency": freq, "sample": label, "lags": p, "cause": causing, "effect": caused,
                       "granger_F": t.test_statistic, "granger_p": t.pvalue,
                       "verdict": "predicts" if t.pvalue < 0.05 else "no predictive content"})
    fevd, irf_rows = [], []
    for oname, order in orderings.items():
        r2 = VAR(data[order].reset_index(drop=True)).fit(p)
        fe, irf = r2.fevd(10), r2.irf(10)
        i_ttf = order.index("TTF")
        for resp in [v for v in order if v not in ("Brent", "TTF")]:
            j = order.index(resp)
            for h in [1, 5, 10]:
                fevd.append({"frequency": freq, "sample": label, "ordering": oname, "variable": resp,
                             "horizon": h, **{f"share_{s}": fe.decomp[j, h - 1, order.index(s)] for s in order}})
            cum = np.cumsum(irf.orth_irfs[:, j, i_ttf])
            for h in range(11):
                irf_rows.append({"frequency": freq, "sample": label, "ordering": oname, "response": resp,
                                 "horizon": h, "orth_irf": irf.orth_irfs[h, j, i_ttf], "cumulative_irf": cum[h]})
    return diag, gr, fevd, irf_rows


def var_analysis(d: pd.DataFrame, w: pd.DataFrame):
    """Daily VAR on LSEG-synchronous closes only; weekly VAR adds Bund 2Y and 2s10s.
       Cholesky FEVD under two orderings (Brent first / TTF first) bounds TTF's contribution."""
    D, G, F, I = [], [], [], []
    daily_vars = {OIL: "Brent", GAS: "TTF", "d_ils_eur_1y1y": "ILS 1y1y", "d_ois_estr_1y1y": "OIS 1y1y",
                  "d_ois_estr_2y": "OIS 2Y"}
    ord_d = {"Brent first": ["Brent", "TTF", "ILS 1y1y", "OIS 1y1y", "OIS 2Y"],
             "TTF first": ["TTF", "Brent", "ILS 1y1y", "OIS 1y1y", "OIS 2Y"]}
    for label, sub, ml in [("Oct 2019 - Oct 2026", d.loc["2019-10-03":], 10),
                           (REGIME_LABELS["R3_iran_war"], d[d.regime == "R3_iran_war"], 4)]:
        data = sub[list(daily_vars)].dropna().rename(columns=daily_vars)
        out = _run_var(data, label, "daily", ml, ord_d)
        D.append(out[0]); G += out[1]; F += out[2]; I += out[3]
    weekly_vars = {OIL: "Brent", GAS: "TTF", "d_ils_eur_1y1y": "ILS 1y1y", "d_ois_estr_1y1y": "OIS 1y1y",
                   "d_bund_2y": "Bund 2Y", "d_slope_2s10s": "Slope 2s10s"}
    ord_w = {"Brent first": ["Brent", "TTF", "ILS 1y1y", "OIS 1y1y", "Bund 2Y", "Slope 2s10s"],
             "TTF first": ["TTF", "Brent", "ILS 1y1y", "OIS 1y1y", "Bund 2Y", "Slope 2s10s"]}
    data = w.loc["2019-10-04":, list(weekly_vars)].dropna().rename(columns=weekly_vars)
    out = _run_var(data, "Oct 2019 - Oct 2026 (weekly)", "weekly", 6, ord_w)
    D.append(out[0]); G += out[1]; F += out[2]; I += out[3]
    save("11a_var_diagnostics", pd.DataFrame(D))
    save("11b_granger_causality", pd.DataFrame(G))
    save("11c_var_fevd", pd.DataFrame(F))
    save("11d_var_irf_ttf_shock", pd.DataFrame(I))


# =========================================================================== 8. predictivity
def local_projections(lv: pd.DataFrame, d: pd.DataFrame) -> pd.DataFrame:
    """Jorda local projections.
       cumulative : y_{t+h} - y_{t-1} = b_h gas_t + controls      (impact and its persistence)
       predictive : y_{t+h} - y_{t+s} = g_h gas_t + controls, h > s  (does gas at t forecast LATER moves?)
         s = 0 for LSEG targets; s = 1 for Bundesbank targets, whose day-(t+1) change still contains part
         of day t's market move (snapshot timing), which would otherwise create spurious predictability.
       Controls: Brent_t, EURUSD_t, gas_{t-1,t-2}, dy_{t-1,t-2}.  HAC lags = h+1."""
    rows = []
    level = {"d_ois_estr_2y": lv.ois_estr_2y * 100, "d_ois_estr_1y1y": lv.ois_estr_1y1y * 100,
             "d_ils_eur_1y1y": lv.ils_eur_1y1y * 100, "d_bund_2y": lv.bund_2y * 100,
             "d_bund_10y": lv.bund_10y * 100, "d_slope_2s10s": lv.slope_2s10s}
    for y, lvl in level.items():
        s = 1 if is_bbk(y) else 0
        X = pd.DataFrame({"gas": d[GAS], OIL: d[OIL], FX: d[FX], "gas_l1": d[GAS].shift(1),
                          "gas_l2": d[GAS].shift(2), "dy_l1": d[y].shift(1), "dy_l2": d[y].shift(2)})
        for label, a, b in [("Full sample", "2014-10-13", "2026-12-31"),
                            (REGIME_LABELS["R3_iran_war"], "2026-03-02", "2026-12-31")]:
            sl = slice(a, b)
            for h in range(0, 21):
                cum = lvl.shift(-h) - lvl.shift(1)
                rc, _ = ols(cum.loc[sl], X.loc[sl], hac_lags=h + 1)
                row = {"dependent": Y_LABELS[y], "sample": label, "horizon_days": h, "n": int(rc.nobs),
                       "cum_bp_per_10pct": rc.params["gas"] * PER10,
                       "cum_lo95_bp10": (rc.params["gas"] - 1.96 * rc.bse["gas"]) * PER10,
                       "cum_hi95_bp10": (rc.params["gas"] + 1.96 * rc.bse["gas"]) * PER10,
                       "cum_p": rc.pvalues["gas"], "pred_window": f"t+{s} to t+{h}" if h > s else ""}
                if h > s:
                    fwd = lvl.shift(-h) - lvl.shift(-s)
                    rf, _ = ols(fwd.loc[sl], X.loc[sl], hac_lags=h + 1)
                    row.update({"pred_bp_per_10pct": rf.params["gas"] * PER10, "pred_p": rf.pvalues["gas"],
                                "pred_r2": rf.rsquared})
                rows.append(row)
    return save("12_local_projections", pd.DataFrame(rows))


def oos_forecast(w: pd.DataFrame) -> pd.DataFrame:
    """Weekly one-step-ahead forecasts of next week's change. Expanding window (estimation from late 2014,
       evaluation from Jan 2020). Bundesbank targets use gas measured to Thursday (`_lag1d`) so the
       predictor ends before the target window starts. Benchmarks: no change / historical mean.
       Clark-West (2007) MSPE-adjusted test for nested models (one-sided, H0 equal accuracy)."""
    from scipy.stats import norm
    rows = []
    wk = w[w.index >= "2014-10-17"]
    for y in ["d_ois_estr_2y", "d_ois_estr_1y1y", "d_ils_eur_1y1y", "d_bund_2y", "d_bund_10y", "d_slope_2s10s"]:
        sfx = "_lag1d" if is_bbk(y) else ""
        df = pd.DataFrame({"y_next": wk[y].shift(-1), "gas": wk[GAS + sfx], "oil": wk[OIL + sfx],
                           "dy": wk[y]}).dropna()
        start = df.index.searchsorted(pd.Timestamp("2020-01-03"))
        if start < 52:
            start = 52
        preds = {"zero": [], "mean": [], "A": [], "B": []}
        actual, dates = [], []
        for t in range(start, len(df)):
            tr, te = df.iloc[:t], df.iloc[t]
            preds["zero"].append(0.0)
            preds["mean"].append(tr.y_next.mean())
            for k, cols in [("A", ["gas"]), ("B", ["gas", "oil", "dy"])]:
                beta = np.linalg.lstsq(np.c_[np.ones(len(tr)), tr[cols].values], tr.y_next.values, rcond=None)[0]
                preds[k].append(beta[0] + te[cols].values @ beta[1:])
            actual.append(te.y_next)
            dates.append(df.index[t])
        actual, dates = np.array(actual), pd.DatetimeIndex(dates)
        for window, mask in [(f"{dates[0]:%b %Y} - Oct 2026", np.ones(len(dates), bool)),
                             ("Iran war only", dates >= "2026-03-06")]:
            a = actual[mask]
            for bench in ["zero", "mean"]:
                pb = np.array(preds[bench])[mask]
                for mdl in ["A", "B"]:
                    pm = np.array(preds[mdl])[mask]
                    mse_b, mse_m = np.mean((a - pb) ** 2), np.mean((a - pm) ** 2)
                    f = (a - pb) ** 2 - ((a - pm) ** 2 - (pb - pm) ** 2)
                    cw_t = f.mean() / (f.std(ddof=1) / np.sqrt(len(f)))
                    p = 1 - norm.cdf(cw_t)
                    rows.append({"target": Y_LABELS[y] + " (next week)", "evaluation": window,
                                 "n_forecasts": len(a), "predictor_timing": "Fri-Thu (lagged 1 day)" if sfx else "Fri-Fri",
                                 "model": {"A": "gas only", "B": "gas + Brent + own lag"}[mdl],
                                 "benchmark": {"zero": "no change", "mean": "historical mean"}[bench],
                                 "rmse_model": np.sqrt(mse_m), "rmse_benchmark": np.sqrt(mse_b),
                                 "oos_r2": 1 - mse_m / mse_b, "clark_west_t": cw_t, "clark_west_p": p,
                                 "beats_benchmark_5pct": bool(p < 0.05 and mse_m < mse_b)})
    return save("13_oos_forecast", pd.DataFrame(rows))


def hicp_passthrough(m: pd.DataFrame) -> pd.DataFrame:
    """First link at its natural frequency: does gas move realised inflation, and with what lag?
       (A) hicp_mom_t = sum_{k=0..12} g_k dlnTTF_{t-k} + sum o_k dlnBrent_{t-k} + month dummies (NSA).
       (B) hicp_yoy_t on 12m log changes of TTF and Brent lagged L = 0..12 months (lag scan)."""
    df = pd.DataFrame({"pi": m.hicp_ea_mom, "gas": np.log(m.gas_ttf_m1_eurmwh_mavg).diff() * 100,
                       "oil": np.log(m.oil_brent_m1_eurbbl_mavg).diff() * 100}).loc["2015-01-01":]
    L = 12
    X = pd.DataFrame(index=df.index)
    for k in range(L + 1):
        X[f"gas_l{k}"] = df.gas.shift(k)
        X[f"oil_l{k}"] = df.oil.shift(k)
    months = pd.get_dummies(df.index.month, prefix="m", drop_first=True).astype(float)
    months.index = df.index
    res, _ = ols(df.pi, X.join(months), hac_lags=6)
    gas_cols, oil_cols = [f"gas_l{k}" for k in range(L + 1)], [f"oil_l{k}" for k in range(L + 1)]
    rows, cg, co = [], 0.0, 0.0
    for k in range(L + 1):
        cg += res.params[f"gas_l{k}"]
        co += res.params[f"oil_l{k}"]
        rows.append({"model": "A: m/m distributed lag", "lag_months": k,
                     "gas_coef": res.params[f"gas_l{k}"], "gas_p": res.pvalues[f"gas_l{k}"],
                     "cum_gas_pp_per_10pct": cg * PER10,
                     "oil_coef": res.params[f"oil_l{k}"], "oil_p": res.pvalues[f"oil_l{k}"],
                     "cum_oil_pp_per_10pct": co * PER10})
    tests = {"joint_gas_all_lags_p": res.wald_test(", ".join(f"{c} = 0" for c in gas_cols), scalar=True).pvalue,
             "granger_gas_lags1to12_p": res.wald_test(", ".join(f"{c} = 0" for c in gas_cols[1:]), scalar=True).pvalue,
             "gas_lags0to6_p": res.wald_test(", ".join(f"{c} = 0" for c in gas_cols[:7]), scalar=True).pvalue,
             "joint_oil_p": res.wald_test(", ".join(f"{c} = 0" for c in oil_cols), scalar=True).pvalue}
    rows.append({"model": "A: joint tests", "lag_months": np.nan, **{k: float(v) for k, v in tests.items()},
                 "r2": res.rsquared, "n_months": int(res.nobs)})
    y2 = pd.DataFrame({"yoy": m.hicp_ea_yoy, "g12": np.log(m.gas_ttf_m1_eurmwh_mavg).diff(12) * 100,
                       "o12": np.log(m.oil_brent_m1_eurbbl_mavg).diff(12) * 100}).loc["2015-12-01":]
    for lag in range(0, 13):
        r, _ = ols(y2.yoy, pd.DataFrame({"gas": y2.g12.shift(lag), "oil": y2.o12.shift(lag)}), hac_lags=12)
        rows.append({"model": "B: y/y on 12m changes, lag scan", "lag_months": lag,
                     "gas_coef": r.params["gas"], "gas_p": r.pvalues["gas"],
                     "cum_gas_pp_per_10pct": r.params["gas"] * PER10,
                     "oil_coef": r.params["oil"], "oil_p": r.pvalues["oil"],
                     "cum_oil_pp_per_10pct": r.params["oil"] * PER10, "r2": r.rsquared, "n_months": int(r.nobs)})
    return save("14_hicp_passthrough", pd.DataFrame(rows))


# =========================================================================== 9. events & curve
EVENT_VARS = {"gas_ttf_m1_eurmwh": "TTF (EUR/MWh)", "oil_brent_m1_usdbbl": "Brent (USD/bbl)",
              "ils_eur_1y": "ILS 1Y (%)", "ils_eur_1y1y": "ILS 1y1y (%)", "ois_estr_1y1y": "OIS 1y1y (%)",
              "ois_estr_2y": "OIS 2Y (%)", "bund_2y": "Bund 2Y (%)", "bund_5y": "Bund 5Y (%)",
              "bund_10y": "Bund 10Y (%)", "bund_30y": "Bund 30Y (%)", "slope_2s10s": "2s10s (bp)",
              "swapsprd_de5y_bp": "5Y swap spread (bp)"}


def event_study(lv: pd.DataFrame, d: pd.DataFrame) -> pd.DataFrame:
    """Levels at t-1, t and t+1 for each event; changes are computed by formulas in the workbook.
    Bund yields are snapshotted before the market close, so their 2-day change (t-1 -> t+1) is the
    comparable window."""
    rows = []
    events = dict(EVENTS)
    war = d[d.regime == "R3_iran_war"][GAS].dropna()
    for dt in war.abs().sort_values(ascending=False).index[:6]:
        events.setdefault(f"{dt:%Y-%m-%d}", f"Large TTF day ({war[dt]:+.1f}%)")
    for ds, desc in sorted(events.items()):
        t = lv.index.searchsorted(pd.Timestamp(ds))
        if t <= 0 or t + 1 >= len(lv):
            continue
        for v, nm in EVENT_VARS.items():
            rows.append({"event_date": lv.index[t].date(), "event": desc, "variable": nm,
                         "level_t-1": lv[v].iloc[t - 1], "level_t": lv[v].iloc[t], "level_t+1": lv[v].iloc[t + 1]})
    return save("15_event_study", pd.DataFrame(rows))


def curve_pca(d: pd.DataFrame) -> pd.DataFrame:
    tenors = ["d_bund_2y", "d_bund_5y", "d_bund_10y", "d_bund_30y"]
    X = d[tenors].dropna()
    Xc = X - X.mean()
    _, S, Vt = np.linalg.svd(Xc.values, full_matrices=False)
    load = pd.DataFrame(Vt[:3].T, index=tenors, columns=["PC1", "PC2", "PC3"])
    # sign conventions: PC1 = level (+ on 10Y), PC2 = steepener (+ on 30Y), PC3 = belly (+ on 5Y)
    for pc, ref in [("PC1", "d_bund_10y"), ("PC2", "d_bund_30y"), ("PC3", "d_bund_5y")]:
        if load.loc[ref, pc] < 0:
            load[pc] *= -1
    scores = pd.DataFrame(Xc.values @ load.values, index=X.index, columns=load.columns)
    var_share = S[:3] ** 2 / np.sum(S ** 2)
    rows = [{"block": "loadings", "item": t.replace("d_", ""), "PC1_level": load.loc[t, "PC1"],
             "PC2_slope": load.loc[t, "PC2"], "PC3_curvature": load.loc[t, "PC3"]} for t in tenors]
    rows.append({"block": "variance share", "item": "share of daily curve variance",
                 "PC1_level": var_share[0], "PC2_slope": var_share[1], "PC3_curvature": var_share[2]})
    sc = scores.join(market_X(d, "d_bund_2y"))
    sc["regime"] = d["regime"]
    xcols = list(market_X(d, "d_bund_2y").columns)
    for reg in REGIME_ORDER:
        sub = sc[sc.regime == reg]
        out = {"block": "TTF total effect, bp per +10%", "item": REGIME_LABELS[reg]}
        for pc, nm in [("PC1", "PC1_level"), ("PC2", "PC2_slope"), ("PC3", "PC3_curvature")]:
            r, _ = ols(sub[pc], sub[xcols])
            b, _, p = total_effect(r, GAS)
            out[nm], out[nm + "_p"] = b * PER10, p
        rows.append(out)
    return save("16_curve_pca", pd.DataFrame(rows))


SLOPES = {"2s5s": ("bund_2y", "bund_5y"), "2s10s": ("bund_2y", "bund_10y"), "5s10s": ("bund_5y", "bund_10y"),
          "10s30s": ("bund_10y", "bund_30y"), "2s30s": ("bund_2y", "bund_30y"), "5s30s": ("bund_5y", "bund_30y")}


def curve_slopes(lv: pd.DataFrame) -> pd.DataFrame:
    """One row per slope: gas sensitivity by regime (daily), war weekly, Brent in the war, war-vs-base test,
    and how the slope actually moved during the war. Reads the transmission / interaction tables."""
    td, tw, ri = RESULTS["04_transmission_daily"], RESULTS["04_transmission_weekly"], RESULTS["05_regime_interaction"]
    pick = lambda df, dep, reg, col: float(df[(df.dependent == dep) & (df.regime == reg)][col].iloc[0])
    war, pre = pd.Timestamp("2026-02-27"), pd.Timestamp("2026-10-09")
    rows = []
    for nm in SLOPES:
        dep = f"Slope {nm}"
        lvl = lv[f"slope_{nm}"]
        hist = lvl.loc["2014-10-01":].dropna()
        row = {"slope": nm}
        for reg in REGIME_ORDER:
            row[f"{REGIME_LABELS[reg]}: bp per +10% TTF"] = pick(td, dep, REGIME_LABELS[reg], "bp_per_10pct_ttf")
            row[f"{REGIME_LABELS[reg]}: p"] = pick(td, dep, REGIME_LABELS[reg], "p_ttf")
        row["war weekly: bp per +10% TTF"] = pick(tw, dep, REGIME_LABELS["R3_iran_war"], "bp_per_10pct_ttf")
        row["war weekly: p"] = pick(tw, dep, REGIME_LABELS["R3_iran_war"], "p_ttf")
        row["war daily: Brent bp per +10%"] = pick(td, dep, REGIME_LABELS["R3_iran_war"], "bp_per_10pct_brent")
        row["war daily: Brent p"] = pick(td, dep, REGIME_LABELS["R3_iran_war"], "p_brent")
        row["war daily: R2"] = pick(td, dep, REGIME_LABELS["R3_iran_war"], "r2")
        m = (ri.dependent == dep) & (ri.regime_vs_base == REGIME_LABELS["R3_iran_war"])
        row["war vs base: p"] = float(ri[m].wald_p.iloc[0])
        row["level 27 Feb 2026 (bp)"] = lvl.asof(war)
        row["level 9 Oct 2026 (bp)"] = lvl.asof(pre)
        row["change during war (bp)"] = lvl.asof(pre) - lvl.asof(war)
        for lab, ds in [("war onset 2-day (bp)", "2026-03-02"), ("ceasefire 2-day (bp)", "2026-04-08")]:
            t = lv.index.searchsorted(pd.Timestamp(ds))
            row[lab] = lvl.iloc[t + 1] - lvl.iloc[t - 1]
        row["percentile since 2014 (now)"] = float((hist < hist.iloc[-1]).mean())
        rows.append(row)
    save("17_curve_slopes", pd.DataFrame(rows))
    moves = [{"tenor": t.upper(), "yield 27 Feb 2026 (%)": lv[f"bund_{t}"].asof(war),
              "yield 9 Oct 2026 (%)": lv[f"bund_{t}"].asof(pre),
              "change (bp)": (lv[f"bund_{t}"].asof(pre) - lv[f"bund_{t}"].asof(war)) * 100}
             for t in ["2y", "5y", "7y", "10y", "15y", "20y", "30y"]]
    return save("17b_tenor_moves_war", pd.DataFrame(moves))


DETAIL_Y = ["d_ils_eur_1y", "d_ils_eur_1y1y", "d_ois_estr_1y1y", "d_ois_estr_2y", "d_bund_2y", "d_bund_5y",
            "d_bund_10y", "d_bund_30y", "d_slope_2s5s", "d_slope_2s10s", "d_slope_2s30s", "d_slope_5s30s"]
REG_NAMES = {"const": "Constant", GAS: "TTF (t)", GAS + "_l1": "TTF (t-1)", OIL: "Brent (t)", OIL + "_l1": "Brent (t-1)",
             FX: "EURUSD (t)", FX + "_l1": "EURUSD (t-1)"}


def regression_details(d: pd.DataFrame, w: pd.DataFrame) -> pd.DataFrame:
    """Full OLS output for the transmission regressions: every coefficient with its Newey-West SE, t, p, and the
    fit statistics (R2, adjusted R2, HAC-robust F test of all slopes, residual SE, Durbin-Watson, AIC/BIC).
    Coefficients on TTF and Brent are in bp per 1% move; EURUSD in bp per 1% move."""
    coefs, fits = [], []
    samples = [("daily", reg, d if reg == "ALL" else d[d.regime == reg]) for reg in REGIME_ORDER + ["ALL"]]
    samples += [("weekly", reg, w if reg == "ALL" else w[w.regime == reg]) for reg in ["R1_gas_crisis", "R3_iran_war", "ALL"]]
    for freq, reg, sub in samples:
        for y in DETAIL_Y:
            if sub[y].notna().sum() < (25 if freq == "weekly" else 60):
                continue
            if freq == "daily":
                X = market_X(sub, y)
            else:
                sfx = "_lag1d" if is_bbk(y) else ""
                X = sub[[GAS + sfx, OIL + sfx, FX + sfx]]
                X.columns = [GAS, OIL, FX]
            res, data = ols(sub[y], X)
            lags = nw_lags(len(data))
            label = REGIME_LABELS.get(reg, "Full sample")
            for k in res.params.index:
                coefs.append({"frequency": freq, "regime": label, "dependent": Y_LABELS[y], "regressor": REG_NAMES[k],
                              "coef": res.params[k], "hac_se": res.bse[k], "t": res.tvalues[k], "p": res.pvalues[k]})
            k_slopes = len(res.params) - 1
            ft = res.f_test(np.eye(len(res.params))[1:])
            g, gse, gp = total_effect(res, GAS)
            fits.append({"frequency": freq, "regime": label, "dependent": Y_LABELS[y], "n": int(res.nobs),
                         "sample_start": data.index[0].date(), "sample_end": data.index[-1].date(),
                         "regressors": k_slopes, "hac_lags": lags, "r2": res.rsquared, "adj_r2": res.rsquared_adj,
                         "robust_F": float(np.squeeze(ft.fvalue)), "robust_F_p": float(np.squeeze(ft.pvalue)),
                         "resid_se_bp": float(np.sqrt(res.scale)), "durbin_watson": durbin_watson(res.resid),
                         "aic": res.aic, "bic": res.bic,
                         "ttf_total_bp_per_10pct": g * PER10, "ttf_total_se": gse * PER10, "ttf_total_p": gp})
    save("18_ols_coefficients", pd.DataFrame(coefs))
    return save("18b_ols_fit", pd.DataFrame(fits))


def main() -> None:
    lv, d, w, m = load()
    steps = [("descriptive", lambda: descriptive(d)), ("unit roots", lambda: unit_roots(lv)),
             ("cointegration", lambda: cointegration(lv)),
             ("transmission daily", lambda: transmission(d, "daily")),
             ("transmission weekly", lambda: transmission(w, "weekly")),
             ("regime interaction", lambda: regime_interaction(d)),
             ("diagnostics", lambda: residual_diagnostics(d)), ("breaks", lambda: structural_breaks(d)),
             ("rolling", lambda: rolling_betas(d)), ("timing", lambda: lead_lag(d)),
             ("mediation", lambda: mediation(d, w)), ("VAR", lambda: var_analysis(d, w)),
             ("local projections", lambda: local_projections(lv, d)), ("OOS", lambda: oos_forecast(w)),
             ("HICP", lambda: hicp_passthrough(m)), ("events", lambda: event_study(lv, d)),
             ("PCA", lambda: curve_pca(d)), ("curve slopes", lambda: curve_slopes(lv)),
             ("OLS details", lambda: regression_details(d, w))]
    for name, fn in steps:
        print(f"-> {name}", flush=True)
        fn()


if __name__ == "__main__":
    main()
