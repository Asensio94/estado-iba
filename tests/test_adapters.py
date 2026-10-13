from collections import Counter
from datetime import date

import pytest
from shapely import box

from estado import adapters as A

TODAY = date(2026, 10, 9)


def resolve(name, provinces):
    return {"Uno": "01001", "Valencia": "46250"}.get(name)


def _notice(ident, deadline, municipal, footprint=None):
    return {"identificador": ident, "fecha": "2026-09-01", "titulo": ident, "url_html": "u",
            "fecha_limite": deadline, "natura": [{"sitecode": c} for c in municipal],
            "municipios": ["Uno"], "provincias": ["Uno"],
            "footprint": {"natura": [{"sitecode": c} for c in footprint]} if footprint is not None else None}


def test_observatorio_prefers_footprint_and_pairs_resolutions():
    state = {
        "anuncios": {"A": _notice("A", "2026-10-20", ["ES1", "ES2"], footprint=["ES2"]),
                     "B": _notice("B", "2026-09-10", ["ES1"])},
        "resoluciones": {"R": {"identificador": "R", "fecha": "2026-09-30", "titulo": "R", "url_html": "u",
                               "emparejado_con": "B", "sentido_etiqueta": "Favorable"}},
    }
    cov, out = A.observatorio(state, resolve)
    by = {s["id"]: s for s in out}
    assert by["A"]["sites"] == [{"code": "ES2"}] and by["A"]["precision"] == "parcelas"
    assert by["B"]["precision"] == "municipio" and by["B"]["municipalities"] == ["01001"]
    assert by["R"]["kind"] == "resolution" and by["R"]["sites"] == by["B"]["sites"]
    assert by["R"]["status"] == "Favorable" and by["R"]["details"]["paired_with"] == "B"
    assert cov["sites"] is None


def test_vigia_prefers_sentinel2_and_respects_window():
    fc = {"features": [
        {"properties": {"id": "F1", "primera": "2026-08-01T12:00", "natura": [{"codigo": "ES1", "ha": 50}],
                        "lugar": {"municipio": "Uno", "provincia": "Uno"}, "centro": [-6.0, 39.8],
                        "perimetro_s2": {"definitivo": True, "ha": 12.5, "natura": [{"codigo": "ES1", "ha": 12.5}]}}},
        {"properties": {"id": "F2", "primera": "2026-09-01T03:00", "natura": [{"codigo": "ES2", "ha": 14}],
                        "ha_focos": 14}},
        {"properties": {"id": "F0", "primera": "2025-01-01T12:00", "natura": [{"codigo": "ES1", "ha": 9}]}},
    ]}
    _, out = A.vigia(fc, resolve, TODAY, 365)
    by = {s["id"]: s for s in out}
    assert set(by) == {"F1", "F2"}
    assert by["F1"]["precision"] == "perimetro" and by["F1"]["sites"] == [{"code": "ES1", "ha": 12.5}]
    assert by["F1"]["status"] == "definitivo" and by["F1"]["municipalities"] == ["01001"]
    assert by["F1"]["url"].endswith("/vigia-incendios/#F1") and by["F1"]["details"]["point"] == [-6.0, 39.8]
    assert by["F2"]["precision"] == "focos" and by["F2"]["value"] == {"amount": 14, "unit": "ha"}


def test_a_measured_burnt_area_decides_the_sites():
    focos = [{"codigo": "ES1", "ha": 14}]
    clear = {"natura": focos, "ha_focos": 14}
    # Sentinel-2 saw it all and none of it burnt inside ES1: the hot pixels no longer count.
    assert A.fire_sites(clear, {"ha": 3.0, "natura": []}) == ([], "perimetro", 3.0, "provisional")
    # Under clouds the burnt area is a lower bound: ES1 stays, without hectares.
    assert A.fire_sites(clear, {"ha": 3.0, "nublado": True, "natura": [{"codigo": "ES2", "ha": 3.0}]})[0] ==         [{"code": "ES2", "ha": 3.0}, {"code": "ES1"}]
    # Clouds hid everything, or no area yet: nothing was measured.
    for s2 in ({"ha": 0, "nublado": True, "natura": []}, {"natura": []}):
        assert A.fire_sites(clear, s2) == ([{"code": "ES1", "ha": 14}], "focos", 14, None)


