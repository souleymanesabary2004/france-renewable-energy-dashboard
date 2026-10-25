"""Cleaning, feature engineering and validation for the regional electricity dataset.

Used by notebooks/02_cleaning_feature_engineering.ipynb and by the Streamlit app.
All functions take and return pandas objects and do not read global state.
"""
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as cfg


# =====================================================================
# helpers
# =====================================================================
def norm(s):
    """'Production nucléaire (GWh)' -> 'production_nucleaire_gwh'."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^0-9a-zA-Z]+", "_", s).strip("_").lower()


def _nfc(s):
    return unicodedata.normalize("NFC", str(s).strip())


def _safe_pct(num, den):
    """num / den * 100, NaN when the denominator is not strictly positive."""
    return num / den.where(den > 0) * 100


def to_markdown_table(df, index=False):
    """Small markdown table writer (no tabulate dependency)."""
    d = df.reset_index() if index else df
    head = "| " + " | ".join(map(str, d.columns)) + " |"
    sep = "| " + " | ".join("---" for _ in d.columns) + " |"
    rows = ["| " + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in r) + " |"
            for r in d.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


# =====================================================================
# loading and cleaning
# =====================================================================
def read_raw(path):
    """Read the CSV (encoding and separator are detected) and return (df, meta)."""
    path = Path(path)
    last = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                head = f.read(20000)
            try:
                sep = csv.Sniffer().sniff(head, delimiters=";,\t|").delimiter
            except csv.Error:
                sep = ";"
            df = pd.read_csv(path, sep=sep, encoding=enc, low_memory=False)
            meta = {"file": path.name, "encoding": enc, "separator": sep,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "size_mb": round(path.stat().st_size / 1e6, 2),
                    "rows": int(len(df)), "columns": int(df.shape[1])}
            return df, meta
        except UnicodeDecodeError as e:
            last = e
    raise last


def standardize_columns(raw):
    """snake_case names, short names for the six production columns."""
    df = raw.copy()
    df.columns = [norm(c) for c in raw.columns]
    missing = [c for c in cfg.RAW_COLUMNS_EXPECTED if c not in df.columns]
    if missing:
        raise KeyError(f"Expected columns not found: {missing}. Found: {list(df.columns)}")
    return df.rename(columns={**cfg.RAW_TO_SHORT, "mois": "month_text",
                              "code_insee_region": "region_code", "region": "region_label_raw"})


def parse_dates_and_regions(df):
    """Dates -> month start timestamps, region names forced from the INSEE code."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["month_text"], format="%Y-%m", errors="coerce")
    n_bad = int(df["date"].isna().sum())
    if n_bad:
        raise ValueError(f"{n_bad} months could not be parsed")
    df["year_month"] = df["date"].dt.strftime("%Y-%m")

    df["region_code"] = df["region_code"].astype(str).str.strip().str.zfill(2)
    unknown = sorted(set(df["region_code"]) - set(cfg.OFFICIAL_REGIONS))
    if unknown:
        raise ValueError(f"Unknown INSEE region codes: {unknown}")
    df["region_label_raw"] = df["region_label_raw"].map(_nfc)
    official = {k: _nfc(v) for k, v in cfg.OFFICIAL_REGIONS.items()}
    df["region"] = df["region_code"].map(official)
    n_renamed = int((df["region_label_raw"] != df["region"]).sum())
    return df.drop(columns=["month_text"]), {"unparsed_dates": n_bad, "labels_changed": n_renamed}


def nuclear_status(df):
    """Per region: how many months have no nuclear value."""
    g = df.groupby("region_code")["nuclear_gwh"].agg(rows="size", missing=lambda s: int(s.isna().sum()))
    g["status"] = np.select([g.missing == g.rows, g.missing == 0],
                            ["structural (never reported)", "complete"], "partial (real gaps)")
    g.insert(0, "region", g.index.map(cfg.OFFICIAL_REGIONS))
    return g


def apply_structural_rule(df, status):
    """NaN -> 0 for nuclear, only in regions where all months are empty."""
    df = df.copy()
    no_nuclear = status.index[status["status"] == "structural (never reported)"]
    mask = df["region_code"].isin(no_nuclear) & df["nuclear_gwh"].isna()
    df["flag_nuclear_structural_zero"] = mask
    df.loc[mask, "nuclear_gwh"] = 0.0
    df["has_nuclear"] = ~df["region_code"].isin(no_nuclear)
    return df


