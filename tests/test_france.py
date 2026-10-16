"""Country as a dimension: contract v2, INSEE codes, French communes, words and figures."""
import json
import re

from shapely import box
from shapely.geometry import mapping

from estado import adapters as A, aves as V, config, i18n, places as P, web
from tests.test_aves import row

NN = " "


def resolve(name, provinces):
    return None


def nowhere(lon, lat):
    return [], []


def _sig(id, country=None, munis=(), **kw):
    s = {"id": id, "kind": "fire", "date": "2026-10-01", "title": "t", "url": "https://x", "precision": "focos",
         "municipalities": list(munis), **kw}
    return s if country is None else {**s, "country": country}


def _v2(signals, coverage=("ES", "FR")):
    return {"source": "s", "version": 2, "generated": "2026-10-15T07:00Z",
            "coverage": {c: {"label": c, "sites": None, "note": "n"} for c in coverage}, "signals": signals}


def test_a_version_1_file_is_spain_and_only_spain():
    doc = {"source": "s", "version": 1, "generated": "g", "coverage": {"label": "Toda España", "sites": None},
           "signals": [_sig("a", munis=["10131"])]}
    cov, out = A.published(doc, "s", resolve, nowhere)
    assert cov["label"] == "Toda España" and [(s["id"], s["country"]) for s in out] == [("a", "ES")]
    assert A.published(doc, "s", resolve, nowhere, "FR") is None


def test_version_2_reads_each_country_apart_and_codes_never_mix():
    # 13004 is Arles for INSEE and Albaladejo (Ciudad Real) for INE: only the signal's country tells them apart.
    doc = _v2([_sig("es", "ES", ["13004", "2A004"]), _sig("fr", "FR", ["13004", "2A004", "1300"])])
    _, es = A.published(doc, "s", resolve, nowhere, "ES")
    cov, fr = A.published(doc, "s", resolve, nowhere, "FR")
    assert [(s["id"], s["municipalities"]) for s in es] == [("es", ["13004"])]  # 2A004 is no INE code
    assert [(s["id"], s["municipalities"]) for s in fr] == [("fr", ["13004", "2A004"])]
    assert cov["label"] == "FR" and fr[0]["country"] == "FR"


def test_a_country_with_no_coverage_is_not_covered_and_its_signals_are_dropped(capsys):
    doc = _v2([_sig("es", "ES"), _sig("fr", "FR")], coverage=("FR",))
    assert A.published(doc, "s", resolve, nowhere, "ES") is None
    assert "1 señales de ES sin cobertura" in capsys.readouterr().err
    assert [s["id"] for s in A.published(doc, "s", resolve, nowhere, "FR")[1]] == ["fr"]


def test_the_schema_takes_both_versions_and_names_each_fault():
    assert A.schema_errors(_v2([_sig("a", "FR", ["2A004"]), _sig("b", "ES", ["10131"])])) == []
    errors = A.schema_errors(_v2([_sig("a", munis=["01001"]), _sig("b", "ES", ["2A004"]), _sig("c", "PT")]))
    assert any(e.startswith("signals/0: 'country' is a required") for e in errors)
    assert any(e.startswith("signals/1/municipalities/0") for e in errors)
    assert any(e.startswith("signals/2/country") for e in errors)
    assert A.schema_errors({**_v2([]), "coverage": {"PT": {"label": "x", "sites": None}}})
    v1 = {"source": "s", "version": 1, "generated": "2026-10-15T07:00Z", "coverage": {"label": "x", "sites": None},
          "signals": [_sig("a", munis=["2A004"])]}
    assert [e.split(":")[0] for e in A.schema_errors(v1)] == ["signals/0/municipalities/0"]


def test_the_examples_of_the_contract_follow_its_schema():
    text = (config.ROOT / "CONTRATO.md").read_text(encoding="utf-8")
    docs = [json.loads(b) for b in re.findall(r"```json\n(.*?)```", text, re.S)]
    assert [d["version"] for d in docs] == [1, 2]
    for d in docs:
        assert A.schema_errors(d) == []


