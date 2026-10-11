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
    ax.set_title("TTF front-month gas, EUR/MWh")
    _war_marker(ax, label=True)
    for d, t in [("2026-04-08", "Ceasefire"), ("2026-06-11", "ECB hike"), ("2026-09-10", "ECB hike")]:
        ax.axvline(pd.Timestamp(d), color=GRID, lw=0.8)
        ax.annotate(t, (pd.Timestamp(d), 0), xycoords=("data", "axes fraction"), xytext=(-3, 4),
                    textcoords="offset points", color=MUTED, fontsize=7.5, ha="right")
    ax = axes[1]
    ax.plot(x.index, x.ils_eur_1y1y, color=S1, label="Inflation swap 1y1y")
    ax.plot(x.index, x.ois_estr_1y1y, color=S2, label="€STR OIS 1y1y (expected policy rate)")
    ax.set_title("Inflation expectations vs expected ECB rate, %")
    ax.legend(loc="upper left")
    _war_marker(ax)
    ax = axes[2]
    ax.plot(x.index, x.bund_2y, color=S1, label="Bund 2Y")
    ax.plot(x.index, x.bund_30y, color=S2, label="Bund 30Y")
    ax.set_title("German yields, % (front end rises more = bear flattening)")
    ax.legend(loc="upper left")
    _war_marker(ax)
    for a in axes:
        for side in ("bottom",):
            a.spines[side].set_color(AXIS)
    fig.savefig(FIGURES / "f1_war_timeline.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


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
    ax.set_title("Gas sensitivity by regime: only in the Iran war does gas lift the front end and flatten the curve")
    ax.legend(ncol=4, loc="upper left", bbox_to_anchor=(0, -0.1))
    ax.annotate("* p < 0.05 (Newey-West HAC)", (1, -0.2), xycoords="axes fraction", ha="right", va="top",
                color=MUTED, fontsize=7.5)
    fig.savefig(FIGURES / "f2_regime_betas.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


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
        ax.set_title(f"{title}: rolling 120-day TTF sensitivity, bp per +10% (95% band)")
    axes[0].annotate("2021-22 gas crisis", (pd.Timestamp("2021-08-01"), 1), xycoords=("data", "axes fraction"),
                     xytext=(0, -10), textcoords="offset points", color=MUTED, fontsize=7.5)
    fig.savefig(FIGURES / "f3_rolling_beta.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_local_projection() -> None:
    lp = pd.read_csv(TABLES / "12_local_projections.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=False, gridspec_kw={"wspace": 0.25})
    for ax, dep in zip(axes, ["Bund 2Y", "€STR OIS 1y1y"]):
        for sample, c in [("Full sample", S1), ("Iran war (Mar 2026+)", S2)]:
            x = lp[(lp.dependent == dep) & (lp["sample"] == sample)]
            ax.fill_between(x.horizon_days, x.cum_lo95_bp10, x.cum_hi95_bp10, color=c, alpha=0.10, lw=0)
            ax.plot(x.horizon_days, x.cum_bp_per_10pct, color=c, label=sample, marker="o", ms=3)
        ax.axhline(0, color=AXIS, lw=0.8)
        ax.set_title(f"{dep}: cumulative response to +10% TTF, bp")
        ax.set_xlabel("business days after the gas move")
    axes[0].legend(loc="upper right")
    fig.savefig(FIGURES / "f4_local_projections.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


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
    ax.set_title("Oil hits inflation immediately; gas arrives 6-12 months later")
    ax.legend(loc="upper center")
    fig.savefig(FIGURES / "f5_hicp_lag_scan.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    lv = pd.read_csv(CLEAN / "daily_levels.csv", index_col=0, parse_dates=True)
    fig_timeline(lv)
    fig_regime_betas()
    fig_rolling()
    fig_local_projection()
    fig_hicp_lags()
    print("figures written to", FIGURES)


if __name__ == "__main__":
    main()
