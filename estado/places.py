"""Municipalities: decode the IGN TopoJSON, cross it with the sites, and match names to INE codes.

France's communes (INSEE codes) go through the same crossing, from the reference france.py keeps.
"""

from __future__ import annotations

import re
import unicodedata

from shapely import STRtree, make_valid, unary_union
from shapely.geometry import shape

KM2_DEG2 = 1.06e-4  # one km² in square degrees around 40° N; good enough for a threshold
KM2_DEG2_FR = 1.17e-4  # the same around 46.5° N


def polygonal(geometry: dict):
    """A valid areal shape from a GeoJSON geometry.

    Simplified to ~300 m, some rings cross themselves and some small parts collapse into lines or
    single points. Each part is repaired on its own and only areas are kept: GEOS 3.14 refuses to
    repair a MultiPolygon with a part collapsed into a point, which older versions let through.
    """
    g = shape(geometry)
    fixed = [make_valid(p) for p in getattr(g, "geoms", [g])]
    return unary_union([q for p in fixed for q in getattr(p, "geoms", [p]) if q.geom_type in ("Polygon", "MultiPolygon")])


def _decode_arcs(topo: dict) -> list[list[tuple[float, float]]]:
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    return arcs


def _ring(arcs: list, refs: list[int]) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in refs:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(a[1:] if pts else a)
    return pts


def topo_features(topo: dict, name: str) -> list[dict]:
    """GeoJSON-like features of one TopoJSON object (Polygon and MultiPolygon only)."""
    arcs = _decode_arcs(topo)
    out = []
    for g in topo["objects"][name]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]] if g["type"] == "Polygon" else []
        # Quantization collapses tiny holes and islets to fewer than four points: drop them.
        rings = [[r for r in (_ring(arcs, a) for a in p) if len(r) >= 4] for p in polys]
        rings = [p for p in rings if p]
        if not rings:
            continue
        geom = {"type": "MultiPolygon", "coordinates": rings}
        out.append({"id": g.get("id"), "properties": g.get("properties") or {}, "geometry": geom})
    return out


# Short names for menus and breadcrumbs; the IGN layer carries the official ones.
REGION_SHORT = {
    "01": "Andalucía", "02": "Aragón", "03": "Asturias", "04": "Illes Balears", "05": "Canarias",
    "06": "Cantabria", "07": "Castilla y León", "08": "Castilla-La Mancha", "09": "Cataluña",
    "10": "Comunitat Valenciana", "11": "Extremadura", "12": "Galicia", "13": "Madrid", "14": "Murcia",
    "15": "Navarra", "16": "País Vasco", "17": "La Rioja", "18": "Ceuta", "19": "Melilla",
}


def regions(topo: dict) -> list[dict]:
    """Autonomous communities and cities (Gibraltar, «20», is left out)."""
    return [{"id": f["id"], "name": REGION_SHORT.get(f["id"], f["properties"]["name"]),
             "official": f["properties"]["name"], "geom": polygonal(f["geometry"])}
            for f in topo_features(topo, "autonomous_regions") if f["id"] in REGION_SHORT]


def municipalities(topo: dict, sites: dict[str, dict], regs: list[dict], min_km2: float = 1.0,
                   min_share: float = 0.1, min_site_share: float = 0.25) -> list[dict]:
    """Every municipality with its province, community and the sites it overlaps.

    Both layers are simplified (~200-300 m), so neighbours share slivers along their borders. A
    site counts for a municipality when the overlap is at least min_km2, or min_share of the
    municipality (small municipalities inside a big site), or min_site_share of the site (small
    sites inside a big municipality, such as the lesser kestrel colonies in village churches).
    """
    provinces = topo_features(topo, "provinces")
    names = {f["id"]: f["properties"]["name"] for f in provinces}
    reg_tree = STRtree([r["geom"] for r in regs])

    def region_at(point):
        hit = reg_tree.query(point, predicate="intersects")
        return regs[hit[0]]["id"] if len(hit) else ""

    region_of = {f["id"]: region_at(polygonal(f["geometry"]).representative_point()) for f in provinces}
    overlaps = _crossing(sites, min_km2 * KM2_DEG2, min_share, min_site_share)
    out = []
    for f in topo_features(topo, "municipalities"):
        g = polygonal(f["geometry"])
        hits = overlaps(g)
        # Simplified into a line, a municipality has no area left (53046, in Burgos) but still a place.
        c = shape(f["geometry"]).centroid if g.is_empty else g.representative_point()
        prov = f["id"][:2]
        # Land held in common by several municipalities (INE «53», like the Bardenas Reales) has no
        # province: its own point says which community it lies in.
        out.append({"ine": f["id"], "name": f["properties"]["name"], "province": names.get(prov, ""),
                    "region": region_of.get(prov) or region_at(c), "point": [round(c.x, 4), round(c.y, 4)],
                    "sites": sorted(hits), "geom": g})
    return out


