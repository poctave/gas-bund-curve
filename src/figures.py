"""Static charts (PNG) for the workbook and memo. Light theme, reference palette (validated:
blue/orange/aqua/yellow adjacent CVD dE >= 9.1). One y-scale per panel; different units are
shown as stacked panels sharing the time axis, never a dual axis."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import CLEAN, FIGURES, TABLES

SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
WAR = pd.Timestamp("2026-03-02")

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.6,
    "lines.solid_capstyle": "round", "legend.frameon": False, "legend.fontsize": 8.5,
    "axes.titlesize": 10, "axes.titleweight": "semibold", "axes.titlecolor": INK, "axes.titlelocation": "left",
})


PAPER = False  # paper mode: serif type, vector PDF, no headline titles (the LaTeX caption carries the finding)


def _title(ax, text: str, panel: bool = False) -> None:
    if PAPER and not panel:
        return
    ax.set_title(text)


def _save(fig, name: str) -> None:
    if PAPER:
        fig.savefig(FIGURES / "paper" / f"{name}.pdf", bbox_inches="tight")
    else:
        fig.savefig(FIGURES / f"{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def _war_marker(ax, label: bool = False):
    ax.axvline(WAR, color=MUTED, lw=0.8)
    if label:
        ax.annotate("War onset 2 Mar", (WAR, 1), xycoords=("data", "axes fraction"), xytext=(4, -10),
                    textcoords="offset points", color=INK2, fontsize=8)


def fig_timeline(lv: pd.DataFrame) -> None:
    x = lv.loc["2025-10-01":]
    fig, axes = plt.subplots(3, 1, figsize=(9, 7.2), sharex=True, gridspec_kw={"hspace": 0.32})
    ax = axes[0]
    ax.plot(x.index, x.gas_ttf_m1_eurmwh, color=S1)
    _title(ax, "TTF front-month gas, EUR/MWh", panel=True)
    _war_marker(ax, label=True)
    for d, t in [("2026-04-08", "Ceasefire"), ("2026-06-11", "ECB hike"), ("2026-09-10", "ECB hike")]:
        ax.axvline(pd.Timestamp(d), color=GRID, lw=0.8)
        ax.annotate(t, (pd.Timestamp(d), 0), xycoords=("data", "axes fraction"), xytext=(-3, 4),
                    textcoords="offset points", color=MUTED, fontsize=7.5, ha="right")
    ax = axes[1]
    ax.plot(x.index, x.ils_eur_1y1y, color=S1, label="Inflation swap 1y1y")
    ax.plot(x.index, x.ois_estr_1y1y, color=S2, label="€STR OIS 1y1y (expected policy rate)")
    _title(ax, "Inflation expectations vs expected ECB rate, %", panel=True)
    ax.legend(loc="upper left")
    _war_marker(ax)
    ax = axes[2]
    ax.plot(x.index, x.bund_2y, color=S1, label="Bund 2Y")
    ax.plot(x.index, x.bund_30y, color=S2, label="Bund 30Y")
    _title(ax, "German yields, % (front end rises more = bear flattening)", panel=True)
    ax.legend(loc="upper left")
    _war_marker(ax)
    for a in axes:
        for side in ("bottom",):
            a.spines[side].set_color(AXIS)
    _save(fig, "f1_war_timeline")


def fig_regime_betas() -> None:
    t = pd.read_csv(TABLES / "04_transmission_daily.csv")
    deps = ["€STR OIS 1y1y", "Bund 2Y", "Bund 5Y", "Bund 10Y", "Bund 30Y", "Slope 2s30s"]
    regs = ["2014-21 pre-crisis", "2021-22 gas crisis", "2023-Feb26 normalisation", "Iran war (Mar 2026+)"]
    cols = [S1, S2, S3, S4]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    width = 0.19
    xs = np.arange(len(deps))
    for i, (r, c) in enumerate(zip(regs, cols)):
        vals = [t[(t.dependent == d) & (t.regime == r)].bp_per_10pct_ttf.squeeze() for d in deps]
        ps = [t[(t.dependent == d) & (t.regime == r)].p_ttf.squeeze() for d in deps]
        pos = xs + (i - 1.5) * (width + 0.01)
        ax.bar(pos, vals, width=width, color=c, label=r, edgecolor=SURFACE, linewidth=1)
        for p_, v, pv in zip(pos, vals, ps):
            if pv < 0.05:
                ax.annotate("*", (p_, v), xytext=(0, 2 if v >= 0 else -10), textcoords="offset points",
                            ha="center", color=INK2, fontsize=10)
    ax.axhline(0, color=AXIS, lw=0.8)
    ax.set_xticks(xs, deps, color=INK2)
    ax.set_ylabel("bp per +10% TTF (same + previous day)")
    _title(ax, "Gas sensitivity by regime: only in the Iran war does gas lift the front end and flatten the curve")
    ax.legend(ncol=4, loc="upper left", bbox_to_anchor=(0, -0.1))
    ax.annotate("* p < 0.05 (Newey-West HAC)", (1, -0.2), xycoords="axes fraction", ha="right", va="top",
                color=MUTED, fontsize=7.5)
    _save(fig, "f2_regime_betas")


def fig_rolling() -> None:
    r = pd.read_csv(TABLES / "08_rolling_betas_120d.csv", parse_dates=["date"])
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True, gridspec_kw={"hspace": 0.3})
    for ax, dep, title in [(axes[0], "Bund 2Y", "Bund 2Y"), (axes[1], "€STR OIS 1y1y", "€STR OIS 1y1y")]:
        x = r[r.dependent == dep]
        ax.fill_between(x.date, x.lo95_bp10, x.hi95_bp10, color=S1, alpha=0.12, lw=0)
        ax.plot(x.date, x.bp_per_10pct_ttf, color=S1)
        ax.axhline(0, color=AXIS, lw=0.8)
        ax.axvspan(pd.Timestamp("2021-07-01"), pd.Timestamp("2022-12-31"), color=GRID, alpha=0.5, lw=0)
        _war_marker(ax)
        _title(ax, f"{title}: rolling 120-day TTF sensitivity, bp per +10% (95% band)", panel=True)
    axes[0].annotate("2021-22 gas crisis", (pd.Timestamp("2021-08-01"), 1), xycoords=("data", "axes fraction"),
                     xytext=(0, -10), textcoords="offset points", color=MUTED, fontsize=7.5)
    _save(fig, "f3_rolling_beta")


def fig_local_projection() -> None:
    lp = pd.read_csv(TABLES / "12_local_projections.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=False, gridspec_kw={"wspace": 0.25})
    for ax, dep in zip(axes, ["Bund 2Y", "€STR OIS 1y1y"]):
        for sample, c in [("Full sample", S1), ("Iran war (Mar 2026+)", S2)]:
            x = lp[(lp.dependent == dep) & (lp["sample"] == sample)]
            ax.fill_between(x.horizon_days, x.cum_lo95_bp10, x.cum_hi95_bp10, color=c, alpha=0.10, lw=0)
            ax.plot(x.horizon_days, x.cum_bp_per_10pct, color=c, label=sample, marker="o", ms=3)
        ax.axhline(0, color=AXIS, lw=0.8)
        _title(ax, f"{dep}: cumulative response to +10% TTF, bp", panel=True)
        ax.set_xlabel("business days after the gas move")
    axes[0].legend(loc="upper right")
    _save(fig, "f4_local_projections")


def fig_hicp_lags() -> None:
    h = pd.read_csv(TABLES / "14_hicp_passthrough.csv")
    x = h[h.model.str.startswith("B")]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(x.lag_months, x.cum_gas_pp_per_10pct, color=S1, marker="o", ms=4, label="TTF gas")
    ax.plot(x.lag_months, x.cum_oil_pp_per_10pct, color=S2, marker="o", ms=4, label="Brent oil")
    ax.axhline(0, color=AXIS, lw=0.8)
    for _, r in x[x.lag_months.isin([0, 9])].iterrows():
        ax.annotate(f"{r.cum_gas_pp_per_10pct:+.2f}", (r.lag_months, r.cum_gas_pp_per_10pct),
                    xytext=(0, 7), textcoords="offset points", ha="center", color=INK2, fontsize=8)
    ax.set_xlabel("months between the energy price change and the inflation print")
    ax.set_ylabel("pp of HICP y/y per +10%")
    _title(ax, "Oil hits inflation immediately; gas arrives 6-12 months later")
    ax.legend(loc="upper center")
    _save(fig, "f5_hicp_lag_scan")


def fig_flatteners() -> None:
    c = pd.read_csv(TABLES / "17_curve_slopes.csv")
    fig, ax = plt.subplots(figsize=(9, 3.9))
    xs = np.arange(len(c))
    wd = 0.32
    for k, (col, pcol, lab, colr) in enumerate([
            ("Iran war (Mar 2026+): bp per +10% TTF", "Iran war (Mar 2026+): p", "Daily (same + previous day)", S1),
            ("war weekly: bp per +10% TTF", "war weekly: p", "Weekly (Fri-Fri)", S2)]):
        pos = xs + (k - 0.5) * (wd + 0.02)
        ax.bar(pos, c[col], width=wd, color=colr, label=lab, edgecolor=SURFACE, linewidth=1)
        for p_, v, pv in zip(pos, c[col], c[pcol]):
            if pv < 0.05:
                ax.annotate("*", (p_, v), xytext=(0, -10), textcoords="offset points", ha="center", color=INK2, fontsize=10)
    ax.axhline(0, color=AXIS, lw=0.8)
    ax.set_xticks(xs, c.slope, color=INK2)
    ax.set_ylabel("slope change, bp per +10% TTF")
    _title(ax, "Iran war: every gas-driven flattener points the same way; 2s30s is the largest and most robust")
    ax.legend(loc="lower left", ncol=2)
    ax.annotate("* p < 0.05 (Newey-West HAC)", (1, -0.13), xycoords="axes fraction", ha="right", va="top",
                color=MUTED, fontsize=7.5)
    _save(fig, "f6_flatteners")


def fig_tenor_moves() -> None:
    t = pd.read_csv(TABLES / "17b_tenor_moves_war.csv")
    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.bar(t.tenor, t["change (bp)"], width=0.45, color=S1)
    for x, v in zip(t.tenor, t["change (bp)"]):
        ax.annotate(f"+{v:.0f}", (x, v), xytext=(0, 3), textcoords="offset points", ha="center", color=INK2, fontsize=8.5)
    ax.set_ylabel("yield change, bp")
    _title(ax, "Bund yields 27 Feb to 9 Oct 2026: each tenor rose less than the one before it (bear flattening)")
    ax.tick_params(axis="x", colors=INK2)
    _save(fig, "f7_tenor_moves_war")


def paper_mode() -> None:
    global PAPER
    PAPER = True
    (FIGURES / "paper").mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"],
                         "mathtext.fontset": "stix", "font.size": 9.5, "axes.facecolor": "white",
                         "figure.facecolor": "white", "axes.titleweight": "normal", "axes.titlesize": 9.5,
                         "pdf.fonttype": 42})


def main() -> None:
    lv = pd.read_csv(CLEAN / "daily_levels.csv", index_col=0, parse_dates=True)
    fig_timeline(lv)
    fig_regime_betas()
    fig_rolling()
    fig_local_projection()
    fig_hicp_lags()
    fig_flatteners()
    fig_tenor_moves()
    print("figures written to", FIGURES)


if __name__ == "__main__":
    main()
    paper_mode()
    main()
