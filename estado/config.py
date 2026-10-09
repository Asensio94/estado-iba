"""Where the sibling projects publish what this panel reads, and the few fixed parameters."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"

PAGES = "https://asensio94.github.io"
RAW = "https://raw.githubusercontent.com/Asensio94"

# Site units. Until SEO/BirdLife clears the reuse of the IBA layer, the panel works on the
# Special Protection Areas (ZEPA) of Natura 2000: open data, and the legal figure most IBAs
# became. Vigía already publishes every Spanish Natura site simplified to 0.003° (~300 m).
SITES_URL = f"{PAGES}/vigia-incendios/natura.geojson"
SITE_KIND = "ZEPA"

# Pressure: environmental assessments in public consultation and their resolutions.
PROJECTS_URL = f"{RAW}/observatorio-alegaciones/main/data/estado.json"
# Pressure: fires seen from satellite, with hectares per Natura site.
FIRES_URL = f"{PAGES}/vigia-incendios/incendios.geojson"
# Pressure: land-cover change alerts. Only Cantabria is watched, so coverage comes from its site list.
LAND_URL = f"{PAGES}/centinela-natura/alertas.geojson"
LAND_SITES_URL = f"{PAGES}/centinela-natura/espacios.geojson"
# State: surface water of the wetlands watched by vigilancia-humedales.
WETLAND_SERIES_URL = RAW + "/vigilancia-humedales/master/data/series/{slug}.csv"
WETLAND_SITE_URL = RAW + "/vigilancia-humedales/master/data/sites/{slug}.geojson"
WETLANDS = ["donana", "mar-menor", "tablas-daimiel", "albufera-valencia", "fuente-piedra", "gallocanta"]

FIRE_WINDOW_DAYS = 365
LAND_STATES = {"confirmada", "provisional"}  # descartada, revertida and fusionada are not pressure
WETLAND_QUALITY = {"ok"}  # cloudy, partial or anomalous scenes do not set the state
WETLAND_MIN_YEARS = 3  # same-month reference needs at least this many earlier years
WETLAND_MAX_AGE_DAYS = 45  # an older observation is shown, but not as the current state

ACCENT = ("#a3336e", "#ec8fc0")
