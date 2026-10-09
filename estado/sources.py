"""Download what the sibling projects publish. Nothing here interprets the data."""

from __future__ import annotations

import csv
import io
import json
import time

import requests
from shapely import make_valid
from shapely.geometry import shape

from . import config

_session = requests.Session()
_session.headers["User-Agent"] = "estado-iba (+https://github.com/Asensio94/estado-iba)"


def _get(url: str) -> bytes:
    for attempt in range(3):
        try:
            r = _session.get(url, timeout=120)
            r.raise_for_status()
            return r.content
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def get_json(url: str) -> dict:
    return json.loads(_get(url).decode("utf-8"))


def get_csv(url: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(_get(url).decode("utf-8"))))


def wetlands(sites: dict[str, dict], min_overlap: float = 0.25) -> list[tuple[dict, list[dict], set[str]]]:
    """Each watched wetland with its series and the sites it falls in.

    A wetland belongs to a site when at least min_overlap of its area lies inside it: the
    wetland's own Natura code may be a ZEC rather than the ZEPA that covers the same water.
    """
    # Simplifying to ~300 m leaves some self-intersecting rings; make_valid repairs them for the overlay.
    shapes = {code: make_valid(shape(s["geometry"])) for code, s in sites.items()}
    out = []
    for slug in config.WETLANDS:
        feature = get_json(config.WETLAND_SITE_URL.format(slug=slug))
        geom = make_valid(shape(feature["geometry"]))
        inside = {code for code, g in shapes.items()
                  if g.intersects(geom) and g.intersection(geom).area >= min_overlap * geom.area}
        rows = get_csv(config.WETLAND_SERIES_URL.format(slug=slug))
        out.append(({"slug": slug, "name": feature["properties"]["name"]}, rows, inside))
    return out
