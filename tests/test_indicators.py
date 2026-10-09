from datetime import date

from estado import indicators as I

SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}


def _natura():
    return {"features": [
        {"properties": {"codigo": "ES1", "nombre": "Uno", "tipo": "ZEPA"}, "geometry": SQUARE},
        {"properties": {"codigo": "ES2", "nombre": "Dos", "tipo": "ZEC y ZEPA"}, "geometry": SQUARE},
        {"properties": {"codigo": "ES3", "nombre": "Tres", "tipo": "ZEC"}, "geometry": SQUARE},
    ]}


def test_load_sites_keeps_zepa_and_mixed():
    assert set(I.load_sites(_natura(), "ZEPA")) == {"ES1", "ES2"}


def _notice(ident, deadline, municipal, footprint=None):
    return {"identificador": ident, "fecha": "2026-09-01", "titulo": ident, "url_html": "u",
            "fecha_limite": deadline, "natura": [{"sitecode": c} for c in municipal],
            "footprint": {"natura": [{"sitecode": c} for c in footprint]} if footprint is not None else None}


def test_projects_prefers_footprint_and_pairs_resolutions():
    state = {
        "anuncios": {
            "A": _notice("A", "2026-10-20", ["ES1", "ES2"], footprint=["ES2"]),
            "B": _notice("B", "2026-09-10", ["ES1"]),
        },
        "resoluciones": {"R": {"identificador": "R", "fecha": "2026-09-30", "titulo": "R", "url_html": "u",
                               "emparejado_con": "B", "sentido_etiqueta": "Favorable"}},
    }
    out = I.projects(state, {"ES1", "ES2"}, date(2026, 10, 9))
    assert [p["id"] for p in out["ES2"]] == ["A"]
    assert out["ES2"][0]["precision"] == "parcelas" and out["ES2"][0]["open"]
    es1 = {p["id"]: p for p in out["ES1"]}
    assert set(es1) == {"B", "R"}  # A's footprint does not reach ES1
    assert es1["B"]["precision"] == "municipio" and not es1["B"]["open"]
    assert es1["R"]["outcome"] == "Favorable"


def test_fires_prefer_sentinel2_and_respect_window():
    fc = {"features": [
        {"properties": {"id": "F1", "primera": "2026-08-01T12:00", "natura": [{"codigo": "ES1", "ha": 50}],
                        "perimetro_s2": {"definitivo": True, "natura": [{"codigo": "ES1", "ha": 12.5}]}}},
        {"properties": {"id": "F0", "primera": "2025-01-01T12:00", "natura": [{"codigo": "ES1", "ha": 9}]}},
    ]}
    out = I.fires(fc, {"ES1"}, date(2026, 10, 9), 365)
    assert out["ES1"] == [{"id": "F1", "date": "2026-08-01", "ha": 12.5, "source": "sentinel2",
                           "final": True, "place": None}]


def test_land_change_distinguishes_unwatched_from_quiet():
    fc = {"features": [
        {"properties": {"id": "C1", "estado": "confirmada", "detectada": "2026-06-01", "ha": 2.0,
                        "espacios": [{"codigo": "ES1"}]}},
        {"properties": {"id": "C2", "estado": "descartada", "detectada": "2026-06-02", "ha": 3.0,
                        "espacios": [{"codigo": "ES1"}]}},
    ]}
    out = I.land_change(fc, {"ES1", "ES2"}, {"ES1", "ES2", "ES3"}, {"confirmada", "provisional"})
    assert [a["id"] for a in out["ES1"]] == ["C1"]
    assert out["ES2"] == [] and "ES3" not in out


def test_wetland_state_against_same_month():
    rows = [{"date": f"{y}-09-15", "water_ha": str(w), "quality": "ok"}
            for y, w in [(2022, 100), (2023, 120), (2024, 80), (2025, 100)]]
    rows += [{"date": "2026-09-20", "water_ha": "50", "quality": "ok"},
             {"date": "2026-10-01", "water_ha": "1", "quality": "nublado"}]
    st = I.wetland_state(rows, date(2026, 10, 9), {"ok"}, 3, 45)
    assert st["date"] == "2026-09-20" and st["ref_ha"] == 100 and st["ratio"] == 0.5 and st["current"]
    assert I.wetland_state(rows[-2:], date(2026, 10, 9), {"ok"}, 3, 45)["ratio"] is None


def test_panel_marks_unwatched_land_as_none():
    sites = I.load_sites(_natura(), "ZEPA")
    rows = I.panel(sites, {}, {}, {"ES1": []}, {})
    by = {r["code"]: r for r in rows}
    assert by["ES1"]["land"] == [] and by["ES2"]["land"] is None


def test_wetland_state_gives_no_ratio_for_usually_dry_month():
    rows = [{"date": f"{y}-08-10", "water_ha": "0.0", "quality": "ok"} for y in (2021, 2022, 2023)]
    rows += [{"date": "2025-02-10", "water_ha": "1200", "quality": "ok"},
             {"date": "2026-08-18", "water_ha": "330", "quality": "ok"}]
    st = I.wetland_state(rows, date(2026, 9, 1), {"ok"}, 3, 45)
    assert st["dry_ref"] and st["ratio"] is None and st["water_ha"] == 330
