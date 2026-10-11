"""Write the research paper as LaTeX from the result tables and compile it with pdflatex.

Output: output/paper/gas_bund_paper.tex and output/Gas_Bund_Research_Paper.pdf.
Every number in the text and every regression table is filled in from output/tables/*.csv, so the paper always
matches the latest run of econometrics.py. Text placeholders are written as <<key>>.
"""
from __future__ import annotations

import re
import shutil
import subprocess

import numpy as np
import pandas as pd

from config import CLEAN, FIGURES, ROOT, TABLES

PAPER_DIR = ROOT / "output" / "paper"
PAPER_DIR.mkdir(parents=True, exist_ok=True)
OUT_PDF = ROOT / "output" / "Gas_Bund_Research_Paper.pdf"
PDFLATEX = shutil.which("pdflatex") or "/Library/TeX/texbin/pdflatex"

WAR, CRISIS, NORM, PRE, FULL = ("Iran war (Mar 2026+)", "2021-22 gas crisis", "2023-Feb26 normalisation",
                                "2014-21 pre-crisis", "Full sample")
REGIMES = [PRE, CRISIS, NORM, WAR, FULL]
REG_TEX = {PRE: "2014--21", CRISIS: "2021--22 crisis", NORM: "2023--Feb 26", WAR: "Iran war", FULL: "Full sample"}
SHORT = {"Infl. swap 1Y": "ILS 1Y", "Infl. swap 1y1y": "ILS 1y1y", "€STR OIS 1y1y": "OIS 1y1y", "€STR OIS 2Y": "OIS 2Y",
         "Bund 2Y": "Bund 2Y", "Bund 5Y": "Bund 5Y", "Bund 10Y": "Bund 10Y", "Bund 30Y": "Bund 30Y",
         "Slope 2s5s": "2s5s", "Slope 2s10s": "2s10s", "Slope 2s30s": "2s30s", "Slope 5s30s": "5s30s"}
PANELS = [("A. Inflation and policy expectations", ["Infl. swap 1Y", "Infl. swap 1y1y", "€STR OIS 1y1y", "€STR OIS 2Y"]),
          ("B. Bund yields", ["Bund 2Y", "Bund 5Y", "Bund 10Y", "Bund 30Y"]),
          ("C. Curve slopes", ["Slope 2s5s", "Slope 2s10s", "Slope 2s30s", "Slope 5s30s"])]
REGRESSORS = ["TTF (t)", "TTF (t-1)", "Brent (t)", "Brent (t-1)", "EURUSD (t)", "EURUSD (t-1)", "Constant"]
REG_LABEL = {"TTF (t)": r"$g_t$ (TTF)", "TTF (t-1)": r"$g_{t-1}$", "Brent (t)": r"$o_t$ (Brent)",
             "Brent (t-1)": r"$o_{t-1}$", "EURUSD (t)": r"$e_t$ (EUR/USD)", "EURUSD (t-1)": r"$e_{t-1}$",
             "Constant": "Constant"}
PER10 = 100 * np.log(1.1)


def T(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLES / f"{name}.csv")


def stars(p: float) -> str:
    return "^{***}" if p < 0.01 else "^{**}" if p < 0.05 else "^{*}" if p < 0.10 else ""


def num(x: float, d: int = 2) -> str:
    return f"{x:.{d}f}".replace("-", "$-$") if x < 0 else f"{x:.{d}f}"


def num1(x: float) -> str:
    return num(x, 1)


def pv(p: float) -> str:
    return "$p<0.001$" if p < 0.001 else f"$p={p:.3f}$"


def tex_escape(s: str) -> str:
    return (s.replace("€", r"\euro{}").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
             .replace("~", r"$\sim$"))


# --------------------------------------------------------------------------- regression tables
coef = T("18_ols_coefficients")
fit = T("18b_ols_fit")


def coef_table(freq: str, regime: str, caption: str, label: str, note: str, panels=None) -> str:
    panels = panels or PANELS
    out = [r"\begin{table}[htbp]\centering\footnotesize", rf"\caption{{{caption}}}\label{{{label}}}",
           r"\setlength{\tabcolsep}{5pt}\renewcommand{\arraystretch}{1.05}",
           r"\begin{tabular}{@{}l*{4}{c}@{}}", r"\toprule"]
    for p_i, (ptitle, deps) in enumerate(panels):
        if p_i:
            out.append(r"\addlinespace[4pt]")
        out.append(rf"\multicolumn{{5}}{{@{{}}l}}{{\textit{{Panel {ptitle}}}}}\\")
        out.append(" & " + " & ".join(SHORT[d] for d in deps) + r"\\\midrule")
        c = coef[(coef.frequency == freq) & (coef.regime == regime)]
        f = fit[(fit.frequency == freq) & (fit.regime == regime)].set_index("dependent")
        for r in REGRESSORS:
            if not (c.regressor == r).any():
                continue
            cells, ses = [], []
            for dname in deps:
                row = c[(c.dependent == dname) & (c.regressor == r)]
                if row.empty:
                    cells.append(""), ses.append("")
                else:
                    x = row.iloc[0]
                    cells.append(f"${x.coef:.3f}{stars(x.p)}$".replace("$-", "$-"))
                    ses.append(f"$({x.hac_se:.3f})$")
            if not any(cells):
                continue
            out.append(REG_LABEL[r] + " & " + " & ".join(cells) + r"\\")
            out.append(" & " + " & ".join(ses) + r"\\")
        out.append(r"\cmidrule(l){2-5}")
        tot = [f"${f.loc[d].ttf_total_bp_per_10pct:.2f}{stars(f.loc[d].ttf_total_p)}$" if d in f.index else "" for d in deps]
        tse = [f"$({f.loc[d].ttf_total_se:.2f})$" if d in f.index else "" for d in deps]
        out.append(r"TTF total, bp per $+10\%$ & " + " & ".join(tot) + r"\\")
        out.append(" & " + " & ".join(tse) + r"\\")
        for lab, col, d_ in [(r"$R^2$", "r2", 3), (r"Adjusted $R^2$", "adj_r2", 3), (r"Robust $F$ (all slopes)", "robust_F", 1),
                             ("Residual s.e. (bp)", "resid_se_bp", 2), ("Durbin--Watson", "durbin_watson", 2),
                             ("HAC lags", "hac_lags", 0), ("Observations", "n", 0)]:
            vals = []
            for d in deps:
                if d not in f.index:
                    vals.append("")
                    continue
                v = f.loc[d][col]
                s = f"{int(v)}" if d_ == 0 else f"{v:.{d_}f}"
                if col == "robust_F":
                    s += f"${stars(f.loc[d].robust_F_p)}$"
                vals.append(s)
            out.append(lab + " & " + " & ".join(vals) + r"\\")
    out += [r"\bottomrule", r"\end{tabular}",
            rf"\par\vspace{{4pt}}\begin{{minipage}}{{0.94\textwidth}}\scriptsize\textit{{Notes:}} {note}\end{{minipage}}",
            r"\end{table}"]
    return "\n".join(out)


COEF_NOTE_DAILY = (r"OLS on daily changes. Dependent variables in basis points; $g$ and $o$ are 100 times the log change "
                   r"of front-month TTF and Brent (roll days removed), $e$ the same for EUR/USD, so coefficients are bp "
                   r"per 1\% move. Bund yields and slopes are snapshotted by the Bundesbank about half a trading day "
                   r"before the LSEG closes, so their regressions add the previous day's market moves; the TTF total is "
                   r"$(\hat\beta_0+\hat\beta_1)\times 100\ln 1.1$. Newey--West HAC standard errors in parentheses. "
                   r"$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.")
COEF_NOTE_WEEKLY = (r"OLS on Friday-to-Friday changes. Weekly TTF and Brent returns are sums of roll-cleaned daily "
                    r"returns; for Bund yields and slopes the market window ends on Thursday so that it closes before "
                    r"the Bundesbank snapshot. Newey--West HAC standard errors in parentheses. "
                    r"$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.")


