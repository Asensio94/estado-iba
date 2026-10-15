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
# Pressure: artificial light at night from NASA Black Marble (VNP46A4, yearly). No sibling reads it:
# `python -m estado.cli luz` keeps the per-site series here once a month (Earthdata Login needed).
LIGHT_FILE = DOCS_DIR / "datos" / "luz.json"
LIGHT_PAGE = "https://blackmarble.gsfc.nasa.gov/"
LIGHT_BASELINE = (2012, 2014)  # the first three years of VIIRS
LIGHT_RECENT = 2  # years averaged as «now», so one odd year makes no signal
LIGHT_MIN_RISE = 0.25  # share over the baseline
LIGHT_MIN_ABS = 0.2  # nW·cm⁻²·sr⁻¹: near darkness a tiny change is a large share
LIGHT_MIN_PIXELS = 4  # ~70 ha: one or two pixels are too noisy to read a trend
LIGHT_PEERS = 25  # sites on each side in baseline brightness whose median change a site is held to

# State of reference: the birds each ZEPA was designated for, from the official Natura 2000 forms.
# `python -m estado.cli aves` writes them here once per yearly EEA release.
BIRDS_FILE = DOCS_DIR / "datos" / "aves.json"

FIRE_WINDOW_DAYS = 365
WINDOWS = {"fire": FIRE_WINDOW_DAYS}  # whoever sends the fires, the panel shows a year of them
LAND_STATES = {"confirmada", "provisional"}  # descartada, revertida and fusionada are not pressure
WETLAND_QUALITY = {"ok"}  # cloudy, partial or anomalous scenes do not set the state
WETLAND_MIN_YEARS = 3  # same-month reference needs at least this many earlier years
WETLAND_MAX_AGE_DAYS = 45  # an older observation is shown, but not as the current state

ACCENT = ("#a3336e", "#ec8fc0")
