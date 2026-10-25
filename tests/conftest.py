"""Synthetic raw file with the same structure as the real one (13 regions x 144 months)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import config as cfg  # noqa: E402


@pytest.fixture(scope="session")
def raw_df():
    rng = np.random.default_rng(42)
    no_nuc = {"27", "53", "94", "52", "93", "11"}
    rows = []
    for k, (code, name) in enumerate(cfg.OFFICIAL_REGIONS.items()):
        x0, y0 = 1.0 + 0.6 * (k % 5), 43.0 + 0.9 * (k // 5)
        poly = [[x0, y0], [x0 + 0.5, y0], [x0 + 0.5, y0 + 0.5], [x0, y0 + 0.5], [x0, y0]]
        shape = json.dumps({"type": "Polygon", "coordinates": [poly]})
        point = f"{y0 + 0.25}, {x0 + 0.25}"
        for m in range(144):
            year, month = 2014 + m // 12, m % 12 + 1
            t = m / 143
            season = np.cos((month - 7) / 12 * 2 * np.pi)
            vals = {"nuclear": np.nan if code in no_nuc else 2500 + 200 * rng.standard_normal(),
                    "thermal": 80 + 20 * rng.random(), "hydro": 400 + 80 * rng.random(),
                    "wind": 100 * (1 + 2 * t) * (1 - 0.3 * season) + 10 * rng.random(),
                    "solar": 30 * (1 + 4 * t) * (1 + 0.8 * season) + 5 * rng.random(),
                    "bioenergy": 40 + 10 * rng.random()}
            if code == "76" and m == 100:
                vals["nuclear"] = -12.0                    # one negative net value
            rows.append({"mois": f"{year}-{month:02d}", "code_insee_region": code, "region": name,
                         **{f"production_{ {'nuclear': 'nucleaire', 'thermal': 'thermique', 'hydro': 'hydraulique', 'wind': 'eolienne', 'solar': 'solaire', 'bioenergy': 'bioenergies'}[s] }_gwh": v
                            for s, v in vals.items()},
                         "geo_shape_region": shape, "geo_point_region": point})
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def tables(raw_df):
    from utils import prep
    return prep.make_tables(raw_df)