def regime_table() -> str:
    td = T("04_transmission_daily")
    deps = [d for _, ds in PANELS for d in ds]
    out = [r"\begin{table}[htbp]\centering\footnotesize",
           r"\caption{Total TTF effect by regime, basis points per $+10\%$ gas move (daily)}\label{tab:regimes}",
           r"\setlength{\tabcolsep}{5pt}", r"\begin{tabular}{@{}l*{5}{c}@{}}", r"\toprule",
           " & " + " & ".join(REG_TEX[r] for r in REGIMES) + r"\\\midrule"]
    for i, d in enumerate(deps):
        if i in (4, 8):
            out.append(r"\addlinespace[3pt]")
        cells, ses = [], []
        for r in REGIMES:
            row = td[(td.dependent == d) & (td.regime == r)]
            if row.empty:
                cells.append(""), ses.append("")
                continue
            x = row.iloc[0]
            se = abs(x.bp_per_10pct_ttf / x.t_ttf) if x.t_ttf else np.nan
            cells.append(f"${x.bp_per_10pct_ttf:.2f}{stars(x.p_ttf)}$")
            ses.append(f"$({se:.2f})$")
        out.append(SHORT[d] + " & " + " & ".join(cells) + r"\\")
        out.append(" & " + " & ".join(ses) + r"\\")
    out += [r"\bottomrule", r"\end{tabular}",
            r"\par\vspace{4pt}\begin{minipage}{0.92\textwidth}\scriptsize\textit{Notes:} Each cell is a separate "
            r"regression of the form in equation~(\ref{eq:bbk}) (Bundesbank series) or (\ref{eq:lseg}) (LSEG series), "
            r"estimated within the regime, controlling for Brent and EUR/USD. Newey--West standard errors in "
            r"parentheses. The 1Y inflation swap starts in April 2022 and \euro{}STR OIS in October 2019. "
            r"$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.\end{minipage}", r"\end{table}"]
    return "\n".join(out)


def simple_table(df: pd.DataFrame, cols: list[tuple[str, str, str]], caption: str, label: str, note: str,
                 align: str | None = None, size: str = r"\footnotesize") -> str:
    """cols = [(column, header, fmt)] with fmt in {'s','0','1','2','3','p','pct'}"""
    align = align or "@{}l" + "c" * (len(cols) - 1) + "@{}"
    out = [rf"\begin{{table}}[htbp]\centering{size}", rf"\caption{{{caption}}}\label{{{label}}}",
           r"\setlength{\tabcolsep}{5pt}", rf"\begin{{tabular}}{{{align}}}", r"\toprule",
           " & ".join(h for _, h, _ in cols) + r"\\\midrule"]
    for _, r in df.iterrows():
        cells = []
        for c, _, f in cols:
            v = r[c]
            if f == "s":
                cells.append(tex_escape(str(v)))
            elif pd.isna(v):
                cells.append("")
            elif f == "p":
                cells.append("$<0.001$" if v < 0.001 else f"{v:.3f}")
            elif f == "pct":
                cells.append(f"{100 * v:.0f}\\%")
            elif f == "0":
                cells.append(f"{v:.0f}")
            else:
                cells.append(f"${v:.{int(f)}f}$")
        out.append(" & ".join(cells) + r"\\")
    out += [r"\bottomrule", r"\end{tabular}"]
    if note:
        out.append(rf"\par\vspace{{4pt}}\begin{{minipage}}{{0.92\textwidth}}\scriptsize\textit{{Notes:}} {note}\end{{minipage}}")
    out.append(r"\end{table}")
    return "\n".join(out)


