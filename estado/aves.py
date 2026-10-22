"""python -m estado.cli aves: the birds each site was designated for, from the Natura 2000 database.

Every Natura 2000 site has an official Standard Data Form, and the EEA publishes them all once a
year as open data (CC BY 4.0). Its SPECIES table lists, per site, each species, whether it is
there all year, breeds, winters or stops on passage, and how much of the national population the
site holds: A over 15 %, B 2-15 %, C under 2 %, D not significant. A to C are why a ZEPA was
designated; D species are counted, not listed. Some forms leave that share blank but still rate the
site's overall value for the species (GLOBAL, A to C): listed as X. Others, mostly in the Canaries,
name the species and assess nothing: listed last, as N, so those sites do not look empty.

Nothing here gives a number of birds or a place inside a site: the counts of the form are left out,
and so is any row the State marked as sensitive (the public database already withholds most).
The Spanish names come from estado/aves_es.tsv, keyed by the species code of the Birds Directive,
and the French ones from estado/aves_fr.tsv: Wikidata's French labels, which follow the list of the
Commission de l'avifaune française, checked by hand, and the subspecies of the forms named by hand.
One file serves every country: each species carries its scientific name and one name per language.
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
import zipfile
from datetime import date
from pathlib import Path

import requests

VERSION = "end2024 rev1"  # the EEA releases one a year; a new one means a new URL and maybe new codes
DOI = "10.2909/d713bff7-0cdf-4f0d-acd1-dc3c63af237e"
# A public share of the EEA datastore: its token is the WebDAV user, with no password.
SHARE_TOKEN = "sptXqwkQr5g7Bp5"
ZIP_URL = ("https://sdi.eea.europa.eu/datashare/public.php/webdav/eea_t_natura2000_p_2024_v01_r01/"
           "Natura2000_end2024_rev1_csv.zip")
SDF_URL = "https://natura2000.eea.europa.eu/Natura2000/SDF.aspx?site={code}"
NAMES_FILE = Path(__file__).with_name("aves_es.tsv")
NAMES_FR_FILE = Path(__file__).with_name("aves_fr.tsv")
SEASONS = "prwc"  # all year, breeding, wintering, on passage: the order the panel shows them in
GRADES = "ABC"  # share of the national population
RANK = "ABCXND"  # best first: shares, overall value only (X), named only (N), not significant (D)


def names(path: Path = NAMES_FILE, column: str = "name_es") -> dict[str, str]:
    """Name per species code, Spanish by default."""
    with path.open(encoding="utf-8", newline="") as f:
        return {r["code"]: r[column] for r in csv.DictReader(f, delimiter="\t")}


def read(path: str | Path) -> list[dict]:
    """The bird rows of the SPECIES table, from the release's CSV zip or from the table itself."""
    path = Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            member = next(n for n in z.namelist() if n.endswith("_SPECIES.csv"))
            text = z.read(member).decode("utf-8-sig")
    else:
        text = path.read_text(encoding="utf-8-sig")
    return [r for r in csv.DictReader(io.StringIO(text)) if r["SPGROUP"] == "Birds"]


def _grade(r: dict) -> str:
    g = r["POPULATION"].strip().upper()
    if g:
        return g if g in RANK else "D"
    return "X" if r["GLOBAL"] and r["GLOBAL"] in GRADES else "N"


def by_site(rows: list[dict], codes, es: dict[str, str], fr: dict[str, str] | None = None) -> dict:
    """Per site, the species it holds a significant share of, with their seasons and that share.

    With French names, each species gets a third element, and a French site's birds are sorted by them.
    """
    codes = set(codes)
    seen: dict[str, dict[str, dict]] = {}
    sci: dict[str, str] = {}
    for r in rows:
        code, sp = r["SITECODE"], r["SPECIESCODE"]
        if code not in codes or r["SENSITIVE"] == "1" or r["NONPRESENCEINSITE"] == "1":
            continue
        sci.setdefault(sp, r["SPECIESNAME"].strip())
        x = seen.setdefault(code, {}).setdefault(sp, {"seasons": set(), "grade": "D"})
        if r["POPULATION_TYPE"] and r["POPULATION_TYPE"] in SEASONS:  # "" is in every string
            x["seasons"].add(r["POPULATION_TYPE"])
        g = _grade(r)
        if RANK.index(g) < RANK.index(x["grade"]):
            x["grade"] = g  # a species in several rows (breeding and wintering) keeps its best grade

    def label(sp, names=es):
        return names.get(sp) or sci[sp]

    sites = {}
    for code, spp in sorted(seen.items()):
        names = fr if fr is not None and code.startswith("FR") else es
        birds = sorted(([sp, "".join(s for s in SEASONS if s in x["seasons"]), x["grade"]]
                        for sp, x in spp.items() if x["grade"] != "D"),
                       key=lambda b: (RANK.index(b[2]), label(b[0], names)))
        sites[code] = {"birds": birds, "other": sum(1 for x in spp.values() if x["grade"] == "D")}

    def used(prefix=""):
        return sorted({b[0] for c, s in sites.items() if c.startswith(prefix) for b in s["birds"]})

    out = {"species": {sp: [sci[sp], label(sp)] + ([label(sp, fr)] if fr is not None else []) for sp in used()},
           "sites": sites, "unnamed": [sp for sp in used("" if fr is None else "ES") if sp not in es]}
    if fr is not None:
        out["unnamed_fr"] = [sp for sp in used("FR") if sp not in fr]
    return out


def download(dest: Path) -> Path:
    with requests.get(ZIP_URL, auth=(SHARE_TOKEN, ""), stream=True, timeout=120) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return dest


def update(codes, out: Path, source: str | None = None, today: date | None = None) -> dict:
    """Write the birds of every site to out; source is the release's zip or SPECIES.csv, else it is downloaded."""
    if source is None:
        with tempfile.TemporaryDirectory() as tmp:
            rows = read(download(Path(tmp) / "natura2000.zip"))
    else:
        rows = read(source)
    got = by_site(rows, codes, names(), names(NAMES_FR_FILE, "name_fr"))
    unnamed, unnamed_fr = got.pop("unnamed"), got.pop("unnamed_fr")
    doc = {"source": f"Natura 2000 ({VERSION}), Agencia Europea de Medio Ambiente, CC BY 4.0", "doi": DOI,
           "version": VERSION, "updated": (today or date.today()).isoformat(), "languages": ["es", "fr"], **got}
    out.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"sites": len(got["sites"]), "species": len(got["species"]), "unnamed": unnamed, "unnamed_fr": unnamed_fr}
