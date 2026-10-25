"""Data quality tables shown in the app (computed from the processed tables, not typed by hand)."""
import numpy as np
import pandas as pd

from . import config as cfg

GCOLS = list(cfg.GWH.values())


def missingness(clean, fact):
    """What was missing or unusual in the raw data and what was done about it."""
    n = len(clean)
    rows = [
        ("Empty nuclear values (structural)", int(clean["flag_nuclear_structural_zero"].sum()),
         "6 regions never report nuclear (all months empty): set to 0 GWh and flagged"),
        ("Other empty values", int(clean["flag_missing_value"].sum()), "none to repair"),
        ("Negative net values", int(clean["flag_negative_value"].sum()),
         "kept in cleaned data and facts; set to 0 in the feature table so shares stay between 0 and 100"),
        ("Extreme values (3 x IQR of the region)", int(clean["flag_extreme_value"].sum()),
         "kept and flagged, used only to annotate charts"),
    ]
    out = pd.DataFrame(rows, columns=["issue", "cells or rows", "treatment"])
    out["% of region-months"] = (out["cells or rows"] / n * 100).round(2)
    return out


def column_missing(feat):
    """Share of empty cells per column of the feature table (windows of 12 / 24 months are empty by design)."""
    m = feat.isna().mean().mul(100).round(1)
    m = m[m > 0].sort_values(ascending=False).rename("% empty").to_frame()
    m["why"] = np.where(m.index.str.contains("12m|rolling|momentum|score|gain|rank_growth|_peer"), "12 or 24-month window (first months)",
                        np.where(m.index.str.contains("growth"), "growth needs a previous period / a positive base", "see feature dictionary"))
    return m


def duplicates(clean, fact):
    k1 = int(clean.duplicated(["region_code", "date"]).sum())
    k2 = int(fact.duplicated(["region_code", "date", "source"]).sum())
    k3 = int(clean.duplicated().sum())
    return pd.DataFrame([("Duplicated region-month keys (wide table)", k1), ("Duplicated region-month-source keys (fact table)", k2),
                         ("Fully duplicated rows", k3)], columns=["check", "count"])


def validation_checks(tables):
    """PASS / FAIL checks on the processed tables."""
    clean, feat, fact = tables["cleaned_dataset"], tables["feature_engineered_dataset"], tables["fact_energy"]
    ann, nat, dimr = tables["annual_region_summary"], tables["national_annual"], tables["dim_region"]
    checks = []

    def chk(name, ok, observed):
        checks.append((name, "PASS" if bool(ok) else "FAIL", observed))

    n_reg, n_mon = clean["region_code"].nunique(), clean["date"].nunique()
    chk("13 regions x 144 months, balanced panel", len(clean) == n_reg * n_mon == 13 * 144, f"{n_reg} regions x {n_mon} months = {len(clean)} rows")
    chk("keys are unique", not clean.duplicated(["region_code", "date"]).any(), "0 duplicated region-month")
    chk("months are consecutive", (clean["date"].drop_duplicates().sort_values().diff().dropna().dt.days.between(28, 31)).all(),
        f"{clean['date'].min():%Y-%m} to {clean['date'].max():%Y-%m}")
    chk("no empty value in the six production columns", clean[GCOLS].notna().all().all(), "0 empty cells after the nuclear rule")
    chk("fact table = wide table x 6 sources", len(fact) == len(clean) * 6, f"{len(fact):,} = {len(clean):,} x 6")
    chk("fact and wide table give the same total (raw values)", np.isclose(fact["production_gwh"].sum(), clean[GCOLS].sum().sum()),
        f"{fact['production_gwh'].sum():,.0f} GWh")
    chk("shares of the six sources add up to 100", np.allclose(feat[[f"{s}_share_pct" for s in cfg.SOURCES]].sum(axis=1), 100),
        "max gap " + f"{(feat[[f'{s}_share_pct' for s in cfg.SOURCES]].sum(axis=1) - 100).abs().max():.1e}")
    sh = feat[[c for c in feat.columns if c.endswith("_share_pct")]]
    chk("every share is between 0 and 100", sh.min().min() >= -1e-9 and sh.max().max() <= 100 + 1e-9, f"min {sh.min().min():.2f}, max {sh.max().max():.2f}")
    chk("renewable = hydro + wind + solar + bioenergy", np.allclose(feat["renewable_gwh"], feat[["hydro_gwh", "wind_gwh", "solar_gwh", "bioenergy_gwh"]].sum(axis=1)), "identity checked on every row")
    chk("annual table = monthly table", np.isclose(ann["renewable_gwh"].sum(), feat["renewable_gwh"].sum()), f"{ann['renewable_gwh'].sum():,.0f} GWh")
    chk("national table = sum of the regions", np.isclose(nat["total_gwh"].sum(), ann["total_gwh"].sum()), f"{nat['total_gwh'].sum():,.0f} GWh")
    chk("scores are inside 0-100", feat[["energy_transition_score", "renewable_momentum_score", "fossil_dependency_score"]].stack().dropna().between(-1e-6, 100 + 1e-6).all(), "3 scores")
    chk("ranks go from 1 to 13", feat["region_rank_renewables"].dropna().between(1, 13).all(), "region_rank_renewables")
    chk("all geometries are valid", bool(dimr["geo_valid"].all()), f"{int(dimr['geo_valid'].sum())} / {len(dimr)} regions")
    return pd.DataFrame(checks, columns=["check", "status", "observed"])
