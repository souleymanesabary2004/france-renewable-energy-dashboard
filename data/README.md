# Data

## Dataset used

**Production régionale mensuelle d'électricité par filière** (monthly electricity production by region and source, from 2014).

- Portal: data.gouv.fr, published by Open Data Réseaux Énergies (ODRÉ); creator and publisher: RTE
- Page: https://www.data.gouv.fr/datasets/production-regionale-mensuelle-delectricite-par-filiere
- Direct CSV link: https://www.data.gouv.fr/api/1/datasets/r/27b32325-0f02-4fb2-871c-dc743af1d7db (about 21 MB, 1,872 rows)
- Licence: Licence Ouverte / Open Licence version 2.0 (Etalab): reuse is free if the source and the date of the last update are cited
- Last update seen on the portal: 25 February 2026 (the portal notes that photovoltaic production of 2022-2024 was revised upward after a new estimate of self-consumption)
- Unit: GWh per region and per month; 13 metropolitan regions, 2014-01 to 2025-12

## What is in this folder

| Folder | Content | In the zip? |
|---|---|---|
| `raw/` | the CSV above, downloaded by `python -m utils.io download` (cached) | no (link + script instead) |
| `processed/` | tables built by `python -m utils.io build` (same code as notebook 02): cleaned data, features, star schema, annual tables, GeoJSON, dictionary | yes (a few MB) |

The app reads `processed/`. If it is missing, the app downloads the raw file and rebuilds it (first start only).
