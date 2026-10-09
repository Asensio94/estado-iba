from datetime import date

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
    rows = [{"lon": "0.5", "lat": "0.5", "risk_max": "9"}, {"lon": "0.5", "lat": "0.5", "risk_max": "8"}]
    rows += [{"lon": "3", "lat": "3", "risk_max": str(i)} for i in range(8)] + [{"lon": "3", "lat": "3", "risk_max": ""}]
    cov, out = A.tendidos({"cantabria": (rows, "2026-10-01")}, {"ES1": box(0, 0, 1, 1), "ES9": box(8, 8, 9, 9)})
    assert [(s["sites"], s["value"]["amount"]) for s in out] == [([{"code": "ES1"}], 1)]
    assert cov["sites"] == ["ES1"]  # ES9 lies outside the modelled region