def _extreme(values, keys, k):
    g = values.groupby(keys)
    q1, q3 = g.transform(lambda s: s.quantile(.25)), g.transform(lambda s: s.quantile(.75))
    iqr = q3 - q1
    return ((values < q1 - k * iqr) | (values > q3 + k * iqr)).fillna(False)


def add_quality_flags(df, k=cfg.EXTREME_IQR_K):
    """Boolean flags plus a readable `quality_flags` string (or 'ok')."""
    df = df.copy()
    tokens = pd.DataFrame(index=df.index)
    neg_any = pd.Series(False, index=df.index)
    ext_any = pd.Series(False, index=df.index)
    for s in cfg.SOURCES:
        col = cfg.GWH[s]
        neg = df[col] < 0
        ext = _extreme(df[col], df["region_code"], k)
        neg_any |= neg
        ext_any |= ext
        tokens[f"neg_{s}"] = np.where(neg, f"negative:{s}", "")
        tokens[f"ext_{s}"] = np.where(ext, f"extreme:{s}", "")
    df["flag_negative_value"] = neg_any
    df["flag_extreme_value"] = ext_any
    df["flag_missing_value"] = df[list(cfg.GWH.values())].isna().any(axis=1)
    tokens["struct"] = np.where(df["flag_nuclear_structural_zero"], "nuclear_structural_zero", "")
    tokens["miss"] = np.where(df["flag_missing_value"], "missing_value", "")
    q = tokens.apply(lambda r: ";".join(x for x in r if x), axis=1)
    df["quality_flags"] = q.where(q != "", "ok")
    return df


CLEAN_COLUMNS = (["date", "year_month", "region_code", "region", "region_label_raw"]
                 + list(cfg.GWH.values())
                 + ["has_nuclear", "flag_nuclear_structural_zero", "flag_negative_value",
                    "flag_extreme_value", "flag_missing_value", "quality_flags"])


def clean_dataset(raw_std):
    """Full cleaning chain; returns (cleaned wide table, nuclear status, info)."""
    df, info = parse_dates_and_regions(raw_std)
    status = nuclear_status(df)
    df = apply_structural_rule(df, status)
    df = add_quality_flags(df)
    df = df.sort_values(["date", "region_code"]).reset_index(drop=True)
    return df[CLEAN_COLUMNS], status, info


# =====================================================================
# dimensions and fact table
# =====================================================================
def _walk(coords):
    if coords and isinstance(coords[0], (int, float)):
        yield coords[0], coords[1]
    else:
        for c in coords:
            yield from _walk(c)


def build_dim_region(raw_std, clean):
    """One row per region: names, centroid, nuclear flag, validated polygon."""
    rows, features = [], []
    span = clean.groupby("region_code")["date"].agg(first_month="min", last_month="max", n_months="nunique")
    has_nuc = clean.groupby("region_code")["has_nuclear"].first()
    for code, g in raw_std.groupby(raw_std["region_code"].astype(str).str.zfill(2)):
        shape, point = g["geo_shape_region"].iloc[0], g["geo_point_region"].iloc[0]
        try:
            geom = json.loads(shape)
            pts = np.array(list(_walk(geom["coordinates"])))
            parsed = True
        except Exception:
            geom, pts, parsed = None, np.empty((0, 2)), False
        try:
            lat, lon = [float(x) for x in str(point).split(",")]
        except Exception:
            lat = lon = np.nan
        inside = bool(parsed and len(pts) and -6 < pts[:, 0].min() and pts[:, 0].max() < 10
                      and 41 < pts[:, 1].min() and pts[:, 1].max() < 52)
        name = cfg.OFFICIAL_REGIONS[code]
        rows.append({"region_code": code, "region": name, "region_short": cfg.REGION_SHORT[code],
                     "region_slug": norm(name), "lat": lat, "lon": lon,
                     "has_nuclear": bool(has_nuc[code]),
                     "geometry_type": geom["type"] if geom else None,
                     "n_polygon_points": int(len(pts)),
                     "geo_valid": bool(parsed and inside and not np.isnan(lat))})
        if geom:
            features.append({"type": "Feature", "id": code,
                             "properties": {"region": name, "region_code": code}, "geometry": geom})
    dim = pd.DataFrame(rows).merge(span.reset_index(), on="region_code", how="left")
    dim["first_month"] = dim["first_month"].dt.strftime("%Y-%m")
    dim["last_month"] = dim["last_month"].dt.strftime("%Y-%m")
    return dim.sort_values("region_code").reset_index(drop=True), \
        {"type": "FeatureCollection", "features": features}


