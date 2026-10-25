"""Feature dictionary: formula, business meaning and use for the research question.

The order of the entries is the column order of the exported datasets.
"""
import pandas as pd

from . import config as cfg

_COLS = ["feature", "group", "unit", "formula", "business_meaning", "research_value"]
_E = []


def _add(feature, group, unit, formula, meaning, value):
    _E.append((feature, group, unit, formula, meaning, value))


# ------------------------------------------------------------ identifiers
_add("date", "Identifier", "date", "first day of the month, parsed from the text column 'mois' (YYYY-MM)",
     "Month of the observation.", "Time axis of every trend and of the date-range filter.")
_add("year_month", "Identifier", "text", "date formatted as YYYY-MM", "Readable month label.",
     "Used in tooltips and tables.")
_add("region_code", "Identifier", "text (2 digits)", "INSEE region code, kept as text",
     "Stable key of a region.", "Join key between fact_energy, dim_region and the GeoJSON map.")
_add("region", "Identifier", "text", "official region name looked up from region_code",
     "Region name.", "Same label in every table, chart and filter.")
_add("region_label_raw", "Identifier", "text", "region name as written in the source file",
     "Original label, kept for traceability.", "Shows that standardisation did not change the meaning of a region.")
_add("region_short", "Identifier", "text", "short label from dim_region (ARA, BFC, IDF, ...)",
     "Compact region label.", "Readable labels on the map and in small multiples.")

# ------------------------------------------------------------ time
_add("year", "Time", "year", "year of date", "Calendar year.", "Before/after comparison 2014 vs 2025 and annual aggregation.")
_add("month", "Time", "1-12", "month of date", "Calendar month.", "Seasonal profile of each source.")
_add("quarter", "Time", "1-4", "quarter of date", "Calendar quarter.", "Coarser seasonal view for small multiples.")
_add("season", "Time", "text", "winter = Dec-Feb, spring = Mar-May, summer = Jun-Aug, autumn = Sep-Nov",
     "Meteorological season.", "Solar peaks in summer, wind and hydro in winter and spring: comparing seasons "
                               "avoids reading a seasonal swing as a trend.")

# ------------------------------------------------------------ base production
for s in cfg.SOURCES:
    extra = " NaN replaced by 0 in the regions that have no nuclear plant (structural zero)." if s == "nuclear" else ""
    _add(cfg.GWH[s], "Base production", "GWh", f"{cfg.LABEL[s].lower()} production of the region in the month, from the source file; negative values set to 0 in the feature dataset (raw value in cleaned_dataset, row flagged)." + extra,
         f"Electricity produced from {cfg.LABEL[s].lower()} in one region and one month.",
         "Raw material of all shares, growth rates and scores.")

# ------------------------------------------------------------ production metrics
_add("total_gwh", "Production metrics", "GWh", "nuclear + thermal + hydro + wind + solar + bioenergy",
     "Total electricity produced in the region.", "Denominator of every share; size of the regional system.")
_add("renewable_gwh", "Production metrics", "GWh", "hydro + wind + solar + bioenergy",
     "All renewable production.", "Headline KPI of the transition.")
_add("new_renewables_gwh", "Production metrics", "GWh", "wind + solar + bioenergy",
     "Renewables without hydro.", "Hydro is old and depends on rain: this isolates the part that is really growing.")

# ------------------------------------------------------------ shares
_add("renewable_share_pct", "Shares", "% of production", "renewable_gwh / total_gwh x 100",
     "Part of regional production that is renewable.", "Main progress indicator for the research question.")
_add("new_renewables_share_pct", "Shares", "% of production", "new_renewables_gwh / total_gwh x 100",
     "Part of production from wind, solar and bioenergy.", "Shows the transition without the hydro baseline.")
for s, lab in [("solar", "solar"), ("wind", "wind"), ("hydro", "hydro"), ("bioenergy", "bioenergy"),
               ("nuclear", "nuclear"), ("thermal", "thermal (fossil)")]:
    why = {"solar": "Links the dashboard to the solar story told in the introduction.",
           "wind": "Compares the wind regions with the solar regions.",
           "hydro": "Shows how much of the renewable share is the historical hydro base.",
           "bioenergy": "Small source, shown for completeness of the mix.",
           "nuclear": "Explains why regions without nuclear have a different starting point.",
           "thermal": "Tracks the fossil part that the transition has to replace."}[s]
    _add(f"{s}_share_pct", "Shares", "% of production", f"{s}_gwh / total_gwh x 100",
         f"Part of regional production that comes from {lab}.", why)
