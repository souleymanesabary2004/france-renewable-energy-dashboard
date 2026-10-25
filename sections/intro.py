"""Chapter 1 - hook, context, audience and how to read the story."""
from pathlib import Path

import streamlit as st

from utils import io, config as cfg
from sections.common import n


def render(ctx):
    nat = ctx["nat_all"].set_index("year")
    y0, y1 = ctx["y_min"], ctx["y_max"]
    s0, s1 = nat.loc[y0, "renewable_share_pct"], nat.loc[y1, "renewable_share_pct"]
    r0, r1 = nat.loc[y0, "renewable_gwh"] / 1000, nat.loc[y1, "renewable_gwh"] / 1000
    nu0, nu1 = nat.loc[y0, "nuclear_gwh"] / 1000, nat.loc[y1, "nuclear_gwh"] / 1000

    st.markdown("### Why it matters")
    st.markdown(
        f"**France produced {n(r1 - r0)} TWh more renewable electricity in {y1} than in {y0}** "
        f"({n(r0)} to {n(r1)} TWh), so the renewable share of the electricity produced went from "
        f"**{s0:.1f} % to {s1:.1f} %**. Over the same period nuclear production changed by {n(nu1 - nu0)} TWh. "
        "But a national number hides the real question of this story: **are all French regions moving "
        "toward a renewable electricity future, and are they moving at the same speed?**")

    why = Path(__file__).resolve().parents[1] / "assets" / "why_this_topic.md"
    if why.exists():
        st.markdown("### Why I chose this topic")
        st.markdown(why.read_text(encoding="utf-8"))

    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("### Who this story is for")
        st.markdown(
            "- **Citizens and students** who hear that France is in energy transition and want to see where and how fast.\n"
            "- **Regional decision makers and analysts** who need to compare regions fairly and see what drives the change.\n\n"
            "**Questions the dashboard answers**\n"
            "1. How much renewable electricity does France produce, and what drives the growth?\n"
            "2. What did the renewables replace in the mix?\n"
            "3. Which regions lead, which fall behind, and does the answer change if I look at *progress* instead of *level*?\n"
            "4. When in the year is the electricity renewable (seasons)?\n"
            "5. Are the regional gaps closing or widening?\n"
            "6. What if wind and solar keep growing at the same pace?")
    with c2:
        st.markdown("### How to read the numbers")
        st.markdown(
            "- **Level** = renewable share of a region's electricity *production* in a year.\n"
            "- **Progress** = change of this share since the first year you selected, in percentage points.\n"
            "- **New sources** = wind + solar + bioenergy (hydro is old and depends on rain).\n"
            "- A share is a share of *production*, not of consumption.\n"
            "- National shares are **weighted** (sums of GWh), not averages of regional percentages.")
        st.caption("Use the sidebar to change the years, the regions or the indicator: every chart and KPI follows your filters.")

    st.markdown("### The data in one glance")
    t = ctx["tables"]
    clean = t["cleaned_dataset"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Region-months", n(len(clean)), help="13 metropolitan regions x 144 months (2014-01 to 2025-12)")
    c2.metric("Regions", clean["region_code"].nunique())
    c3.metric("Sources", len(cfg.SOURCES), help="nuclear, thermal, hydro, wind, solar, bioenergy (GWh per month)")
    c4.metric("Period", f"{y0}-{y1}")
    st.markdown(io.LICENSE_TEXT)
    st.markdown(f"Dataset page: [{io.DATASET_TITLE}]({io.DATASET_PAGE})")
    st.caption("Chapters: 2 France (what changed) - 3 Regions (who moves) - 4 Seasons and gaps - 5 What if - 6 Conclusions - Data and quality.")
