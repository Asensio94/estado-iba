"""Download what the sibling projects publish. Nothing here interprets the data."""

from __future__ import annotations

import csv
import io
import json
import time
from datetime import date
from email.utils import parsedate_to_datetime

import requests
from . import config
from .places import polygonal

_session = requests.Session()
_session.headers["User-Agent"] = "estado-iba (+https://github.com/Asensio94/estado-iba)"


def _get(url: str) -> bytes:
    return _response(url).content


def _response(url: str) -> requests.Response:
    for attempt in range(3):
        try:
            r = _session.get(url, timeout=180)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def get_csv_dated(url: str) -> tuple[list[dict], str]:
    """Rows of a CSV and the date the server says it was last modified (today if it does not say)."""
    r = _response(url)
    stamp = r.headers.get("Last-Modified")
    day = parsedate_to_datetime(stamp).date().isoformat() if stamp else date.today().isoformat()
    return list(csv.DictReader(io.StringIO(r.content.decode("utf-8")))), day


def caudal() -> tuple[list[dict], dict[str, list[dict]], list[dict]]:
    """Stations, daily flows per station and the legal minimum flows of caudal-ecologico."""
    stations = get_csv(f"{config.FLOW_RAW}/stations.csv")
    flows = {}
    for st in stations:
        try:
            flows[st["station_id"]] = get_csv(f"{config.FLOW_RAW}/flows/{st['station_id']}.csv")
        except requests.HTTPError:
            flows[st["station_id"]] = []
    req = [r for b in config.FLOW_BASINS for r in get_csv(f"{config.FLOW_RAW}/requirements/{b}.csv")]
    return stations, flows, req


def get_json(url: str) -> dict:
    return json.loads(_get(url).decode("utf-8"))


def get_csv(url: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(_get(url).decode("utf-8"))))


def wetlands(sites: dict[str, dict], min_overlap: float = 0.25) -> list[tuple[dict, list[dict], set[str]]]:
    """Each watched wetland with its series and the sites it falls in.

    A wetland belongs to a site when at least min_overlap of its area lies inside it: the
    wetland's own Natura code may be a ZEC rather than the ZEPA that covers the same water.
    """
    shapes = {code: polygonal(s["geometry"]) for code, s in sites.items()}
    out = []
    for slug in config.WETLANDS:
        feature = get_json(config.WETLAND_SITE_URL.format(slug=slug))
        geom = polygonal(feature["geometry"])
        inside = {code for code, g in shapes.items()
                  if g.intersects(geom) and g.intersection(geom).area >= min_overlap * geom.area}
        rows = get_csv(config.WETLAND_SERIES_URL.format(slug=slug))
        c = geom.representative_point()
        out.append(({"slug": slug, "name": feature["properties"]["name"], "point": [round(c.x, 4), round(c.y, 4)]},
                    rows, inside))
    return out
