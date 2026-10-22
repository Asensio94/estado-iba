import json
import re
from pathlib import Path

from estado import adapters as A, contract

ROOT = Path(__file__).resolve().parent.parent


def _doc(*signals, source="vigia-incendios"):
    return {"source": source, "version": 1, "generated": "2026-10-15T07:02Z",
            "coverage": {"label": "Toda España", "sites": None, "note": "n"}, "signals": list(signals)}


def _sig(id="F1", **kw):
    return {"id": id, "kind": "fire", "date": "2026-08-01", "title": "Incendio", "url": "https://x/#F1",
            "sites": [{"code": "ES0000014", "ha": 12.5}], "municipalities": ["10131"], "precision": "perimetro",
            "deadline": None, "status": "definitivo", "value": {"amount": 12.5, "unit": "ha"}, "details": {}, **kw}


def test_schema_and_panel_agree_on_kinds():
    assert contract.kinds() == A.KINDS


def test_schema_lists_the_kinds_and_precisions_of_contrato():
    text = (ROOT / "CONTRATO.md").read_text(encoding="utf-8")
    kinds = text.split("## Tipos", 1)[1].split("\n## ", 1)[0]
    table = set(re.findall(r"^\| `([a-z_]+)` \|", kinds, re.MULTILINE))
    assert table - {"kind"} == contract.kinds()
    precisions = contract.schema()["$defs"]["signal"]["properties"]["precision"]["enum"]
    line = next(l for l in text.splitlines() if l.startswith("| `precision`"))
    assert set(re.findall(r"`([a-z]+)`", line)) - {"precision"} == set(precisions)


def test_the_example_of_contrato_is_valid():
    text = (ROOT / "CONTRATO.md").read_text(encoding="utf-8")
    example = json.loads(re.search(r"```json\n(.*?)```", text, re.DOTALL).group(1))
    assert contract.validate(example, "vigia-incendios").ok


def test_unknown_kinds_are_counted_apart():
    r = contract.validate(_doc(_sig("A", kind="water_status"), _sig("B", kind="water_status"), _sig("C")))
    assert r.unknown_kinds == {"water_status": 2} and not r.errors and not r.ok


def test_errors_say_where():
    r = contract.validate(_doc(_sig(date="1/8/2026"), _sig("F2", municipios=["x"])), "vigia-incendios")
    assert any(e.startswith("signals[0].date") for e in r.errors)
    assert any(e.startswith("signals[1]") and "municipios" in e for e in r.errors)


def test_source_and_repeated_ids():
    r = contract.validate(_doc(_sig("A"), _sig("A")), "caudal-ecologico")
    assert any("source" in e for e in r.errors) and any("repetidos" in e for e in r.errors)


def test_a_point_signal_needs_somewhere_to_go():
    r = contract.validate(_doc(_sig("P", precision="punto", sites=[], municipalities=[])))
    assert r.ok and len(r.warnings) == 1
    r = contract.validate(_doc(_sig("P", precision="punto", sites=[], municipalities=[], details={"point": [-3.7, 40.4]})))
    assert r.ok and not r.warnings


def test_every_kind_has_its_words_and_a_map_layer():
    from estado import i18n

    app = (ROOT / "estado" / "static" / "app.js").read_text(encoding="utf-8")
    drawn = {k for ks in re.findall(r"kinds: \[([^\]]*)\]", app) for k in re.findall(r'"([a-z_]+)"', ks)}
    for lang in ("es", "fr"):
        assert A.KINDS <= i18n.UI[lang]["kinds"].keys()
    assert A.KINDS - {"resolution", "flood_building"} <= drawn  # those two are never drawn
