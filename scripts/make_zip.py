"""Build the submission zip.

    python scripts/make_zip.py --number 20000 --name SOUMAHORO --group DE1

File name: StApp26_<student number>_<NAME>_<GROUP>.zip (groups: DE1, DE2, BIO, DAI, BIA).
Content: code, README, report, storyboard, notebooks, reports, small processed tables and the data link.
The raw file (21 MB) is not included: `python -m utils.io download` fetches it.
"""
import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {"DE1", "DE2", "BIO", "DAI", "BIA"}
TOP_FILES = ["app.py", "README.md", "REPORT.md", "requirements.txt", "requirements-dev.txt", "seeds.json", "Makefile", ".gitignore"]
DIRS = ["sections", "utils", "scripts", "tests", "docs", "assets", ".streamlit", "notebooks", "reports", "data"]
SKIP_PARTS = {"__pycache__", ".ipynb_checkpoints", ".venv", "venv", "raw", ".pytest_cache", ".git"}
SKIP_SUFFIX = {".pyc", ".bak", ".part", ".zip"}


def keep(path):
    rel = path.relative_to(ROOT)
    if any(p in SKIP_PARTS for p in rel.parts):
        return False
    if path.suffix in SKIP_SUFFIX or path.name.startswith(("build_nb", "patch_nb")):
        return False
    if rel.parts[0] == "data" and len(rel.parts) == 2 and path.suffix == ".csv":      # stray raw copy next to README
        return False
    return path.is_file()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--number", required=True, help="student number")
    ap.add_argument("--name", required=True, help="family name in capitals")
    ap.add_argument("--group", required=True, help="DE1, DE2, BIO, DAI or BIA")
    a = ap.parse_args()
    if a.group.upper() not in GROUPS:
        sys.exit(f"group must be one of {sorted(GROUPS)}")
    stem = f"StApp26_{a.number}_{a.name.upper()}_{a.group.upper()}"
    files = [ROOT / f for f in TOP_FILES if (ROOT / f).exists()]
    for d in DIRS:
        files += [p for p in sorted((ROOT / d).rglob("*")) if keep(p)] if (ROOT / d).exists() else []
    missing = [m for m in ["app.py", "data/processed/feature_engineered_dataset.csv", "data/processed/regions.geojson",
                           "notebooks/03_eda_storytelling.ipynb", "README.md"] if not (ROOT / m).exists()]
    if missing:
        print("WARNING, not found (the zip is built anyway):", ", ".join(missing))
    out = ROOT / f"{stem}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, Path(stem) / p.relative_to(ROOT))
    print(f"{out.name}: {len(files)} files, {out.stat().st_size / 1e6:.1f} MB")
    big = [p for p in files if p.stat().st_size > 5e6]
    if big:
        print("files above 5 MB:", ", ".join(str(p.relative_to(ROOT)) for p in big))


if __name__ == "__main__":
    main()
