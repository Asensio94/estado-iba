from shapely import box
from shapely.geometry import mapping

from estado import places as P

# Two unit squares side by side (the first also held in common, without province), a province
# and a community around them, Gibraltar (which the
# IGN layer carries as a region), an islet that quantization collapsed to three points and a
# municipality simplified into a line that goes out and back. Arcs are delta-encoded, as in any quantized TopoJSON.
TOPO = {
    "type": "Topology",
    "transform": {"scale": [1, 1], "translate": [0, 0]},
    "arcs": [
        [[0, 0], [1, 0], [0, 1], [-1, 0], [0, -1]],
        [[1, 0], [1, 0], [0, 1], [-1, 0], [0, -1]],
        [[0, 0], [2, 0], [0, 1], [-2, 0], [0, -1]],
        [[5, 5], [1, 0], [-1, 0]],
        [[7, 7], [1, 0], [-1, 0], [0, 0]],
    ],
    "objects": {
        "municipalities": {"type": "GeometryCollection", "geometries": [
            {"type": "Polygon", "arcs": [[0]], "id": "01001", "properties": {"name": "Uno"}},
            {"type": "Polygon", "arcs": [[1]], "id": "01002", "properties": {"name": "Dos"}},
            {"type": "Polygon", "arcs": [[3]], "id": "01003", "properties": {"name": "Islote"}},
            {"type": "Polygon", "arcs": [[4]], "id": "01004", "properties": {"name": "Línea"}},
            {"type": "Polygon", "arcs": [[0]], "id": "53001", "properties": {"name": "Facería de Uno"}},
        ]},
        "provinces": {"type": "GeometryCollection", "geometries": [
            {"type": "Polygon", "arcs": [[2]], "id": "01", "properties": {"name": "Araba/Álava"}},
        ]},
        "autonomous_regions": {"type": "GeometryCollection", "geometries": [
            {"type": "Polygon", "arcs": [[2]], "id": "16", "properties": {"name": "País Vasco/Euskadi"}},
            {"type": "Polygon", "arcs": [[2]], "id": "20", "properties": {"name": "Gibraltar"}},
        ]},
    },
}
SHAPES = {"ES1": box(0, 0, 1.05, 1), "ES2": box(1.5, 0, 2, 1)}
SITES = {c: {"geometry": mapping(g)} for c, g in SHAPES.items()}
REGS = P.regions(TOPO)


def _sites(shapes):
    return {c: {"geometry": mapping(g)} for c, g in shapes.items()}


def test_topo_features_decode_and_drop_degenerate_rings():
    feats = P.topo_features(TOPO, "municipalities")
    assert [f["id"] for f in feats] == ["01001", "01002", "01004", "53001"]
    assert feats[1]["geometry"]["coordinates"][0][0] == [(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]


def test_polygonal_keeps_areas_and_drops_collapsed_parts():
    # An islet rounded into a single point and listed first, as off Lanzarote in ES0000100 (GEOS 3.14
    # fails on that order), a square, a bow tie (self-crossing, so its signed area is zero) and a
    # part simplified into a line.
    g = P.polygonal({"type": "MultiPolygon", "coordinates": [
        [[[7, 7], [7, 7], [7, 7], [7, 7]]],
        [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        [[[2, 0], [4, 2], [4, 0], [2, 2], [2, 0]]],
        [[[5, 5], [6, 5], [5, 5], [5, 5]]],
    ]})
    assert g.geom_type == "MultiPolygon" and g.is_valid and g.area == 3


def test_regions_use_short_names_and_skip_gibraltar():
    assert [(r["id"], r["name"], r["official"]) for r in REGS] == [("16", "País Vasco", "País Vasco/Euskadi")]


def test_municipalities_ignore_border_slivers():
    # Absolute threshold off: only the shares decide.
    munis = {m["ine"]: m for m in P.municipalities(TOPO, SITES, REGS, min_km2=1e9)}
    assert munis["01001"]["sites"] == ["ES1"]
    assert munis["01002"]["sites"] == ["ES2"]  # ES1 spills 5 % into it, under 5 % of ES1 too
    assert munis["01001"]["province"] == "Araba/Álava" and munis["01001"]["region"] == "16"
    assert munis["53001"]["province"] == "" and munis["53001"]["region"] == "16"
    assert munis["01004"]["point"] == [7.5, 7] and munis["01004"]["sites"] == []  # no area, still a place


def test_municipalities_keep_small_sites_inside_big_municipalities():
    # A colony in a church: 0.5 % of the municipality, but half of the site lies in it.
    munis = {m["ine"]: m for m in P.municipalities(TOPO, _sites({"COL": box(1.9, 0.9, 2.1, 0.95)}), REGS, min_km2=1e9)}
    assert munis["01002"]["sites"] == ["COL"] and munis["01001"]["sites"] == []


def test_site_regions_send_offshore_sites_to_the_nearest_coast():
    regs = [{"id": "01", "geom": box(0, 0, 1, 1)}, {"id": "05", "geom": box(10, 0, 11, 1)}]
    munis = [{"region": "01", "sites": ["A"]}, {"region": "05", "sites": ["A"]}]
    out = P.site_regions(munis, {"A": box(0.5, 0.5, 0.6, 0.6), "SEA": box(9, 0, 9.5, 1)}, regs)
    assert out["A"] == {"regions": ["01", "05"], "marine": False}
    assert out["SEA"] == {"regions": ["05"], "marine": True}


def test_locator_gives_sites_and_municipality():
    locate = P.locator(P.municipalities(TOPO, SITES, REGS, min_km2=1e9), SHAPES)
    assert locate(0.5, 0.5) == (["ES1"], ["01001"])
    assert locate(1.003, 0.5) == (["ES1"], ["01002"])
    assert locate(1.497, 0.5) == (["ES2"], ["01002"])  # within ~300 m of a thin riverside strip
    assert locate(9, 9) == ([], [])


def test_resolve_names_homonyms_and_bilingual():
    idx = P.name_index([
        {"ine": "11008", "name": "Barrios, Los", "province": "Cádiz"},
        {"ine": "03014", "name": "Alacant/Alicante", "province": "Alacant/Alicante"},
        {"ine": "18087", "name": "Granada", "province": "Granada"},
        {"ine": "08096", "name": "La Granada", "province": "Barcelona"},
        {"ine": "41097", "name": "Villanueva", "province": "Sevilla"},
        {"ine": "14068", "name": "Villanueva", "province": "Córdoba"},
    ])
    assert P.resolve(idx, "LOS BARRIOS") == "11008"
    assert P.resolve(idx, "Alicante") == P.resolve(idx, "Alacant") == "03014"
    assert P.resolve(idx, "Granada") == "18087"
    assert P.resolve(idx, "Villanueva") is None
    assert P.resolve(idx, "Villanueva", ["Cordoba"]) == "14068"
