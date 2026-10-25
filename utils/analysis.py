"""Small, testable aggregation functions used by the app (all start from the processed tables)."""
import numpy as np
import pandas as pd

from . import config as cfg, viz

GCOLS = list(cfg.GWH.values())
SUMS = GCOLS + ["total_gwh", "renewable_gwh", "new_renewables_gwh"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def add_shares(df):
    """Weighted shares from sums of GWh (never an average of percentages)."""
    df = df.copy()
    for s in cfg.SOURCES:
        df[f"{s}_share_pct"] = df[cfg.GWH[s]] / df["total_gwh"] * 100
    df["renewable_share_pct"] = df["renewable_gwh"] / df["total_gwh"] * 100
    df["new_renewables_share_pct"] = df["new_renewables_gwh"] / df["total_gwh"] * 100
    return df


def national(ann_sel):
    """Year table for the selected regions."""
    n = ann_sel.groupby("year", as_index=False)[SUMS].sum()
    return add_shares(n)


def source_table(nat, y0, y1):
    """Growth rate and volume added by source between two years (rate AND volume, never one alone)."""
    a, b = nat.set_index("year").loc[y0], nat.set_index("year").loc[y1]
    rows = []
    for s in cfg.SOURCES:
        c = cfg.GWH[s]
        rows.append({"source": cfg.LABEL[s], "key": s, "start_twh": a[c] / 1000, "end_twh": b[c] / 1000,
                     "added_twh": (b[c] - a[c]) / 1000, "growth_pct_per_year": viz.cagr(a[c], b[c], y1 - y0),
                     "share_start": a[f"{s}_share_pct"], "share_end": b[f"{s}_share_pct"],
                     "share_change_pts": b[f"{s}_share_pct"] - a[f"{s}_share_pct"]})
    return pd.DataFrame(rows)


def region_summary(annual, feat, codes, y0, y1):
    """One row per selected region: level, progress, volume, scores and profile (median split)."""
    a = annual[annual["region_code"].isin(codes)]
    a0, a1 = a[a.year == y0].set_index("region_code"), a[a.year == y1].set_index("region_code")
    reg = pd.DataFrame(index=a1.index)
    reg["region"], reg["region_short"] = a1["region"], a1["region_short"]
    reg["has_nuclear"] = annual.groupby("region_code")["nuclear_gwh"].sum().gt(0).reindex(a1.index)
    reg["share0"], reg["share1"] = a0["renewable_share_pct"], a1["renewable_share_pct"]
    reg["gain"] = reg["share1"] - reg["share0"]
    reg["new0"], reg["new1"] = a0["new_renewables_share_pct"], a1["new_renewables_share_pct"]
    reg["new_gain"] = reg["new1"] - reg["new0"]
    reg["total1"], reg["ren1"], reg["ren0"] = a1["total_gwh"], a1["renewable_gwh"], a0["renewable_gwh"]
    reg["ren_added_twh"] = (reg["ren1"] - reg["ren0"]) / 1000
    reg["thermal1"], reg["nuclear1"] = a1["thermal_share_pct"], a1["nuclear_share_pct"]
    reg["transition_score"], reg["momentum_score"] = a1["energy_transition_score"], a1["renewable_momentum_score"]
    reg["diversity"] = a1["mix_diversity_12m"]
    reg["rank_level"] = reg["share1"].rank(ascending=False, method="min").astype(int)
    reg["rank_gain"] = reg["gain"].rank(ascending=False, method="min").astype(int)
    reg = reg.reset_index()
    reg["profile"] = profiles(reg)
    return reg


def profiles(reg):
    """Leaders / catching up / resting on its level / lagging, using the median of the selected regions."""
    if len(reg) < 4:
        return pd.Series(["(select 4 regions or more)"] * len(reg), index=reg.index)
    ml, mg = reg["share1"].median(), reg["gain"].median()
    hi_l, hi_g = reg["share1"] >= ml, reg["gain"] >= mg
    return pd.Series(np.select([hi_l & hi_g, ~hi_l & hi_g, hi_l & ~hi_g], ["Leader", "Catching up", "Resting on its level"], "Lagging"), index=reg.index)


def gap_table(ann_sel, has_nuclear):
    """Dispersion between the selected regions, year by year."""
    g = ann_sel.groupby("year")["renewable_share_pct"]
    out = pd.DataFrame({"std": g.std(), "range": g.max() - g.min(), "mean_of_regions": g.mean()})
    out["std_new"] = ann_sel.groupby("year")["new_renewables_share_pct"].std()
    grp = ann_sel.assign(nuc=ann_sel["region_code"].map(has_nuclear)).groupby(["year", "nuc"])["renewable_share_pct"].mean().unstack()
    out["without_nuclear"] = grp.get(False)
    out["with_nuclear"] = grp.get(True)
    return out.reset_index()


def monthly_national(feat_sel):
    m = feat_sel.groupby("date")[SUMS].sum()
    m = add_shares(m)
    m["month"] = m.index.month
    return m


def seasonal_tables(m):
    """Average month (production + share) and relative profile of each source."""
    mm = m.groupby("month")[GCOLS + ["renewable_share_pct"]].mean().reset_index()
    prof = pd.DataFrame({s: m.groupby("month")[cfg.GWH[s]].mean() / m[cfg.GWH[s]].mean() for s in cfg.RENEWABLE})
    return mm, prof


def transition_rank(feat, year, weights, codes):
    """Transition score of the selected regions in December of `year` with user weights (components are stored)."""
    from . import prep
    d = feat[(feat["year"] == year) & (feat["month"] == 12) & feat["region_code"].isin(codes)].copy()
    d["score_custom"] = prep.weighted_transition_score(d, weights)
    d["rank_custom"] = d["score_custom"].rank(ascending=False, method="min").astype(int)
    d["rank_default"] = d["energy_transition_score"].rank(ascending=False, method="min").astype(int)
    return d


def scenario(nat, y_end, horizon, growth_pct):
    """Compound scenario from the last observed year: growth_pct = {source: % per year}; other sources stay flat."""
    base = nat.set_index("year").loc[y_end]
    rows = []
    for k, year in enumerate(range(y_end, horizon + 1)):
        vals = {s: base[cfg.GWH[s]] * ((1 + growth_pct.get(s, 0) / 100) ** k) for s in cfg.SOURCES}
        tot = sum(vals.values())
        ren = sum(vals[s] for s in cfg.RENEWABLE)
        rows.append({"year": year, "total_gwh": tot, "renewable_gwh": ren, "renewable_share_pct": ren / tot * 100,
                     **{cfg.GWH[s]: vals[s] for s in cfg.SOURCES}})
    return pd.DataFrame(rows)