def test_centinela_keeps_live_states_and_flips_point():
    fc = {"features": [
        {"properties": {"id": "C1", "estado": "confirmada", "detectada": "2026-06-01", "ha": 2.0,
                        "espacios": [{"codigo": "ES1"}], "centro": [43.3, -4.0], "foto_antes": "f/a.jpg"}},
        {"properties": {"id": "C2", "estado": "descartada", "detectada": "2026-06-02", "ha": 3.0,
                        "espacios": [{"codigo": "ES1"}]}},
    ]}
    cov, out = A.centinela(fc, ["ES2", "ES1"], resolve, {"confirmada", "provisional"})
    assert [s["id"] for s in out] == ["C1"]
    assert out[0]["details"]["point"] == [-4.0, 43.3]
    assert out[0]["details"]["before"].endswith("/centinela-natura/f/a.jpg")
    assert cov["sites"] == ["ES1", "ES2"]


def test_humedales_titles_by_state():
    def state_of(rows):
        return rows[0]
    st = {"date": "2026-09-20", "water_ha": 50.0, "ratio": 0.5, "ref_ha": 100.0, "ref_years": [2024, 2025],
          "dry_ref": False, "current": True}
    cov, out = A.humedales([({"slug": "h", "name": "Laguna"}, [st], {"ES1"}),
                            ({"slug": "v", "name": "Vacía"}, [None], {"ES2"})], state_of)
    assert len(out) == 1 and out[0]["title"] == "Laguna: 50 % del agua normal en ese mes"
    assert cov["sites"] == ["ES1", "ES2"]  # watched even when there is no state today


def test_chains_reach_listed_company_through_group_and_skip_people():
    grafo = {
        "sociedades": {"A1": {"nombres": ["Solar Uno SL"], "actos_boe": ["BOE-1"], "grupo": "R"},
                       "R": {"nombres": ["Raíz SA"]}, "M": {"nombres": ["Matriz SA"]},
                       "PF-x": {"nombres": ["Persona"], "actos_boe": ["BOE-1"]}},
        "grupos": [{"id": "G-R", "sociedades": ["A1", "R", "M"]}],
        "instalaciones": {},
    }
    cartera = {"cotizadas": [{"id": "X", "nombre": "Cotizada SA", "sociedades": [{"id": "M"}]}]}
    out = A.chains(grafo, cartera, {"BOE-1", "BOE-2"})
    assert list(out) == ["BOE-1"] and len(out["BOE-1"]) == 1
    links = out["BOE-1"][0]["links"]
    assert [(x["role"], x["name"]) for x in links] == [
        ("promotor", "Solar Uno SL"), ("grupo", "grupo Raíz SA (3 sociedades)"), ("cotizada", "Cotizada SA")]
    assert links[2]["via"] == "por el grupo" and links[2]["url"].endswith("#c=X&t=sociedades")


