"""France: its SPAs (ZPS) from the EEA and its communes and regions from the IGN.

The EEA serves every Natura 2000 site of the latest release through a public map service, so the
407 French ZPS come in one request, already simplified to the ~300 m of the Spanish layer.

The communes come from IGN Admin Express COG-CARTO (Licence Ouverte 2.0), the generalised layer
the IGN makes for maps, through its public WFS. At full resolution the 34 877 communes weigh
~150 MB, too much for a daily build, and they change once a year with the official code (COG): so
`python -m estado.cli communes` downloads them once a year, simplifies them to the same ~200 m as
the Spanish municipalities and keeps them in estado/ref/communes_fr.json.gz.

Natura 2000 does not apply in the overseas departments, so only metropolitan France is kept.
"""

from __future__ import annotations

import gzip
import json
from datetime import date
from pathlib import Path

import requests
from shapely.geometry import mapping, shape

from .places import polygonal

SPA_URL = ("https://bio.discomap.eea.europa.eu/arcgis/rest/services/ProtectedSites/Natura2000Sites/MapServer/1/query"
           "?where=MS%3D%27FR%27&outFields=SITECODE,SITENAME,RELEASE_DATE&returnGeometry=true&outSR=4326"
           "&maxAllowableOffset=0.003&geometryPrecision=5&f=geojson")
SPA_PAGE = "https://www.eea.europa.eu/en/datahub/datahubitem-view/6fc8ad2d-195d-40f4-bdec-576e7d1268e4"
WFS_URL = "https://data.geopf.fr/wfs/ows"
LAYER = "ADMINEXPRESS-COG-CARTO.LATEST"
OVERSEAS = {"01", "02", "03", "04", "06"}  # Guadeloupe, Martinique, Guyane, La Réunion, Mayotte
REF_FILE = Path(__file__).with_name("ref") / "communes_fr.json.gz"
SIMPLIFY = 0.002  # degrees, ~200 m: the resolution of the Spanish municipalities
PAGE = 5000


def load_sites(fc: dict) -> dict[str, dict]:
    """The ZPS with code, name and geometry, as the Spanish sites are loaded."""
    sites = {}
    for f in fc["features"]:
        p = f["properties"]
        if f.get("geometry") and p["SITECODE"].startswith("FR"):
            sites[p["SITECODE"]] = {"code": p["SITECODE"], "name": p["SITENAME"].strip(), "geometry": f["geometry"]}
    return sites


def _features(session: requests.Session, layer: str, fields: str) -> list[dict]:
    out, start = [], 0
    while True:
        r = session.get(WFS_URL, params={
            "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature", "TYPENAMES": f"{LAYER}:{layer}",
            "OUTPUTFORMAT": "application/json", "COUNT": PAGE, "STARTINDEX": start, "SORTBY": "code_insee",
            "PROPERTYNAME": fields}, timeout=300)
        r.raise_for_status()
        got = r.json()["features"]
        out += got
        if len(got) < PAGE:
            return out
        start += PAGE


def _small(geometry: dict, tolerance: float, nd: int = 4) -> dict | None:
    g = polygonal(geometry)
    if g.is_empty:
        return None
    s = g.simplify(tolerance, preserve_topology=True)
    if s.is_empty:
        s = g

    def r(c):
        return [round(c[0], nd), round(c[1], nd)] if isinstance(c[0], float | int) else [r(x) for x in c]

    m = mapping(s)
    return {"type": m["type"], "coordinates": r(json.loads(json.dumps(m["coordinates"])))}


def download(out: Path = REF_FILE, session: requests.Session | None = None, today: date | None = None) -> dict:
    """Fetch the metropolitan communes, departments and regions from the IGN and keep them simplified."""
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", "estado-iba (+https://github.com/Asensio94/estado-iba)")
    regions = [f for f in _features(session, "region", "code_insee,nom_officiel,geometrie")
               if f["properties"]["code_insee"] not in OVERSEAS]
    depts = _features(session, "departement", "code_insee,nom_officiel,code_insee_de_la_region")
    communes = [f for f in _features(session, "commune", "code_insee,nom_officiel,code_insee_du_departement,"
                                                          "code_insee_de_la_region,geometrie")
                if f["properties"]["code_insee_de_la_region"] not in OVERSEAS]
    doc = {
        "source": f"IGN Admin Express COG-CARTO ({LAYER}), Licence Ouverte 2.0",
        "updated": (today or date.today()).isoformat(),
        "regions": [{"id": f["properties"]["code_insee"], "name": f["properties"]["nom_officiel"],
                     "geometry": _small(f["geometry"], 0.005)} for f in regions],
        "departments": {f["properties"]["code_insee"]: f["properties"]["nom_officiel"] for f in depts
                        if f["properties"]["code_insee_de_la_region"] not in OVERSEAS},
        "communes": [[f["properties"]["code_insee"], f["properties"]["nom_officiel"],
                      f["properties"]["code_insee_du_departement"], f["properties"]["code_insee_de_la_region"],
                      _small(f["geometry"], SIMPLIFY)] for f in communes],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wt", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    return {"regions": len(doc["regions"]), "departments": len(doc["departments"]), "communes": len(doc["communes"]),
            "bytes": out.stat().st_size}


def load_reference(path: Path = REF_FILE) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)
