from datetime import date

from estado import indicators as I

SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}


def _natura():
    return {"features": [
        {"properties": {"codigo": "ES1", "nombre": "Uno", "tipo": "ZEPA"}, "geometry": SQUARE},
        {"properties": {"codigo": "ES2", "nombre": "Dos", "tipo": "ZEC y ZEPA"}, "geometry": SQUARE},
        {"properties": {"codigo": "ES3", "nombre": "Tres", "tipo": "ZEC"}, "geometry": SQUARE},
    ]}


def _sig(kind, sites, precision="municipio", deadline=None, value=None, munis=(), **details):
    return {"source": "s", "id": kind, "kind": kind, "date": "2026-09-01", "title": kind, "url": "u",
            "sites": sites, "municipalities": list(munis), "precision": precision, "deadline": deadline,
            "status": None, "value": value, "details": details}


def test_load_sites_keeps_zepa_and_mixed():
    assert set(I.load_sites(_natura(), "ZEPA")) == {"ES1", "ES2"}


def test_wetland_state_against_same_month():
    rows = [{"date": f"{y}-09-15", "water_ha": str(w), "quality": "ok"}
            for y, w in [(2022, 100), (2023, 120), (2024, 80), (2025, 100)]]
    rows += [{"date": "2026-09-20", "water_ha": "50", "quality": "ok"},
             {"date": "2026-10-01", "water_ha": "1", "quality": "nublado"}]
    st = I.wetland_state(rows, date(2026, 10, 9), {"ok"}, 3, 45)
    assert st["date"] == "2026-09-20" and st["ref_ha"] == 100 and st["ratio"] == 0.5 and st["current"]
    assert I.wetland_state(rows[-2:], date(2026, 10, 9), {"ok"}, 3, 45)["ratio"] is None


def test_wetland_state_gives_no_ratio_for_usually_dry_month():
    rows = [{"date": f"{y}-08-10", "water_ha": "0.0", "quality": "ok"} for y in (2021, 2022, 2023)]
    rows += [{"date": "2025-02-10", "water_ha": "1200", "quality": "ok"},
             {"date": "2026-08-18", "water_ha": "330", "quality": "ok"}]
    st = I.wetland_state(rows, date(2026, 9, 1), {"ok"}, 3, 45)
    assert st["dry_ref"] and st["ratio"] is None and st["water_ha"] == 330


def test_summary_counts_and_tells_unwatched_from_quiet():
    sites = I.load_sites(_natura(), "ZEPA")
    signals = [
        _sig("notice", [{"code": "ES1"}], "parcelas", deadline="2026-10-20"),
        _sig("notice", [{"code": "ES1"}, {"code": "ES2"}], deadline="2026-09-10"),
        _sig("resolution", [{"code": "ES1"}]),
        _sig("fire", [{"code": "ES1", "ha": 12.5}, {"code": "ES2", "ha": None}], "perimetro"),
        _sig("land_change", [{"code": "ES1"}], "pixeles"),
        _sig("wetland_water", [{"code": "ES2"}], "lamina", ratio=0.4, current=True),
        _sig("wetland_water", [{"code": "ES2"}], "lamina", ratio=0.1, current=False),
    ]
    coverage = {"centinela-natura": {"sites": ["ES1"]}, "riesgo-tendidos-aves": {"sites": None}}
    n = I.summary(sites, signals, coverage, date(2026, 10, 9))
    assert n["ES1"] == {"notices": 2, "precise": 1, "open": 1, "resolutions": 1, "fires": 1, "fire_ha": 12.5,
                        "land": 1, "lines": 0, "flow": 0, "water": None}
    assert n["ES2"]["land"] is None  # centinela does not watch ES2: unknown, not zero
    assert n["ES2"]["lines"] == 0 and n["ES2"]["fire_ha"] == 0
    assert n["ES2"]["water"] == 0.4  # an outdated observation does not count


def test_restrict_drops_codes_outside_the_panel():
    signals = [_sig("notice", [{"code": "ES1"}, {"code": "ESZEC"}]),
               _sig("fire", [{"code": "ESZEC"}], munis=["01001"]),
               _sig("resolution", [{"code": "ESZEC"}])]
    out = I.restrict(signals, {"ES1", "ES2"})
    assert [(s["kind"], s["sites"]) for s in out] == [("notice", [{"code": "ES1"}]), ("fire", [])]
    assert signals[0]["sites"] == [{"code": "ES1"}, {"code": "ESZEC"}]  # the input is left alone