def test_caudal_counts_days_below_ordinary_minimum():
    stations = [{"station_id": "S1", "name": "Río", "river": "R", "lon": "0.5", "lat": "0.5"},
                {"station_id": "S2", "name": "Sin mínimo", "river": "R", "lon": "3", "lat": "3"}]
    flows = {"S1": [{"date": "2026-09-20", "q_mean": "0.1"}, {"date": "2026-09-21", "q_mean": "2"},
                    {"date": "2026-07-01", "q_mean": "0"}, {"date": "2026-09-22", "q_mean": ""}],
             "S2": [{"date": "2026-09-20", "q_mean": "0"}]}
    reqs = [{"station_id": "S1", "regime": "ordinary", "valid_to": "", "m09": "1"},
            {"station_id": "S1", "regime": "drought", "valid_to": "", "m09": "5"}]
    cov, out = A.caudal(stations, flows, reqs, lambda lon, lat: (["ES1"], ["01001"]), TODAY)
    assert len(out) == 1
    s = out[0]
    assert s["details"]["days_below"] == 1 and s["details"]["days"] == 2 and s["details"]["minimum"] == 1.0
    assert s["date"] == "2026-09-21" and s["value"]["amount"] == 2.0 and s["sites"] == [{"code": "ES1"}]
    assert s["url"] == "https://asensio94.github.io/caudal-ecologico/"
    assert cov["sites"] == ["ES1"]


def test_subnocte_takes_first_spanish_night_and_names_levels():
    fc = [{"night": "2026-10-09", "city": "Valencia", "country": "ES", "level": "very high", "lon": "-0.4", "lat": "39.5"},
          {"night": "2026-10-10", "city": "Valencia", "country": "ES", "level": "low", "lon": "-0.4", "lat": "39.5"},
          {"night": "2026-10-09", "city": "Paris", "country": "FR", "level": "high", "lon": "2.3", "lat": "48.8"},
          {"night": "2026-10-08", "city": "Valencia", "country": "ES", "level": "high", "lon": "-0.4", "lat": "39.5"}]
    _, out = A.subnocte(fc, resolve, TODAY)
    assert len(out) == 1
    assert out[0]["title"] == "Valencia: migración nocturna muy alta prevista"
    assert out[0]["municipalities"] == ["46250"] and out[0]["sites"] == []


def test_tendidos_counts_top_risk_inside_each_site():
    rows = [{"type": "turbine", "lon": "0.5", "lat": "0.5", "risk_max": "19"},
            {"type": "pylon", "lon": "0.5", "lat": "0.5", "risk_max": "18"}]
    rows += [{"type": "pylon", "lon": "3", "lat": "3", "risk_max": str(i)} for i in range(18)]
    rows += [{"type": "pylon", "lon": "3", "lat": "3", "risk_max": ""}]
    cov, out = A.tendidos({"cantabria": (rows, "2026-10-01")}, {"ES1": box(0, 0, 1, 1), "ES9": box(8, 8, 9, 9)})
    assert [(s["sites"], s["value"]["amount"]) for s in out] == [([{"code": "ES1"}], 2)]
    assert out[0]["title"] == "1 aerogenerador y 1 apoyo de riesgo alto para las aves dentro del espacio"
    assert cov["sites"] == ["ES1"]  # ES9 lies outside the modelled region


def test_titles_name_wind_turbines_first():
    assert A.elements(Counter(pylon=40, line=2, turbine=3)) == "3 aerogeneradores, 40 apoyos y 2 tramos de línea"
    assert A.elements(Counter(line=1)) == "1 tramo de línea"
    assert A.elements(Counter(pylon=2, substation=1)) == "2 apoyos y 1 otro elemento"


def _doc(signals, source="s", version=1):
    return {"source": source, "version": version, "generated": "2026-10-09T07:00Z",
            "coverage": {"label": "Toda España", "sites": None, "note": "n"}, "signals": signals}