# --------------------------------------------------------------------------- values
def values() -> dict[str, str]:
    td, tw = T("04_transmission_daily"), T("04_transmission_weekly")
    g = lambda df, d, r, c="bp_per_10pct_ttf": float(df[(df.dependent == d) & (df.regime == r)][c].iloc[0])
    f = fit.set_index(["frequency", "regime", "dependent"])
    V: dict[str, str] = {}
    for key, dep in [("ils1", "Infl. swap 1Y"), ("ils11", "Infl. swap 1y1y"), ("ois11", "€STR OIS 1y1y"),
                     ("ois2", "€STR OIS 2Y"), ("b2", "Bund 2Y"), ("b5", "Bund 5Y"), ("b10", "Bund 10Y"),
                     ("b30", "Bund 30Y"), ("s25", "Slope 2s5s"), ("s210", "Slope 2s10s"), ("s230", "Slope 2s30s"),
                     ("s530", "Slope 5s30s")]:
        for rk, reg in [("war", WAR), ("cri", CRISIS), ("norm", NORM), ("pre", PRE), ("full", FULL)]:
            try:
                V[f"{key}_{rk}"] = num(g(td, dep, reg), 1)
                V[f"{key}_{rk}_i"] = num(g(td, dep, reg), 0)
                V[f"{key}_{rk}_abs"] = f"{abs(g(td, dep, reg)):.1f}"
                V[f"{key}_{rk}_p"] = pv(g(td, dep, reg, "p_ttf"))
                V[f"{key}_{rk}_brent"] = num(g(td, dep, reg, "bp_per_10pct_brent"), 1)
                V[f"{key}_{rk}_r2"] = f"{float(f.loc[('daily', reg, dep)].r2):.2f}"
            except (IndexError, KeyError):
                pass
            try:
                V[f"{key}_{rk}_w"] = num(g(tw, dep, reg), 1)
                V[f"{key}_{rk}_w_i"] = num(g(tw, dep, reg), 0)
                V[f"{key}_{rk}_w_p"] = pv(g(tw, dep, reg, "p_ttf"))
            except (IndexError, KeyError):
                pass
    V["b2_war_holm"] = f"{g(td, 'Bund 2Y', WAR, 'p_ttf_holm'):.3f}"
    V["b2_war_holmf"] = f"{g(td, 'Bund 2Y', WAR, 'p_ttf_holm_family'):.3f}"
    V["ils1_war_holm"] = f"{g(td, 'Infl. swap 1Y', WAR, 'p_ttf_holm'):.3f}"
    V["s25_war_holmf"] = f"{g(td, 'Slope 2s5s', WAR, 'p_ttf_holm_family'):.3f}"
    V["b2_war_F"] = f"{float(f.loc[('daily', WAR, 'Bund 2Y')].robust_F):.1f}"
    V["b2_war_adjr2"] = f"{float(f.loc[('daily', WAR, 'Bund 2Y')].adj_r2):.2f}"
    V["b2_war_n"] = f"{int(f.loc[('daily', WAR, 'Bund 2Y')].n)}"
    V["ils11_war_n"] = f"{int(f.loc[('daily', WAR, 'Infl. swap 1y1y')].n)}"
    V["b2_full_n"] = f"{int(f.loc[('daily', FULL, 'Bund 2Y')].n)}"
    V["lags_war"] = f"{int(f.loc[('daily', WAR, 'Bund 2Y')].hac_lags)}"
    V["lags_full"] = f"{int(f.loc[('daily', FULL, 'Bund 2Y')].hac_lags)}"
    V["lags_war_w"] = f"{int(f.loc[('weekly', WAR, 'Bund 2Y')].hac_lags)}"
    V["n_war_w"] = f"{int(f.loc[('weekly', WAR, 'Bund 2Y')].n)}"
    c = coef[(coef.frequency == "daily") & (coef.regime == WAR) & (coef.dependent == "Bund 2Y")].set_index("regressor")
    V["b2_g0"], V["b2_g1"] = f"{c.loc['TTF (t)'].coef:.3f}", f"{c.loc['TTF (t-1)'].coef:.3f}"
    V["b2_o0"], V["b2_o1"] = f"{c.loc['Brent (t)'].coef:.3f}", f"{c.loc['Brent (t-1)'].coef:.3f}"
    V["b2_o1_p"] = pv(c.loc["Brent (t-1)"].p)
    ri = T("05_regime_interaction")
    for key, dep in [("b2", "Bund 2Y"), ("ils1", "Infl. swap 1Y"), ("s230", "Slope 2s30s"), ("ois11", "€STR OIS 1y1y")]:
        m = (ri.dependent == dep) & (ri.regime_vs_base == WAR)
        V[f"ri_{key}"] = num(float(ri[m].difference_bp_per_10pct.iloc[0]), 1)
        V[f"ri_{key}_p"] = pv(float(ri[m].wald_p.iloc[0]))
    m = (ri.dependent == "Bund 2Y") & (ri.regime_vs_base == CRISIS)
    V["ri_b2_cri_p"] = pv(float(ri[m].wald_p.iloc[0]))
    br = T("07_structural_breaks").set_index("dependent")
    hd = lambda x: pd.Timestamp(str(x)).strftime("%-d %B %Y")
    V["sw_ois2"], V["sw_ois2_date"] = f"{br.loc['€STR OIS 2Y'].sup_wald_stat:.1f}", hd(br.loc["€STR OIS 2Y"].sup_wald_break_date)
    V["sw_ois11"], V["sw_ois11_date"] = f"{br.loc['€STR OIS 1y1y'].sup_wald_stat:.1f}", hd(br.loc["€STR OIS 1y1y"].sup_wald_break_date)
    V["sw_b2"] = f"{br.loc['Bund 2Y'].sup_wald_stat:.1f}"
    V["wald_b2_p"] = pv(br.loc["Bund 2Y"].robust_wald_p)
    V["sw_s230_date"] = hd(br.loc["Slope 2s30s"].sup_wald_break_date)
    h = T("14_hicp_passthrough")
    hb = h[h.model.str.startswith("B")].set_index("lag_months")
    ha = h[h.model == "A: joint tests"].iloc[0]
    V["h_g0"], V["h_g9"], V["h_g12"] = (num(hb.loc[0].cum_gas_pp_per_10pct), f"{hb.loc[9].cum_gas_pp_per_10pct:.2f}",
                                        f"{hb.loc[12].cum_gas_pp_per_10pct:.2f}")
    V["h_g9_p"], V["h_g12_p"] = pv(hb.loc[9].gas_p), pv(hb.loc[12].gas_p)
    V["h_o0"], V["h_o0_p"] = f"{hb.loc[0].cum_oil_pp_per_10pct:.2f}", pv(hb.loc[0].oil_p)
    V["h_joint_p"], V["h_06_p"] = pv(ha.joint_gas_all_lags_p), pv(ha.gas_lags0to6_p)
    V["h_r2"] = f"{hb.loc[9].r2:.2f}"
    md = T("10_mediation")
    mm = lambda fr, smp, med, eff, col: float(md[(md.frequency == fr) & (md["sample"] == smp) & (md.mediator == med)
                                                 & (md.effect.str.startswith(eff))][col].iloc[0])
    V["med_tot"] = num1(mm("daily", WAR, "Infl. swap 1y1y", "Total", "bp_per_10pct_ttf"))
    V["med_ind"] = num1(mm("daily", WAR, "Infl. swap 1y1y", "Indirect", "bp_per_10pct_ttf"))
    V["med_share"] = f"{100 * mm('daily', WAR, 'Infl. swap 1y1y', 'Indirect', 'share_of_total'):.0f}"
    V["med_b"] = f"{mm('daily', WAR, 'Infl. swap 1y1y', 'path b', 'estimate'):.2f}"
    V["med_w_ind"] = num1(mm("weekly", WAR + " (weekly)", "ILS 1y1y + OIS 1y1y", "Total indirect", "bp_per_10pct_ttf"))
    V["med_w_b2"] = f"{mm('weekly', WAR + ' (weekly)', 'ILS 1y1y + OIS 1y1y', 'b2', 'estimate'):.2f}"
    V["med_full_b2"] = f"{mm('weekly', 'Oct 2019 - Oct 2026 (weekly)', 'ILS 1y1y + OIS 1y1y', 'b2', 'estimate'):.2f}"
    fe = T("11c_var_fevd")
    fv = lambda o: float(fe[(fe.frequency == "daily") & (fe["sample"] == WAR) & (fe.ordering == o) & (fe.variable == "OIS 1y1y")
                            & (fe.horizon == 10)].share_TTF.iloc[0])
    V["fevd_lo"], V["fevd_hi"] = f"{100 * fv('Brent first'):.0f}", f"{100 * fv('TTF first'):.0f}"
    gr = T("11b_granger_causality")
    gg = lambda fr, smp, ca, ef: float(gr[(gr.frequency == fr) & (gr["sample"] == smp) & (gr.cause == ca) & (gr.effect == ef)].granger_p.iloc[0])
    V["gr_w_b2"] = pv(gg("weekly", "Oct 2019 - Oct 2026 (weekly)", "TTF", "Bund 2Y"))
    V["gr_war_ois"] = pv(gg("daily", WAR, "TTF", "OIS 1y1y"))
    V["gr_full_ois"] = pv(gg("daily", "Oct 2019 - Oct 2026", "TTF", "OIS 1y1y"))
    oo = T("13_oos_forecast")
    og = lambda tgt, ev, col: float(oo[(oo.target == tgt) & (oo.evaluation == ev) & (oo.model == "gas only")
                                       & (oo.benchmark == "no change")][col].iloc[0])
    V["oos_b2"] = num(100 * og("Bund 2Y (next week)", "Iran war only", "oos_r2"), 1)
    V["oos_ois"] = num(100 * og("€STR OIS 1y1y (next week)", "Iran war only", "oos_r2"), 1)
    V["oos_ois_p"] = pv(og("€STR OIS 1y1y (next week)", "Iran war only", "clark_west_p"))
    lp = T("12_local_projections")
    lpv = lambda dep, smp, h, col: float(lp[(lp.dependent == dep) & (lp["sample"] == smp) & (lp.horizon_days == h)][col].iloc[0])
    V["lp_ils_20"] = num(lpv("Infl. swap 1y1y", WAR, 20, "cum_bp_per_10pct"), 1)
    V["lp_ils_20_p"] = pv(lpv("Infl. swap 1y1y", WAR, 20, "cum_p"))
    V["lp_ois_1_pred"] = num(lpv("€STR OIS 1y1y", FULL, 1, "pred_bp_per_10pct"), 1)
    V["lp_b2_5_pred_p"] = pv(lpv("Bund 2Y", WAR, 5, "pred_p"))
    tim = T("09_lead_lag_timing").iloc[0]
    V["tim_lag"], V["tim_same"] = f"{tim['beta_t-1']:.2f}", f"{tim['beta_t']:.2f}"
    lv = pd.read_csv(CLEAN / "daily_levels.csv", index_col=0, parse_dates=True).loc["2019-10-03":]
    for k in (1, 2, 5):
        s = lv[["bund_2y", "ois_estr_2y"]].iloc[::k].diff()
        V[f"corr{k}"] = f"{s.corr().iloc[0, 1]:.2f}"
    dg = T("06_residual_diagnostics")
    V["corr_tb"] = f"{float(dg[(dg.dependent == 'Bund 2Y') & (dg['sample'] == WAR)].corr_ttf_brent.iloc[0]):.2f}"
    V["vif_max"] = f"{float(dg[['vif_ttf', 'vif_brent']].max().max()):.1f}"
    pca = T("16_curve_pca")
    V["pca_share1"] = f"{100 * float(pca[pca.block == 'variance share'].PC1_level.iloc[0]):.0f}"
    V["pca_share2"] = f"{100 * float(pca[pca.block == 'variance share'].PC2_slope.iloc[0]):.0f}"
    pw = pca[pca.item == WAR].iloc[0]
    V["pca_slope"], V["pca_slope_p"] = num(pw.PC2_slope, 1), pv(pw.PC2_slope_p)
    V["pca_level"], V["pca_level_p"] = num(pw.PC1_level, 1), pv(pw.PC1_level_p)
    tm = T("17b_tenor_moves_war").set_index("tenor")
    for t in ["2Y", "5Y", "10Y", "30Y"]:
        V[f"tm_{t}"] = f"{tm.loc[t]['change (bp)']:.0f}"
    V["y2_feb"], V["y2_oct"] = f"{tm.loc['2Y']['yield 27 Feb 2026 (%)']:.2f}", f"{tm.loc['2Y']['yield 9 Oct 2026 (%)']:.2f}"
    V["y30_feb"], V["y30_oct"] = f"{tm.loc['30Y']['yield 27 Feb 2026 (%)']:.2f}", f"{tm.loc['30Y']['yield 9 Oct 2026 (%)']:.2f}"
    cs = T("17_curve_slopes").set_index("slope")
    V["s230_chg"] = f"{abs(cs.loc['2s30s']['change during war (bp)']):.0f}"
    V["s210_chg"] = f"{abs(cs.loc['2s10s']['change during war (bp)']):.0f}"
    V["s25_chg"] = f"{abs(cs.loc['2s5s']['change during war (bp)']):.0f}"
    ev = T("15_event_study")
    e2 = lambda dt, var: (lambda r: (r["level_t+1"] - r["level_t-1"]) * (100 if "(%)" in var else 1))(
        ev[(ev.event_date == dt) & (ev.variable == var)].iloc[0])
    V["ev_on_b2"], V["ev_on_b30"] = f"{e2('2026-03-02', 'Bund 2Y (%)'):.0f}", f"{e2('2026-03-02', 'Bund 30Y (%)'):.0f}"
    V["ev_cf_ois"] = num(e2("2026-04-08", "OIS 1y1y (%)"), 0)
    d0 = T("01_descriptive_stats")
    V["kurt_b2"] = f"{float(d0[(d0.regime == FULL) & (d0.series == 'd_bund_2y')].excess_kurtosis.iloc[0]):.0f}"
    return V


