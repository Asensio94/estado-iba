from shapely import box
from shapely.geometry import mapping

from estado import places as P

# Two unit squares side by side, a province around them and an islet that quantization
# collapsed to three points. Arcs are delta-encoded, as in any quantized TopoJSON.
TOPO = {
    "type": "Topology",
    "transform": {"scale": [1, 1], "translate": [0, 0]},
    "arcs": [
        [[0, 0], [1, 0], [0, 1], [-1, 0], [0, -1]],
        [[1, 0], [1, 0], [0, 1], [-1, 0], [0, -1]],
        [[0, 0], [2, 0], [0, 1], [-2, 0], [0, -1]],
        [[5, 5], [1, 0], [-1, 0]],
    ],
    "objects": {
        "municipalities": {"type": "GeometryCollection", "geometries": [
            {"type": "Polygon", "arcs": [[0]], "id": "01001", "properties": {"name": "Uno"}},
            {"type": "Polygon", "arcs": [[1]], "id": "01002", "properties": {"name": "Dos"}},
            {"type": "Polygon", "arcs": [[3]], "id": "01003", "properties": {"name": "Islote"}},
        ]},
        "provinces": {"type": "GeometryCollection", "geometries": [
            {"type": "Polygon", "arcs": [[2]], "id": "01", "properties": {"name": "Araba/Álava"}},
        ]},
    },
}
SHAPES = {"ES1": box(0, 0, 1.05, 1), "ES2": box(1.5, 0, 2, 1)}
SITES = {c: {"geometry": mapping(g)} for c, g in SHAPES.items()}


def test_topo_features_decode_and_drop_degenerate_rings():
    feats = P.topo_features(TOPO, "municipalities")
    assert [f["id"] for f in feats] == ["01001", "01002"]
    assert feats[1]["geometry"]["coordinates"][0][0] == [(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]


def test_municipalities_ignore_border_slivers():
    # Absolute threshold off: only the share of the municipality decides.
    munis = {m["ine"]: m for m in P.municipalities(TOPO, SITES, min_km2=1e9)}
    assert munis["01001"]["sites"] == ["ES1"]
    assert munis["01002"]["sites"] == ["ES2"]  # ES1 spills 5 % into it: not enough
    assert munis["01001"]["province"] == "Araba/Álava"


def test_locator_gives_sites_and_municipality():
    locate = P.locator(P.municipalities(TOPO, SITES, min_km2=1e9), SHAPES)
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
