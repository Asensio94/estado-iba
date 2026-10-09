"""Per-site figures from signals (see CONTRATO.md).

Every function is pure. The same code works for ZEPA today and for IBAs once the sibling
cross-checks carry their codes. There is no composite score: the page sorts by any one figure.
"""

from __future__ import annotations

import statistics
from datetime import date


def load_sites(natura: dict, kind: str) -> dict[str, dict]:
    """Sites of one kind ("ZEPA" also matches "ZEC y ZEPA") with name and geometry."""
    sites = {}
    for f in natura["features"]:
        p = f["properties"]
        if kind in p["tipo"]:
            sites[p["codigo"]] = {"code": p["codigo"], "name": p["nombre"], "geometry": f["geometry"]}
    return sites


def wetland_state(rows: list[dict], today: date, quality: set[str], min_years: int, max_age: int,
                  dry_share: float = 0.05) -> dict | None:
    """Latest good observation of surface water against the same month in earlier years.

    The ratio compares water_ha with the median of the good observations of that calendar month
    in previous years; it needs at least min_years of them to say anything. Seasonal lagoons
    that are usually dry in that month (reference under dry_share of the series maximum) get no
    ratio: dividing by almost nothing would turn a normal wet year into thousands of percent.
    """
    good = [r for r in rows if r["quality"] in quality and r.get("water_ha") not in (None, "")]
    if not good:
        return None
    last = max(good, key=lambda r: r["date"])
    d = date.fromisoformat(last["date"])
    ref: dict[int, list[float]] = {}
    for r in good:
        rd = date.fromisoformat(r["date"])
        if rd.month == d.month and rd.year < d.year:
            ref.setdefault(rd.year, []).append(float(r["water_ha"]))
    median = statistics.median(statistics.median(v) for v in ref.values()) if len(ref) >= min_years else None
    water = float(last["water_ha"])
    dry = median is not None and median < dry_share * max(float(r["water_ha"]) for r in good)
    return {
        "date": last["date"], "water_ha": round(water, 1), "ref_ha": None if median is None else round(median, 1),
        "ratio": round(water / median, 2) if median and not dry else None, "dry_ref": dry, "ref_years": sorted(ref),
        "current": (today - d).days <= max_age,
    }


def restrict(signals: list[dict], codes) -> list[dict]:
    """Keep only the sites this panel speaks of; a signal left with no site still serves its municipalities.

    Siblings cross with every Natura 2000 site, so a ZEC-only code would show as a bare code
    in a ZEPA panel. A signal with neither site nor municipality has no place to be shown.
    """
    out = []
    for s in signals:
        s = {**s, "sites": [x for x in s["sites"] if x["code"] in codes]}
        if s["sites"] or s["municipalities"]:
            out.append(s)
    return out


def _watched(coverage: dict | None, code: str) -> bool:
    return coverage is not None and (coverage["sites"] is None or code in coverage["sites"])


def summary(sites: dict[str, dict], signals: list[dict], coverage: dict[str, dict], today: date) -> dict[str, dict]:
    """The figures each site is sorted and coloured by.

    A count is None when no sibling watches that pressure in the site: «not watched» must never
    read as «nothing found».
    """
    by_site: dict[str, list[tuple[dict, dict]]] = {}
    for s in signals:
        for x in s["sites"]:
            by_site.setdefault(x["code"], []).append((s, x))
    out = {}
    for code in sites:
        items = by_site.get(code, [])
        notices = [s for s, _ in items if s["kind"] == "notice"]
        fires = [x for s, x in items if s["kind"] == "fire"]
        water = [s["details"]["ratio"] for s, _ in items if s["kind"] == "wetland_water"
                 and s["details"]["current"] and s["details"]["ratio"] is not None]
        out[code] = {
            "notices": len(notices),
            "precise": sum(s["precision"] == "parcelas" for s in notices),
            "open": sum(bool(s["deadline"]) and s["deadline"] >= today.isoformat() for s in notices),
            "resolutions": sum(s["kind"] == "resolution" for s, _ in items),
            "fires": len(fires),
            "fire_ha": round(sum(x.get("ha") or 0 for x in fires), 1),
            "land": sum(s["kind"] == "land_change" for s, _ in items)
            if _watched(coverage.get("centinela-natura"), code) else None,
            "lines": sum(s["value"]["amount"] for s, _ in items if s["kind"] == "power_line")
            if _watched(coverage.get("riesgo-tendidos-aves"), code) else None,
            "flow": sum(s["kind"] == "river_flow" for s, _ in items),
            "water": min(water, default=None),
        }
    return out
