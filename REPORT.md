# Report: French regions and the renewable electricity transition

Soumahoro Souleymane, EFREI Paris, Data Storytelling project 2026

The numbers in this report come from my runs of notebooks 02 and 03 on the real file (2014 to 2025, 13 metropolitan regions). The dashboard recomputes them from the filters.

## 1. Why this question and who it is for

I wanted a subject where the number we hear in the news and the situation on the ground can differ. The energy transition is a good example: we hear one national figure, but electricity is produced region by region, and the regions do not start from the same place. My question is how French regions are progressing toward a renewable electricity future.

I wrote the story for two kinds of readers: citizens and students who want to see where and how fast things move, and regional analysts who need to compare regions fairly. After the dashboard I want them to remember three things:

1. Renewable electricity grew a lot, and the growth is wind and solar, not hydro.
2. It replaced nuclear production much more than fossil production.
3. Regions are not equal. A high renewable share mostly means "no nuclear plant", so progress is the fairer comparison, and the gap between regions is not closing.

The story follows the pattern before/after over time combined with a comparison of regions. It goes from a hook (a national number hides the real question), to the context, to the insights (sources, regions, seasons, gaps), then to implications and next steps.

## 2. Data work

The dataset is *Production régionale mensuelle d'électricité par filière* (data.gouv.fr, RTE / ODRÉ, Licence Ouverte 2.0): 1,872 rows (13 regions × 144 months), six sources in GWh and the polygon of each region. In notebook 01 I found no duplicate and a balanced panel. The decisions I took in notebook 02:

- **864 empty nuclear values.** All of them are in six regions where every month is empty, so they are structural. I set them to 0 and added a flag. Nothing else was imputed.
- **34 negative values.** They are net production. I kept them with a flag, and set them to 0 only in the shares, because they pushed a renewable share above 100 % (the adjustment is 0.0001 % of the energy).
- **39 extreme values** (3 × IQR of the region's own history), all solar. Flagged, not deleted.
- **A 21 MB file.** The polygon was repeated on every row. I keep it once per region, so the processed tables are a few MB.

For the features I built shares, year-on-year growth, 12-month sums and shares, ranks among the 13 regions, a diversity index, a transition score (level) and a momentum score (speed). Their components are stored so that the app can test other weights. The same code runs in notebook 02 and in the app, and 39 validation checks were run on the tables.

## 3. What I found

| Finding | Evidence |
|---|---|
| Renewable output rose strongly | 97 to 156 TWh (+60 %); share 18.1 % to 28.4 % (+10.3 points); the 3-year averages give 18.2 % and 28.8 % |
| Wind and solar drive it, hydro does not | wind +32.7 TWh, solar +26.9, bioenergy +3.8, hydro −5.1; solar grows fastest (16.8 % per year), wind adds the most volume |
| Renewables replaced nuclear more than fossil | nuclear −42.8 TWh (−9.2 points of the mix), thermal −5.9 TWh (−1.2 points) |
| Level is not progress | highest shares: Bourgogne-Franche-Comté 93 %, PACA 87 %, Pays de la Loire 86 %. Biggest gains: Pays de la Loire +51.9 points, Île-de-France +29.0, Hauts-de-France +18.1 |
| The level mostly separates regions with and without nuclear | 77 % on average without nuclear (6 regions), 27 % with (7 regions); the 5 highest shares are regions without nuclear |
| Gaps are not closing | standard deviation of the regional shares 30.1 to 31.0 points, and 19.6 to 28.8 for wind, solar and bioenergy; no systematic catch-up (Spearman −0.22, p = 0.53, 13 regions) |
| Seasons matter, and wind and solar complement each other | seasonal shapes correlate at −0.91; the renewable share is highest in May (27.7 %) and lowest in September (20.6 %) |
| Two shares that look alike are different | mean of the 13 regional shares 49.9 %, weighted national share 28.4 % |

## 4. How the dashboard is built

The sidebar controls years, group of regions, regions and the indicator on the map. A header of six KPIs follows the filters. The charts are interactive (hover on every one): stacked production, change of the mix, lines by family, map and ranking, a level-versus-progress quadrant, heatmap, seasonal charts, decomposition, dispersion and scenario. Each section starts with a one-sentence headline, the quadrant shows the medians, and warning boxes appear when a selection is too small or is a subset. What-if: sliders on the weights of the transition score, and a scenario with written assumptions. The last tab shows live validation checks, missing values, duplicates, method, dictionary and licence.

## 5. Limits, uncertainty, ethics

- The data is production only. A region can look very renewable because it produces little of anything else.
- Weather moves the yearly values, so I compare 3-year averages when it matters. The portal also notes a revision of photovoltaic production for 2022 to 2024.
- I do not know why nuclear output moved: it is not in the data, so I only describe it.
- With 13 regions, the profiles and correlations are descriptive. A large gain in points can come from a small production, so volumes in TWh sit next to the points.
- The scenario is arithmetic, not a forecast. Only aggregated data is used, with no personal data.

## 6. Next steps

Installed capacity and connection queues, regional consumption (to move from a share of production to a share of consumption), hourly data for storage needs, and CO₂ intensity and prices.

## 7. Reproducibility

`requirements.txt` is pinned. `python -m utils.io build` downloads the file (cached) and rebuilds every table. Notebooks 01 to 03 give the audit, the cleaning and the exploration. `python -m pytest -q tests` checks the pipeline. `seeds.json` keeps the constants used for reproducible plots.
