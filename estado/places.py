"""Municipalities: decode the IGN TopoJSON, cross it with the sites, and match names to INE codes."""

from __future__ import annotations

import re
import unicodedata

from shapely import STRtree, make_valid
from shapely.geometry import shape

KM2_DEG2 = 1.06e-4  # one km² in square degrees around 40° N; good enough for a threshold


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
             "official": f["properties"]["name"], "geom": make_valid(shape(f["geometry"]))}
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

    region_of = {f["id"]: region_at(make_valid(shape(f["geometry"])).representative_point()) for f in provinces}
    codes = list(sites)
    geoms = [make_valid(shape(sites[c]["geometry"])) for c in codes]
    tree = STRtree(geoms)
    out = []
    for f in topo_features(topo, "municipalities"):
        g = make_valid(shape(f["geometry"]))
        hits = []
        for i in tree.query(g, predicate="intersects"):
            area = g.intersection(geoms[i]).area
            if area >= min_km2 * KM2_DEG2 or area >= min_share * g.area or area >= min_site_share * geoms[i].area:
                hits.append(codes[i])
        c = g.representative_point()
        prov = f["id"][:2]
        # Land held in common by several municipalities (INE «53», like the Bardenas Reales) has no
        # province: its own point says which community it lies in.
        out.append({"ine": f["id"], "name": f["properties"]["name"], "province": names.get(prov, ""),
                    "region": region_of.get(prov) or region_at(c), "point": [round(c.x, 4), round(c.y, 4)],
                    "sites": sorted(hits), "geom": g})
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


def name_key(s: str) -> str:
    """Comparable form of a place name: no accents, articles moved or dropped, no punctuation.

    «Barrios, Los», «Los Barrios» and «LOS BARRIOS» all give «barrios»; bilingual names keep
    each side so «Alacant/Alicante» matches either.
    """
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()
    s = re.sub(r",\s*(el|la|los|las|l'|lo|o|a|os|as|es|sa|ses|els|les)$", "", s.strip())
    s = re.sub(r"^(el|la|los|las|lo|o|a|os|as|es|sa|ses|els|les)\s+|^l'", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def _plain(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower().strip()


def name_index(munis: list[dict]) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = {}
    for m in munis:
        for part in re.split(r"\s*/\s*", m["name"]):
            idx.setdefault(name_key(part), []).append(m)
    return idx


def resolve(idx: dict[str, list[dict]], name: str, provinces: list[str] | None = None) -> str | None:
    """INE code for a municipality name; provinces break ties between homonyms."""
    hits = idx.get(name_key(name), [])
    if len(hits) > 1:  # «Granada» before «La Granada»: an exact name wins over one that only matches without its article
        exact = [m for m in hits if _plain(m["name"]) == _plain(name)]
        hits = exact or hits
    if len(hits) > 1 and provinces:
        keys = {name_key(p) for p in provinces}
        hits = [m for m in hits if name_key(m["province"]) in keys] or hits
    return hits[0]["ine"] if len({h["ine"] for h in hits}) == 1 else None