def test_french_figures_use_narrow_no_break_spaces():
    assert (i18n.n(34748), i18n.n(34748, "fr")) == ("34.748", f"34{NN}748")
    assert (i18n.p(15), i18n.p(15, "fr")) == ("15 %", f"15{NN}%")
    assert i18n.d(1234.5, 1, "fr") == f"1{NN}234,5" and i18n.d(0.25, 2) == "0,25"
    assert i18n._typo("Pas « en France » : 3 % ?") == f"Pas «{NN}en France{NN}»{NN}: 3{NN}%{NN}?"


def test_both_languages_have_every_word_and_spanish_keeps_its_own():
    def keys(d, pre=""):  # each country's own indicators and region kinds are data, not words
        return {pre + k for k in d} | {x for k, v in d.items() if isinstance(v, dict)
                                       and k not in ("indicators", "region_kinds") for x in keys(v, pre + k + ".")}
    assert keys(i18n.UI["es"]) == keys(i18n.UI["fr"]) and keys(i18n.PY["es"]) == keys(i18n.PY["fr"])
    assert NN not in json.dumps(i18n.UI["es"]) + json.dumps(i18n.PY["es"])
    assert i18n.page("FR") == {"lang": "fr", "country": "FR", "locale": "fr-FR", "center": [46.6, 2.4],
                               "zoom": 5.5, "shared": "../"}


def test_night_light_in_france_speaks_french():
    flat = lambda ref, cur: [ref] * 4 + [cur] * 2  # noqa: E731
    doc = {"doi": "10.5067/VIIRS/VNP46A4.002", "years": [2012, 2013, 2014, 2015, 2024, 2025], "sites": {
        c: {"pixels": 50, "radiance": r} for c, r in {
            "FR1": [1.05, 1.05, 1.05, 1.2, 2.1, 2.1], "P1": flat(0.9, 1.35), "P2": flat(1.0, 1.5),
            "P3": flat(1.2, 1.8), "P4": flat(1.3, 1.95)}.items()}}
    cov, out = A.luz(doc, {c: box(0, 0, 1, 1) for c in doc["sites"]}, (2012, 2014), 2, 0.25, 0.2, 4, 2, "FR")
    assert [(s["id"], s["country"]) for s in out] == [("FR1", "FR")]
    assert out[0]["title"] == (f"La lumière artificielle la nuit a augmenté de 100{NN}% depuis 2012-2014{NN}; "
                               f"dans les sites aussi sombres, elle a augmenté de 50{NN}%")
    assert cov["label"] == "Toute la France métropolitaine" and "2012-2025" in cov["note"]


def test_one_bird_file_names_each_species_in_both_languages():
    rows = [r for r in (row("ES1", "A031", "Ciconia ciconia", "r", "A"), row("ES1", "A127", "Grus grus", "w", "A"),
                        {**row("FR1", "A031", "Ciconia ciconia", "r", "A"), "COUNTRY_CODE": "FR"},
                        {**row("FR1", "A127", "Grus grus", "w", "A"), "COUNTRY_CODE": "FR"},
                        {**row("FR1", "A026", "Egretta garzetta", "p", "A"), "COUNTRY_CODE": "FR"})]
    es = {"A031": "Cigüeña blanca", "A127": "Grulla común"}
    fr = {"A031": "Cigogne blanche", "A127": "Grue cendrée"}
    got = V.by_site(rows, ["ES1", "FR1"], es, fr)
    assert got["species"]["A127"] == ["Grus grus", "Grulla común", "Grue cendrée"]
    assert [b[0] for b in got["sites"]["ES1"]["birds"]] == ["A031", "A127"]  # Cigüeña < Grulla
    assert [b[0] for b in got["sites"]["FR1"]["birds"]] == ["A031", "A026", "A127"]  # Cigogne < Egretta < Grue
    assert got["unnamed"] == [] and got["unnamed_fr"] == ["A026"]  # Egretta is only French here
    assert V.by_site(rows, ["ES1"], es)["species"]["A031"] == ["Ciconia ciconia", "Cigüeña blanca"]


