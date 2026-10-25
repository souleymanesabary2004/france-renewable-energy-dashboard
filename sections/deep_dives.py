"""Chapters 3 and 4 - regions, seasons and regional gaps."""
import numpy as np
import pandas as pd
import streamlit as st

from utils import analysis, config as cfg, viz
from sections.common import chart, headline, insight, caution, n, trend_word

INDICATORS = {
    "Renewable share, end year (level)": dict(col="share1", unit=" %", scale="YlGn", zmid=None, title="Renewable share (%)", fmt=".1f"),
    "Progress: change of the renewable share since the first year (points)": dict(col="gain", unit=" pts", scale="PuOr", zmid=0, title="Change (points)", fmt="+.1f"),
    "Wind + solar + bioenergy share, end year": dict(col="new1", unit=" %", scale="YlGn", zmid=None, title="New-source share (%)", fmt=".1f"),
    "Transition score (0-100)": dict(col="transition_score", unit="", scale="YlGn", zmid=None, title="Score (0-100)", fmt=".0f"),
    "Momentum score (50 = no change)": dict(col="momentum_score", unit="", scale="PuOr", zmid=50, title="Score (50 = no change)", fmt=".0f"),
    "Thermal (fossil) share, end year": dict(col="thermal1", unit=" %", scale="Greys", zmid=None, title="Thermal share (%)", fmt=".1f"),
}