def build_dim_source():
    return pd.DataFrame({
        "source": cfg.SOURCES,
        "label": [cfg.LABEL[s] for s in cfg.SOURCES],
        "family": [cfg.FAMILY[s] for s in cfg.SOURCES],
        "is_renewable": [s in cfg.RENEWABLE for s in cfg.SOURCES],
        "is_new_renewable": [s in cfg.NEW_RENEWABLES for s in cfg.SOURCES],
        "color_hex": [cfg.COLOR[s] for s in cfg.SOURCES],
    })


def build_fact(clean):
    """Long table: one row per month x region x source."""
    ids = ["date", "year_month", "region_code"]
    long = clean.melt(id_vars=ids + ["flag_nuclear_structural_zero"], value_vars=list(cfg.GWH.values()),
                      var_name="col", value_name="production_gwh")
    long["source"] = long["col"].str.replace("_gwh", "", regex=False)
    long["family"] = long["source"].map(cfg.FAMILY)
    long["is_renewable"] = long["source"].isin(cfg.RENEWABLE)
    long["is_new_renewable"] = long["source"].isin(cfg.NEW_RENEWABLES)
    long["flag_structural_zero"] = long["flag_nuclear_structural_zero"] & (long["source"] == "nuclear")
    long["flag_negative_value"] = long["production_gwh"] < 0
    long["flag_extreme_value"] = _extreme(long["production_gwh"], [long["region_code"], long["source"]],
                                          cfg.EXTREME_IQR_K)
    long["source"] = pd.Categorical(long["source"], categories=cfg.SOURCES, ordered=True)
    long = long.sort_values(["date", "region_code", "source"]).reset_index(drop=True)
    long["source"] = long["source"].astype(str)
    return long[ids + ["source", "family", "production_gwh", "is_renewable", "is_new_renewable",
                       "flag_structural_zero", "flag_negative_value", "flag_extreme_value"]]


# =====================================================================
# feature engineering (one function per group)
# =====================================================================
def _roll12(df, col):
    w = cfg.ROLL_WINDOW
    return df.groupby("region_code", sort=False)[col].transform(lambda s: s.rolling(w, min_periods=w).sum())


def _growth(df, col, lag):
    prev = df.groupby("region_code", sort=False)[col].shift(lag)
    return (df[col] - prev) / prev.where(prev > 0) * 100


def floor_negatives(df):
    """Negative net values are set to 0 in the feature tables (raw values stay in cleaned_dataset)."""
    df = df.copy()
    cols = list(cfg.GWH.values())
    df[cols] = df[cols].clip(lower=0)
    return df


def add_time_features(df):
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["season"] = df["month"].map(cfg.SEASON)
    return df


def add_production_metrics(df):
    g = cfg.GWH
    df["total_gwh"] = df[list(g.values())].sum(axis=1)
    df["renewable_gwh"] = df[[g[s] for s in cfg.RENEWABLE]].sum(axis=1)
    df["new_renewables_gwh"] = df[[g[s] for s in cfg.NEW_RENEWABLES]].sum(axis=1)
    return df


def add_shares(df):
    tot = df["total_gwh"]
    for s in cfg.SOURCES:
        df[f"{s}_share_pct"] = _safe_pct(df[cfg.GWH[s]], tot)
    df["renewable_share_pct"] = _safe_pct(df["renewable_gwh"], tot)
    df["new_renewables_share_pct"] = _safe_pct(df["new_renewables_gwh"], tot)
    df["low_carbon_share_pct"] = _safe_pct(df["renewable_gwh"] + df["nuclear_gwh"], tot)
    return df


def add_growth(df):
    df["monthly_growth_pct"] = _growth(df, "total_gwh", 1)
    df["yearly_growth_pct"] = _growth(df, "total_gwh", 12)
    df["renewable_growth_pct"] = _growth(df, "renewable_gwh", 12)
    df["new_renewables_growth_pct"] = _growth(df, "new_renewables_gwh", 12)
    df["solar_growth_pct"] = _growth(df, "solar_gwh", 12)
    df["wind_growth_pct"] = _growth(df, "wind_gwh", 12)
    return df


