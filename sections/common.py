"""Small display helpers shared by the sections."""
import inspect

import streamlit as st

CHART_CONFIG = {"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 2},
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


_PARAMS = inspect.signature(st.plotly_chart).parameters


def chart(fig, alt, key):
    """Interactive plotly chart + a text alternative below it (accessibility).

    Works with old (use_container_width) and new (width="stretch") Streamlit versions."""
    if "width" in _PARAMS:
        st.plotly_chart(fig, config=CHART_CONFIG, key=key, width="stretch")
    else:
        st.plotly_chart(fig, config=CHART_CONFIG, key=key, use_container_width=True)
    st.caption(f"Text alternative: {alt}")


def headline(text):
    st.markdown(f"#### {text}")


def insight(text):
    st.info(f"**Key insight.** {text}")


def caution(text):
    st.warning(f"**Read with care.** {text}")


def n(x, nd=0):
    return f"{x:,.{nd}f}".replace(",", " ")


def trend_word(delta, up="rose", down="fell", tol=0.05):
    return up if delta > tol else down if delta < -tol else "stayed about the same"
