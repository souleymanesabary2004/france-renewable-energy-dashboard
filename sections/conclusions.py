"""Chapter 6 - insights, implications, next steps, limits."""
import numpy as np
import streamlit as st

from utils import analysis, config as cfg, io
from sections.common import n


def render(ctx):
    nat, reg, y0, y1 = ctx["nat"], ctx["reg"], ctx["y0"], ctx["y1"]
    a, b = nat.set_index("year").loc[y0], nat.set_index("year").loc[y1]
    src = analysis.source_table(nat, y0, y1).set_index("source")
    nuc, the = src.loc["Nuclear", "added_twh"], src.loc["Thermal", "added_twh"]
    new_add = src.loc[[cfg.LABEL[s] for s in cfg.NEW_RENEWABLES], "added_twh"].sum()

    st.markdown("### What the data says (numbers follow your filters)")
    pts = [f"**The renewable share {('rose' if b['renewable_share_pct'] > a['renewable_share_pct'] else 'fell')} from {a['renewable_share_pct']:.1f} % to {b['renewable_share_pct']:.1f} %** "
           f"between {y0} and {y1}; wind, solar and bioenergy add {new_add:+.1f} TWh while hydro moves by {src.loc['Hydro', 'added_twh']:+.1f} TWh.",
           (f"**Renewables took the place of nuclear more than of fossil fuel**: nuclear {nuc:+.1f} TWh, thermal {the:+.1f} TWh." if abs(nuc) > abs(the) and nuc < 0
            else f"**Renewables mostly replaced thermal**: thermal {the:+.1f} TWh, nuclear {nuc:+.1f} TWh.")]
    if len(reg) >= 4:
        top, gp = reg.sort_values("share1", ascending=False), reg.sort_values("gain", ascending=False)
        pts.append(f"**Level is not progress.** Highest shares: {', '.join(top.head(3)['region'])}. Biggest gains: {', '.join(gp.head(3)['region'])}. "
                   "Regions without nuclear start from a much higher level.")
        g = analysis.gap_table(ctx["ann"], ctx["has_nuc"])
        if len(g) > 1:
            d = g.iloc[-1]["std"] - g.iloc[0]["std"]
            pts.append(f"**The regional gap {'widens' if d > 0.5 else 'narrows' if d < -0.5 else 'is about stable'}** (standard deviation of the regional shares {g.iloc[0]['std']:.1f} to {g.iloc[-1]['std']:.1f} points); "
                       f"for wind + solar + bioenergy it goes from {g.iloc[0]['std_new']:.1f} to {g.iloc[-1]['std_new']:.1f}.")
    pts.append("**Renewable production has a season**: solar peaks in summer and wind in winter, so the yearly share hides a monthly rhythm.")
    for p in pts:
        st.markdown(f"- {p}")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Implications")
        st.markdown(
            "- **Compare regions on progress as well as level**: a ranking by level mostly separates regions with and without nuclear plants.\n"
            "- **Look at the sources, not only the total**: the change is driven by wind and solar; hydro follows the weather.\n"
            "- **Gaps between regions are a policy question**: if they widen, national averages hide regions that are not moving.\n"
            "- **Seasons matter**: complementarity of wind and solar helps, but the data cannot say how much storage or flexibility is needed.")
    with c2:
        st.markdown("### Next steps")
        st.markdown(
            "- Add installed capacity and connection queues to link production to investment.\n"
            "- Add regional consumption to move from share of *production* to share of *consumption*.\n"
            "- Add hourly data to study complementarity and storage needs.\n"
            "- Add CO2 intensity and prices to connect the transition to climate and cost.")

    st.markdown("### Limits and ethics")
    st.markdown(
        "- The file contains **production only** (no consumption, imports, exports, capacity or prices); shares are shares of production.\n"
        "- Values are **net production**: 34 negative values exist and are set to 0 in the shares (0.0001 % of the energy).\n"
        "- **Weather** (rain, wind, sun) moves yearly values; compare several years before concluding.\n"
        "- With **13 regions**, quadrants and correlations are descriptive; I do not claim causality (policy, installations and demand are not in the data).\n"
        "- The classification of regions with nuclear is derived from the data (empty nuclear column), not from an external list.\n"
        "- Only aggregated regional data is used: no personal data and no re-identification risk.")
    st.caption(io.CITATION)