def add_rolling(df):
    df["rolling_12m_renewable"] = _roll12(df, "renewable_gwh")
    df["rolling_12m_solar"] = _roll12(df, "solar_gwh")
    df["rolling_12m_wind"] = _roll12(df, "wind_gwh")
    df["rolling_12m_new_renewables"] = _roll12(df, "new_renewables_gwh")
    df["rolling_12m_total"] = _roll12(df, "total_gwh")
    thermal12 = _roll12(df, "thermal_gwh")
    tot = df["rolling_12m_total"]
    df["renewable_share_12m_pct"] = _safe_pct(df["rolling_12m_renewable"], tot)
    df["new_renewables_share_12m_pct"] = _safe_pct(df["rolling_12m_new_renewables"], tot)
    df["solar_share_12m_pct"] = _safe_pct(df["rolling_12m_solar"], tot)
    df["wind_share_12m_pct"] = _safe_pct(df["rolling_12m_wind"], tot)
    df["thermal_share_12m_pct"] = _safe_pct(thermal12, tot)
    for src, new in [("renewable_share_12m_pct", "renewable_share_gain_12m_pts"),
                     ("new_renewables_share_12m_pct", "new_renewables_share_gain_12m_pts")]:
        df[new] = df[src] - df.groupby("region_code", sort=False)[src].shift(12)
    return df


def add_rankings(df):
    """Rank among the 13 regions in the same month (1 = best), on 12-month values."""
    basis = {"region_rank_renewables": "renewable_share_12m_pct",
             "region_rank_solar": "solar_share_12m_pct",
             "region_rank_wind": "wind_share_12m_pct",
             "region_rank_growth": "renewable_share_gain_12m_pts"}
    for name, col in basis.items():
        df[name] = df.groupby("date")[col].rank(method="min", ascending=False).astype("Int64")
    # same ranking inside the group of regions with / without nuclear production
    df["region_rank_renewables_peer"] = (df.groupby(["date", "has_nuclear"])["renewable_share_12m_pct"]
                                         .rank(method="min", ascending=False).astype("Int64"))
    return df


def _diversity(values):
    """Normalised Simpson index: 0 = one source only, 1 = six equal sources."""
    v = values.clip(lower=0)
    tot = v.sum(axis=1).where(lambda s: s > 0)
    p = v.div(tot, axis=0)
    return (1 - (p ** 2).sum(axis=1, min_count=1)) / (1 - 1 / values.shape[1])


def add_diversity(df):
    cols = list(cfg.GWH.values())
    df["mix_diversity_index"] = _diversity(df[cols])
    roll = pd.DataFrame({c: _roll12(df, c) for c in cols})
    df["mix_diversity_12m"] = _diversity(roll)
    return df


def fit_scales(df):
    """Robust bounds (percentiles) used to put components on a 0-100 scale."""
    lo_p, hi_p = (p / 100 for p in cfg.SCALE_PERCENTILES)

    def bounds(col):
        s = df[col].dropna()
        return [float(s.quantile(lo_p)), float(s.quantile(hi_p))]

    sc = {"renewable": bounds("renewable_share_12m_pct"),
          "new_renewables": bounds("new_renewables_share_12m_pct"),
          "fossil": bounds("thermal_share_12m_pct"),
          "diversity": bounds("mix_diversity_12m")}
    for key, col in {"gain_renewable": "renewable_share_gain_12m_pts",
                     "gain_new": "new_renewables_share_gain_12m_pts"}.items():
        lo, hi = bounds(col)
        sc[key] = max(abs(lo), abs(hi))          # symmetric bound: 50 = no change
    return sc


def _minmax(x, lo, hi):
    return x * 0 if hi <= lo else ((x - lo) / (hi - lo)).clip(0, 1) * 100


def _centred(x, bound):
    return x * 0 + 50 if bound <= 0 else 50 + 50 * (x / bound).clip(-1, 1)


def weighted_transition_score(df, weights):
    """Re-weight the stored components (used by the what-if slider of the app)."""
    w = weights
    assert abs(sum(w.values()) - 1) < 1e-9, "weights must sum to 1"
    return (w["renewable"] * df["score_renewable"] + w["new_renewables"] * df["score_new_renewables"]
            + w["fossil_free"] * df["score_fossil_free"] + w["diversity"] * df["score_diversity"])