def _crossing(sites: dict[str, dict], min_area: float, min_share: float, min_site_share: float):
    """municipality shape -> the codes of the sites it overlaps enough (see municipalities)."""
    codes = list(sites)
    geoms = [polygonal(sites[c]["geometry"]) for c in codes]
    tree = STRtree(geoms)

    def overlaps(g) -> list[str]:
        hits = []
        for i in tree.query(g, predicate="intersects"):
            area = g.intersection(geoms[i]).area
            if area >= min_area or area >= min_share * g.area or area >= min_site_share * geoms[i].area:
                hits.append(codes[i])
        return sorted(hits)

    return overlaps


def regions_fr(ref: dict) -> list[dict]:
    """The metropolitan regions of France, from the reference france.py keeps."""
    return [{"id": r["id"], "name": r["name"], "official": r["name"], "geom": polygonal(r["geometry"])}
            for r in ref["regions"]]


def communes_fr(ref: dict, sites: dict[str, dict], min_km2: float = 1.0, min_share: float = 0.1,
                min_site_share: float = 0.25) -> list[dict]:
    """Every metropolitan commune with its department, region and the sites it overlaps.

    Same rule and same dict as the Spanish municipalities: «ine» holds the INSEE code (2A004 in
    Corsica) and «province» the department. The IGN gives each commune its region, so there is no
    point to look up.
    """
    overlaps = _crossing(sites, min_km2 * KM2_DEG2_FR, min_share, min_site_share)
    out = []
    for code, name, dept, region, geometry in ref["communes"]:
        g = polygonal(geometry) if geometry else None
        empty = g is None or g.is_empty
        c = (shape(geometry).centroid if geometry else None) if empty else g.representative_point()
        if c is None or c.is_empty:
            continue
        out.append({"ine": code, "name": name, "province": ref["departments"].get(dept, ""), "region": region,
                    "point": [round(c.x, 4), round(c.y, 4)], "sites": [] if empty else overlaps(g),
                    "geom": g if g is not None else shape(geometry)})
    return out


def site_regions(munis: list[dict], shapes: dict, regs: list[dict]) -> dict[str, dict]:
    """The communities each site lies in, through its municipalities.

    A site that overlaps no municipality lies at sea or on islets the IGN layer leaves out. It
    goes to the community with the nearest coast and is flagged as marine: the State, not the
    community, manages the marine sites.
    """
    by_site: dict[str, set[str]] = {}
    for m in munis:
        for c in m["sites"]:
            if m["region"]:
                by_site.setdefault(c, set()).add(m["region"])
    out = {}
    for code, g in shapes.items():
        if code in by_site:
            out[code] = {"regions": sorted(by_site[code]), "marine": False}
        else:
            near = min(regs, key=lambda r: r["geom"].distance(g))
            out[code] = {"regions": [near["id"]], "marine": True}
    return out


def locator(munis: list[dict], shapes: dict, tolerance: float = 0.005):
    """(lon, lat) -> (site codes, INE codes) for a point.

    Gauging stations sit on the river line, and riverside sites are thin strips simplified to
    ~300 m, so a point counts for a site within tolerance degrees (~500 m) of it.
    """
    from shapely.geometry import Point

    codes = list(shapes)
    site_tree = STRtree([shapes[c] for c in codes])
    muni_tree = STRtree([m["geom"] for m in munis])

    def locate(lon: float, lat: float) -> tuple[list[str], list[str]]:
        p = Point(lon, lat)
        sites = sorted(codes[i] for i in site_tree.query(p, predicate="dwithin", distance=tolerance))
        inside = muni_tree.query(p, predicate="intersects")
        return sites, [munis[i]["ine"] for i in inside[:1]]

    return locate


# Articles a place name may start with, or carry at the end after a comma, in each country.
ARTICLES = {"ES": "el|la|los|las|lo|o|a|os|as|es|sa|ses|els|les", "FR": "le|la|les"}


def name_key(s: str, country: str = "ES") -> str:
    """Comparable form of a place name: no accents, articles moved or dropped, no punctuation.

    «Barrios, Los», «Los Barrios» and «LOS BARRIOS» all give «barrios»; bilingual names keep
    each side so «Alacant/Alicante» matches either. In France, «Le Havre» and «Havre, Le» give «havre».
    """
    art = ARTICLES[country]
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()
    s = re.sub(rf",\s*({art}|l')$", "", s.strip())
    s = re.sub(rf"^({art})\s+|^l'", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def _plain(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower().strip()


def name_index(munis: list[dict], country: str = "ES") -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = {}
    for m in munis:
        for part in re.split(r"\s*/\s*", m["name"]):
            idx.setdefault(name_key(part, country), []).append(m)
    return idx


def resolve(idx: dict[str, list[dict]], name: str, provinces: list[str] | None = None,
            country: str = "ES") -> str | None:
    """INE (or INSEE) code for a municipality name; provinces (departments) break ties between homonyms."""
    hits = idx.get(name_key(name, country), [])
    if len(hits) > 1:  # «Granada» before «La Granada»: an exact name wins over one that only matches without its article
        exact = [m for m in hits if _plain(m["name"]) == _plain(name)]
        hits = exact or hits
    if len(hits) > 1 and provinces:
        keys = {name_key(p, country) for p in provinces}
        hits = [m for m in hits if name_key(m["province"], country) in keys] or hits
    return hits[0]["ine"] if len({h["ine"] for h in hits}) == 1 else None