def render_regions(ctx):
    reg, y0, y1 = ctx["reg"].copy(), ctx["y0"], ctx["y1"]
    if len(reg) < 2:
        caution("Select at least two regions to compare them.")
        return
    top, gp = reg.sort_values("share1", ascending=False), reg.sort_values("gain", ascending=False)
    overlap = len(set(top.head(5).index) & set(gp.head(5).index)) if len(reg) >= 5 else None
    headline(f"Level and progress tell different stories: {top.iloc[0]['region']} has the highest share, {gp.iloc[0]['region']} moved the most")

    ind = INDICATORS[ctx["indicator"]]
    c1, c2 = st.columns([1.1, 1])
    with c1:
        fig = viz.map_chart(ctx["geo"], reg, ind["col"], colorbar_title=ind["title"], scale=ind["scale"], zmid=ind["zmid"], fmt=ind["fmt"],
                            extra=[(f"Share {y1}", "share1", ".1f"), ("Change (pts)", "gain", "+.1f"), ("Profile", "profile", "")], height=500)
        chart(fig, f"Map of the 13 regions coloured by: {ctx['indicator']}. Highest: {reg.sort_values(ind['col']).iloc[-1]['region']} "
                   f"({reg[ind['col']].max():{ind['fmt']}}); lowest: {reg.sort_values(ind['col']).iloc[0]['region']} ({reg[ind['col']].min():{ind['fmt']}}).", "rg_map")
    with c2:
        fig = viz.ranked_bars(reg, "region", ind["col"], group="has_nuclear", xtitle=ctx["indicator"], fmt=ind["fmt"], unit=ind["unit"], height=500)
        chart(fig, "Ranking of the regions on the same indicator; colour shows whether the region has a nuclear plant. "
                   "Regions without nuclear dominate the top of the level ranking.", "rg_rank")
    st.caption("Change the indicator in the sidebar. Green bars = regions without a nuclear plant, pink = with nuclear.")

    nuc_g = reg.groupby("has_nuclear")["share1"].mean()
    if len(nuc_g) == 2:
        insight(f"In {y1} the mean renewable share is {nuc_g[False]:.0f} % in regions without nuclear and {nuc_g[True]:.0f} % in regions with nuclear. "
                "A high *level* partly measures the absence of nuclear, so I always read it next to the *progress*."
                + (f" Only {overlap} region(s) are in the top 5 of both rankings." if overlap is not None else ""))

    headline("Four profiles of regions: level (x) against progress (y)")
    c1, c2 = st.columns([1.3, 1])
    with c1:
        fig = viz.quadrant_chart(reg, "share1", "gain", "total1", xtitle=f"Level: renewable share in {y1} (%)", ytitle=f"Progress: change since {y0} (points)",
                                 xline=reg["share1"].median() if len(reg) >= 4 else None, yline=reg["gain"].median() if len(reg) >= 4 else None)
        chart(fig, "Scatter of the regions: horizontal axis is the renewable share in the last year, vertical axis the change since the first year. Dashed lines are the medians; "
                   "bubble size is the production of the region.", "rg_quadrant")
    with c2:
        prof = reg.groupby("profile")["region"].apply(lambda s: ", ".join(sorted(s)))
        for k in ["Leader", "Catching up", "Resting on its level", "Lagging"]:
            if k in prof.index:
                st.markdown(f"**{k}**: {prof[k]}")
        if len(reg) >= 4:
            from scipy import stats
            rho = stats.spearmanr(reg["share0"], reg["gain"])
            st.markdown(f"Link between the starting share and the gain: Spearman **{rho.statistic:+.2f}** (p = {rho.pvalue:.2f}, {len(reg)} regions). " +
                        ("No clear catch-up: low starters do not systematically progress faster." if abs(rho.statistic) < 0.3 or rho.pvalue > 0.1
                         else "Regions that started low progress faster." if rho.statistic < 0 else "Regions that started high progress even faster."))
        st.caption("Medians of the selected regions are the cut-offs. With only a few regions the profiles are descriptive, not statistical.")
        big = gp.head(3)
        st.markdown("**Volume check (TWh)**: " + ", ".join(f"{r.region} {r.ren_added_twh:+.1f}" for r in big.itertuples()) +
                    ". A large gain in points can come from a small production, so the volume matters.")

    headline("When did each region move?")
    piv = ctx["ann"].pivot(index="region", columns="year", values="renewable_share_pct").loc[top["region"]]
    fig = viz.heatmap(piv, colorbar_title="Renewable share (%)", height=420)
    chart(fig, "Heatmap of the annual renewable share by region (rows, sorted by the last year) and year (columns).", "rg_heat")
    with st.expander("Start and end of the period for every region (dumbbell)"):
        fig = viz.dumbbell(reg, "region", "share0", "share1", xtitle="Renewable share (%)")
        chart(fig, "For each region, a segment between the share in the first year (empty marker) and in the last year (full marker).", "rg_dumbbell")

    headline("Region in focus")
    choice = st.selectbox("Choose a region", list(reg.sort_values("region")["region"]), key="focus_region")
    r = reg[reg["region"] == choice].iloc[0]
    code = r["region_code"]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"Renewable share {y1}", f"{r['share1']:.1f} %", f"{r['gain']:+.1f} pts since {y0}")
    k2.metric("Rank by level", f"{int(r['rank_level'])} / {len(reg)}")
    k3.metric("Rank by progress", f"{int(r['rank_gain'])} / {len(reg)}")
    k4.metric("Profile", r["profile"], help="Median split on the selected regions")
    one = ctx["ann"][ctx["ann"]["region_code"] == code]
    c1, c2 = st.columns(2)
    with c1:
        chart(viz.mix_area(one), f"Stacked area of the share of each source in {choice} from {y0} to {y1}.", "rg_focus_mix")
    with c2:
        rk = ctx["ann"].assign(rank=ctx["ann"].groupby("year")["renewable_share_pct"].rank(ascending=False, method="min"))
        rk = rk[rk["region_code"] == code]
        fig = viz.line_chart(rk, "year", {"Rank by renewable share (1 = best)": ("rank", "#0072B2")}, ytitle="Rank among the selected regions", xtitle="Year", fmt=".0f")
        fig.update_yaxes(autorange="reversed", dtick=1)
        chart(fig, f"Line of the rank of {choice} among the selected regions by year (1 is the highest renewable share).", "rg_focus_rank")


