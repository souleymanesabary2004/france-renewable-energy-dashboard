"""Data quality and method (missingness, duplicates, validation checks, dictionary, licence)."""
import streamlit as st

from utils import io, quality, config as cfg
from sections.common import n


@st.cache_data(show_spinner=False)
def _checks(_tables, version):
    return quality.validation_checks(_tables)


def render(ctx):
    t = ctx["tables"]
    clean, feat, fact = t["cleaned_dataset"], t["feature_engineered_dataset"], t["fact_energy"]

    st.markdown("### Validation checks")
    chk = _checks(t, ctx["data_version"])
    ok = int((chk["status"] == "PASS").sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Checks passed", f"{ok} / {len(chk)}")
    c2.metric("Region-months", n(len(clean)))
    c3.metric("Duplicates", int(clean.duplicated(['region_code', 'date']).sum()), help="Duplicated region-month keys")
    st.dataframe(chk, hide_index=True, column_config={"status": st.column_config.TextColumn("status", width="small")})
    st.caption("Computed when the app loads, from the processed tables. The full audit of the raw file is in notebooks 01 and 02.")

    st.markdown("### Missing values, anomalies and what I did")
    st.dataframe(quality.missingness(clean, fact), hide_index=True)
    st.markdown("**Missingness rule.** The 864 empty nuclear values are not holes: they belong to six regions that never report nuclear (all 144 months empty in each). "
                "A missing value therefore means 'no nuclear production' and is set to 0 GWh with a flag. No other value is imputed.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Duplicates**")
        st.dataframe(quality.duplicates(clean, fact), hide_index=True)
    with c2:
        st.markdown("**Empty cells left in the feature table**")
        st.dataframe(quality.column_missing(feat))
    st.caption("Empty cells in the features are by design: 12-month windows need 12 months (24 for gains), growth needs a previous period.")

    st.markdown("### Method and assumptions")
    st.markdown(
        "- **Classification**: renewables = hydro + wind + solar + bioenergy; *new sources* = wind + solar + bioenergy; this grouping is an assumption set in `utils/config.py`.\n"
        "- **Shares** = source / total production of the region and month (negative net values set to 0 in the feature table).\n"
        "- **12-month windows** are used for levels, ranks and scores (in December they equal the calendar year).\n"
        f"- **Transition score** (0-100) = {', '.join(f'{k} {v:.0%}' for k, v in cfg.WEIGHTS_TRANSITION.items())}; each component is scaled between the 1st and the 99th percentile. "
        "**Momentum score** centres the 12-month gain of the shares on 50.\n"
        "- **Extreme values**: 3 x IQR of the region's own history (flag only, no deletion).\n"
        "- **Reproducibility**: `python -m utils.io build` downloads the raw file and rebuilds every table with the same code as notebook 02.")
    with st.expander("Feature dictionary (every column of the feature table)"):
        st.dataframe(t["feature_dictionary"], hide_index=True)
    with st.expander("Source, licence and citation"):
        st.markdown(io.LICENSE_TEXT)
        st.markdown(f"Dataset page: {io.DATASET_PAGE}")
        st.code(io.CITATION, language=None)
