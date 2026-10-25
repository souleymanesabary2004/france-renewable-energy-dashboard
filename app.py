"""Data-storytelling dashboard: French regions and the renewable electricity transition.

Run:  streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from utils import analysis, config as cfg, io
from sections import conclusions, deep_dives, intro, overview, quality, whatif
from sections.common import n

ROOT = Path(__file__).resolve().parent
SEEDS = json.loads((ROOT / "seeds.json").read_text(encoding="utf-8")) if (ROOT / "seeds.json").exists() else {"seed": 42}

st.set_page_config(page_title="French regions and the renewable electricity transition", page_icon="⚡", layout="wide")


@st.cache_data(show_spinner="Loading the processed tables...")
def get_data():
    return io.load_data()


@st.cache_data(show_spinner=False)
def get_national(annual):
    return analysis.national(annual)


try:
    T = get_data()
except Exception as e:                                                  # no processed data and no raw file
    st.error("The processed data is not available and could not be built.")
    st.code(f"{type(e).__name__}: {e}")
    st.markdown("Run `python -m utils.io build` once (it downloads the raw file from data.gouv.fr), then reload this page.")
    st.stop()

annual, feat, dimr = T["annual_region_summary"], T["feature_engineered_dataset"], T["dim_region"]
Y_MIN, Y_MAX = int(annual["year"].min()), int(annual["year"].max())
NAME = dict(zip(dimr["region_code"], dimr["region"]))
HAS_NUC = dimr.set_index("region_code")["has_nuclear"].to_dict()

# ------------------------------------------------------------------ sidebar
INDICATORS = list(deep_dives.INDICATORS)
with st.sidebar:
    st.header("Filters")
    years = st.slider("Years", Y_MIN, Y_MAX, (Y_MIN, Y_MAX), help="First and last year compared in the story. Levels are annual values; progress is the change between the two years.")
    group = st.radio("Regions", ["All", "Without nuclear plant", "With nuclear plant"], help="6 of the 13 regions have no nuclear plant: their starting point is very different.")
    pool = [c for c in dimr.sort_values("region")["region_code"] if group == "All" or (group.startswith("Without") and not HAS_NUC[c]) or (group.startswith("With ") and HAS_NUC[c])]
    chosen = st.multiselect("Choose regions", [NAME[c] for c in pool], default=[NAME[c] for c in pool], key=f"regions_{group}",
                            help="Remove regions to focus; KPIs and charts update.")
    indicator = st.selectbox("Indicator on the map and ranking", INDICATORS, help="Level and progress rank the regions differently: switch to compare.")
    st.divider()
    st.caption(f"Source: {io.DATASET_TITLE}, data.gouv.fr (RTE / ODRE), Licence Ouverte 2.0.")
    st.caption("Individual project, EFREI Paris, Data Storytelling 2026.")

y0, y1 = years
if y1 <= y0:
    st.warning("Choose two different years in the sidebar to compare a start and an end.")
    st.stop()
codes = [c for c in dimr["region_code"] if NAME[c] in chosen]
if not codes:
    st.warning("Select at least one region in the sidebar.")
    st.stop()

# ------------------------------------------------------------------ data for the selection
ann = annual[annual["region_code"].isin(codes) & annual["year"].between(y0, y1)]
feat_sel = feat[feat["region_code"].isin(codes) & feat["year"].between(y0, y1)]
nat = analysis.national(ann)
reg = analysis.region_summary(annual, feat, codes, y0, y1)
ctx = dict(tables=T, annual=annual, feat=feat, geo=T["geojson"], codes=codes, y0=y0, y1=y1, y_min=Y_MIN, y_max=Y_MAX, ann=ann, feat_sel=feat_sel,
           nat=nat, nat_all=get_national(annual), reg=reg, indicator=indicator, has_nuc=HAS_NUC, seed=SEEDS["seed"],
           data_version=int(len(feat) * 1000 + feat["renewable_gwh"].sum()))

# ------------------------------------------------------------------ title and KPI header (tied to the filters)
st.title("French regions and the renewable electricity transition")
a, b = nat.set_index("year").loc[y0], nat.set_index("year").loc[y1]
st.caption(f"{len(codes)} region(s) selected, {y0} to {y1}. Every number below follows your filters.")
k = st.columns(6)
k[0].metric("Renewable production", f"{b['renewable_gwh'] / 1000:,.0f} TWh".replace(",", " "), f"{(b['renewable_gwh'] / a['renewable_gwh'] - 1) * 100:+.0f} % vs {y0}",
            help="Hydro + wind + solar + bioenergy, sum of the selected regions in the last year")
k[1].metric("Renewable share", f"{b['renewable_share_pct']:.1f} %", f"{b['renewable_share_pct'] - a['renewable_share_pct']:+.1f} pts vs {y0}",
            help="Renewable GWh / total GWh of the selected regions (weighted share)")
k[2].metric("Wind + solar + bioenergy", f"{b['new_renewables_share_pct']:.1f} %", f"{b['new_renewables_share_pct'] - a['new_renewables_share_pct']:+.1f} pts vs {y0}",
            help="The 'new' renewable sources, without hydro")
k[3].metric("Nuclear share", f"{b['nuclear_share_pct']:.1f} %", f"{b['nuclear_share_pct'] - a['nuclear_share_pct']:+.1f} pts vs {y0}", delta_color="off")
k[4].metric("Thermal (fossil) share", f"{b['thermal_share_pct']:.1f} %", f"{b['thermal_share_pct'] - a['thermal_share_pct']:+.1f} pts vs {y0}", delta_color="inverse")
k[5].metric("Production, all sources", f"{b['total_gwh'] / 1000:,.0f} TWh".replace(",", " "), f"{(b['total_gwh'] / a['total_gwh'] - 1) * 100:+.1f} % vs {y0}", delta_color="off")

# ------------------------------------------------------------------ the story, chapter by chapter
tabs = st.tabs(["1 · Why it matters", "2 · France: what changed", "3 · Regions: who moves", "4 · Seasons and gaps", "5 · What if", "6 · Conclusions", "Data and quality"])
with tabs[0]:
    intro.render(ctx)
with tabs[1]:
    overview.render(ctx)
with tabs[2]:
    deep_dives.render_regions(ctx)
with tabs[3]:
    deep_dives.render_time_gaps(ctx)
with tabs[4]:
    whatif.render(ctx)
with tabs[5]:
    conclusions.render(ctx)
with tabs[6]:
    quality.render(ctx)