_add("low_carbon_share_pct", "Shares", "% of production", "(renewable_gwh + nuclear_gwh) / total_gwh x 100",
     "Part of production that does not burn fossil fuel.", "French context: separates 'renewable' from 'low carbon'.")

# ------------------------------------------------------------ growth
_add("monthly_growth_pct", "Growth", "%", "(total_gwh - total_gwh one month before) / total_gwh one month before x 100",
     "Month-on-month change of total production.", "Descriptive only: strongly seasonal, not used for conclusions.")
_add("yearly_growth_pct", "Growth", "%", "(total_gwh - same month one year before) / same month one year before x 100",
     "Year-on-year change of total production.", "Context: is the whole system growing or shrinking.")
for name, col, lab, why in [
        ("renewable_growth_pct", "renewable_gwh", "renewable production", "Speed of renewable growth, season removed."),
        ("new_renewables_growth_pct", "new_renewables_gwh", "wind + solar + bioenergy production", "Speed of the real transition."),
        ("solar_growth_pct", "solar_gwh", "solar production", "How fast solar grows region by region."),
        ("wind_growth_pct", "wind_gwh", "wind production", "How fast wind grows region by region.")]:
    _add(name, "Growth", "%", f"({col} - same month one year before) / same month one year before x 100",
         f"Year-on-year change of {lab}.", why + " Empty when the base month is 0 or less; noisy when the base is small.")

# ------------------------------------------------------------ rolling 12 months
for name, col, lab in [("rolling_12m_renewable", "renewable_gwh", "renewable"), ("rolling_12m_solar", "solar_gwh", "solar"),
                       ("rolling_12m_wind", "wind_gwh", "wind"), ("rolling_12m_new_renewables", "new_renewables_gwh", "wind + solar + bioenergy"),
                       ("rolling_12m_total", "total_gwh", "total")]:
    _add(name, "Rolling 12 months", "GWh", f"sum of {col} over the last 12 months of the region (empty before month 12)",
         f"Production of the last 12 months ({lab}).", "Removes seasonality; in December it equals the calendar year.")
for name, num, lab in [("renewable_share_12m_pct", "rolling_12m_renewable", "renewable"),
                       ("new_renewables_share_12m_pct", "rolling_12m_new_renewables", "wind + solar + bioenergy"),
                       ("solar_share_12m_pct", "rolling_12m_solar", "solar"), ("wind_share_12m_pct", "rolling_12m_wind", "wind")]:
    _add(name, "Rolling 12 months", "% of production", f"{num} / rolling_12m_total x 100",
         f"Smoothed share of {lab} production.", "Stable version of the share: base of the ranks and of the scores.")
_add("thermal_share_12m_pct", "Rolling 12 months", "% of production", "sum of thermal_gwh over 12 months / rolling_12m_total x 100",
     "Smoothed share of thermal production.", "Base of the fossil dependency score.")
_add("renewable_share_gain_12m_pts", "Rolling 12 months", "percentage points",
     "renewable_share_12m_pct - same value 12 months earlier", "Progress of the renewable share during the last year.",
     "Measures progress, not level: the right comparison between regions that start from different points.")
_add("new_renewables_share_gain_12m_pts", "Rolling 12 months", "percentage points",
     "new_renewables_share_12m_pct - same value 12 months earlier", "Progress of wind + solar + bioenergy during the last year.",
     "Same idea, without the hydro baseline.")

# ------------------------------------------------------------ ranking
for name, base, why in [
        ("region_rank_renewables", "renewable_share_12m_pct", "Who leads the renewable transition, month after month."),
        ("region_rank_solar", "solar_share_12m_pct", "Solar leaders and laggards."),
        ("region_rank_wind", "wind_share_12m_pct", "Wind leaders and laggards."),
        ("region_rank_growth", "renewable_share_gain_12m_pts", "Fastest progress of the last year (can differ from the level ranking).")]:
    _add(name, "Ranking", "rank 1-13", f"rank of {base} among the 13 regions in the same month, 1 = highest (ties share the lowest rank)",
         "Position of the region in the month.", why)

