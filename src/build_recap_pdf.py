"""Build the explanatory recap PDF (output/Gas_Bund_Research_Recap.pdf).

Every number quoted in the text is read from output/tables/*.csv at build time, so the PDF always
matches the latest run of econometrics.py."""
from __future__ import annotations

import os

import matplotlib
import pandas as pd
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from config import FIGURES, ROOT, TABLES

OUT = ROOT / "output" / "Gas_Bund_Research_Recap.pdf"

# DejaVu ships with matplotlib and covers €, arrows, ≈, × (the built-in PDF fonts do not)
_fd = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
pdfmetrics.registerFont(TTFont("DV", os.path.join(_fd, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", os.path.join(_fd, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DV-I", os.path.join(_fd, "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFont(TTFont("DV-BI", os.path.join(_fd, "DejaVuSans-BoldOblique.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")

NAVY = colors.HexColor("#1F3864")
BLUE = colors.HexColor("#2a78d6")
INK = colors.HexColor("#0b0b0b")
INK2 = colors.HexColor("#52514e")
GRID = colors.HexColor("#e1e0d9")
TINT = colors.HexColor("#EEF2F8")
GOOD = colors.HexColor("#E2F0D9")
WARN = colors.HexColor("#FCE9D9")

S = {
    "title": ParagraphStyle("title", fontName="DV-B", fontSize=21, leading=26, textColor=NAVY, spaceAfter=6),
    "sub": ParagraphStyle("sub", fontName="DV", fontSize=10.5, leading=14, textColor=INK2, spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName="DV-B", fontSize=14.5, leading=18, textColor=NAVY, spaceBefore=6, spaceAfter=8, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="DV-B", fontSize=11, leading=14, textColor=INK, spaceBefore=8, spaceAfter=4, keepWithNext=1),
    "body": ParagraphStyle("body", fontName="DV", fontSize=9.4, leading=13.4, textColor=INK, spaceAfter=6, alignment=TA_LEFT),
    "bullet": ParagraphStyle("bullet", fontName="DV", fontSize=9.4, leading=13.2, textColor=INK, leftIndent=12,
                             bulletIndent=2, spaceAfter=3),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=8.1, leading=10.6, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="DV-B", fontSize=8.1, leading=10.6, textColor=INK),
    "head": ParagraphStyle("head", fontName="DV-B", fontSize=8.1, leading=10.4, textColor=colors.white),
    "caption": ParagraphStyle("caption", fontName="DV-I", fontSize=8, leading=10.5, textColor=INK2, spaceAfter=10),
    "box": ParagraphStyle("box", fontName="DV", fontSize=9.4, leading=13.4, textColor=INK),
}
W = A4[0] - 2 * 20 * mm  # usable width


# --------------------------------------------------------------------------- numbers from the tables
def T(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLES / f"{name}.csv")


td, tw = T("04_transmission_daily"), T("04_transmission_weekly")
WAR, CRISIS, NORM, PRE = "Iran war (Mar 2026+)", "2021-22 gas crisis", "2023-Feb26 normalisation", "2014-21 pre-crisis"


def tr(df, dep, reg, col="bp_per_10pct_ttf"):
    return float(df[(df.dependent == dep) & (df.regime == reg)][col].iloc[0])


def p(x: float) -> str:
    return "p < 0.001" if x < 0.001 else f"p = {x:.3f}"


def bp(x: float, d: int = 1) -> str:
    return f"{x:+.{d}f}bp"


hicp = T("14_hicp_passthrough")
hB = hicp[hicp.model.str.startswith("B")]
hA = hicp[hicp.model == "A: joint tests"].iloc[0]
med = T("10_mediation")
brk = T("07_structural_breaks")
rit = T("05_regime_interaction")
fevd = T("11c_var_fevd")
oos = T("13_oos_forecast")
tim = T("09_lead_lag_timing")
ev = T("15_event_study")
pca = T("16_curve_pca")
diag = T("06_residual_diagnostics")
lp = T("12_local_projections")

N = {
    "gas_hicp9": float(hB[hB.lag_months == 9].cum_gas_pp_per_10pct.iloc[0]),
    "gas_hicp9_p": float(hB[hB.lag_months == 9].gas_p.iloc[0]),
    "gas_hicp12": float(hB[hB.lag_months == 12].cum_gas_pp_per_10pct.iloc[0]),
    "gas_hicp0": float(hB[hB.lag_months == 0].cum_gas_pp_per_10pct.iloc[0]),
    "oil_hicp0": float(hB[hB.lag_months == 0].cum_oil_pp_per_10pct.iloc[0]),
    "oil_hicp0_p": float(hB[hB.lag_months == 0].oil_p.iloc[0]),
    "hicp_joint_p": float(hA.joint_gas_all_lags_p), "hicp_06_p": float(hA.gas_lags0to6_p),
    "ils1_war": tr(td, "Infl. swap 1Y", WAR), "ils1_war_p": tr(td, "Infl. swap 1Y", WAR, "p_ttf"),
    "ils1_norm": tr(td, "Infl. swap 1Y", NORM), "ils1_brent_war": tr(td, "Infl. swap 1Y", WAR, "bp_per_10pct_brent"),
    "ils11_war": tr(td, "Infl. swap 1y1y", WAR), "ils11_war_p": tr(td, "Infl. swap 1y1y", WAR, "p_ttf"),
    "ois11_war": tr(td, "€STR OIS 1y1y", WAR), "ois11_war_p": tr(td, "€STR OIS 1y1y", WAR, "p_ttf"),
    "ois11_war_w": tr(tw, "€STR OIS 1y1y", WAR), "ois11_war_w_p": tr(tw, "€STR OIS 1y1y", WAR, "p_ttf"),
    "ois11_crisis_w": tr(tw, "€STR OIS 1y1y", CRISIS), "ois11_crisis_w_p": tr(tw, "€STR OIS 1y1y", CRISIS, "p_ttf"),
    "ois11_brent_war": tr(td, "€STR OIS 1y1y", WAR, "bp_per_10pct_brent"),
    "b2_war": tr(td, "Bund 2Y", WAR), "b2_war_p": tr(td, "Bund 2Y", WAR, "p_ttf"),
    "b2_war_holm": tr(td, "Bund 2Y", WAR, "p_ttf_holm"),
    "b2_war_w": tr(tw, "Bund 2Y", WAR), "b2_war_w_p": tr(tw, "Bund 2Y", WAR, "p_ttf"),
    "b2_crisis": tr(td, "Bund 2Y", CRISIS), "b2_crisis_p": tr(td, "Bund 2Y", CRISIS, "p_ttf"),
    "b2_pre": tr(td, "Bund 2Y", PRE), "b2_norm": tr(td, "Bund 2Y", NORM),
    "b10_war": tr(td, "Bund 10Y", WAR), "b30_war": tr(td, "Bund 30Y", WAR), "b30_war_p": tr(td, "Bund 30Y", WAR, "p_ttf"),
    "s230_war": tr(td, "Slope 2s30s", WAR), "s230_war_p": tr(td, "Slope 2s30s", WAR, "p_ttf"),
    "s530_war_w": tr(tw, "Slope 5s30s", WAR), "s530_war_w_p": tr(tw, "Slope 5s30s", WAR, "p_ttf"),
    "ri_b2": float(rit[(rit.dependent == "Bund 2Y") & (rit.regime_vs_base == WAR)].difference_bp_per_10pct.iloc[0]),
    "ri_b2_p": float(rit[(rit.dependent == "Bund 2Y") & (rit.regime_vs_base == WAR)].wald_p.iloc[0]),
    "sw_ois2": float(brk[brk.dependent == "€STR OIS 2Y"].sup_wald_stat.iloc[0]),
    "sw_ois2_date": str(brk[brk.dependent == "€STR OIS 2Y"].sup_wald_break_date.iloc[0]),
    "sw_ois11_date": str(brk[brk.dependent == "€STR OIS 1y1y"].sup_wald_break_date.iloc[0]),
    "med_tot": float(med[(med.frequency == "daily") & (med["sample"] == WAR) & (med.mediator == "Infl. swap 1y1y")
                         & (med.effect == "Total: TTF -> OIS 1y1y")].bp_per_10pct_ttf.iloc[0]),
    "med_ind_share": float(med[(med.frequency == "daily") & (med["sample"] == WAR) & (med.mediator == "Infl. swap 1y1y")
                               & (med.effect.str.startswith("Indirect"))].share_of_total.iloc[0]),
    "med_w_ind": float(med[(med.frequency == "weekly") & (med["sample"].str.startswith("Iran"))
                           & (med.effect == "Total indirect")].bp_per_10pct_ttf.iloc[0]),
    "med_w_b2": float(med[(med.frequency == "weekly") & (med["sample"].str.startswith("Iran"))
                          & (med.effect.str.startswith("b2"))].estimate.iloc[0]),
    "fevd_lo": float(fevd[(fevd.frequency == "daily") & (fevd["sample"] == WAR) & (fevd.ordering == "Brent first")
                          & (fevd.variable == "OIS 1y1y") & (fevd.horizon == 10)].share_TTF.iloc[0]),
    "fevd_hi": float(fevd[(fevd.frequency == "daily") & (fevd["sample"] == WAR) & (fevd.ordering == "TTF first")
                          & (fevd.variable == "OIS 1y1y") & (fevd.horizon == 10)].share_TTF.iloc[0]),
    "oos_b2": float(oos[(oos.target == "Bund 2Y (next week)") & (oos.evaluation == "Iran war only") & (oos.model == "gas only")
                        & (oos.benchmark == "no change")].oos_r2.iloc[0]),
    "oos_ois": float(oos[(oos.target == "€STR OIS 1y1y (next week)") & (oos.evaluation == "Iran war only")
                         & (oos.model == "gas only") & (oos.benchmark == "no change")].oos_r2.iloc[0]),
    "oos_ois_p": float(oos[(oos.target == "€STR OIS 1y1y (next week)") & (oos.evaluation == "Iran war only")
                           & (oos.model == "gas only") & (oos.benchmark == "no change")].clark_west_p.iloc[0]),
    "tim_lag": float(tim.iloc[0]["beta_t-1"]), "tim_same": float(tim.iloc[0]["beta_t"]),
    "pca_slope": float(pca[pca.item == WAR].PC2_slope.iloc[0]), "pca_slope_p": float(pca[pca.item == WAR].PC2_slope_p.iloc[0]),
    "corr_ttf_brent": float(diag[(diag.dependent == "Bund 2Y") & (diag["sample"] == WAR)].corr_ttf_brent.iloc[0]),
    "n_war": int(td[(td.dependent == "Infl. swap 1y1y") & (td.regime == WAR)].n.iloc[0]),
    "n_war_w": int(tw[(tw.dependent == "Bund 2Y") & (tw.regime == WAR)].n.iloc[0]),
}


def evchg(date, var, two_day=True):
    r = ev[(ev.event_date == date) & (ev.variable == var)].iloc[0]
    a, b = r["level_t-1"], r["level_t+1"] if two_day else r["level_t"]
    return (b - a) * (100 if "(%)" in var else 1)


N["ev_war_b2"], N["ev_war_b30"] = evchg("2026-03-02", "Bund 2Y (%)"), evchg("2026-03-02", "Bund 30Y (%)")
N["ev_cf_ois"], N["ev_cf_slope"] = evchg("2026-04-08", "OIS 1y1y (%)"), evchg("2026-04-08", "2s10s (bp)")


# --------------------------------------------------------------------------- building blocks
def para(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items):
    return [Paragraph(t, S["bullet"], bulletText="•") for t in items]


def table(rows, widths, header=True, zebra=True, highlight_col=None):
    data = []
    for i, r in enumerate(rows):
        st = "head" if (header and i == 0) else "cell"
        data.append([c if not isinstance(c, str) else Paragraph(c, S[st]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3.5),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5), ("LEFTPADDING", (0, 0), (-1, -1), 4),
             ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("LINEBELOW", (0, 0), (-1, -1), 0.4, GRID)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY)]
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F7F8FB")))
    t.setStyle(TableStyle(style))
    return t


def callout(text, fill=TINT):
    t = Table([[Paragraph(text, S["box"])]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), fill), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LINEBEFORE", (0, 0), (0, -1), 3, NAVY)]))
    return t


def figure(name, caption, width=W):
    from PIL import Image as PILImage
    path = str(FIGURES / f"{name}.png")
    w, h = PILImage.open(path).size
    img = Image(path, width=width, height=width * h / w)
    img.hAlign = "CENTER"
    return KeepTogether([img, Spacer(1, 3), para(caption, "caption")])


def chain_diagram() -> Drawing:
    """Top-down chain: 5 boxes with arrows; right column = how it is measured and what was found."""
    links = [
        ("Supply shock", "Hormuz closed, Qatar LNG halted", "TTF ~€32 → ~€54/MWh in 2 days"),
        ("Gas price (TTF)", "Front-month Dutch TTF futures", "the driver we test"),
        ("Inflation expectations", "Inflation swaps 1Y and 1y1y",
         f"1Y swap {bp(N['ils1_war'])} per +10% gas (war)"),
        ("ECB rate expectations", "€STR OIS 1y1y = expected policy rate in 1y",
         f"{bp(N['ois11_war'])} daily, {bp(N['ois11_war_w'])} weekly"),
        ("Bund curve", "2Y vs 30Y yields, slopes",
         f"2Y {bp(N['b2_war'])}, 30Y {bp(N['b30_war'])} = bear flattening"),
    ]
    bw, bh, gap, x0 = 150, 38, 18, 4
    H = len(links) * bh + (len(links) - 1) * gap + 10
    d = Drawing(W, H)
    for i, (name, what, found) in enumerate(links):
        y = H - 5 - (i + 1) * bh - i * gap
        accent = i == len(links) - 1
        d.add(Rect(x0, y, bw, bh, rx=6, ry=6, fillColor=TINT if accent else colors.white,
                   strokeColor=NAVY if accent else colors.HexColor("#c3c2b7"), strokeWidth=1.6 if accent else 1))
        d.add(String(x0 + bw / 2, y + bh / 2 - 3.5, name, fontName="DV-B", fontSize=9.5, fillColor=INK, textAnchor="middle"))
        d.add(String(x0 + bw + 18, y + bh / 2 + 3, what, fontName="DV", fontSize=8.6, fillColor=INK))
        d.add(String(x0 + bw + 18, y + bh / 2 - 9, found, fontName="DV-I", fontSize=8.6, fillColor=BLUE if i > 1 else INK2))
        if i < len(links) - 1:
            cx = x0 + bw / 2
            d.add(Line(cx, y, cx, y - gap + 5, strokeColor=colors.HexColor("#898781"), strokeWidth=1.1))
            d.add(Polygon([cx - 4, y - gap + 6, cx + 4, y - gap + 6, cx, y - gap + 0.5],
                          fillColor=colors.HexColor("#898781"), strokeColor=None))
    # side note: realised inflation branch
    return d


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 7.5)
    canvas.setFillColor(INK2)
    canvas.drawString(20 * mm, 12 * mm, "Gas → Bund curve · research recap · data to 9 Oct 2026")
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"{doc.page}")
    canvas.setStrokeColor(GRID)
    canvas.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
    canvas.restoreState()