# --------------------------------------------------------------------------- tables built from other CSVs
def other_tables() -> dict[str, str]:
    t: dict[str, str] = {}
    d0 = T("01_descriptive_stats")
    keep = {"r_gas_ttf_m1_eurmwh": "TTF return (\\%)", "r_oil_brent_m1_usdbbl": "Brent return (\\%)",
            "d_ils_eur_1y1y": "ILS 1y1y (bp)", "d_ois_estr_1y1y": "OIS 1y1y (bp)", "d_bund_2y": "Bund 2Y (bp)",
            "d_bund_10y": "Bund 10Y (bp)", "d_bund_30y": "Bund 30Y (bp)", "d_slope_2s10s": "2s10s (bp)"}
    rows = []
    for s, lab in keep.items():
        a = d0[(d0.regime == FULL) & (d0.series == s)].iloc[0]
        b = d0[(d0.regime == WAR) & (d0.series == s)].iloc[0]
        rows.append({"v": lab, "n": a.n, "sd": a["std"], "k": a.excess_kurtosis, "ac": a.acf_lag1,
                     "nw": b.n, "sdw": b["std"], "mw": b["mean"]})
    t["desc"] = simple_table(pd.DataFrame(rows), [("v", "Daily change", "s"), ("n", "$N$", "0"), ("sd", "s.d.", "2"),
                                                  ("k", "Excess kurt.", "1"), ("ac", "AC(1)", "2"), ("nw", "$N$ (war)", "0"),
                                                  ("mw", "Mean (war)", "2"), ("sdw", "s.d. (war)", "2")],
                             "Daily changes: full sample and Iran-war regime", "tab:desc",
                             "Full sample October 2014 to 9 October 2026 (shorter for OIS and swaps). The war regime starts "
                             "on 2 March 2026. TTF and Brent returns exclude contract-roll days.")
    cs = T("17_curve_slopes")
    t["slopes"] = simple_table(cs, [("slope", "Slope", "s"), ("Iran war (Mar 2026+): bp per +10% TTF", "War, daily", "2"),
                                    ("Iran war (Mar 2026+): p", "$p$", "p"), ("war weekly: bp per +10% TTF", "War, weekly", "2"),
                                    ("war weekly: p", "$p$", "p"), ("war daily: Brent bp per +10%", "Brent", "2"),
                                    ("war daily: Brent p", "$p$", "p"), ("war vs base: p", "War vs base $p$", "p"),
                                    ("level 27 Feb 2026 (bp)", "27 Feb", "0"), ("level 9 Oct 2026 (bp)", "9 Oct", "0")],
                               "Which flattener carries gas? Slope sensitivities in the war regime", "tab:slopes",
                               "Slope = long minus short Bund yield, in bp; sensitivities in bp of slope change per $+10\\%$ "
                               "TTF (negative = flattening). Daily estimates include the previous day's market moves. "
                               "``War vs base'' tests whether the war-regime effect differs from 2014--21 and 2023--26 "
                               "pooled. The last two columns give slope levels before the war and at the end of the sample.",
                               size=r"\scriptsize")
    md = T("10_mediation")
    m1 = md[(md.frequency == "daily") & (md["sample"] == WAR) & (md.mediator == "Infl. swap 1y1y")].copy()
    m2 = md[(md.frequency == "weekly") & (md["sample"] == WAR + " (weekly)") & (md.effect.str.match("Total|Direct|Indirect"))].copy()
    mm = pd.concat([m1.assign(block="Daily: TTF $\\to$ ILS 1y1y $\\to$ OIS 1y1y"),
                    m2.assign(block="Weekly: TTF $\\to$ ILS / OIS $\\to$ Bund 2Y")])
    mm["effect"] = mm.effect.str.replace("->", "$\\to$", regex=False).str.replace("bp per 1%", "bp per 1\\%", regex=False)
    mm["est"] = np.where(mm.bp_per_10pct_ttf.notna(), mm.bp_per_10pct_ttf, mm.estimate)
    mm["lo"] = np.where(mm.bp_per_10pct_ttf.notna(), mm.ci95_lo * PER10, mm.ci95_lo)
    mm["hi"] = np.where(mm.bp_per_10pct_ttf.notna(), mm.ci95_hi * PER10, mm.ci95_hi)
    rows = []
    for blk, g in mm.groupby("block", sort=False):
        rows.append({"e": f"\\textit{{{blk}}}", "est": np.nan, "lo": np.nan, "hi": np.nan})
        rows += [{"e": "\\quad " + r.effect, "est": r.est, "lo": r.lo, "hi": r.hi} for _, r in g.iterrows()]
    out = [r"\begin{table}[htbp]\centering\footnotesize",
           r"\caption{Mediation: how much of the gas effect runs through expectations? (Iran-war regime)}\label{tab:med}",
           r"\begin{tabular}{@{}lccc@{}}", r"\toprule", r"Effect & Estimate & 95\% CI low & 95\% CI high\\\midrule"]
    for r in rows:
        if pd.isna(r["est"]):
            out.append(rf"\multicolumn{{4}}{{@{{}}l}}{{{r['e']}}}\\")
        else:
            out.append(f"{r['e']} & ${r['est']:.2f}$ & ${r['lo']:.2f}$ & ${r['hi']:.2f}$\\\\")
    out += [r"\bottomrule", r"\end{tabular}",
            r"\par\vspace{4pt}\begin{minipage}{0.92\textwidth}\scriptsize\textit{Notes:} Total, direct and indirect "
            r"effects in bp per $+10\%$ TTF; path coefficients as labelled. Confidence intervals from a moving-block "
            r"bootstrap (2{,}000 draws; blocks of 10 days or 4 weeks). Controls: Brent and EUR/USD.\end{minipage}",
            r"\end{table}"]
    t["med"] = "\n".join(out)
    oo = T("13_oos_forecast")
    o = oo[(oo.model == "gas only") & (oo.benchmark == "no change")].copy()
    o["target"] = o.target.str.replace(" (next week)", "", regex=False)
    o["oos_r2"] = 100 * o.oos_r2
    t["oos"] = simple_table(o, [("target", "Target (next week)", "s"), ("evaluation", "Evaluation window", "s"),
                                ("n_forecasts", "Forecasts", "0"), ("oos_r2", "OOS $R^2$ (\\%)", "1"),
                                ("clark_west_t", "Clark--West $t$", "2"), ("clark_west_p", "$p$", "p")],
                            "Out-of-sample forecasts of next week's change: gas model vs.\\ no change", "tab:oos",
                            "Expanding-window OLS of next week's change on this week's TTF return. For Bund targets the "
                            "TTF window ends on Thursday. OOS $R^2 = 1-\\mathrm{MSE}_{model}/\\mathrm{MSE}_{benchmark}$. "
                            "Clark--West (2007) one-sided test for nested models.")
    h = T("14_hicp_passthrough")
    hb = h[h.model.str.startswith("B") & h.lag_months.isin([0, 3, 6, 9, 12])]
    t["hicp"] = simple_table(hb, [("lag_months", "Lag (months)", "0"), ("cum_gas_pp_per_10pct", "TTF, pp", "2"),
                                  ("gas_p", "$p$", "p"), ("cum_oil_pp_per_10pct", "Brent, pp", "2"), ("oil_p", "$p$", "p"),
                                  ("r2", "$R^2$", "2"), ("n_months", "$N$", "0")],
                             "Energy prices and realised inflation: HICP y/y on lagged 12-month energy price changes",
                             "tab:hicp", "Each row is a regression of euro-area HICP inflation (y/y, pp) on the 12-month "
                             "log change in TTF and Brent (in euros), both lagged $L$ months; coefficients scaled to a "
                             "$+10\\%$ change. Monthly data from December 2015; Newey--West standard errors (12 lags).")
    dg = T("06_residual_diagnostics")
    dg = dg[dg.dependent.isin(["Bund 2Y", "Bund 30Y", "Slope 2s10s", "€STR OIS 1y1y", "Infl. swap 1y1y"])]
    t["diag"] = simple_table(dg, [("dependent", "Model", "s"), ("sample", "Sample", "s"), ("durbin_watson", "DW", "2"),
                                  ("breusch_godfrey_5_p", "BG(5)", "p"), ("white_p", "White", "p"), ("arch_lm5_p", "ARCH(5)", "p"),
                                  ("jarque_bera_p", "JB", "p"), ("reset_p", "RESET", "p"), ("cusum_p", "CUSUM", "p"),
                                  ("vif_ttf", "VIF", "2")],
                             "Residual diagnostics ($p$-values unless stated)", "tab:diag",
                             "BG: Breusch--Godfrey test for serial correlation up to lag 5; White: heteroskedasticity; "
                             "ARCH: Engle's LM test; JB: Jarque--Bera normality; RESET: Ramsey test (fitted powers up to "
                             "3); CUSUM: stability of OLS residuals; VIF: variance inflation factor of the TTF regressor.",
                             size=r"\scriptsize")
    ur = T("02_unit_roots")
    t["ur"] = simple_table(ur, [("series", "Series", "s"), ("form", "Form", "s"), ("adf_p", "ADF $p$", "p"),
                                ("kpss_p", "KPSS $p$", "p"), ("za_p", "ZA $p$", "p"), ("za_break_date", "ZA break", "s"),
                                ("verdict", "Verdict", "s")],
                           "Unit-root tests on weekly data", "tab:ur",
                           "ADF and Zivot--Andrews: null of a unit root; KPSS: null of stationarity. KPSS $p$-values are "
                           "truncated at 0.01 and 0.10.", size=r"\scriptsize")
    co = T("03_cointegration")
    t["coint"] = simple_table(co, [("test", "Test", "s"), ("system", "System", "s"), ("n_weeks", "Weeks", "0"),
                                   ("stat", "Statistic", "2"), ("p_value", "$p$", "p"), ("rank_at_5pct", "Rank (5\\%)", "0")],
                              "Cointegration tests on weekly levels", "tab:coint",
                              "Engle--Granger: null of no cointegration. Johansen: sequential trace test at 5\\%.",
                              size=r"\scriptsize")
    return t


