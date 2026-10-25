"""Chapter 5 - what if: weights of the transition score and a simple scenario."""
import numpy as np
import pandas as pd
import streamlit as st

from utils import analysis, config as cfg, viz
from sections.common import chart, headline, insight, caution, n


def render(ctx):
    st.markdown("Two small experiments. Both use assumptions that are written on the page; they are **not forecasts**.")
    part_weights(ctx)
    st.divider()
    part_scenario(ctx)


def part_weights(ctx):
    headline("A. Does the ranking of the regions depend on the weights of the transition score?")
    st.markdown("The transition score (0-100) combines four components. I chose the default weights; move the sliders to test others "
                "(the weights are rescaled to add up to 100 %).")
    d = cfg.WEIGHTS_TRANSITION
    c = st.columns(4)
    w = {"renewable": c[0].slider("Renewable share", 0, 100, int(d["renewable"] * 100), 5, key="w_ren", help="Share of all renewables in the production"),
         "new_renewables": c[1].slider("Wind + solar + bioenergy share", 0, 100, int(d["new_renewables"] * 100), 5, key="w_new", help="Share of the new sources"),
         "fossil_free": c[2].slider("Low fossil dependency", 0, 100, int(d["fossil_free"] * 100), 5, key="w_fos", help="100 minus the scaled thermal share"),
         "diversity": c[3].slider("Diversity of the mix", 0, 100, int(d["diversity"] * 100), 5, key="w_div", help="Normalised Simpson index of the six sources")}
    tot = sum(w.values())
    if tot == 0:
        caution("At least one weight must be above zero.")
        return
    w = {k: v / tot for k, v in w.items()}
    r = analysis.transition_rank(ctx["feat"], ctx["y1"], w, ctx["codes"]).sort_values("score_custom", ascending=False)
    if len(r) < 2:
        caution("Select at least two regions.")
        return
    r["moved"] = r["rank_default"] - r["rank_custom"]
    from scipy import stats
    rho = stats.spearmanr(r["energy_transition_score"], r["score_custom"]).statistic
    c1, c2 = st.columns([1.2, 1])
    with c1:
        fig = viz.ranked_bars(r, "region", "score_custom", group="has_nuclear", xtitle=f"Transition score in {ctx['y1']} with your weights (0-100)", fmt=".0f", height=460)
        chart(fig, f"Ranking of the regions by the transition score with the weights chosen above. Correlation of the ranking with the default weights: {rho:.2f}.", "wi_rank")
    with c2:
        t = r[["region", "rank_default", "rank_custom", "moved"]].rename(columns={"rank_default": "Rank (default weights)", "rank_custom": "Rank (your weights)", "moved": "Places gained"})
        st.dataframe(t, hide_index=True)
        insight(f"With your weights the ranking keeps a Spearman correlation of {rho:.2f} with the default one and the largest move is {int(r['moved'].abs().max())} place(s). " +
                ("The ranking is robust to the choice of weights." if rho > 0.9 else "The ranking depends noticeably on the weights: I should say which weights I use."))
    st.caption("Components are computed in notebook 02 from 12-month shares and scaled between the 1st and the 99th percentile of the dataset (see Data and quality).")


def part_scenario(ctx):
    headline("B. What if the pace of the last years continued?")
    nat_all, y1_all = ctx["nat_all"], ctx["y_max"]
    hist = analysis.source_table(nat_all, ctx["y_min"], y1_all).set_index("key")
    st.markdown("Each source grows or shrinks at a constant yearly rate from the last observed year; hydro and thermal stay flat. "
                "France as a whole (13 regions) is used here, whatever the regional filter.")
    c = st.columns(4)

    def dflt(s):
        return float(np.clip(round(hist.loc[s, "growth_pct_per_year"]), -10, 30))
    g = {"wind": c[0].slider("Wind (% per year)", -10, 30, int(dflt("wind")), key="g_wind", help=f"Observed {ctx['y_min']}-{y1_all}: {hist.loc['wind', 'growth_pct_per_year']:.1f} % per year"),
         "solar": c[1].slider("Solar (% per year)", -10, 30, int(dflt("solar")), key="g_solar", help=f"Observed: {hist.loc['solar', 'growth_pct_per_year']:.1f} % per year"),
         "nuclear": c[2].slider("Nuclear (% per year)", -10, 10, int(np.clip(round(hist.loc["nuclear", "growth_pct_per_year"]), -10, 10)), key="g_nuc",
                                help=f"Observed: {hist.loc['nuclear', 'growth_pct_per_year']:.1f} % per year"),
         "bioenergy": c[3].slider("Bioenergy (% per year)", -10, 30, int(np.clip(round(hist.loc["bioenergy", "growth_pct_per_year"]), -10, 30)), key="g_bio",
                                  help=f"Observed: {hist.loc['bioenergy', 'growth_pct_per_year']:.1f} % per year")}
    horizon = st.slider("Horizon (year)", y1_all + 1, 2035, min(2030, 2035), key="horizon")
    sc = analysis.scenario(nat_all, y1_all, horizon, g)
    hist_s = nat_all.set_index("year")["renewable_share_pct"]
    fig = viz.scenario_chart({"hist": list(hist_s.index), "proj": list(sc["year"])}, list(hist_s.values), list(sc["renewable_share_pct"]))
    chart(fig, f"Line of the observed national renewable share until {y1_all} ({hist_s.iloc[-1]:.1f} %) and a dashed scenario line until {horizon} "
               f"({sc['renewable_share_pct'].iloc[-1]:.1f} %).", "wi_scen")
    last = sc.iloc[-1]
    k1, k2, k3 = st.columns(3)
    k1.metric(f"Renewable share {horizon}", f"{last['renewable_share_pct']:.1f} %", f"{last['renewable_share_pct'] - hist_s.iloc[-1]:+.1f} pts vs {y1_all}")
    k2.metric(f"Renewable production {horizon}", f"{last['renewable_gwh'] / 1000:.0f} TWh", f"{(last['renewable_gwh'] / nat_all.set_index('year').loc[y1_all, 'renewable_gwh'] - 1) * 100:+.0f} %")
    k3.metric(f"Total production {horizon}", f"{last['total_gwh'] / 1000:.0f} TWh", f"{(last['total_gwh'] / nat_all.set_index('year').loc[y1_all, 'total_gwh'] - 1) * 100:+.0f} %")
    with st.expander("Assumptions and limits of the scenario"):
        st.markdown("- Constant compound growth from the last observed year; hydro and thermal stay flat.\n"
                    "- No demand, capacity, policy, price or weather in the model: it only extends the arithmetic of the mix.\n"
                    "- A high growth rate on a small base cannot continue for long (solar and wind are still small in the mix).\n"
                    "- Read it as: *what the share would be if...*, never as *what will happen*.")