def test_every_french_name_is_filled():
    fr = V.names(V.NAMES_FR_FILE, "name_fr")
    assert len(fr) > 200 and all(fr.values())


REF = {
    "regions": [{"id": "93", "name": "Provence-Alpes-Côte d'Azur", "geometry": mapping(box(0, 0, 2, 1))},
                {"id": "94", "name": "Corse", "geometry": mapping(box(5, 0, 6, 1))}],
    "departments": {"13": "Bouches-du-Rhône", "2A": "Corse-du-Sud"},
    "communes": [["13004", "Arles", "13", "93", mapping(box(0, 0, 1, 1))],
                 ["13005", "Le Havre", "13", "93", mapping(box(1, 0, 2, 1))],
                 ["2A004", "Ajaccio", "2A", "94", mapping(box(5, 0, 6, 1))]],
}


def test_communes_carry_insee_codes_departments_and_their_sites():
    sites = {"FR9310019": {"geometry": mapping(box(0.2, 0.2, 0.8, 0.8))}}
    got = {c["ine"]: c for c in P.communes_fr(REF, sites)}
    assert got["13004"]["sites"] == ["FR9310019"] and got["13005"]["sites"] == []
    assert (got["2A004"]["province"], got["2A004"]["region"]) == ("Corse-du-Sud", "94")
    assert [r["id"] for r in P.regions_fr(REF)] == ["93", "94"]


def test_french_names_drop_their_articles():
    munis = [{"ine": "76351", "name": "Le Havre", "province": "Seine-Maritime"},
             {"ine": "13004", "name": "Arles", "province": "Bouches-du-Rhône"},
             {"ine": "2A004", "name": "Ajaccio", "province": "Corse-du-Sud"}]
    idx = P.name_index(munis, "FR")
    assert P.name_key("Le Havre", "FR") == P.name_key("Havre, Le", "FR")
    assert P.resolve(idx, "LE HAVRE", country="FR") == "76351"
    assert P.resolve(idx, "Ajaccio", ["Corse-du-Sud"], country="FR") == "2A004"


def test_french_feeds_speak_french_and_link_to_the_french_page(tmp_path):
    s = {"source": "black-marble", "id": "FR1", "kind": "night_light", "date": "2025-12-31", "title": "t",
         "sites": [{"code": "FR1"}], "regions": ["93"], "deadline": None}
    web._rss(tmp_path, {"FR1": {"name": "Camargue"}},
             [{"id": "93", "name": "PACA", "official": "Provence-Alpes-Côte d'Azur"}], [s], "FR")
    xml = (tmp_path / "FR1.xml").read_text(encoding="utf-8")
    assert "<language>fr</language>" in xml and "Camargue · État des IBA" in xml
    assert f"{config.PAGES}/estado-iba/fr/#/a/black-marble/FR1" in xml
    assert "les sites et les communes de Provence" in (tmp_path / "ca-93.xml").read_text(encoding="utf-8")


def test_the_light_figure_counts_the_sites_that_rise_once_there_is_light():
    sig = {"kind": "night_light", "sites": [{"code": "FR1"}, {"code": "FR2"}]}
    meta = {"black-marble": {"name": "NASA Black Marble", "coverage": {"label": "x", "sites": ["FR1", "FR2", "FR3"]}}}
    got = web._figures({}, [sig], meta, "fr")
    assert (got["light"], got["light_sites"]) == ("2", "3")
    none = web._figures({}, [], {"black-marble": {"coverage": {"label": "x", "sites": []}}}, "fr")
    assert (none["light"], none["light_sites"]) == ("—", "—")
