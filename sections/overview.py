"""Chapter 2 - France: what changed (selected regions and years)."""
import pandas as pd
import streamlit as st

from utils import analysis, config as cfg, viz
from sections.common import chart, headline, insight, caution, n, trend_word


def render(ctx):
    nat, y0, y1 = ctx["nat"], ctx["y0"], ctx["y1"]
    a, b = nat.set_index("year").loc[y0], nat.set_index("year").loc[y1]
    src = analysis.source_table(nat, y0, y1).set_index("source")
    new_add = src.loc[[cfg.LABEL[s] for s in cfg.NEW_RENEWABLES], "added_twh"].sum()
    ren_add = (b["renewable_gwh"] - a["renewable_gwh"]) / 1000
    chg = (b["renewable_gwh"] / a["renewable_gwh"] - 1) * 100

    headline(f"Renewable output {trend_word(chg)} by {abs(chg):.0f} % between {y0} and {y1}, and wind and solar did most of the work")
    fig = viz.production_bars(nat)
    chart(fig, f"Stacked bars of renewable production in TWh per year from {y0} to {y1} by source (hydro, bioenergy, wind, solar) and a line of the renewable "
               f"share, which goes from {a['renewable_share_pct']:.1f} % to {b['renewable_share_pct']:.1f} %.", "ov_bars")

    c1, c2 = st.columns(2)
    with c1:
        headline("What replaced what in the mix?")
        d = pd.Series({cfg.LABEL[s]: b[f"{s}_share_pct"] - a[f"{s}_share_pct"] for s in cfg.SOURCES})
        fig = viz.change_bars(d, {cfg.LABEL[s]: cfg.COLOR[s] for s in cfg.SOURCES}, xtitle=f"Change of the share of production, {y0} to {y1} (points)")
        chart(fig, "Horizontal bars of the change of each source's share of production, in points. They add up to zero: " +
              ", ".join(f"{k} {v:+.1f}" for k, v in d.sort_values(ascending=False).items()) + ".", "ov_change")
    with c2:
        headline("Production by family (TWh)")
        fam = nat.assign(Renewables=nat["renewable_gwh"] / 1000, Nuclear=nat["nuclear_gwh"] / 1000, Thermal=nat["thermal_gwh"] / 1000)
        fig = viz.line_chart(fam, "year", {"Renewables": ("Renewables", "#0072B2"), "Nuclear": ("Nuclear", cfg.COLOR["nuclear"]), "Thermal": ("Thermal", cfg.COLOR["thermal"])},
                             ytitle="TWh per year", xtitle="Year", fmt=".0f", unit=" TWh")
        chart(fig, f"Lines of annual production in TWh for renewables ({a['renewable_gwh']/1000:.0f} to {b['renewable_gwh']/1000:.0f}), nuclear "
                   f"({a['nuclear_gwh']/1000:.0f} to {b['nuclear_gwh']/1000:.0f}) and thermal ({a['thermal_gwh']/1000:.0f} to {b['thermal_gwh']/1000:.0f}).", "ov_family")

    headline("Which source grows fastest? Rate and volume tell different things")
    tbl = src[["start_twh", "end_twh", "added_twh", "growth_pct_per_year", "share_change_pts"]].rename(columns={
        "start_twh": f"{y0} (TWh)", "end_twh": f"{y1} (TWh)", "added_twh": "Added (TWh)", "growth_pct_per_year": "Growth (% per year)", "share_change_pts": "Share change (pts)"})
    st.dataframe(tbl.round(1), column_config={c: st.column_config.NumberColumn(c, format="%.1f") for c in tbl.columns})
    ren = src.loc[[cfg.LABEL[s] for s in cfg.RENEWABLE]]
    fast, big = ren["growth_pct_per_year"].idxmax(), ren["added_twh"].idxmax()
    nuc, the = src.loc["Nuclear", "added_twh"], src.loc["Thermal", "added_twh"]
    insight(f"{fast} grows fastest ({ren.loc[fast, 'growth_pct_per_year']:.1f} % per year) and {big} adds the most electricity ({ren.loc[big, 'added_twh']:+.1f} TWh). "
            f"Wind, solar and bioenergy add {new_add:+.1f} TWh against a net renewable change of {ren_add:+.1f} TWh, because hydro moves by {src.loc['Hydro', 'added_twh']:+.1f} TWh. "
            f"In the same period nuclear changes by {nuc:+.1f} TWh and thermal by {the:+.1f} TWh, so " +
            ("the renewables mostly took the place of nuclear production, not of fossil production." if abs(nuc) > abs(the) and nuc < 0 else
             "the renewables mostly took the place of thermal production." if the < 0 else "the renewables grew next to the other sources."))
    with st.expander("A share can rise for two reasons: more renewables, or less of everything else"):
        cf = b["renewable_gwh"] / a["total_gwh"] * 100
        st.markdown(f"If total production had stayed at its {y0} level ({n(a['total_gwh'] / 1000)} TWh), the {y1} renewable output would be {cf:.1f} % of it, "
                    f"against {b['renewable_share_pct']:.1f} % observed: {b['renewable_share_pct'] - cf:+.1f} points of the change come from the change in total production. "
                    "This is why every share in this dashboard is shown next to a volume in TWh.")
    if len(ctx["codes"]) < 13:
        caution("You selected a subset of regions: the numbers are sums over these regions only.")