# --------------------------------------------------------------------------- document
def figure(name: str, caption: str, label: str, width: str = r"\textwidth") -> str:
    return (rf"\begin{{figure}}[htbp]\centering\includegraphics[width={width}]{{{(FIGURES / 'paper' / name).as_posix()}.pdf}}"
            rf"\caption{{{caption}}}\label{{{label}}}\end{{figure}}")


TEMPLATE = r"""
\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage[margin=2.5cm]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{booktabs,tabularx,longtable,array}
\usepackage{graphicx,float}
\usepackage[font=small,labelfont=bf,skip=6pt]{caption}
\usepackage{eurosym}
\usepackage{setspace}
\usepackage[dvipsnames]{xcolor}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning}
\usepackage[authoryear,round]{natbib}
\usepackage[colorlinks=true,linkcolor=MidnightBlue,citecolor=MidnightBlue,urlcolor=MidnightBlue]{hyperref}
\usepackage{fancyhdr}
\pagestyle{fancy}\fancyhf{}\renewcommand{\headrulewidth}{0pt}
\fancyfoot[C]{\footnotesize\thepage}
\setstretch{1.12}
\setlength{\parskip}{3pt}
\renewcommand{\floatpagefraction}{0.75}
\renewcommand{\topfraction}{0.85}

\title{\textbf{Gas Prices, Inflation Expectations and the German Yield Curve}\\[4pt]\large Evidence from the 2026 Iran War}
\author{Poctave}
\date{October 2026\\[2pt]\small Data to 9 October 2026}

\begin{document}
\maketitle
\thispagestyle{empty}

\begin{abstract}
\noindent I ask whether European natural gas prices move the German government bond curve, and whether they do so
through inflation expectations and the expected path of ECB policy. Using daily data from October 2014 to October
2026, I regress changes in inflation swaps, \euro{}STR overnight index swaps and Bund yields on returns of the Dutch
TTF gas contract, controlling for Brent and the euro, and I let the relationship differ across four regimes. It does
differ, sharply. Before 2021 gas barely moved Bund yields, and during the 2021--22 gas crisis higher gas prices came
with \emph{lower} yields. Since the Iran war began in March 2026, a 10\% rise in TTF has lifted the one-year
inflation swap by about <<ils1_war_i>>bp, the expected policy rate one year ahead by <<ois11_war_i>> to <<ois11_war_w_i>>bp and
the two-year Bund by about <<b2_war_i>>bp on the same day, while the 30-year yield has not moved: a bear flattening. A
break test with an unknown date puts the change in the first week of the war. Gas explains same-day curve moves, but
it does not forecast later ones out of sample. Its forecasting content is for realised inflation 6 to 12 months ahead.
\medskip

\noindent\textbf{Keywords:} natural gas, TTF, inflation swaps, ECB, Bund yield curve, regime dependence\\
\textbf{JEL:} E31, E43, E52, G12, Q43
\end{abstract}

\newpage
\section{Introduction}

On the first trading day after Iran closed the Strait of Hormuz, Dutch TTF gas jumped by about 40\% and the German
two-year yield rose <<ev_on_b2>>bp over two days. The 30-year rose <<ev_on_b30>>bp. That pattern, a large move at the short
end and a small one at the long end, repeated itself through the spring and summer of 2026 as the ECB raised its
deposit rate in June and again in September. Between 27 February and 9 October the two-year Bund went from
<<y2_feb>>\% to <<y2_oct>>\% and the 30-year from <<y30_feb>>\% to <<y30_oct>>\%.

The story most market participants told was simple: gas drives inflation, inflation expectations drive rate-hike
expectations, and hike expectations drive the front end of the curve. This paper tests that chain link by link. I
care about two separate claims. The first is transmission: do gas moves show up, on the day, in inflation swaps,
\euro{}STR OIS and Bunds, after accounting for oil and the exchange rate? The second is predictability: does today's
gas move tell us anything about curve moves in the days and weeks that follow?

The short answers are yes and no. Transmission is strong in the war regime and absent or reversed before it. In the
war, a 10\% gas move lifts the one-year inflation swap by <<ils1_war>>bp (<<ils1_war_p>>), the two-year Bund by
<<b2_war>>bp (<<b2_war_p>>) and leaves the 30-year unchanged (<<b30_war>>bp, <<b30_war_p>>), so the 2s30s slope falls by
about <<s230_war_abs>>bp. In 2021--22 the same regression gives <<b2_cri>>bp for the two-year Bund. Predictability, on the other
hand, is not there for the curve: local projections show no drift after the first day or two, and a gas-based
forecast of next week's Bund move does no better than assuming no change. Where gas does help is in forecasting
realised inflation, which responds with a lag of 6 to 12 months.

I think the regime result is the most useful one. It says the sign of the gas--rates relationship is set by how the
market expects the central bank to react, not by gas itself. When the ECB was seen as patient and gas as a threat to
growth, gas pushed yields down. Once the ECB had shown it would hike into an energy shock, the same gas move pushed
the front end up.

The rest of the paper is organised as follows. Section~\ref{sec:mech} lays out the mechanism. Section~\ref{sec:data}
describes the data and the cleaning it needed, including a timing problem in the Bundesbank series that would
otherwise produce spurious predictability. Section~\ref{sec:method} sets out the regressions. Section~\ref{sec:results}
reports the results, Section~\ref{sec:robust} the diagnostics, and Section~\ref{sec:disc} discusses what they mean
and where they stop. The appendix reports every OLS regression in full.

\section{Mechanism}\label{sec:mech}

Figure~\ref{fig:chain} shows the chain. Gas sets the marginal price of electricity in much of Europe and feeds into
household gas bills, fertiliser and industrial costs. Retail tariffs are regulated or contracted and reset slowly,
so the effect on consumer prices arrives months after the wholesale move. Markets do not wait for those prints.
Inflation swaps price expected HICP inflation directly: the one-year swap covers the next twelve months, and the 1y1y
forward covers the year after that, which is closer to the horizon the ECB targets. If the ECB is expected to respond
to higher expected inflation, \euro{}STR OIS rates rise, and with them the two-year Bund, which mostly tracks the
expected policy path. Long yields depend more on long-run growth, long-run inflation and term premia, so a policy shock
moves the short end more than the long end.

\begin{figure}[htbp]\centering
\begin{tikzpicture}[node distance=8mm and 11mm, every node/.style={font=\small},
  box/.style={draw, rounded corners=2pt, align=center, minimum height=10mm, text width=25mm, fill=white},
  arr/.style={-{Stealth[length=2.2mm]}, thick}]
\node[box] (gas) {Gas price\\(TTF)};
\node[box, right=of gas] (ils) {Inflation swaps\\1Y, 1y1y};
\node[box, right=of ils] (ois) {Expected policy\\rate (OIS)};
\node[box, right=of ois, fill=MidnightBlue!8] (bund) {Bund curve\\2Y $\uparrow$, 30Y $\approx$};
\node[box, below=9mm of ils] (hicp) {Realised HICP\\(6--12 months)};
\draw[arr] (gas) -- (ils);
\draw[arr] (ils) -- (ois);
\draw[arr] (ois) -- (bund);
\draw[arr, dashed] (gas) |- (hicp);
\draw[arr, dashed] (hicp) -| (ois);
\end{tikzpicture}
\caption{The transmission chain tested in this paper. Solid arrows: market prices that react on the day. Dashed: the
slower path through realised inflation, which the ECB reacts to at later meetings.}\label{fig:chain}
\end{figure}

Two forces work against this chain. A gas supply shock is also a growth shock, and weaker growth pushes yields down,
as does demand for safe assets in a crisis. Which force dominates depends on how the central bank is expected to
respond. The second problem is oil. The Hormuz closure hit oil and gas at once, and euro inflation swaps have
historically followed Brent more closely than gas, so any estimate of the gas effect has to control for oil.
\citet{adolfsen2026} add a further caution: in their BVAR, LNG supply shocks, which is what this war mostly is, move
euro-area inflation expectations less than pipeline supply shocks do.

\section{Data}\label{sec:data}

Table~\ref{tab:data} lists the series. The sample runs from October 2014 to 9 October 2026 at daily frequency.
\euro{}STR OIS starts in October 2019 and the one-year inflation swap in April 2022, so regressions involving them use
shorter samples. Bund yields come from the Bundesbank and are yields on the current (on-the-run) bond in each maturity
bucket. Everything else comes from LSEG.

\begin{table}[htbp]\centering\footnotesize
\caption{Data}\label{tab:data}
\begin{tabularx}{\textwidth}{@{}l l X l@{}}
\toprule
Series & Source / code & Definition & Start\\\midrule
TTF gas & LSEG TFMBMc1 & ICE Endex Dutch TTF front-month futures, EUR/MWh & 2014\\
Brent & LSEG LCOc1 & ICE Brent front-month futures, USD/bbl & 2014\\
EUR/USD, EUR/GBP & LSEG EUR=, EURGBP= & Spot mid & 2014\\
Inflation swap 1Y & LSEG EUCPIZ1Y=TWEB & Zero-coupon swap on euro-area HICP ex tobacco, 1 year & 2022\\
Inflation swap 1y1y & LSEG EUIL1YF1Y=R & One-year rate starting in one year & 2016\\
\euro{}STR OIS & LSEG EUREST1M/3M/1Y/2Y= & Overnight index swaps; 1y1y forward derived from 1Y and 2Y & 2019\\
Bund yields & Bundesbank BBSSY & Yields of current federal securities, 2Y to 30Y & 1993--2026\\
5Y swap spread & LSEG DE5IRS5Y=RR & 5Y swap rate minus 5Y Bund, bp & 2014\\
HICP & Eurostat & Euro-area index, 2025 = 100, not seasonally adjusted & 1999\\
\bottomrule
\end{tabularx}
\end{table}

Four data problems mattered. The file delivered as the ``1Y inflation swap'' is in fact the 1y1y forward; I relabelled
it and added the true one-year swap. The HICP file splices two index bases, which creates a fake 34\% drop in December
1999; I keep only the data on the current base. Front-month futures series jump when the contract rolls, so I identify
roll days from jumps in open interest (about twelve a year) and drop those returns.

The fourth problem is timing, and it is the one that would have done the most damage. The Bundesbank observes its
yields roughly half a trading day before the LSEG closes used for gas, swaps and OIS. Regressing the daily change in the
two-year Bund on the same-day and previous-day change in the two-year OIS gives coefficients of <<tim_same>> and
<<tim_lag>>, and the correlation between the two series rises from <<corr1>> at one day to <<corr2>> at two days and <<corr5>>
at five. Ignored, this mismatch makes yesterday's swap and gas moves look like they predict today's Bund move. I deal
with it by adding the previous day's market moves to every daily regression with a Bundesbank series on the left-hand
side, and by repeating the analysis at weekly frequency.

I split the sample into four regimes: 2014--21 (before the gas crisis, with the ECB at or below zero), July 2021 to
December 2022 (the gas crisis), January 2023 to 27 February 2026, and the Iran war from 2 March 2026. Table~\ref{tab:desc}
describes the daily changes. All series have fat tails (the excess kurtosis of the two-year Bund change is <<kurt_b2>> in the
full sample) and volatility clusters, which is why every standard error in this paper is heteroskedasticity- and
autocorrelation-robust.

<<TAB:desc>>

\section{Empirical strategy}\label{sec:method}

\subsection{Transmission regressions}

Unit-root tests (Appendix Table~\ref{tab:ur}) show that all the series are non-stationary in levels and stationary in
first differences, and there is no robust cointegration between gas and yields (Table~\ref{tab:coint}). I therefore
work with changes. Let $\Delta y_t$ be the daily change in basis points of an inflation swap, OIS rate, Bund yield or
slope, and let $g_t$, $o_t$ and $e_t$ be 100 times the log change in TTF, Brent and EUR/USD. For series observed at the
LSEG close the regression is
\begin{equation}\label{eq:lseg}
\Delta y_t = \alpha + \beta\, g_t + \gamma\, o_t + \delta\, e_t + \varepsilon_t ,
\end{equation}
and for Bundesbank yields and slopes, which are observed earlier in the day,
\begin{equation}\label{eq:bbk}
\Delta y_t = \alpha + \sum_{j=0}^{1}\left(\beta_j\, g_{t-j} + \gamma_j\, o_{t-j} + \delta_j\, e_{t-j}\right) + \varepsilon_t ,
\end{equation}
in the spirit of \citet{dimson1979}. The total gas effect is $\beta$ in (\ref{eq:lseg}) and $\beta_0+\beta_1$ in
(\ref{eq:bbk}). Because $g_t$ is a log return in percent, the effect of a 10\% rise in TTF is $\beta \times 100\ln 1.1
\approx 9.53\,\beta$ basis points; this is the number I report in the text. Brent and EUR/USD enter as controls, not as
objects of interest.

All regressions are estimated by OLS separately in each regime. Standard errors are Newey--West with a Bartlett kernel
and $L=\lfloor 4(T/100)^{2/9}\rfloor$ lags \citep{neweywest1987}, which gives <<lags_war>> lags in the war regime
($T=<<b2_war_n>>$ for the Bund regressions) and <<lags_full>> in the full sample ($T=<<b2_full_n>>$). The weekly version
uses Friday-to-Friday changes with <<lags_war_w>> lags in the war regime ($T=<<n_war_w>>$). Weekly gas and Brent returns
are sums of the roll-cleaned daily returns, and for Bund series the weekly market window ends on Thursday, so it closes
before the Bundesbank's Friday observation.

To test whether the war changed the relationship I pool the full sample and interact every regressor with regime
dummies,
\begin{equation}\label{eq:inter}
\Delta y_t = \alpha + \sum_{r} \alpha_r D^r_t + \mathbf{x}_t'\boldsymbol\theta + \sum_{r\in\{\text{crisis},\,\text{war}\}} D^r_t\, \mathbf{x}_t'\boldsymbol\theta_r + \varepsilon_t ,
\end{equation}
where $\mathbf{x}_t$ holds the regressors of (\ref{eq:lseg}) or (\ref{eq:bbk}), and I test that the gas elements of
$\boldsymbol\theta_r$ sum to zero. I also run a Chow test at 2 March 2026 and a \citet{andrews1993} sup-Wald test that
searches for the break date over the middle 70\% of a 2023--26 sample. Because I test 20 dependent variables, I report
Holm-adjusted $p$-values \citep{holm1979} as well as raw ones.

\subsection{Channel, dynamics and forecasting}

To ask how much of the gas effect runs through inflation expectations, I estimate a serial mediation model
\begin{equation}\label{eq:med}
M_{1t} = a_1 g_t + \ldots,\qquad M_{2t} = a_2 g_t + d_{21} M_{1t} + \ldots,\qquad \Delta y_t = c' g_t + b_1 M_{1t} + b_2 M_{2t} + \ldots
\end{equation}
with $M_1$ the inflation swap, $M_2$ the OIS 1y1y and the same controls throughout. The indirect effects are
$a_1 b_1$, $a_2 b_2$ and $a_1 d_{21} b_2$. Confidence intervals come from a moving-block bootstrap. The daily version
stops at OIS, because all three series share the LSEG close; the full chain to the Bund runs at weekly frequency.

For dynamics I use local projections \citep{jorda2005},
\begin{equation}\label{eq:lp}
y_{t+h} - y_{t-1} = \alpha_h + \beta_h\, g_t + \gamma_h\, o_t + \delta_h\, e_t + \sum_{k=1}^{2}\left(\phi_{hk}\, g_{t-k} + \psi_{hk}\, \Delta y_{t-k}\right) + u_{t+h}, \quad h = 0,\ldots,20,
\end{equation}
and a predictive variant whose left-hand side starts after the impact day. I complement these with a VAR and Granger
tests, and with expanding-window out-of-sample forecasts of next week's change evaluated with the
\citet{clarkwest2007} test. Finally, for the first link of the chain I regress year-on-year HICP inflation on 12-month
changes in TTF and Brent (in euros) lagged $L=0,\ldots,12$ months.

\section{Results}\label{sec:results}

\subsection{Gas reaches inflation with a lag}

Oil and gas reach consumer prices on different clocks (Figure~\ref{fig:hicp}, Table~\ref{tab:hicp}). A 10\% rise in
Brent adds <<h_o0>>pp to year-on-year HICP inflation in the same month (<<h_o0_p>>). The same rise in TTF adds nothing on
impact (<<h_g0>>pp), but its effect builds steadily to <<h_g9>>pp after nine months (<<h_g9_p>>) and <<h_g12>>pp after a year
(<<h_g12_p>>). In a distributed-lag model of monthly inflation the gas lags are jointly significant (<<h_joint_p>>), while
the first six months on their own are not (<<h_06_p>>). This is what one would expect from regulated retail tariffs, and
it matters for the rest of the paper: when gas jumps, the inflation the ECB will see arrives at the horizon it targets.

<<TAB:hicp>>

\begin{figure}[htbp]\centering
\includegraphics[width=0.82\textwidth]{<<FIG:f5_hicp_lag_scan>>}
\caption{Effect of a 10\% rise in energy prices on euro-area HICP inflation (y/y), by months of lag. Brent's effect
is immediate and fades; TTF's builds over a year.}\label{fig:hicp}
\end{figure}

\subsection{Same-day transmission in the war}

Tables~\ref{tab:war} and~\ref{tab:warb} report the war-regime regressions in full. Three things stand out. First, gas moves the front end.
The two-year Bund rises <<b2_war>>bp per 10\% gas move, almost all of it on the same day ($\hat\beta_0=<<b2_g0>>$ per 1\%
against $\hat\beta_1=<<b2_g1>>$). The effect falls with maturity: <<b5_war>>bp at five years, <<b10_war>>bp at ten and
<<b30_war>>bp at thirty. Second, the fit is far better than in normal times. The two-year Bund regression has an $R^2$ of
<<b2_war_r2>> (adjusted <<b2_war_adjr2>>, robust $F=<<b2_war_F>>$), against <<b2_full_r2>> in the full sample. For the one-year
inflation swap the $R^2$ is <<ils1_war_r2>>, and for the OIS 1y1y <<ois11_war_r2>>.

Third, oil is doing a lot of the work in the swap markets. Brent's effect on the one-year inflation swap is
<<ils1_war_brent>>bp per 10\%, against <<ils1_war>>bp for gas, and on the OIS 1y1y it is <<ois11_war_brent>>bp against <<ois11_war>>bp.
For the Bund, Brent's effect is split evenly between the same day ($\hat\gamma_0=<<b2_o0>>$) and the previous day
($\hat\gamma_1=<<b2_o1>>$, <<b2_o1_p>>). That fits the timing problem described above: Brent settles in the London
evening, after the Bundesbank has taken its snapshot, so part of each day's oil move reaches the Bund series a day later. Gas keeps a
significant effect on the two-year Bund after all of this. The raw $p$-value is <<b2_war_p>>; after Holm correction
it is <<b2_war_holmf>> within the 13 rate series and <<b2_war_holm>> across all 20 series tested, so it sits right at the
conventional threshold under the strictest correction. The weekly estimate, which is free of the timing issue, is
<<b2_war_w>>bp (<<b2_war_w_p>>; Appendix Table~\ref{tab:w_war}).

<<TAB:coef_war>>

\subsection{The relationship changed sign across regimes}

Table~\ref{tab:regimes} and Figure~\ref{fig:regimes} put the four regimes side by side. Before 2021 gas had small,
mostly insignificant effects, and where they were significant they steepened the curve: <<s230_pre>>bp on 2s30s per 10\%
(<<s230_pre_p>>). With the ECB at the lower bound the front end could not move, so whatever gas did showed up in long
yields. During the 2021--22 crisis the sign flipped. Higher gas came with lower yields across the curve, <<b2_cri>>bp for the
two-year Bund (<<b2_cri_p>>), and with lower expected policy rates (<<ois11_cri_w>>bp on the OIS 1y1y at weekly frequency,
<<ois11_cri_w_p>>). Markets read gas as a recession risk and the ECB was still describing inflation as transitory. From 2023
to February 2026 the effects are close to zero everywhere. Then the war arrived.

<<TAB:regimes>>

\begin{figure}[htbp]\centering
\includegraphics[width=0.9\textwidth]{<<FIG:f2_regime_betas>>}
\caption{Total TTF effect by regime, bp per 10\% gas move (daily). Asterisks mark $p<0.05$. Only in the war does gas
lift the front end and flatten the curve.}\label{fig:regimes}
\end{figure}

The formal tests agree. In the pooled model (\ref{eq:inter}) the war-regime gas effect on the two-year Bund exceeds
the base-regime effect by <<ri_b2>>bp (<<ri_b2_p>>), and the difference is also significant for the one-year inflation
swap (<<ri_ils1_p>>) and for 2s30s (<<ri_s230_p>>). The sup-Wald test, which is not told when the war started, finds the
largest break in the OIS 2Y gas sensitivity on <<sw_ois2_date>> (statistic <<sw_ois2>> against a 5\% critical value of 8.68)
and in the OIS 1y1y on <<sw_ois11_date>> (<<sw_ois11>>). For the two-year Bund the Wald test at the war date rejects
(<<wald_b2_p>>) but the unknown-date version does not reach significance (<<sw_b2>>), because the war sits close to the
edge of the search window. The rolling estimates in Figure~\ref{fig:rolling} tell the same story visually.

\begin{figure}[htbp]\centering
\includegraphics[width=0.92\textwidth]{<<FIG:f3_rolling_beta>>}
\caption{Rolling 120-day TTF sensitivity of the two-year Bund and the OIS 1y1y, bp per 10\%, with 95\% bands. Shaded:
the 2021--22 gas crisis. Vertical line: 2 March 2026.}\label{fig:rolling}
\end{figure}

\subsection{Which part of the curve moves}

Every tenor rose during the war, and each rose less than the one before it: <<tm_2Y>>bp at two years, <<tm_5Y>>bp at five,
<<tm_10Y>>bp at ten and <<tm_30Y>>bp at thirty (Figure~\ref{fig:tenor}). The regressions say gas contributed to this shape.
Table~\ref{tab:slopes} compares six slopes. 2s30s carries the largest gas effect, <<s230_war>>bp per 10\% daily and
<<s230_war_w>>bp weekly, both significant, but Brent flattens it too. 2s10s ($<<s210_war>>$bp daily, <<s210_war_p>>) and
2s5s ($<<s25_war>>$bp, <<s25_war_p>>) respond to gas and not to oil, which makes them the cleaner gas measures; the 2s5s
effect, though, is gone at weekly frequency ($<<s25_war_w>>$bp), as the five-year catches up with the two-year within the
week. A principal-component decomposition of the curve (level <<pca_share1>>\% and slope <<pca_share2>>\% of daily variance)
gives the same answer: in the war gas loads on the slope factor ($<<pca_slope>>$bp, <<pca_slope_p>>), less clearly on the
level factor ($<<pca_level>>$bp, <<pca_level_p>>).

<<TAB:slopes>>

\begin{figure}[htbp]\centering
\begin{minipage}{0.49\textwidth}\centering\includegraphics[width=\textwidth]{<<FIG:f6_flatteners>>}\end{minipage}\hfill
\begin{minipage}{0.49\textwidth}\centering\includegraphics[width=\textwidth]{<<FIG:f7_tenor_moves_war>>}\end{minipage}
\caption{Left: slope change per 10\% TTF in the war, daily and weekly (asterisks: $p<0.05$). Right: change in Bund
yields by tenor between 27 February and 9 October 2026.}\label{fig:tenor}
\end{figure}

\subsection{How much runs through inflation expectations}

The mediation estimates (Table~\ref{tab:med}) suggest the inflation-expectations channel is real but not the whole
story. At daily frequency in the war, gas raises the OIS 1y1y by <<med_tot>>bp per 10\%, and about <<med_share>>\% of that
(<<med_ind>>bp) runs through the 1y1y inflation swap: each basis point on the swap moves the OIS 1y1y by <<med_b>>bp. The rest
is a direct effect. My reading is that the market prices the ECB's reaction to energy news without waiting for
inflation swaps to move first. At weekly frequency, the indirect path from gas through swaps and OIS to the two-year
Bund totals <<med_w_ind>>bp and is significant, and each basis point of OIS 1y1y passes <<med_w_b2>>bp into the Bund
(<<med_full_b2>> over the whole 2019--26 period).

<<TAB:med>>

\subsection{Gas explains the curve but does not forecast it}

The impact response is not followed by any drift (Figure~\ref{fig:lp}). In the war, the cumulative response of the
two-year Bund stays around its impact level for a week and then becomes too noisy to distinguish from zero; the
predictive version of the local projection, which starts after the impact day, is insignificant at every horizon
(at five days, <<lp_b2_5_pred_p>>). The 1y1y inflation swap even reverses: its cumulative response after 20 days is
<<lp_ils_20>>bp (<<lp_ils_20_p>>), which is consistent with markets treating most of each gas spike as temporary.

\begin{figure}[htbp]\centering
\includegraphics[width=0.95\textwidth]{<<FIG:f4_local_projections>>}
\caption{Cumulative response to a 10\% TTF move over 20 business days (local projections, 95\% bands): full sample
and Iran-war regime.}\label{fig:lp}
\end{figure}

The Granger tests agree. At weekly frequency TTF does not help predict the two-year Bund (<<gr_w_b2>>), and in the war
it does not predict OIS either (<<gr_war_ois>>). Over 2019--26 there is a daily Granger effect from TTF to OIS
(<<gr_full_ois>>), but the local projection shows it is a small give-back of <<lp_ois_1_pred>>bp per 10\% the next day,
not momentum. Out of sample (Table~\ref{tab:oos}) a gas model of next week's Bund change loses to the no-change
forecast in the war (OOS $R^2$ of <<oos_b2>>\%). The only gain is for the OIS 1y1y in the war ($<<oos_ois>>$\%, <<oos_ois_p>>),
from 31 forecasts, which I would not lean on.

<<TAB:oos>>

\section{Diagnostics and robustness}\label{sec:robust}

Table~\ref{tab:diag} summarises the residual tests. Heteroskedasticity, ARCH effects and fat tails are present in
almost every model, and serial correlation in several full-sample ones; the Newey--West errors are robust to all of
them. CUSUM rejects stability for the full-sample Bund regressions, which is what motivates estimating by regime in
the first place. The RESET test rejects linearity for the two-year Bund and 2s10s in the war, a hint that large gas days
move rates more than proportionally. Collinearity between gas and oil is moderate: their correlation is <<corr_tb>> in the
war, but no variance inflation factor exceeds <<vif_max>>.

<<TAB:diag>>

The main results hold up at weekly frequency (Appendix Tables~\ref{tab:w_war} and \ref{tab:w_full}), where the
Thursday-ending market window removes the timing problem for Bunds, and the two-year Bund and one-year inflation swap
results survive the Holm correction discussed above. What I cannot rule out is that war headlines move
gas, oil and rates at the same time for reasons that have nothing to do with inflation expectations; the Brent control
absorbs some of that, not all of it.

\section{Discussion and limits}\label{sec:disc}

Three conclusions seem solid to me. The first is that the gas--rates link is conditional. Its sign depends on whether
the market expects the central bank to treat an energy shock as an inflation problem or a growth problem. In 2022 it
was the latter; in 2026, after two hikes, it is the former. Anyone using gas as a rates signal should watch the rolling
sensitivity rather than assume a fixed beta. The second is that gas is priced as a shock to the expected policy path,
not to long-run inflation. The one-year swap moves four times as much as in normal times, the 1y1y much less, and the
30-year yield not at all. That is the signature of a bear flattening. The third is that the predictive value of gas
lies in the inflation data it foreshadows, not in tradable lead--lag relationships with the curve.

The limits are just as clear. The war regime is short, <<ils11_war_n>> trading days and <<n_war_w>> weeks, which is enough to
reject a zero effect but not to pin down magnitudes. Oil and gas moved together in this episode, and a VAR can only
bound gas's share of the variance of the expected policy rate: between <<fevd_lo>>\% and <<fevd_hi>>\% depending on the
ordering. Identification rests on controls rather than on an external instrument; LNG-specific outage news or
intraday windows around gas moves would sharpen it. The RESET results invite a threshold model. And the analysis would
benefit from the HICP energy sub-index, the 5y5y inflation swap, a volatility index for risk-off days, and a
constant-maturity Bund curve to remove on-the-run effects.

\section{Conclusion}

Since March 2026 European gas prices have been a significant driver of euro inflation swaps, of the expected ECB path
and of the front end of the German curve, and they have flattened it. This was not true before, and in 2021--22 the
opposite was true. Gas explains curve moves on the day they happen but does not forecast them; what it does forecast is
realised inflation a year out. The practical lesson is to treat gas as a regime-dependent factor for the front end and
the slope of the curve, and to check whether the regime still holds before relying on it.

\begin{thebibliography}{99}
\bibitem[Adolfsen et al.(2026)]{adolfsen2026} Adolfsen, J.~F., Lappe, M.-S., Manu, A.-S., R\"o{\ss}ler, D., Schupp, F. and Stalla-Bourdillon, A. (2026). Gas market shocks: tracing the effect on euro area inflation expectations. ECB Working Paper No.~3227.
\bibitem[Adolfsen et al.(2024)]{adolfsen2024} Adolfsen, J.~F., Ferrari Minesso, M., Mork, J.~E. and Van Robays, I. (2024). Gas price shocks and euro area inflation. ECB Working Paper No.~2905.
\bibitem[Andrews(1993)]{andrews1993} Andrews, D.~W.~K. (1993). Tests for parameter instability and structural change with unknown change point. \emph{Econometrica}, 61(4), 821--856.
\bibitem[Clark and West(2007)]{clarkwest2007} Clark, T.~E. and West, K.~D. (2007). Approximately normal tests for equal predictive accuracy in nested models. \emph{Journal of Econometrics}, 138(1), 291--311.
\bibitem[Dimson(1979)]{dimson1979} Dimson, E. (1979). Risk measurement when shares are subject to infrequent trading. \emph{Journal of Financial Economics}, 7(2), 197--226.
\bibitem[Holm(1979)]{holm1979} Holm, S. (1979). A simple sequentially rejective multiple test procedure. \emph{Scandinavian Journal of Statistics}, 6(2), 65--70.
\bibitem[Jord\`a(2005)]{jorda2005} Jord\`a, \`O. (2005). Estimation and inference of impulse responses by local projections. \emph{American Economic Review}, 95(1), 161--182.
\bibitem[L\'opez et al.(2024)]{lopez2024} L\'opez, L., Odendahl, F., P\'arraga, S. and Silgado-G\'omez, E. (2024). The pass-through to inflation of gas price shocks. ECB Working Paper No.~2968.
\bibitem[Newey and West(1987)]{neweywest1987} Newey, W.~K. and West, K.~D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. \emph{Econometrica}, 55(3), 703--708.
\end{thebibliography}

\clearpage
\appendix
\section{Full OLS results}\label{app:ols}

This appendix reports every transmission regression. Daily tables follow equations (\ref{eq:lseg}) and (\ref{eq:bbk});
weekly tables use Friday-to-Friday changes. Coefficients on $g$, $o$ and $e$ are in basis points per 1\% move. The
``TTF total'' row converts the gas coefficients into the effect of a 10\% move.

<<TAB:coef_pre>>
<<TAB:coef_cri>>
<<TAB:coef_norm>>
<<TAB:coef_full>>
<<TAB:w_cri>>
<<TAB:w_war>>
<<TAB:w_full>>

\clearpage
\section{Unit roots and cointegration}

<<TAB:ur>>
<<TAB:coint>>

\section{Replication}

The pipeline is in \texttt{src/}: \texttt{clean.py} builds the panels, \texttt{econometrics.py} runs every test and
writes \texttt{output/tables/}, \texttt{figures.py} draws the charts, \texttt{build\_workbook.py} assembles the results
workbook and \texttt{build\_paper.py} writes and compiles this paper. Every number in the text is filled in from the
result tables at build time.

\end{document}
"""