def add_scores(df, scales, w_transition=None, w_momentum=None):
    wt = w_transition or cfg.WEIGHTS_TRANSITION
    wm = w_momentum or cfg.WEIGHTS_MOMENTUM
    df["score_renewable"] = _minmax(df["renewable_share_12m_pct"], *scales["renewable"])
    df["score_new_renewables"] = _minmax(df["new_renewables_share_12m_pct"], *scales["new_renewables"])
    df["fossil_dependency_score"] = _minmax(df["thermal_share_12m_pct"], *scales["fossil"])
    df["score_fossil_free"] = 100 - df["fossil_dependency_score"]
    df["score_diversity"] = _minmax(df["mix_diversity_12m"], *scales["diversity"])
    df["energy_transition_score"] = weighted_transition_score(df, wt)
    df["momentum_renewable"] = _centred(df["renewable_share_gain_12m_pts"], scales["gain_renewable"])
    df["momentum_new_renewables"] = _centred(df["new_renewables_share_gain_12m_pts"], scales["gain_new"])
    df["renewable_momentum_score"] = (wm["renewable"] * df["momentum_renewable"]
                                      + wm["new_renewables"] * df["momentum_new_renewables"])
    return df


def build_features(clean, dim_region):
    """Run all feature groups. Returns (features, scales)."""
    df = clean.merge(dim_region[["region_code", "region_short"]], on="region_code", how="left")
    df = df.sort_values(["region_code", "date"]).reset_index(drop=True)
    df = floor_negatives(df)
    df = add_time_features(df)
    df = add_production_metrics(df)
    df = add_shares(df)
    df = add_growth(df)
    df = add_rolling(df)
    df = add_rankings(df)
    df = add_diversity(df)
    scales = fit_scales(df)
    df = add_scores(df, scales)
    df = df.drop(columns=["region_label_raw"], errors="ignore").sort_values(["date", "region_code"]).reset_index(drop=True)
    return df, scales


# =====================================================================
# pre-aggregated tables for the app
# =====================================================================
def build_annual(feat):
    """Region x calendar year. 12-month features are taken in December (= calendar year)."""
    sums = list(cfg.GWH.values()) + ["total_gwh", "renewable_gwh", "new_renewables_gwh"]
    ann = feat.groupby(["region_code", "region", "region_short", "year"], as_index=False)[sums].sum()
    ann["months"] = feat.groupby(["region_code", "year"])["date"].nunique().values
    for s in cfg.SOURCES:
        ann[f"{s}_share_pct"] = _safe_pct(ann[cfg.GWH[s]], ann["total_gwh"])
    ann["renewable_share_pct"] = _safe_pct(ann["renewable_gwh"], ann["total_gwh"])
    ann["new_renewables_share_pct"] = _safe_pct(ann["new_renewables_gwh"], ann["total_gwh"])
    ann["low_carbon_share_pct"] = _safe_pct(ann["renewable_gwh"] + ann["nuclear_gwh"], ann["total_gwh"])
    keep = ["region_code", "year", "energy_transition_score", "renewable_momentum_score",
            "fossil_dependency_score", "mix_diversity_12m", "region_rank_renewables", "region_rank_solar",
            "region_rank_wind", "region_rank_growth", "region_rank_renewables_peer",
            "renewable_share_gain_12m_pts",
            "new_renewables_share_gain_12m_pts"]
    ann = ann.merge(feat.loc[feat["month"] == 12, keep], on=["region_code", "year"], how="left")
    first = ann[ann.year == ann.year.min()].set_index("region_code")
    for col, new in [("renewable_share_pct", "renewable_share_change_since_start_pts"),
                     ("new_renewables_share_pct", "new_renewables_share_change_since_start_pts")]:
        ann[new] = ann[col] - ann["region_code"].map(first[col])
    return ann.sort_values(["year", "region_code"]).reset_index(drop=True)


