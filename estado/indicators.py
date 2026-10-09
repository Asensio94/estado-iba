"""Per-site indicators from what the sibling projects publish.

Every function is pure: it takes the parsed sources and returns plain dicts keyed by site code,
so the same code works for ZEPA today and for IBAs once their sibling cross-checks carry them.
Each indicator keeps the records it counts, so every figure on the page links to its source.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta


def load_sites(natura: dict, kind: str) -> dict[str, dict]:
    """Sites of one kind ("ZEPA" also matches "ZEC y ZEPA") with name and geometry."""
    sites = {}
    for f in natura["features"]:
        p = f["properties"]
        if kind in p["tipo"]:
            sites[p["codigo"]] = {"code": p["codigo"], "name": p["nombre"], "geometry": f["geometry"]}
    return sites


def _codes(items: list[dict] | None) -> set[str]:
    return {n.get("sitecode") or n.get("codigo") for n in items or []}


def projects(state: dict, codes: set[str], today: date) -> dict[str, list[dict]]:
    """Notices in public consultation and the resolutions paired with them, per site.

    A notice reaches a site through its cadastral footprint when there is one (precise), and
    otherwise through the municipalities it names (approximate: the whole municipality is
    crossed with Natura 2000). Resolutions carry no geometry, so they inherit the sites of the
    notice observatorio paired them with.
    """
    out: dict[str, list[dict]] = {}
    notice_sites: dict[str, tuple[set[str], str]] = {}
    for n in state["anuncios"].values():
        footprint = _codes((n.get("footprint") or {}).get("natura"))
        hit, precision = (footprint, "parcelas") if footprint else (_codes(n.get("natura")), "municipio")
        hit &= codes
        notice_sites[n["identificador"]] = (hit, precision)
        deadline = n.get("fecha_limite")
        for code in hit:
            out.setdefault(code, []).append({
                "id": n["identificador"], "kind": "anuncio", "date": n["fecha"], "title": n["titulo"],
                "category": n.get("categoria"), "mw": n.get("potencia_mw"), "url": n["url_html"],
                "precision": precision, "deadline": deadline,
                "open": bool(deadline) and date.fromisoformat(deadline) >= today,
            })
    for r in state["resoluciones"].values():
        hit, precision = notice_sites.get(r.get("emparejado_con") or "", (set(), ""))
        for code in hit:
            out.setdefault(code, []).append({
                "id": r["identificador"], "kind": "resolucion", "date": r["fecha"], "title": r["titulo"],
                "category": r.get("categoria"), "mw": r.get("potencia_mw"), "url": r["url_html"],
                "precision": precision, "outcome": r.get("sentido_etiqueta") or r.get("sentido"),
            })
    for items in out.values():
        items.sort(key=lambda x: x["date"], reverse=True)
    return out


def fires(fc: dict, codes: set[str], today: date, window_days: int) -> dict[str, list[dict]]:
    """Fires of the last window_days touching each site, with the hectares inside it.

    The Sentinel-2 burnt area is used when vigía has it; otherwise the extent of the hot pixels,
    which overstates small fires (a 1 ha fire lights a 14 ha VIIRS pixel) and is flagged as such.
    """
    since = today - timedelta(days=window_days)
    out: dict[str, list[dict]] = {}
    for f in fc["features"]:
        p = f["properties"]
        if date.fromisoformat(p["primera"][:10]) < since:
            continue
        s2 = p.get("perimetro_s2") or {}
        by_code = {n["codigo"]: n.get("ha") for n in p.get("natura") or []}
        source = "focos"
        if s2.get("natura"):
            by_code = {n["codigo"]: n.get("ha") for n in s2["natura"]}
            source = "sentinel2"
        for code, ha in by_code.items():
            if code in codes:
                out.setdefault(code, []).append({
                    "id": p["id"], "date": p["primera"][:10], "ha": ha, "source": source,
                    "final": bool(s2.get("definitivo")), "place": (p.get("lugar") or {}).get("municipio"),
                })
    for items in out.values():
        items.sort(key=lambda x: x["date"], reverse=True)
    return out


def land_change(fc: dict, watched: set[str], codes: set[str], states: set[str]) -> dict[str, list[dict]]:
    """Land-cover change alerts per site, only where centinela watches (watched codes)."""
    out: dict[str, list[dict]] = {code: [] for code in watched & codes}
    for f in fc["features"]:
        p = f["properties"]
        if p["estado"] not in states:
            continue
        for e in p.get("espacios") or []:
            if e["codigo"] in out:
                out[e["codigo"]].append({
                    "id": p["id"], "date": p["detectada"], "ha": p["ha"], "state": p["estado"],
                    "class": p.get("clase_nombre"), "permit": p.get("cruce"),
                })
    for items in out.values():
        items.sort(key=lambda x: x["date"], reverse=True)
    return out


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
    ref = {}
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


def panel(sites: dict[str, dict], proj: dict, fire: dict, land: dict, wetlands: dict[str, list[dict]]) -> list[dict]:
    """One row per site. No composite score: the page sorts by any indicator, never by a blend."""
    rows = []
    for code, s in sites.items():
        p = proj.get(code, [])
        f = fire.get(code, [])
        notices = [x for x in p if x["kind"] == "anuncio"]
        rows.append({
            "code": code, "name": s["name"],
            "projects": p,
            "n_notices": len(notices),
            "n_precise": sum(x["precision"] == "parcelas" for x in notices),
            "n_open": sum(x["open"] for x in notices),
            "n_resolutions": len(p) - len(notices),
            "fires": f,
            "fire_ha": round(sum(x["ha"] or 0 for x in f), 1),
            "land": land.get(code),  # None = not watched, [] = watched and nothing found
            "land_ha": round(sum(x["ha"] for x in land[code]), 1) if code in land else None,
            "wetlands": wetlands.get(code, []),
        })
    rows.sort(key=lambda r: (-r["n_precise"], -r["n_open"], -r["n_notices"], -r["fire_ha"], r["name"]))
    return rows
