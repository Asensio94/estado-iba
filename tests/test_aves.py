"""Birds per site from the Natura 2000 SPECIES table: seasons, grade, what is left out."""
import csv
import io
import zipfile

from estado import aves as V

FIELDS = ["COUNTRY_CODE", "SITECODE", "SPECIESNAME", "SPECIESCODE", "REF_SPGROUP", "SPGROUP", "SENSITIVE",
          "NONPRESENCEINSITE", "POPULATION_TYPE", "LOWERBOUND", "UPPERBOUND", "COUNTING_UNIT",
          "ABUNDANCE_CATEGORY", "DATAQUALITY", "POPULATION", "CONSERVATION", "ISOLATION", "GLOBAL",
          "INTRODUCTION_CANDIDATE"]


def row(site, sp, name, kind, grade, group="Birds", sensitive="", absent="0"):
    overall = "" if grade == "D" or (not grade and not kind) else "A"
    return dict(zip(FIELDS, ["ES", site, name, sp, "", group, sensitive, absent, kind, "10", "20", "p", "",
                             "G", grade, "B", "C", overall, "No"]))


ROWS = [
    row("ES1", "A031", "Ciconia ciconia", "r", "C"),
    row("ES1", "A031", "Ciconia ciconia", "c", "B"),  # same bird on passage, a larger share
    row("ES1", "A127", "Grus grus", "w", "A"),
    row("ES1", "A053", "Anas platyrhynchos", "p", "D"),
    row("ES1", "A405", "Aquila adalberti", "r", "A", sensitive="1"),
    row("ES1", "A094", "Pandion haliaetus", "c", "C", absent="1"),
    row("ES1", "1355", "Lutra lutra", "p", "C", group="Mammals"),
    row("ES1", "A387", "Bulweria bulwerii", "r", ""),  # share blank, overall value A
    row("ES1", "A026", "Egretta garzetta", "", ""),  # named, nothing assessed: listed last
    row("ES9", "A127", "Grus grus", "w", "A"),  # not a site of the panel
]


def test_a_site_lists_its_significant_birds_with_seasons_and_best_grade():
    got = V.by_site([r for r in ROWS if r["SPGROUP"] == "Birds"], ["ES1"], {"A127": "Grulla común"})
    assert got["sites"] == {"ES1": {"birds": [["A127", "w", "A"], ["A031", "rc", "B"], ["A387", "r", "X"],
                                            ["A026", "", "N"]], "other": 1}}
    assert got["species"] == {"A127": ["Grus grus", "Grulla común"], "A031": ["Ciconia ciconia", "Ciconia ciconia"],
                              "A387": ["Bulweria bulwerii", "Bulweria bulwerii"],
                              "A026": ["Egretta garzetta", "Egretta garzetta"]}
    assert got["unnamed"] == ["A026", "A031", "A387"]  # no Spanish name: shown by its scientific one, and reported


def test_counts_sensitive_and_absent_rows_never_reach_the_output(tmp_path):
    buf = io.StringIO()
    w = csv.DictWriter(buf, FIELDS)
    w.writeheader()
    w.writerows(ROWS)
    z = tmp_path / "n2k.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("Natura2000_end2024_rev1_SPECIES.csv", "﻿" + buf.getvalue())
    out = tmp_path / "aves.json"
    got = V.update(["ES1"], out, str(z))
    text = out.read_text(encoding="utf-8")
    assert got["sites"] == 1 and "Lutra" not in text
    assert "A405" not in text and "A094" not in text  # sensitive, and recorded as not present
    assert '"20"' not in text and "LOWERBOUND" not in text  # no population figures at all


def test_every_spanish_name_is_filled():
    es = V.names()
    assert len(es) > 200 and all(es.values())
