"""Loading, downloading and saving data.

- `load_data()`        : tables used by the app (reads data/processed, builds them from the raw file if missing)
- `fetch_and_cache()`  : downloads the raw CSV once from data.gouv.fr and keeps it in data/raw (not committed)
- `build_processed()`  : raw CSV -> data/processed/*.csv (same code as notebook 02)

Command line:
    python -m utils.io download      # download the raw file (cached)
    python -m utils.io build         # download if needed, then rebuild data/processed
"""
import json
import sys
from pathlib import Path

import pandas as pd

from . import config as cfg

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"

# ---------------------------------------------------------------- source and licence
DATASET_TITLE = "Production régionale mensuelle d'électricité par filière"
DATASET_PAGE = "https://www.data.gouv.fr/datasets/production-regionale-mensuelle-delectricite-par-filiere"
DATA_URL = "https://www.data.gouv.fr/api/1/datasets/r/27b32325-0f02-4fb2-871c-dc743af1d7db"
PORTAL = "data.gouv.fr (published by Open Data Réseaux Énergies, ODRÉ; creator and publisher: RTE)"
LICENSE_NAME = "Licence Ouverte / Open Licence version 2.0 (Etalab)"
LICENSE_TEXT = (
    f"**Data**: *{DATASET_TITLE}*, {PORTAL}, under the {LICENSE_NAME}. "
    "Reuse is free provided the source and the date of the last update are cited "
    "(last update seen on the portal: 25 February 2026). "
    "**Code**: written for the EFREI Data Storytelling project (academic use); the licence of the code is "
    "independent from the licence of the data.")
CITATION = (f"RTE / ODRÉ, « {DATASET_TITLE} », data.gouv.fr, Licence Ouverte 2.0, "
            f"consulted in October 2026. {DATASET_PAGE}")

TABLES = ["cleaned_dataset", "feature_engineered_dataset", "dim_region", "fact_energy", "dim_source",
          "annual_region_summary", "national_annual", "feature_dictionary"]
_DATE_COLS = {"cleaned_dataset": ["date"], "feature_engineered_dataset": ["date"], "fact_energy": ["date"]}


# ---------------------------------------------------------------- download with cache
def fetch_and_cache(url=DATA_URL, dest=None, force=False, timeout=120):
    """Download the raw CSV once. If the file is already there it is reused (cache)."""
    import requests
    dest = Path(dest) if dest else RAW_DIR / cfg.RAW_FILE
    if dest.exists() and dest.stat().st_size > 1_000_000 and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    with requests.get(url, stream=True, timeout=timeout, headers={"User-Agent": "efrei-data-storytelling/1.0"}) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    head = tmp.read_bytes()[:2000].decode("utf-8-sig", errors="ignore").lower()
    if "production_nucleaire" not in head and "nucl" not in head:
        tmp.unlink()
        raise ValueError("The downloaded file does not look like the expected dataset (header check failed).")
    tmp.replace(dest)
    return dest


def find_raw_file():
    """Raw file in data/ or data/raw/ or at the local path used for notebook 01-02."""
    for p in (RAW_DIR / cfg.RAW_FILE, ROOT / "data" / cfg.RAW_FILE, Path(cfg.LOCAL_RAW_PATH)):
        if p.exists():
            return p
    return None


def load_raw(download=True):
    """Raw dataframe + metadata (file name, hash, size). Downloads the file if it is not available."""
    from . import prep
    path = find_raw_file()
    if path is None:
        if not download:
            raise FileNotFoundError("Raw file not found. Run `python -m utils.io download`.")
        path = fetch_and_cache()
    return prep.read_raw(path)


# ---------------------------------------------------------------- processed tables
def read_table(name, folder=PROC_DIR):
    path = Path(folder) / f"{name}.csv"
    kw = {"dtype": {"region_code": str}} if name not in ("dim_source", "feature_dictionary") else {}
    df = pd.read_csv(path, parse_dates=_DATE_COLS.get(name, []), **kw)
    return df


def processed_available(folder=PROC_DIR):
    return all((Path(folder) / f"{n}.csv").exists() for n in TABLES) and (Path(folder) / "regions.geojson").exists()


def _rounded(df, nd=6):
    out = df.copy()
    fl = out.select_dtypes(include=["float"]).columns
    out[fl] = out[fl].round(nd)
    return out


def save_tables(tables, folder=PROC_DIR):
    """Write the tables like notebook 02 does (UTF-8, 6 decimals, ISO dates)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        _rounded(tables[name]).to_csv(folder / f"{name}.csv", index=False, encoding="utf-8", date_format="%Y-%m-%d")
    (folder / "regions.geojson").write_text(json.dumps(tables["geojson"]), encoding="utf-8")
    (folder / "feature_scales.json").write_text(json.dumps(
        {"scales": tables["scales"], "weights_transition": cfg.WEIGHTS_TRANSITION,
         "weights_momentum": cfg.WEIGHTS_MOMENTUM, "percentiles": cfg.SCALE_PERCENTILES}, indent=2), encoding="utf-8")
    return folder


def build_processed(folder=PROC_DIR, raw_path=None):
    """Raw CSV -> processed tables on disk. Returns the dict of tables."""
    from . import prep
    if raw_path is not None:
        raw, meta = prep.read_raw(raw_path)
    else:
        raw, meta = load_raw()
    tables = prep.make_tables(raw)
    tables["meta"] = meta
    save_tables(tables, folder)
    return tables


def load_data(folder=PROC_DIR):
    """Tables for the app. Uses data/processed; if it is missing, rebuilds it from the raw file."""
    if not processed_available(folder):
        build_processed(folder)
    out = {n: read_table(n, folder) for n in TABLES}
    out["geojson"] = json.loads((Path(folder) / "regions.geojson").read_text(encoding="utf-8"))
    sc = Path(folder) / "feature_scales.json"
    out["scales"] = json.loads(sc.read_text(encoding="utf-8")) if sc.exists() else {}
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "download":
        print("raw file:", fetch_and_cache(force="--force" in sys.argv))
    elif cmd == "build":
        t = build_processed()
        print("processed tables written to", PROC_DIR, "|", {n: t[n].shape for n in TABLES})
    else:
        print(__doc__)