def render_time_gaps(ctx):
    feat_sel, ann, y0, y1 = ctx["feat_sel"], ctx["ann"], ctx["y0"], ctx["y1"]
    m = analysis.monthly_national(feat_sel)
    mm, prof = analysis.seasonal_tables(m)
    months = analysis.MONTHS
    pk, tr = int(mm.loc[mm["renewable_share_pct"].idxmax(), "month"]), int(mm.loc[mm["renewable_share_pct"].idxmin(), "month"])

    headline(f"Renewable electricity has a season: the share peaks in {months[pk - 1]} and is lowest in {months[tr - 1]}")
    fig = viz.seasonal_chart(mm)
    chart(fig, f"Stacked bars of the average monthly renewable production by source for each calendar month, with the renewable share as a line "
               f"(highest in {months[pk - 1]}: {mm['renewable_share_pct'].max():.1f} %, lowest in {months[tr - 1]}: {mm['renewable_share_pct'].min():.1f} %).", "tm_season")
    c1, c2 = st.columns([1.2, 1])
    with c1:
        headline("Sun in summer, wind in winter?")
        chart(viz.profile_chart(prof), "Lines of each renewable source's production relative to its average month, by calendar month.", "tm_profile")
    with c2:
        rho = float(np.corrcoef(prof["wind"], prof["solar"])[0, 1])
        peaks = {s: months[int(prof[s].idxmax()) - 1] for s in cfg.RENEWABLE}
        amp = {s: prof[s].max() / prof[s].min() for s in cfg.RENEWABLE}
        st.markdown("**Peak month**: " + ", ".join(f"{cfg.LABEL[s]} {peaks[s]}" for s in cfg.RENEWABLE))
        st.markdown("**Best month / weakest month**: " + ", ".join(f"{cfg.LABEL[s]} x{amp[s]:.1f}" for s in cfg.RENEWABLE))
        st.markdown(f"Correlation of the seasonal shapes of wind and solar: **{rho:+.2f}**.")
        insight(("Wind and solar are seasonal complements: when one is low the other is higher, which smooths the year." if rho < -0.3
                 else "In this selection wind and solar are not clear seasonal complements.") +
                " This is a monthly national picture: it says nothing about the hour of the day, storage or consumption.")
    tot = m.groupby("month")["total_gwh"].mean()
    st.caption(f"The share also depends on the total: production is lowest in {months[int(tot.idxmin()) - 1]}, so a month with little nuclear output "
               "can raise the renewable share without any new renewable capacity.")
    if len(m) >= 36:
        with st.expander("Seasonal decomposition of the renewable production (trend + season)"):
            dec = viz.decompose(m["renewable_gwh"] / 1000, 12)
            fs, ft = viz.strengths(dec)
            chart(viz.decomposition_chart(dec), f"Three panels: observed monthly renewable production, its 12-month trend and its seasonal component. Seasonal strength {fs:.2f}, trend strength {ft:.2f}.", "tm_dec")
            st.markdown(f"Seasonal strength **{fs:.2f}**, trend strength **{ft:.2f}** (0 = absent, 1 = dominant).")

    headline("Are the regional gaps closing?")
    if ann["region_code"].nunique() < 3:
        caution("Select at least three regions to measure the gaps between regions.")
        return
    gap = analysis.gap_table(ann, ctx["has_nuc"])
    s0, s1 = gap.iloc[0], gap.iloc[-1]
    c1, c2 = st.columns(2)
    with c1:
        fig = viz.line_chart(gap, "year", {"Std of the renewable share": ("std", "#0072B2"), "Range (max - min)": ("range", "#D55E00"), "Std of the wind+solar+bio share": ("std_new", "#009E73")},
                             title="Dispersion between regions", ytitle="Percentage points", xtitle="Year")
        chart(fig, f"Lines of the standard deviation and range of the regional renewable share by year: std {s0['std']:.1f} to {s1['std']:.1f} points, range {s0['range']:.0f} to {s1['range']:.0f}.", "gp_disp")
    with c2:
        series = {}
        if gap["without_nuclear"].notna().any():
            series["Regions without nuclear (mean)"] = ("without_nuclear", viz.GROUP_COLOR[False])
        if gap["with_nuclear"].notna().any():
            series["Regions with nuclear (mean)"] = ("with_nuclear", viz.GROUP_COLOR[True])
        fig = viz.line_chart(gap, "year", series, title="Two groups", ytitle="Renewable share (%)", xtitle="Year")
        chart(fig, "Lines of the mean renewable share of regions without nuclear and of regions with nuclear, by year.", "gp_groups")
    d_std = s1["std"] - s0["std"]
    d_new = s1["std_new"] - s0["std_new"]
    between = (s1["without_nuclear"] - s1["with_nuclear"]) if gap["without_nuclear"].notna().any() and gap["with_nuclear"].notna().any() else np.nan
    insight(f"The dispersion of the regional shares {'widens' if d_std > 0.5 else 'narrows' if d_std < -0.5 else 'is about stable'} ({s0['std']:.1f} to {s1['std']:.1f} points). "
            f"For the new sources it {'widens' if d_new > 0.5 else 'narrows' if d_new < -0.5 else 'is about stable'} ({s0['std_new']:.1f} to {s1['std_new']:.1f} points)."
            + ("" if np.isnan(between) else f" The gap between the two groups of regions is {between:.0f} points in {y1}."))
