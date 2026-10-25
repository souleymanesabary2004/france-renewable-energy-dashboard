"""Constants shared by notebooks 01-02 and the Streamlit app.

Everything that is an assumption (energy families, weights of the scores,
scaling percentiles) is defined here once, so the app and the reports use the
same values.
"""

RAW_FILE = "production-regionale-mensuelle-filiere.csv"
LOCAL_RAW_PATH = (r"C:\Users\HP\Desktop\EFREI\2026-2027\Data_anlysis"
                  r"\personnal_project_Efrei\data\production-regionale-mensuelle-filiere.csv")

# ---------------------------------------------------------------- sources
SOURCES = ["nuclear", "thermal", "hydro", "wind", "solar", "bioenergy"]
GWH = {s: f"{s}_gwh" for s in SOURCES}

# raw column (snake_case of the CSV header) -> short name used everywhere else
RAW_TO_SHORT = {
    "production_nucleaire_gwh": "nuclear_gwh",
    "production_thermique_gwh": "thermal_gwh",
    "production_hydraulique_gwh": "hydro_gwh",
    "production_eolienne_gwh": "wind_gwh",
    "production_solaire_gwh": "solar_gwh",
    "production_bioenergies_gwh": "bioenergy_gwh",
}
RAW_COLUMNS_EXPECTED = ["mois", "code_insee_region", "region", *RAW_TO_SHORT,
                        "geo_shape_region", "geo_point_region"]

# assumption: classification of the sources
FAMILY = {"nuclear": "Nuclear", "thermal": "Fossil / thermal", "hydro": "Renewable",
          "wind": "Renewable", "solar": "Renewable", "bioenergy": "Renewable"}
RENEWABLE = ["hydro", "wind", "solar", "bioenergy"]
NEW_RENEWABLES = ["wind", "solar", "bioenergy"]          # renewables without hydro

LABEL = {"nuclear": "Nuclear", "thermal": "Thermal", "hydro": "Hydro",
         "wind": "Wind", "solar": "Solar", "bioenergy": "Bioenergy"}
# colour-blind safe palette (Okabe-Ito)
COLOR = {"nuclear": "#E69F00", "thermal": "#7F7F7F", "hydro": "#0072B2",
         "wind": "#56B4E9", "solar": "#D55E00", "bioenergy": "#009E73"}

# ---------------------------------------------------------------- regions
OFFICIAL_REGIONS = {
    "84": "Auvergne-Rhône-Alpes", "27": "Bourgogne-Franche-Comté", "53": "Bretagne",
    "24": "Centre-Val de Loire", "94": "Corse", "44": "Grand Est", "32": "Hauts-de-France",
    "11": "Île-de-France", "28": "Normandie", "75": "Nouvelle-Aquitaine", "76": "Occitanie",
    "52": "Pays de la Loire", "93": "Provence-Alpes-Côte d'Azur"}
REGION_SHORT = {
    "84": "ARA", "27": "BFC", "53": "Bretagne", "24": "CVL", "94": "Corse", "44": "Grand Est",
    "32": "HdF", "11": "IDF", "28": "Normandie", "75": "N-Aquitaine", "76": "Occitanie",
    "52": "PdL", "93": "PACA"}

# ---------------------------------------------------------------- time
SEASON = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
          6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}
ROLL_WINDOW = 12

# ---------------------------------------------------------------- scores
WEIGHTS_TRANSITION = {"renewable": 0.35, "new_renewables": 0.30, "fossil_free": 0.20, "diversity": 0.15}
WEIGHTS_MOMENTUM = {"renewable": 0.50, "new_renewables": 0.50}
SCALE_PERCENTILES = (1, 99)          # robust min / max used to scale components to 0-100
EXTREME_IQR_K = 3.0

# ---------------------------------------------------------------- audit (notebook 01)
EXPECTED_AUDIT = {
    "rows": 1872, "regions": 13, "months": 144, "missing_cells": 864,
    "nuclear_gwh": 4398501.37, "hydro_gwh": 743387.07, "thermal_gwh": 431166.08,
    "wind_gwh": 407731.99, "solar_gwh": 179541.21, "bioenergy_gwh": 113547.44,
    "neg_nuclear": 6, "neg_thermal": 26, "neg_wind": 2,
}