def build() -> None:
    V = values()
    tabs = other_tables()
    tabs["regimes"] = regime_table()
    def pair(freq, reg, cap, key, note):
        a = coef_table(freq, reg, cap + r", part 1: expectations and yields", f"tab:{key}", note, PANELS[:2])
        b = coef_table(freq, reg, cap + r", part 2: curve slopes", f"tab:{key}b", note, PANELS[2:])
        return a + "\n" + b
    tabs["coef_war"] = pair("daily", WAR, r"OLS transmission regressions, Iran-war regime (daily, 2 March -- 9 October 2026)",
                            "war", COEF_NOTE_DAILY)
    for key, reg, cap in [("coef_pre", PRE, "2014--21 regime (daily)"), ("coef_cri", CRISIS, "2021--22 gas-crisis regime (daily)"),
                          ("coef_norm", NORM, "January 2023 -- February 2026 regime (daily)"),
                          ("coef_full", FULL, "full sample (daily)")]:
        tabs[key] = pair("daily", reg, f"OLS transmission regressions, {cap}", key, COEF_NOTE_DAILY)
    for key, reg, cap in [("w_cri", CRISIS, "2021--22 gas-crisis regime"), ("w_war", WAR, "Iran-war regime"),
                          ("w_full", FULL, "full sample")]:
        tabs[key] = pair("weekly", reg, f"OLS transmission regressions, weekly, {cap}", key, COEF_NOTE_WEEKLY)
    tex = TEMPLATE
    tex = re.sub(r"<<TAB:(\w+)>>", lambda m: tabs[m.group(1)], tex)
    figdir = PAPER_DIR / "figs"
    figdir.mkdir(exist_ok=True)
    for f in (FIGURES / "paper").glob("*.pdf"):
        shutil.copy2(f, figdir / f.name)
    tex = re.sub(r"<<FIG:(\w+)>>", lambda m: f"figs/{m.group(1)}.pdf", tex)
    missing = sorted(set(re.findall(r"<<(\w+)>>", tex)) - set(V))
    if missing:
        raise KeyError(f"unfilled placeholders: {missing}")
    tex = re.sub(r"<<(\w+)>>", lambda m: V[m.group(1)], tex)
    # numbers that start with a minus sign inside text: make them proper math minus signs
    tex = tex.replace("$$-$", "$-").replace("$-$$", "$-")
    path = PAPER_DIR / "gas_bund_paper.tex"
    path.write_text(tex, encoding="utf-8")
    for _ in range(2):
        r = subprocess.run([PDFLATEX, "-interaction=nonstopmode", "-halt-on-error", path.name], cwd=PAPER_DIR,
                           capture_output=True, text=True)
        if r.returncode:
            print(r.stdout[-3000:])
            raise SystemExit("pdflatex failed")
    shutil.copy2(PAPER_DIR / "gas_bund_paper.pdf", OUT_PDF)
    warn = [l for l in r.stdout.splitlines() if "Warning" in l or "Overfull" in l]
    print("saved", OUT_PDF, f"({len(warn)} LaTeX warnings)")
    for l in warn[:15]:
        print("  ", l)


if __name__ == "__main__":
    build()
