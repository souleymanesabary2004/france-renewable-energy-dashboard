# French regions and the renewable electricity transition

Individual Data Storytelling project, EFREI Paris (#EFREIDataStories2026)
Soumahoro Souleymane

My question: **how are French regions progressing toward a renewable electricity future?**

I built a Streamlit dashboard on the monthly regional electricity production published by RTE. My main finding is that the national figure hides a lot. Renewable electricity grew a lot between 2014 and 2025, mostly wind and solar, and it replaced nuclear production more than fossil production. But regions do not move at the same speed, and a region with a high renewable share is not necessarily a region that progressed.

- Deployed app: `<URL>`
- Demo video: `<link>`
- Repository: `<link>`
- Report, storyboard and video script: `REPORT.md`, `docs/storyboard.md`, `docs/video_script.md`

## What is in the app

The sidebar (years, group of regions, regions, indicator) drives the KPI header and all the charts. The story goes through seven tabs:

1. Why it matters: why I chose the topic, the audience, the questions, how to read level and progress.
2. France, what changed: production by source, what replaced what, rate versus volume of growth.
3. Regions, who moves: map and ranking (switch between level and progress), four profiles of regions, heatmap, one region in focus.
4. Seasons and gaps: sun in summer and wind in winter, and whether the gaps between regions close.
5. What if: another set of weights for my transition score, and a simple scenario with written assumptions.
6. Conclusions: insights, implications, next steps, limits.
7. Data and quality: validation checks, missing values, duplicates, method, dictionary, licence.

## Run it

Python 3.12 or 3.13.

```bash
python -m venv .venv
.venv\Scripts\activate              # Linux / macOS: source .venv/bin/activate
pip install -r requirements.txt

python -m utils.io build            # only if data/processed/ is empty: downloads the raw file once and rebuilds the tables
streamlit run app.py
```

If `data/processed/` is missing, the app does the download and the build by itself at the first start (it needs an internet connection). Tests: `pip install -r requirements-dev.txt`, then `python -m pytest -q tests`. A `Makefile` gives the same commands (`make setup`, `make data`, `make app`, `make test`).

## Folders

```
app.py            sidebar, KPI header, tabs
sections/         one file per chapter of the story
utils/            config.py (constants), io.py (download with cache, load/save), prep.py (cleaning and features),
                  analysis.py (aggregations for the app), quality.py (data quality tables), viz.py (charts), dictionary.py
notebooks/        01 audit, 02 cleaning and features, 03 EDA and storytelling
data/             README.md (source and licence), processed/ (small tables), raw/ (downloaded, not committed)
reports/          data quality, feature engineering, EDA, key insights, storytelling candidates, dashboard recommendations
docs/             storyboard, video script
scripts/          make_zip.py
tests/            pytest
seeds.json        constants used for reproducibility
```

## Data

*Production régionale mensuelle d'électricité par filière*, data.gouv.fr, published by ODRÉ, created by RTE, Licence Ouverte 2.0. 13 metropolitan regions, 144 months (2014-01 to 2025-12), six sources in GWh.
Link: https://www.data.gouv.fr/datasets/production-regionale-mensuelle-delectricite-par-filiere
The raw file is 21 MB, so it is not in the zip: `python -m utils.io download` fetches it and keeps it in `data/raw/`.

Citation: RTE / ODRÉ, « Production régionale mensuelle d'électricité par filière », data.gouv.fr, Licence Ouverte 2.0, consulted in October 2026.

## What I did to the data

- 864 nuclear values are empty. They all belong to six regions that never report nuclear (every month is empty), so I set them to 0 and flagged them. I imputed nothing else.
- 34 values are negative (net production). I kept them in the cleaned tables with a flag, and set them to 0 only when I compute shares, otherwise a share went above 100 %.
- 39 solar values are extreme compared with their own region. I flagged them and kept them.
- Levels, ranks and scores use 12-month windows. National shares are sums of GWh divided by sums of GWh, never an average of percentages.
- Every column of the feature table is described in the feature dictionary (formula, meaning, why it helps the question).

## Performance and accessibility

`st.cache_data` on the loaders, pre-aggregated annual and national tables, no raw file in the repository. Colours are colour-blind safe (Okabe-Ito), every chart has a text alternative under it, axes have units, controls have a help text.

## Deploy

Push the project to GitHub (with `data/processed/`, without `data/raw/`), then on share.streamlit.io choose the repository, the branch and `app.py`, and select Python 3.12 or 3.13 in the advanced settings.

## Limits

The file has production only: no consumption, capacity or prices, so a share is a share of production. Weather moves the yearly values. With 13 regions, the profiles and correlations describe, they do not prove, and I do not claim causes. Only aggregated regional data is used, so there is no personal data. The scenario is arithmetic with assumptions written on the page, not a forecast.
