import numpy as np
import pandas as pd

from utils import analysis, config as cfg, quality, viz

GC = list(cfg.GWH.values())


def test_structural_nuclear_rule(tables):
    clean = tables["cleaned_dataset"]
    assert len(clean) == 13 * 144
    assert clean[GC].notna().all().all()
    flagged = clean.loc[clean["flag_nuclear_structural_zero"], "region_code"].unique()
    assert sorted(flagged) == ["11", "27", "52", "53", "93", "94"]
    assert (clean.loc[clean["flag_nuclear_structural_zero"], "nuclear_gwh"] == 0).all()
    assert not clean.duplicated(["region_code", "date"]).any()


def test_negative_values_kept_in_clean_floored_in_features(tables):
    clean, feat = tables["cleaned_dataset"], tables["feature_engineered_dataset"]
    assert (clean[GC] < 0).sum().sum() == 1
    assert (feat[GC] >= 0).all().all()
    sh = feat[[f"{s}_share_pct" for s in cfg.SOURCES]]
    assert np.allclose(sh.sum(axis=1), 100)
    assert sh.min().min() >= 0 and sh.max().max() <= 100


def test_features_identities(tables):
    f = tables["feature_engineered_dataset"]
    assert np.allclose(f["renewable_gwh"], f[["hydro_gwh", "wind_gwh", "solar_gwh", "bioenergy_gwh"]].sum(axis=1))
    assert np.allclose(f["new_renewables_gwh"], f[["wind_gwh", "solar_gwh", "bioenergy_gwh"]].sum(axis=1))
    first = f[f["date"] == f["date"].min()]
    assert first["rolling_12m_renewable"].isna().all()                 # 12-month window needs 12 months
    dec = f[f["month"] == 12]
    assert dec["region_rank_renewables"].dropna().between(1, 13).all()
    for c in ["energy_transition_score", "renewable_momentum_score", "fossil_dependency_score"]:
        assert f[c].dropna().between(-1e-6, 100 + 1e-6).all()


def test_annual_and_national_tables_match_monthly(tables):
    f, a, n = tables["feature_engineered_dataset"], tables["annual_region_summary"], tables["national_annual"]
    assert np.isclose(a["renewable_gwh"].sum(), f["renewable_gwh"].sum())
    assert np.isclose(n["total_gwh"].sum(), f["total_gwh"].sum())
    assert len(a) == 13 * 12 and len(n) == 12


def test_validation_checks_pass_on_clean_tables(tables):
    t = {k: tables[k] for k in ["cleaned_dataset", "feature_engineered_dataset", "fact_energy", "annual_region_summary",
                                "national_annual", "dim_region"]}
    chk = quality.validation_checks(t)
    assert (chk["status"] == "PASS").all(), chk[chk["status"] == "FAIL"]


def test_national_share_is_weighted_not_averaged(tables):
    a = tables["annual_region_summary"]
    n = analysis.national(a).set_index("year")
    y = a["year"].max()
    sub = a[a["year"] == y]
    assert np.isclose(n.loc[y, "renewable_share_pct"], sub["renewable_gwh"].sum() / sub["total_gwh"].sum() * 100)
    assert not np.isclose(n.loc[y, "renewable_share_pct"], sub["renewable_share_pct"].mean())


def test_region_summary_profiles(tables):
    a, f = tables["annual_region_summary"], tables["feature_engineered_dataset"]
    reg = analysis.region_summary(a, f, list(a["region_code"].unique()), 2014, 2025)
    assert len(reg) == 13
    assert set(reg["profile"]) <= {"Leader", "Catching up", "Resting on its level", "Lagging"}
    assert reg["rank_level"].min() == 1


def test_scenario_is_compound_and_keeps_flat_sources(tables):
    n = analysis.national(tables["annual_region_summary"])
    y = int(n["year"].max())
    sc = analysis.scenario(n, y, y + 3, {"solar": 10.0})
    assert np.isclose(sc.loc[sc.year == y + 3, "solar_gwh"].iloc[0], n.set_index("year").loc[y, "solar_gwh"] * 1.1 ** 3)
    assert np.isclose(sc.loc[sc.year == y + 3, "hydro_gwh"].iloc[0], n.set_index("year").loc[y, "hydro_gwh"])


def test_helpers():
    assert np.isclose(viz.cagr(100, 200, 10), (2 ** 0.1 - 1) * 100)
    assert np.isnan(viz.cagr(0, 10, 5))
    s = pd.Series(10 + np.sin(np.arange(60) / 12 * 2 * np.pi) + np.arange(60) * 0.1)
    d = viz.decompose(s, 12)
    fs, ft = viz.strengths(d)
    assert fs > 0.5 and ft > 0.5
    assert np.allclose((d["trend"] + d["seasonal"] + d["resid"]).dropna(), s[d["trend"].notna()])