_add("region_rank_renewables_peer", "Ranking", "rank", "rank of renewable_share_12m_pct among the regions of the same group (with / without nuclear) in the same month",
     "Position of the region among comparable regions.",
     "Level of the renewable share mostly separates regions with and without nuclear; the peer rank compares like with like.")

# ------------------------------------------------------------ advanced
_add("mix_diversity_index", "Advanced", "0-1", "(1 - sum of squared source shares) / (1 - 1/6), negative values set to 0",
     "How balanced the monthly mix is: 0 = one source, 1 = six equal sources.", "A diverse mix is less dependent on one technology.")
_add("mix_diversity_12m", "Advanced", "0-1", "same formula on the 12-month sums of each source",
     "Smoothed diversity of the mix.", "Input of the transition score (no seasonal noise).")
_add("score_renewable", "Advanced", "0-100", "renewable_share_12m_pct scaled between the 1st and 99th percentile of the dataset",
     "Level component of the transition score.", "Stored so the app can re-weight the score (what-if).")
_add("score_new_renewables", "Advanced", "0-100", "new_renewables_share_12m_pct scaled the same way",
     "Wind, solar and bioenergy component.", "Rewards the part of the transition that is really new.")
_add("score_fossil_free", "Advanced", "0-100", "100 - fossil_dependency_score", "Low use of thermal production.",
     "Rewards regions that rely less on fossil generation.")
_add("score_diversity", "Advanced", "0-100", "mix_diversity_12m scaled between the 1st and 99th percentile",
     "Diversity component.", "Rewards balanced mixes.")
_add("energy_transition_score", "Advanced", "0-100",
     "0.35 x score_renewable + 0.30 x score_new_renewables + 0.20 x score_fossil_free + 0.15 x score_diversity (weights in config.py)",
     "One number for the state of the transition of a region (12-month basis, empty during the first 11 months).",
     "Allows a ranking and a map with a single colour scale; weights can be changed in the what-if section.")
_add("momentum_renewable", "Advanced", "0-100", "50 + 50 x renewable_share_gain_12m_pts / bound, limited to 0-100 (bound = largest 1st/99th percentile)",
     "Speed component on the renewable share.", "50 = no change, above 50 = progress.")
_add("momentum_new_renewables", "Advanced", "0-100", "same formula on new_renewables_share_gain_12m_pts",
     "Speed component on wind + solar + bioenergy.", "Same reading, without hydro.")
_add("renewable_momentum_score", "Advanced", "0-100", "0.5 x momentum_renewable + 0.5 x momentum_new_renewables",
     "Speed of the transition over the last 12 months (empty during the first 23 months).",
     "Separates regions that are already high from regions that are moving fast.")
_add("fossil_dependency_score", "Advanced", "0-100", "thermal_share_12m_pct scaled between the 1st and 99th percentile",
     "Relative dependence on thermal (fossil) production.", "The part of the system the transition has to replace.")

# ------------------------------------------------------------ flags
_add("has_nuclear", "Quality flag", "boolean", "False if nuclear was never reported for the region (144 of 144 months empty)",
     "Region with or without a nuclear plant.", "Explains different starting points between regions.")
_add("flag_nuclear_structural_zero", "Quality flag", "boolean", "nuclear value was empty and replaced by 0",
     "Row where nuclear = 0 comes from the cleaning rule.", "Keeps the rule visible and reversible.")
_add("flag_negative_value", "Quality flag", "boolean", "at least one source has a negative value",
     "Net production below zero in the month.", "Lets the app annotate or exclude these rows.")
_add("flag_extreme_value", "Quality flag", "boolean", "at least one source outside [Q1 - 3 x IQR, Q3 + 3 x IQR] computed on the region's own history",
     "Unusual value compared with the region's own history.", "Used to annotate charts, never to delete rows.")
_add("flag_missing_value", "Quality flag", "boolean", "a measure is still empty after cleaning",
     "Real missing value.", "Expected to be 0; kept as a safety net.")
_add("quality_flags", "Quality flag", "text", "list of the flags of the row separated by ';', or 'ok'",
     "Readable summary of the row quality.", "Filter and audit trail.")


def feature_dictionary():
    return pd.DataFrame(_E, columns=_COLS)


def feature_order():
    return [e[0] for e in _E]
