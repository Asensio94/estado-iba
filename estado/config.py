"""Where the sibling projects publish what this panel reads, and the few fixed parameters."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"

OWNER = "Asensio94"
PAGES = "https://asensio94.github.io"
RAW = f"https://raw.githubusercontent.com/{OWNER}"
API = "https://api.github.com"

# Every sibling with a bot, for the daily health check, and how many days its signals.json may
# age before it counts as stale (None: no limit). Each figure leaves a margin over its cron.
SIBLINGS = {
    "observatorio-alegaciones": 3,  # Monday to Saturday
    "vigia-incendios": 2,  # hourly
    "centinela-natura": 3,
    "vigilancia-humedales": 3,
    "caudal-ecologico": 3,
    "sub-nocte": 3,
    "grafo-promotores": 3,  # Monday to Saturday
    "cartera-cotizadas": 3,  # Monday to Saturday
    "depuracion-y-bano": 10,  # weekly
    "riesgo-tendidos-aves": 35,  # monthly
    "zona-inundable": 35,  # monthly
    "quien-tiene-sombra": 400,  # yearly
    "barbechos-esteparias": None,  # by hand, once a campaign
    "cuaderno-campo": None,  # published on push
    "estado-iba": 2,
}

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

# Municipalities with INE codes: IGN reference data, packaged as TopoJSON by es-atlas (~200 m).
MUNICIPALITIES_URL = "https://cdn.jsdelivr.net/npm/es-atlas@0.6.0/es/municipalities.json"
# Who is behind each project: grafo links BOE acts to companies and groups, cartera to listed companies.
GRAFO_URL = f"{RAW}/grafo-promotores/main/data/grafo.json"
CARTERA_URL = f"{PAGES}/cartera-cotizadas/datos/cartera.json"
# State: river flow against the legal minimum (Júcar and Guadiana).
FLOW_RAW = f"{RAW}/caudal-ecologico/main/data"
FLOW_BASINS = ["jucar", "guadiana"]
# Nocturnal migration forecast per city.
MIGRATION_URL = f"{PAGES}/sub-nocte/data/phase3_forecast.csv"
# Pressure: power-line risk per pylon and span, only in the regions already modelled.
LINES_URL = PAGES + "/riesgo-tendidos-aves/{region}/ranking_elements.csv"
LINE_REGIONS = ["cantabria", "estrecho"]

FIRE_WINDOW_DAYS = 365
WINDOWS = {"fire": FIRE_WINDOW_DAYS}  # whoever sends the fires, the panel shows a year of them
LAND_STATES = {"confirmada", "provisional"}  # descartada, revertida and fusionada are not pressure
WETLAND_QUALITY = {"ok"}  # cloudy, partial or anomalous scenes do not set the state
WETLAND_MIN_YEARS = 3  # same-month reference needs at least this many earlier years
WETLAND_MAX_AGE_DAYS = 45  # an older observation is shown, but not as the current state

ACCENT = ("#a3336e", "#ec8fc0")