def build_national(annual):
    sums = list(cfg.GWH.values()) + ["total_gwh", "renewable_gwh", "new_renewables_gwh"]
    nat = annual.groupby("year", as_index=False)[sums].sum()
    for s in cfg.SOURCES:
        nat[f"{s}_share_pct"] = _safe_pct(nat[cfg.GWH[s]], nat["total_gwh"])
    nat["renewable_share_pct"] = _safe_pct(nat["renewable_gwh"], nat["total_gwh"])
    nat["new_renewables_share_pct"] = _safe_pct(nat["new_renewables_gwh"], nat["total_gwh"])
    nat["low_carbon_share_pct"] = _safe_pct(nat["renewable_gwh"] + nat["nuclear_gwh"], nat["total_gwh"])
    nat["renewable_growth_pct"] = nat["renewable_gwh"].pct_change() * 100
    nat["new_renewables_growth_pct"] = nat["new_renewables_gwh"].pct_change() * 100
    return nat


# =====================================================================
# validation
# =====================================================================
def run_checks(raw_std, clean, fact, dim, feat, annual, dictionary):
    """Return a table of PASS/FAIL checks covering the clean layer and the features."""
    rows = []

    def chk(layer, name, ok, observed, expected=""):
        rows.append({"layer": layer, "check": name, "status": "PASS" if bool(ok) else "FAIL",
                     "observed": str(observed), "expected": str(expected)})

    gcols = list(cfg.GWH.values())
    n_reg, n_mon = clean["region_code"].nunique(), clean["date"].nunique()

    # ---- clean layer
    chk("clean", "row count = regions x months", len(clean) == n_reg * n_mon, len(clean), n_reg * n_mon)
    chk("clean", "unique key (date, region_code)", not clean.duplicated(["date", "region_code"]).any(),
        int(clean.duplicated(["date", "region_code"]).sum()), 0)
    chk("clean", "13 official regions", set(clean.region_code) == set(cfg.OFFICIAL_REGIONS), n_reg, 13)
    chk("clean", "region name = official name for the INSEE code",
        (clean["region"] == clean["region_code"].map(cfg.OFFICIAL_REGIONS).map(_nfc)).all(), "all rows", "all rows")
    full = pd.date_range(clean.date.min(), clean.date.max(), freq="MS")
    chk("clean", "12 full years, no month missing for any region",
        clean.groupby("region_code")["date"].nunique().eq(len(full)).all(), len(full), "same for all regions")
    chk("clean", "no missing value left in the six measures", int(clean[gcols].isna().sum().sum()) == 0,
        int(clean[gcols].isna().sum().sum()), 0)
    raw_nan = int(raw_std["nuclear_gwh"].isna().sum())
    chk("clean", "structural zeros = raw nuclear NaN", int(clean.flag_nuclear_structural_zero.sum()) == raw_nan,
        int(clean.flag_nuclear_structural_zero.sum()), raw_nan)
    tot_ok = all(np.isclose(clean[c].sum(), raw_std[c].sum(skipna=True), rtol=1e-9, atol=1e-6) for c in gcols)
    chk("clean", "totals per source unchanged vs raw file", tot_ok, "6/6 sources", "6/6 sources")
    exp = cfg.EXPECTED_AUDIT
    aud = all(abs(clean[c].sum() - exp[c]) <= 0.011 for c in gcols)
    chk("clean", "totals match notebook 01 (audit)", aud, "within 0.01 GWh", "within 0.01 GWh")
    neg = {k: int((clean[cfg.GWH[k]] < 0).sum()) for k in ["nuclear", "thermal", "wind"]}
    chk("clean", "negative values match notebook 01",
        neg == {"nuclear": exp["neg_nuclear"], "thermal": exp["neg_thermal"], "wind": exp["neg_wind"]}, neg,
        {"nuclear": exp["neg_nuclear"], "thermal": exp["neg_thermal"], "wind": exp["neg_wind"]})
    chk("clean", "quality flags consistent", (clean["quality_flags"].eq("ok")
        == ~(clean.flag_negative_value | clean.flag_extreme_value | clean.flag_nuclear_structural_zero
             | clean.flag_missing_value)).all(), "ok", "ok")

    # ---- star schema
    chk("schema", "fact rows = clean rows x 6 sources", len(fact) == len(clean) * 6, len(fact), len(clean) * 6)
    chk("schema", "unique key (date, region_code, source)",
        not fact.duplicated(["date", "region_code", "source"]).any(), 0, 0)
    chk("schema", "fact sums = clean sums", all(np.isclose(fact.loc[fact.source == s, "production_gwh"].sum(),
                                                            clean[cfg.GWH[s]].sum()) for s in cfg.SOURCES),
        "6/6", "6/6")
    chk("schema", "every fact region_code exists in dim_region", set(fact.region_code) <= set(dim.region_code),
        "yes", "yes")
    chk("schema", "dim_region: 13 rows and valid geometry", len(dim) == 13 and bool(dim.geo_valid.all()),
        f"{len(dim)} rows, valid={int(dim.geo_valid.sum())}", "13 / 13")
    chk("schema", "extreme flags: fact = clean",
        int(fact.flag_extreme_value.sum()) == int(sum(_extreme(clean[cfg.GWH[s]], clean["region_code"],
                                                               cfg.EXTREME_IQR_K).sum() for s in cfg.SOURCES)),
        int(fact.flag_extreme_value.sum()), "same")

    # ---- features
    num = feat.select_dtypes(include=[np.number])
    chk("features", "total = sum of the six sources", np.allclose(feat.total_gwh, feat[gcols].sum(axis=1)), "ok", "ok")
    chk("features", "renewable = hydro + wind + solar + bioenergy",
        np.allclose(feat.renewable_gwh, feat[["hydro_gwh", "wind_gwh", "solar_gwh", "bioenergy_gwh"]].sum(axis=1)),
        "ok", "ok")
    chk("features", "new renewables <= renewables", (feat.new_renewables_gwh <= feat.renewable_gwh + 1e-9).all(),
        "ok", "ok")
    pos = feat.total_gwh > 0
    s6 = feat.loc[pos, [f"{s}_share_pct" for s in cfg.SOURCES]].sum(axis=1)
    chk("features", "the six shares add up to 100", np.allclose(s6, 100), f"max gap {float((s6 - 100).abs().max()):.2e}", "0")
    chk("features", "renewable + nuclear + thermal shares = 100",
        np.allclose(feat.loc[pos, ["renewable_share_pct", "nuclear_share_pct", "thermal_share_pct"]].sum(axis=1), 100),
        "ok", "ok")
    chk("features", "low carbon = renewable + nuclear",
        np.allclose(feat.loc[pos, "low_carbon_share_pct"], feat.loc[pos, "renewable_share_pct"] + feat.loc[pos, "nuclear_share_pct"]),
        "ok", "ok")
    sh = feat[[f"{s}_share_pct" for s in cfg.SOURCES] + ["renewable_share_pct", "new_renewables_share_pct", "low_carbon_share_pct"]]
    chk("features", "all shares inside [0, 100]", sh.min().min() >= -1e-9 and sh.max().max() <= 100 + 1e-9,
        f"{sh.min().min():.3f} .. {sh.max().max():.3f}", "[0, 100]")
    m = clean.merge(feat[["date", "region_code"] + gcols], on=["date", "region_code"], suffixes=("_c", ""))
    floor_ok = all(np.allclose(m[c], m[f"{c}_c"].clip(lower=0)) for c in gcols)
    n_neg = int((clean[gcols] < 0).sum().sum())
    adj = float(-clean[gcols].clip(upper=0).sum().sum())
    chk("features", "feature values = cleaned values, only negative cells set to 0", floor_ok,
        f"{n_neg} cells, {adj:.1f} GWh adjusted", "negative cells only")
    nan_roll = feat.groupby("region_code")["rolling_12m_renewable"].apply(lambda s: int(s.isna().sum()))
    chk("features", "rolling 12m: 11 empty months per region", nan_roll.eq(11).all(), sorted(set(nan_roll)), [11])
    nan_gain = feat.groupby("region_code")["renewable_share_gain_12m_pts"].apply(lambda s: int(s.isna().sum()))
    chk("features", "12m share gain: 23 empty months per region", nan_gain.eq(23).all(), sorted(set(nan_gain)), [23])
    cal = feat.groupby(["region_code", "year"])["renewable_gwh"].sum()
    dec = feat[feat.month == 12].set_index(["region_code", "year"])["rolling_12m_renewable"].dropna()
    chk("features", "rolling 12m in December = calendar-year sum", np.allclose(cal.loc[dec.index], dec), len(dec), "all Decembers")
    rk = feat.dropna(subset=["region_rank_renewables"])
    chk("features", "ranks between 1 and 13, rank 1 exists every month",
        rk.region_rank_renewables.between(1, n_reg).all() and rk.groupby("date").region_rank_renewables.min().eq(1).all(),
        f"{int(rk.region_rank_renewables.min())}..{int(rk.region_rank_renewables.max())}", "1..13")
    pr = feat.dropna(subset=["region_rank_renewables_peer"])
    gs = pr.groupby(["date", "has_nuclear"])["region_rank_renewables_peer"].agg(["min", "max", "size"])
    chk("features", "peer ranks start at 1 and stay within the group size", (gs["min"] == 1).all() and (gs["max"] <= gs["size"]).all(),
        f"groups of {sorted({int(x) for x in gs['size']})} regions", "rank 1 in every group")
    score_cols = ["energy_transition_score", "renewable_momentum_score", "fossil_dependency_score",
                  "score_renewable", "score_new_renewables", "score_fossil_free", "score_diversity",
                  "momentum_renewable", "momentum_new_renewables"]
    sc = feat[score_cols].stack().dropna()
    chk("features", "scores inside [0, 100]", sc.between(-1e-9, 100 + 1e-9).all(), f"{sc.min():.1f} .. {sc.max():.1f}", "[0, 100]")
    dv = feat[["mix_diversity_index", "mix_diversity_12m"]].stack().dropna()
    chk("features", "diversity indices inside [0, 1]", dv.between(-1e-9, 1 + 1e-9).all(),
        f"{dv.min():.3f} .. {dv.max():.3f}", "[0, 1]")
    chk("features", "12m diversity empty exactly where the 12m window is empty",
        feat.mix_diversity_12m.isna().equals(feat.rolling_12m_total.isna()), int(feat.mix_diversity_12m.isna().sum()),
        int(feat.rolling_12m_total.isna().sum()))
    chk("features", "no infinite value", not np.isinf(num.to_numpy(dtype=float)).any(), 0, 0)
    chk("features", "transition weights sum to 1", abs(sum(cfg.WEIGHTS_TRANSITION.values()) - 1) < 1e-9,
        sum(cfg.WEIGHTS_TRANSITION.values()), 1)
    dec_share = feat[feat.month == 12][["region_code", "year", "renewable_share_12m_pct"]]
    m = annual.merge(dec_share, on=["region_code", "year"]).dropna(subset=["renewable_share_12m_pct"])
    chk("features", "annual renewable share = December 12m share", np.allclose(m.renewable_share_pct, m.renewable_share_12m_pct),
        f"{len(m)} region-years", "all equal")

    # ---- documentation
    doc = set(dictionary["feature"])
    chk("docs", "every column of the feature dataset is documented", set(feat.columns) <= doc,
        sorted(set(feat.columns) - doc) or "all", "all")
    chk("docs", "every column of the cleaned dataset is documented", set(clean.columns) <= doc,
        sorted(set(clean.columns) - doc) or "all", "all")
    chk("docs", "no documented feature is missing from the datasets",
        doc <= (set(feat.columns) | set(clean.columns)), sorted(doc - set(feat.columns) - set(clean.columns)) or "none", "none")
    return pd.DataFrame(rows)


# =====================================================================
# one call for the whole pipeline (used by the app, the scripts and the tests)
# =====================================================================
def make_tables(raw_df):
    """Raw dataframe (as read from the CSV) -> every table of the project.

    Same steps and same functions as notebook 02, so the tables are identical to the ones
    exported there. Returns a dict with the dataframes, the geojson and the scales.
    """
    from . import dictionary
    raw_std = standardize_columns(raw_df)
    clean, status, info = clean_dataset(raw_std)
    dim_region, geojson = build_dim_region(raw_std, clean)
    dim_source = build_dim_source()
    fact = build_fact(clean)
    feat, scales = build_features(clean, dim_region)
    order = [c for c in dictionary.feature_order() if c in feat.columns]
    feat = feat[order]
    annual = build_annual(feat)
    national = build_national(annual)
    fdict = dictionary.feature_dictionary()
    return {"cleaned_dataset": clean,
            "feature_engineered_dataset": feat, "dim_region": dim_region, "fact_energy": fact,
            "dim_source": dim_source, "annual_region_summary": annual, "national_annual": national,
            "feature_dictionary": fdict, "geojson": geojson, "scales": scales,
            "nuclear_status": status, "cleaning_info": info, "raw_std": raw_std}