def test_published_resolves_names_places_points_and_drops_incomplete():
    doc = _doc([
        {"id": 1, "kind": "fire", "date": "2026-10-01", "title": "t", "url": "u", "precision": "focos",
         "sites": [{"code": "ES1", "ha": 2}], "municipality_names": ["Uno"], "provinces": ["Uno"], "extra": "x"},
        {"id": "P", "kind": "river_flow", "date": "2026-10-01", "title": "t", "url": "u", "precision": "punto",
         "details": {"point": [0.5, 0.5]}},
        {"id": "N", "kind": "fire", "date": "2026-10-01", "title": "t", "url": "", "precision": "focos"},
        {"id": "K", "kind": "meteor", "date": "2026-10-01", "title": "t", "url": "u", "precision": "punto"},
    ])
    cov, out = A.published(doc, "s", resolve, lambda lon, lat: (["ES9"], ["09999"]))
    assert cov == {"label": "Toda España", "sites": None, "note": "n"}
    assert [s["id"] for s in out] == ["1", "P"]  # no link, or a kind the map cannot draw: dropped
    first = out[0]
    assert first["source"] == "s" and first["sites"] == [{"code": "ES1", "ha": 2}]
    assert first["municipalities"] == ["01001"] and first["details"] == {} and "extra" not in first
    assert out[1]["sites"] == [{"code": "ES9"}] and out[1]["municipalities"] == ["09999"]


def test_published_refuses_another_source_or_version():
    for doc in (_doc([], source="otro"), _doc([], version=2)):
        with pytest.raises(ValueError):
            A.published(doc, "s", resolve, lambda lon, lat: ([], []))


def test_natural_persons_are_never_named_as_promoters():
    state = {"anuncios": {"A": dict(_notice("A", None, ["ES1"]), promotor="D. Juan Pérez García"),
                          "B": dict(_notice("B", None, ["ES1"]), promotor="Esteyco")},
             "resoluciones": {}}
    _, out = A.observatorio(state, resolve)
    assert [s["details"]["promoter"] for s in out] == [None, "Esteyco"]
    doc = _doc([{"id": "A", "kind": "notice", "date": "2026-10-01", "title": "t", "url": "u",
                 "precision": "municipio", "details": {"promoter": "Dña. Ana López"}}])
    assert A.published(doc, "s", resolve, lambda lon, lat: ([], []))[1][0]["details"]["promoter"] is None


def _light(**sites):
    return {"doi": "10.5067/VIIRS/VNP46A4.002", "years": [2012, 2013, 2014, 2015, 2024, 2025],
            "sites": {c: {"pixels": px, "radiance": r} for c, (px, r) in sites.items()}}


def test_night_light_signals_rises_only_over_both_thresholds():
    shapes = {c: box(0, 0, 1, 1) for c in ("ES1", "ES2", "ES3", "ES4", "ES5", "ES6")}
    doc = _light(ES1=(50, [1.0, 1.1, 0.9, 1.2, 1.5, 1.7]),  # +60 %
                 ES2=(50, [0.2, 0.2, 0.2, 0.3, 0.35, 0.35]),  # +75 %, but only 0.15 more: noise floor
                 ES3=(50, [2.0, 2.0, 2.0, 1.0, 1.0, 1.0]),  # a fall: maybe just LEDs
                 ES4=(2, [1.0, 1.0, 1.0, 1.0, 3.0, 3.0]),  # two pixels: too few to judge
                 ES5=(50, [1.0, None, 1.0, 1.0, 2.0, 2.0]),  # a year without data in the baseline
                 ES6=(50, [1.0, 1.0, 1.0, 1.0, 1.2, 1.2]))  # +20 %: under the share
    cov, out = A.luz(doc, shapes, (2012, 2014), 2, 0.25, 0.2, 4)
    assert cov["sites"] == ["ES1", "ES2", "ES3", "ES6"] and "2012-2025" in cov["note"]
    assert [s["id"] for s in out] == ["ES1"]
    s = out[0]
    assert s["title"] == "La luz artificial de noche ha subido un 60 % desde 2012-2014 dentro del espacio"
    assert (s["date"], s["value"], s["precision"]) == ("2025-12-31", {"amount": 60, "unit": "%"}, "pixeles")
    assert s["details"]["years"] == [2024, 2025] and s["details"]["baseline"] == 1.0 and s["details"]["radiance"] == 1.6
    assert s["url"] == "https://doi.org/10.5067/VIIRS/VNP46A4.002"