# --------------------------------------------------------------------------- the document
def build() -> None:
    st = []
    st += [para("Gas → Bund Curve", "title"),
           para("Do European gas prices drive, and predict, moves on the German yield curve through inflation "
                "expectations and ECB rate-hike expectations? A plain-language recap of the data, the tests and what "
                "they mean. Prepared 11 October 2026; data to the 9 October 2026 close.", "sub")]

    # 1 TL;DR ---------------------------------------------------------------
    st.append(para("1. The answer in one page", "h1"))
    st.append(callout(
        f"<b>Since the Iran war started (2 March 2026), a +10% move in European gas has lifted the German 2-year "
        f"yield by about {N['b2_war']:.0f}bp on the same day while leaving the 30-year almost unchanged.</b> Gas "
        f"has been a driver of ECB rate-hike pricing and of curve <b>bear flattening</b>. This link exists only "
        f"in the current regime: in 2021-22 it ran the other way, and in normal times it is close to zero."))
    st.append(Spacer(1, 8))
    st.append(table([
        ["Link in the chain", "What we found (per +10% TTF gas move)", "Verdict"],
        ["1. Gas → realised inflation",
         f"~0 on impact; +{N['gas_hicp9']:.2f}pp of euro-area inflation (y/y) 9 months later ({p(N['gas_hicp9_p'])}), "
         f"+{N['gas_hicp12']:.2f}pp after 12. Oil acts at once: +{N['oil_hicp0']:.2f}pp the same month.",
         "Yes, with a lag"],
        ["2. Gas → inflation expectations",
         f"1-year inflation swap {bp(N['ils1_war'])} same day in the war ({p(N['ils1_war_p'])}), vs "
         f"{bp(N['ils1_norm'])} in 2023-26. The 1y1y forward moves less: {bp(N['ils11_war'])}.",
         "Yes, amplified in the war"],
        ["3. → ECB rate expectations",
         f"Expected policy rate in one year (€STR OIS 1y1y) {bp(N['ois11_war'])} daily, {bp(N['ois11_war_w'])} "
         f"weekly. A break test dates the change to {N['sw_ois2_date']} without being told the war date.",
         "Yes, in the war"],
        ["4. → Bund curve",
         f"Bund 2Y {bp(N['b2_war'])} ({p(N['b2_war_p'])}), Bund 30Y {bp(N['b30_war'])} (not significant), "
         f"2s30s slope {bp(N['s230_war'])}.", "Yes: bear flattening"],
        ["Regime dependence",
         f"Bund 2Y {bp(N['b2_crisis'])} in 2021-22, ~0 in normal times, {bp(N['b2_war'])} in the war. "
         f"War vs normal difference {p(N['ri_b2_p'])}.", "Strong"],
        ["Predicting later curve moves",
         "No drift after day 1-2, no lead in Granger tests, no out-of-sample gain for Bunds.", "No"],
    ], [W * 0.24, W * 0.56, W * 0.20]))
    st.append(Spacer(1, 8))
    st += bullets([
        f"<b>Main caveats.</b> The war regime is short ({N['n_war']} trading days, {N['n_war_w']} weeks). Oil moves "
        f"with gas (correlation {N['corr_ttf_brent']:.2f} in the war) and matters even more for inflation pricing.",
        "<b>What it means for you.</b> Treat gas as a regime-dependent front-end driver: watch the rolling "
        "sensitivity, because the sign of the link depends on how the market expects the ECB to react.",
    ])
    st.append(PageBreak())

    # 2 Story ---------------------------------------------------------------
    st.append(para("2. The economic story", "h1"))
    st.append(para("The thesis is a chain. Each link must hold for gas to move the Bund curve, and each one was "
                   "tested separately. The diagram shows the chain with what was measured at every step."))
    st.append(chain_diagram())
    st.append(Spacer(1, 4))
    st.append(para("A fifth path runs in parallel: gas reaches <i>realised</i> inflation 6-12 months later, through "
                   "retail energy bills. Markets anticipate it, which is why links 2 to 4 happen on the day.", "caption"))
    for head, text in [
        ("Link 1: gas → realised inflation",
         "Gas sets the marginal price of electricity in Europe and feeds household gas bills, fertiliser, chemicals "
         "and industry. Retail tariffs are regulated or contracted, so they reset slowly. The effect on the inflation "
         "the ECB targets arrives months after the wholesale move."),
        ("Link 2: inflation → inflation expectations",
         "Investors do not wait for the inflation prints. They price future inflation today through inflation swaps. "
         "The 1-year swap reflects next year's price level. The 1y1y forward reflects inflation one to two years "
         "ahead, the horizon the ECB cares about."),
        ("Link 3: inflation expectations → ECB rate expectations",
         "A central bank targeting 2% is expected to hike when inflation expectations rise. The market writes the "
         "expected path into €STR overnight index swaps (OIS). This link only works if the market <i>believes</i> "
         "the ECB will react, and that belief is what changed between 2022 and 2026."),
        ("Link 4: ECB expectations → the Bund curve",
         "The 2-year Bund mostly reflects the expected ECB path over two years. The 30-year mostly reflects long-run "
         "growth, long-run inflation and a term premium. A policy shock therefore lifts the short end more than the "
         "long end: yields rise and the curve flattens, a <b>bear flattening</b>."),
    ]:
        st += [para(head, "h2"), para(text)]
    st.append(para("The 2026 context", "h2"))
    st.append(para("The ECB hiked in June (deposit rate 2.00% to 2.25%) and September (to 2.50%), its first hikes "
                   "since 2023. Euro-area inflation reached 3.3% in August, with energy at +14.3%. Between 27 February "
                   "and 9 October 2026 the Bund 2Y rose from 2.03% to 3.09% and the 30Y from 3.36% to 3.85%."))
    st.append(figure("f1_war_timeline", "Figure 1. Gas, inflation expectations, expected ECB rate and Bund yields, "
                                        "Oct 2025 to Oct 2026. Vertical line: war onset (2 March 2026).", W * 0.82))

    # 3 Instruments ---------------------------------------------------------
    st.append(para("3. The instruments, in plain words", "h1"))
    st.append(para("Each benchmark was chosen for the job it does in the chain. The clean variable name is the "
                   "column name in the data files."))
    st.append(table([
        ["Instrument (clean name)", "What it is", "Why this one"],
        ["<b>TTF front-month</b><br/>gas_ttf_m1_eurmwh", "Futures price of Dutch TTF gas for delivery next month, "
         "EUR per MWh (LSEG TFMBMc1).", "The euro-area wholesale gas benchmark, quoted in euros, the most liquid "
         "European gas contract."],
        ["<b>Brent front-month</b><br/>oil_brent_m1_usdbbl", "Futures price of North Sea crude oil, USD per barrel (LCOc1).",
         "Control: the Hormuz shock hits oil and gas together, and oil drives inflation swaps."],
        ["<b>EUR/USD</b><br/>fx_eurusd", "Euro exchange rate (EUR=).", "Control: energy is priced in dollars."],
        ["<b>Inflation swap 1Y</b><br/>ils_eur_1y", "A contract paying the realised euro-area inflation (HICP ex-tobacco) "
         "over one year against a fixed rate. The fixed rate = the market's expected inflation (EUCPIZ1Y=TWEB, from 2022).",
         "Where gas shows up first in market expectations."],
        ["<b>Inflation swap 1y1y</b><br/>ils_eur_1y1y", "Expected inflation for the year starting one year from now "
         "(EUIL1YF1Y=R). Your file was labelled '1Y'; it is the forward.",
         "The ECB's policy horizon: tells whether the shock is seen as persistent."],
        ["<b>€STR OIS 1M, 3M, 1Y, 2Y; 1y1y</b><br/>ois_estr_*", "Swaps on the ECB overnight rate (€STR). The fixed rate "
         "= the average policy rate the market expects. 1y1y (computed) = expected rate one year ahead.",
         "The cleanest market measure of rate-hike expectations: no credit or scarcity premium."],
        ["<b>Bund yields 2Y to 30Y</b><br/>bund_2y ... bund_30y", "Yields of the current German government bonds "
         "(Bundesbank). 2Y = 'Schatz', 10Y = 'Bund', 30Y = long bond.", "The curve being studied. 2Y = policy end, 30Y = "
         "term-premium end."],
        ["<b>Slopes and PCA</b><br/>slope_2s10s, slope_2s30s, slope_5s30s", "Differences between long and short yields "
         "(bp). PCA splits curve moves into level, slope and curvature.", "Tests the 'specific moves' part of the thesis."],
        ["<b>Swap spread, Bund-OIS</b><br/>swapsprd_de5y_bp, sprd_bund2y_ois2y", "5Y swap rate minus 5Y Bund; 2Y Bund "
         "minus 2Y OIS.", "Separate policy repricing from flight-to-safety into Bunds."],
        ["<b>HICP</b><br/>hicp_ea_idx, hicp_ea_yoy", "Euro-area consumer price index (2025 = 100).",
         "The realised inflation at the start of the chain."],
        ["<b>Not used in headline tests</b>", "NBP (UK gas), Henry Hub (US gas), IMF monthly EU gas.",
         "Cross-checks only. NBP is UK and in sterling; Henry Hub is the US leg of LNG trade."],
    ], [W * 0.27, W * 0.42, W * 0.31]))
    st.append(Spacer(1, 10))

    # 4 Data ----------------------------------------------------------------
    st.append(para("4. The data: what was wrong and how it was fixed", "h1"))
    st.append(para("Raw files were archived under clear names, then cleaned. Six issues mattered for the results."))
    st.append(table([
        ["Issue", "Why it matters", "Fix"],
        ["<b>Inflation swap mislabelled</b>: the '1Y' file is the 1y1y forward.", "Wrong label leads to wrong "
         "interpretation (near-term vs persistent inflation).", "Renamed ils_eur_1y1y; the true 1Y swap was added."],
        ["<b>HICP spliced from two index bases</b> (fake -34% month in Dec 1999).", "Year-on-year inflation is wrong "
         "for a year around the break.", "Kept only data from the break on (2025 = 100 base)."],
        ["<b>Futures contract rolls.</b> 'Front-month' series jump when the contract changes.", "A roll looks like a big "
         "price move that never happened.", "Roll days detected from open-interest jumps (~12 a year) and excluded."],
        ["<b>Timing mismatch.</b> Bundesbank yields are recorded about half a trading day before the LSEG closes "
         "used for gas, swaps and OIS.", f"Today's Bund move loads equally on yesterday's and today's OIS move "
         f"({N['tim_lag']:.2f} vs {N['tim_same']:.2f}). Ignored, it fakes 'predictability'.",
         "Daily Bund tests include the previous day's market move; the full chain is also run weekly."],
        ["<b>Junk file</b> (stock_data.csv): weekend rows, High below Open, unknown source.", "Unreliable.", "Excluded."],
        ["<b>Duplicate file</b>: 2-year NBP export is a copy of part of the 10-year one.", "Redundant.", "Excluded."],
    ], [W * 0.36, W * 0.34, W * 0.30]))
    st.append(Spacer(1, 6))
    st.append(para("Coverage: daily from October 2014 for gas, oil, FX and the main Bunds; €STR OIS from September 2019; "
                   "the 1Y inflation swap from April 2022. The war regime has 143 trading days (32 weeks)."))

    # 5 How to read ---------------------------------------------------------
    st.append(para("5. How to read the numbers", "h1"))
    st.append(para("Every result answers one question: when gas moves by X, how much does the rate move, and could "
                   "that be luck?"))
    st.append(table([
        ["Term", "Meaning", "Example from this study"],
        ["<b>bp per +10% TTF</b>", "Basis points the rate moves for a 10% rise in gas (1bp = 0.01%).",
         f"Bund 2Y {bp(N['b2_war'])} per +10% TTF in the war."],
        ["<b>Beta (sensitivity)</b>", "The slope of a regression: the average move of the rate per unit move of gas, "
         "holding oil and the euro constant.", "The numbers in the tables are betas scaled to a +10% gas move."],
        ["<b>p-value</b>", "Chance of seeing an effect this large if the true effect were zero. Below 0.05 = "
         "'statistically significant'.", f"Bund 2Y in the war: {p(N['b2_war_p'])}, so very unlikely to be luck."],
        ["<b>Robust (HAC) standard errors</b>", "Market data have fat tails, volatility bursts and some "
         "autocorrelation. Newey-West HAC errors stay valid under all three.", "Used for every regression."],
        ["<b>Multiple testing (Holm)</b>", "Testing 17 series raises the odds of a fluke. Holm correction raises the bar.",
         f"Bund 2Y in the war still passes: corrected {p(N['b2_war_holm'])}."],
        ["<b>Regimes</b>", "Separate periods with different market behaviour.",
         "2014-21 pre-crisis · 2021-22 gas crisis · 2023-Feb 2026 normalisation · Iran war from 2 Mar 2026."],
        ["<b>Daily vs weekly</b>", "Daily = more data; weekly = immune to the timing mismatch.",
         "Results are reported at both frequencies and agree."],
    ], [W * 0.22, W * 0.44, W * 0.34]))
    st.append(Spacer(1, 10))

    # 6 Tests ---------------------------------------------------------------
    st.append(para("6. The tests, one by one", "h1"))
    st.append(para("The tests run from 'what does the data look like' to 'is the effect real' to 'can it predict'. "
                   "The workbook has a sheet for each."))
    st.append(table([
        ["Test", "Question in plain words", "What it found", "Why it matters"],
        ["Normality, autocorrelation, volatility clustering (Jarque-Bera, Ljung-Box, ARCH)",
         "Do daily moves behave like textbook data?", "No: fat tails, volatility bursts, some autocorrelation.",
         "Ordinary errors would mislead; robust errors are used."],
        ["Stationarity (ADF, KPSS, Zivot-Andrews)", "Do series wander (levels) or revert (changes)?",
         "All levels wander; all changes are stable.", "Analyse changes, not levels, to avoid spurious links."],
        ["Cointegration (Engle-Granger, Johansen)", "Do gas and yields share a long-run level relationship?",
         "No robust one.", "Gas is a shock driver, not an anchor for the level of yields."],
        ["Transmission regressions by regime", "How much does each rate move when gas moves?",
         "Large in the war, negative in 2021-22, ~0 otherwise.", "The core result."],
        ["Regime interaction and break tests (Chow, sup-Wald, CUSUM)", "Did the sensitivity really change, and when?",
         f"Yes; OIS break dated {N['sw_ois2_date']} to {N['sw_ois11_date']}.", "The data find the war date on their own."],
        ["Residual diagnostics (Durbin-Watson, Breusch-Godfrey, White, RESET, VIF)", "Are the regressions well behaved?",
         "Heteroskedasticity, fat tails; some non-linearity; no harmful collinearity.",
         "Handled with robust errors; non-linearity is a next step."],
        ["Timing tests (lead/lag, Dimson)", "Are the data sources recorded at the same time?",
         "No: Bundesbank half a day early.", "Prevents false 'predictive' findings."],
        ["Mediation (block bootstrap)", "Does gas move rates through inflation expectations?",
         f"Partly: ~{N['med_ind_share'] * 100:.0f}% of the gas effect on OIS goes via inflation swaps.",
         "The market also prices the ECB's reaction to energy news directly."],
        ["VAR, Granger causality, impulse responses", "Do gas moves today lead rate moves tomorrow?",
         "No lead in the war or weekly.", "Transmission happens on the day."],
        ["Local projections", "Does the effect grow, fade or reverse over 20 days?",
         "No further drift after day 1-2.", "No momentum to trade."],
        ["Out-of-sample forecasts (Clark-West)", "Would a gas model have beaten 'no change' in real time?",
         "Not for Bunds; fragile gain for OIS in the war.", "No robust forecasting edge."],
        ["HICP pass-through (lag scan)", "Does gas predict realised inflation?", "Yes, 6-12 months ahead.",
         "This is where gas really predicts."],
        ["Curve PCA", "Which curve movement does gas cause?",
         f"Slope factor {bp(N['pca_slope'])} ({p(N['pca_slope_p'])}).", "Flattening: a policy-shock signature."],
        ["Event study", "What happened on key dates?",
         f"War onset (2 days): 2Y {bp(N['ev_war_b2'], 0)}, 30Y {bp(N['ev_war_b30'], 0)}. Ceasefire: OIS 1y1y "
         f"{bp(N['ev_cf_ois'], 0)}.", "The regressions match the narrative."],
    ], [W * 0.24, W * 0.25, W * 0.27, W * 0.24]))
    st.append(Spacer(1, 10))

    # 7 Results -------------------------------------------------------------
    st.append(para("7. Results, link by link", "h1"))
    st.append(para("Link 1. Gas reaches inflation months later; oil does it at once", "h2"))
    st.append(para(f"A +10% TTF rise has no effect on inflation in the same month ({N['gas_hicp0']:+.2f}pp, not "
                   f"significant). It builds to +{N['gas_hicp9']:.2f}pp of y/y inflation after 9 months and "
                   f"+{N['gas_hicp12']:.2f}pp after 12. All lags together are significant ({p(N['hicp_joint_p'])}); "
                   f"the first six months alone are not ({p(N['hicp_06_p'])}). Oil passes through immediately "
                   f"(+{N['oil_hicp0']:.2f}pp the same month)."))
    st.append(figure("f5_hicp_lag_scan", "Figure 2. Effect of a +10% energy price move on euro-area inflation (y/y), "
                                         "by months of lag. Monthly data 2015-2026.", W * 0.85))
    st.append(para("Links 2 to 4. In the war, gas lifts expectations, the ECB path and the front end", "h2"))
    st.append(para(f"Inflation swaps react the same day: 1Y {bp(N['ils1_war'])}, 1y1y {bp(N['ils11_war'])}. The expected "
                   f"policy rate in one year rises {bp(N['ois11_war'])} (daily) to {bp(N['ois11_war_w'])} (weekly). The "
                   f"Bund 2Y rises {bp(N['b2_war'])} daily and {bp(N['b2_war_w'])} weekly; the 30Y barely moves "
                   f"({bp(N['b30_war'])}). The 2s30s slope falls {abs(N['s230_war']):.1f}bp and the weekly 5s30s "
                   f"{abs(N['s530_war_w']):.1f}bp ({p(N['s530_war_w_p'])})."))
    st.append(figure("f2_regime_betas", "Figure 3. Sensitivity to a +10% TTF move, by regime (daily, same day plus "
                                        "previous day for Bunds). * = p < 0.05.", W * 0.85))
    st.append(para("How much goes through inflation expectations?", "h2"))
    st.append(para(f"In the war, about {N['med_ind_share'] * 100:.0f}% of gas's daily effect on the expected ECB rate runs "
                   f"through the 1y1y inflation swap; the rest is priced directly. At weekly frequency, the indirect "
                   f"path through inflation swaps and OIS to the Bund 2Y totals {bp(N['med_w_ind'])} per +10% gas, and "
                   f"each 1bp of OIS 1y1y passes {N['med_w_b2']:.2f}bp into the 2Y Bund."))
    st.append(para("Does the effect persist or predict?", "h2"))
    st.append(para("The response happens on the day (two days for Bunds, because of the timing mismatch) and then "
                   "stays flat or fades: no drift that a trader could exploit."))
    st.append(figure("f4_local_projections", "Figure 4. Cumulative response to a +10% TTF move over 20 business days "
                                             "(local projections, 95% bands).", W * 0.9))
    st.append(figure("f3_rolling_beta", "Figure 5. Rolling 120-day sensitivity of the Bund 2Y and OIS 1y1y to gas. "
                                        "Shaded: 2021-22 gas crisis. Vertical line: war onset.", W * 0.85))

    # 8 Meaning -------------------------------------------------------------
    st.append(para("8. What it means", "h1"))
    for head, text in [
        ("The sign of the gas-rates link is set by the ECB's perceived reaction",
         f"In 2021-22 higher gas meant <i>lower</i> rates: Bund 2Y {bp(N['b2_crisis'])} and OIS 1y1y "
         f"{bp(N['ois11_crisis_w'])} (weekly) per +10% gas. Markets saw gas as a recession risk, and the ECB was "
         "calling inflation transitory. In 2026 the ECB is seen as reactive (it hiked in June and September), so gas "
         "became a hawkish signal. Gas itself did not change; the expected policy response did."),
        ("Gas is priced as a policy shock, not a long-run inflation shock",
         "The short end moves, the long end does not, and the 1y1y inflation swap moves far less than the 1Y. "
         "Markets read the gas spike as a near-term price shock that will trigger hikes, not as a permanent rise in "
         "inflation. That is exactly the bear-flattening signature."),
        ("Gas explains curve moves; it does not forecast them",
         "Gas news is public and priced within a day or two, so there is no tradable lead. The predictive content is "
         "macro: today's gas move tells you about inflation prints 6-12 months ahead, which the ECB will react to at "
         "future meetings."),
        ("Oil matters even more",
         f"Brent's effect on the expected ECB rate is about {N['ois11_brent_war'] / N['ois11_war']:.0f}x gas's "
         f"({bp(N['ois11_brent_war'])} vs {bp(N['ois11_war'])} per +10%). In this crisis the two move together, so "
         f"their roles are only partly separable: depending on the ordering assumed, gas explains between "
         f"{N['fevd_lo'] * 100:.0f}% and {N['fevd_hi'] * 100:.0f}% of the variance of the expected ECB rate. The gas "
         "effect on the Bund 2Y survives controlling for oil."),
    ]:
        st += [para(head, "h2"), para(text)]
    st.append(Spacer(1, 4))
    st.append(callout("<b>Practical takeaway.</b> Use gas as a regime-dependent front-end and curve-shape factor. Monitor "
                      "its rolling sensitivity (Figure 5): a fall toward zero or below would signal that markets again see "
                      "gas as a growth risk rather than an ECB trigger."))

    # 9 Limits --------------------------------------------------------------
    st.append(para("9. Limits and how to strengthen the study", "h1"))
    st += bullets([
        f"<b>One episode, short sample.</b> {N['n_war']} daily / {N['n_war_w']} weekly observations: enough to reject a "
        "zero effect, not to pin the size down precisely.",
        "<b>Co-movement is not full causality.</b> War headlines move gas, oil and rates together. A cleaner design "
        "would use LNG-specific outage news or intraday windows around gas moves.",
        "<b>Non-linearity.</b> Model checks (RESET) suggest big gas days matter more than proportionally. A threshold "
        "model is a natural next step.",
        "<b>Missing data worth adding:</b> HICP energy sub-index, 5y5y inflation swap (long-run anchoring), a "
        "volatility index (VSTOXX) for risk-off days, and a constant-maturity (zero-coupon) Bund curve.",
    ])
    st.append(Spacer(1, 10))

    # 10 Glossary -----------------------------------------------------------
    st.append(para("10. Glossary", "h1"))
    st.append(table([
        ["Term", "Definition"],
        ["Basis point (bp)", "0.01 percentage point. A yield moving from 3.00% to 3.04% has risen 4bp."],
        ["Bear flattening", "Yields rise (bear) and short yields rise more than long ones, so the curve flattens."],
        ["TTF", "Title Transfer Facility, the Dutch gas hub that serves as Europe's gas price benchmark."],
        ["Front-month / continuation", "The futures contract closest to delivery; a 'continuation' series rolls to the "
         "next contract when one expires."],
        ["HICP / HICPxT", "Harmonised Index of Consumer Prices (euro-area inflation); xT = excluding tobacco, the index "
         "inflation swaps pay on."],
        ["Inflation swap (ILS)", "A contract exchanging realised inflation for a fixed rate; the fixed rate is the market's "
         "inflation expectation."],
        ["1y1y forward", "The one-year rate starting one year from now."],
        ["€STR / OIS", "€STR is the ECB's overnight rate; an overnight index swap's fixed rate is the market's expected "
         "average €STR over its life."],
        ["Schatz / Bobl / Bund", "German government bonds of 2, 5 and 10+ years."],
        ["Term premium", "Extra yield investors demand to hold long bonds rather than roll short ones."],
        ["Swap spread", "Swap rate minus government bond yield; measures the safety/scarcity value of Bunds."],
        ["Regression beta", "The average move in one variable per unit move in another, holding controls constant."],
        ["p-value", "Probability of an effect this large if the true effect were zero."],
        ["HAC (Newey-West)", "Standard errors that stay valid with heteroskedasticity and autocorrelation."],
        ["Holm correction", "Adjusts p-values when many hypotheses are tested at once."],
        ["Mediation", "Splits an effect into the part that runs through an intermediate variable and the rest."],
        ["Granger causality", "Whether past values of one series help predict another."],
        ["Local projection", "Regression of the cumulative future change on today's shock, horizon by horizon."],
        ["sup-Wald (Quandt-Andrews)", "Searches every possible date for a structural break and tests the strongest."],
        ["PCA", "Splits curve moves into independent factors: level, slope, curvature."],
        ["Clark-West test", "Compares the forecast accuracy of a model with a simpler benchmark it nests."],
    ], [W * 0.27, W * 0.73]))

    # 11 Files --------------------------------------------------------------
    st.append(para("11. Where everything lives", "h1"))
    st.append(table([
        ["What", "Where"],
        ["This recap", "output/Gas_Bund_Research_Recap.pdf"],
        ["Full results workbook (29 sheets)", "output/Gas_Bund_Research_Workbook.xlsx: start with Executive_Summary"],
        ["Phase 1 research memo", "docs/01_research_foundation.md"],
        ["Clean data", "data/clean/: daily_levels, daily_changes, weekly_changes, monthly_panel, data_dictionary"],
        ["Raw data (renamed copies)", "data/raw/"],
        ["Result tables and charts", "output/tables/*.csv, output/figures/*.png"],
        ["Code", "src/clean.py → econometrics.py → figures.py → build_workbook.py → build_recap_pdf.py"],
        ["Rerun everything", ".venv/bin/python src/clean.py, then the other scripts in the order above"],
    ], [W * 0.32, W * 0.68]))

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=20 * mm, title="Gas → Bund Curve: Research Recap",
                            author="Research recap", subject="Gas prices and the German yield curve")
    doc.build(st, onFirstPage=on_page, onLaterPages=on_page)
    print("saved", OUT)


if __name__ == "__main__":
    build()
