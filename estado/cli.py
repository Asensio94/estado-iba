"""python -m estado.cli build: read the sibling projects, turn them into signals and write docs/.

Country is a dimension: Spain is built into docs/ and France into docs/fr/, each with its own sites,
municipalities, signals and page in its own language. France is built after Spain and on its own:
whatever fails in France, Spain's panel is written all the same.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import date, datetime, timezone
from functools import partial
from pathlib import Path

from . import adapters as A, aves, config, france, i18n, indicators as I, luz, places, sources, web

# Name and what each source watches, as the site card says it (each language has its own in i18n).
SOURCES = i18n.PY["es"]["sources"]
SITE_LEVEL = {k for k in SOURCES if k != "sub-nocte"}  # sub-nocte works per city, not per site
# Read here from open data rather than from a sibling: no signals.json to look for, and their own link.
OWN = {"black-marble": config.LIGHT_PAGE}


def _try(name: str, fn, failed: list[str]):
    """Run one source; a sibling that is down today must not take the whole panel with it."""
    try:
        return fn()
    except Exception:  # noqa: BLE001 - any failure of one source is reported, not fatal
        traceback.print_exc()
        print(f"[{name}] sin datos hoy", file=sys.stderr)
        failed.append(name)
        return None


def _sites(country: str = "ES") -> dict[str, dict]:
    if country == "FR":
        return france.load_sites(sources.get_json(france.SPA_URL))
    return I.load_sites(sources.get_json(config.SITES_URL), config.SITE_KIND)


def _places(country: str = "ES") -> dict:
    """The sites, the municipalities and regions around them, and the lookups built on both."""
    sites = _sites(country)
    shapes = {c: places.polygonal(s["geometry"]) for c, s in sites.items()}
    if country == "FR":
        ref = france.load_reference()
        regs = places.regions_fr(ref)
        munis = places.communes_fr(ref, sites)
    else:
        topo = sources.get_json(config.MUNICIPALITIES_URL)
        regs = places.regions(topo)
        munis = places.municipalities(topo, sites, regs)
    return {"country": country, "sites": sites, "shapes": shapes, "regs": regs, "munis": munis,
            "site_reg": places.site_regions(munis, shapes, regs),
            "resolve": partial(places.resolve, places.name_index(munis, country), country=country),
            "locate": places.locator(munis, shapes)}


def _light(p: dict) -> tuple[dict, list[dict]]:
    path = config.LIGHT_FILES[p["country"]]
    return A.luz(json.loads(path.read_text(encoding="utf-8")), p["shapes"], config.LIGHT_BASELINE,
                 config.LIGHT_RECENT, config.LIGHT_MIN_RISE, config.LIGHT_MIN_ABS, config.LIGHT_MIN_PIXELS,
                 config.LIGHT_PEERS, p["country"])


def _adapters(p: dict, today: date) -> dict:
    """How to read each sibling that does not publish its own signals.json yet (they all read Spain)."""
    if p["country"] != "ES":
        return {"black-marble": lambda: _light(p)}
    sites, shapes, resolve, locate = p["sites"], p["shapes"], p["resolve"], p["locate"]
    return {
        "observatorio-alegaciones": lambda: A.observatorio(sources.get_json(config.PROJECTS_URL), resolve),
        "vigia-incendios": lambda: A.vigia(sources.get_json(config.FIRES_URL), resolve, today, config.FIRE_WINDOW_DAYS),
        "centinela-natura": lambda: A.centinela(
            sources.get_json(config.LAND_URL),
            [f["properties"]["codigo"] for f in sources.get_json(config.LAND_SITES_URL)["features"]],
            resolve, config.LAND_STATES),
        "vigilancia-humedales": lambda: A.humedales(
            sources.wetlands(sites),
            partial(I.wetland_state, today=today, quality=config.WETLAND_QUALITY,
                    min_years=config.WETLAND_MIN_YEARS, max_age=config.WETLAND_MAX_AGE_DAYS)),
        "caudal-ecologico": lambda: A.caudal(*sources.caudal(), locate, today),
        "riesgo-tendidos-aves": lambda: A.tendidos(
            {r: sources.get_csv_dated(config.LINES_URL.format(region=r)) for r in config.LINE_REGIONS}, shapes),
        "sub-nocte": lambda: A.subnocte(sources.get_csv(config.MIGRATION_URL), resolve, today),
        "black-marble": lambda: _light(p),
    }


def _read(name: str, adapter, p: dict, origin: dict[str, str], docs: dict):
    """The sibling's own signals.json when it publishes a valid one for this country; its adapter otherwise.

    None when neither covers the country. Each signals.json is fetched once for every country.
    """
    if name not in OWN and name not in docs:
        docs[name] = sources.published(name)
    doc = docs.get(name)
    if doc is not None:
        try:
            got = A.published(doc, name, p["resolve"], p["locate"], p["country"])
            if got is not None:
                origin[name] = "signals.json"
                return got
            if adapter is None:  # the file is there, but says nothing of this country
                return None
        except (KeyError, TypeError, ValueError):
            traceback.print_exc()
            print(f"[{name}] signals.json no válido: se lee con su adaptador", file=sys.stderr)
    if adapter is None:
        return None
    origin[name] = "adaptador"
    return adapter()


def build(today: date | None = None) -> None:
    today = today or date.today()
    docs: dict = {}
    _build("ES", today, docs)
    failed: list[str] = []
    _try("FR", lambda: _build("FR", today, docs), failed)
    if failed:
        print("Francia no se ha podido construir hoy; España sí.", file=sys.stderr)


def _build(country: str, today: date, docs: dict) -> None:
    lang = i18n.LANG_BY_COUNTRY[country]
    T = i18n.PY[lang]
    failed: list[str] = []
    p = _places(country)
    sites, munis, regs, site_reg = p["sites"], p["munis"], p["regs"], p["site_reg"]

    origin: dict[str, str] = {}
    coverage, signals = {}, []
    readers = _adapters(p, today)
    for name in SOURCES:
        got = _try(name, lambda: _read(name, readers.get(name), p, origin, docs), failed)
        if got:
            coverage[name], sig = got
            signals += sig
        elif name in failed:
            coverage[name] = {"label": T["no_data"], "sites": [], "note": T["no_data_note"], "failed": True}
        else:  # nothing of this source reaches the country: grey on the map, never «nothing found»
            coverage[name] = {"label": T["absent"], "sites": [], "note": T["absent_note"], "absent": True}
    signals = I.recent(signals, today, config.WINDOWS)
    signals = I.with_regions(I.restrict(signals, sites), {m["ine"]: m["region"] for m in munis}, site_reg)

    chains = {}
    if country == "ES":  # the BORME and the Spanish annual accounts
        ids = {s["id"] for s in signals if s["source"] == "observatorio-alegaciones"}
        chains = _try("grafo-promotores", lambda: A.chains(sources.get_json(config.GRAFO_URL),
                                                             sources.get_json(config.CARTERA_URL), ids), failed) or {}

    n = I.summary(sites, signals, coverage, today)
    meta = {k: {"name": name, "url": OWN.get(k, f"{config.PAGES}/{k}/"),
                "watches": watches, "site_level": k in SITE_LEVEL, "coverage": coverage[k]}
            for k, (name, watches) in T["sources"].items()}
    web.build(sites, n, signals, chains, meta, munis, regs, site_reg, datetime.now(timezone.utc), today, country)
    by_kind: dict[str, int] = {}
    for s in signals:
        by_kind[s["kind"]] = by_kind.get(s["kind"], 0) + 1
    own = [k for k, v in origin.items() if v == "signals.json"]
    print(f"{country}: {len(sites)} espacios · {len(signals)} señales {by_kind} · {len(chains)} actos con promotor"
          + f" · con signals.json propio: {', '.join(own) or 'ninguno'}"
          + (f" · fallaron: {', '.join(failed)}" if failed else ""))


def _sorted_sites(s: dict) -> dict:
    return {**s, "sites": sorted(s["sites"], key=lambda x: x["code"])}


def check(name: str, where: str, today: date | None = None) -> bool:
    """Check a sibling's signals.json (a path or a URL): its form, then what it says against its adapter.

    First the JSON Schema of the contract (docs/signals.schema.json), versions 1 and 2. Then its
    Spanish part is compared with what the adapter reads today: both sides go through the same
    reading as in a build and keep only the panel's sites, so any difference is one the panel would
    show. The adapter reads what is live, so a file made from newer data differs by the newest facts.
    Its other countries have no adapter to compare with: what the panel would keep is reported.
    """
    today = today or date.today()
    doc = sources.get_json(where) if where.startswith("http") else json.loads(Path(where).read_text(encoding="utf-8"))
    errors = A.schema_errors(doc)
    for e in errors[:20]:
        print(f"esquema: {e}")
    if errors:
        print(f"No cumple el esquema ({len(errors)} errores).")
        return False
    print(f"Cumple el esquema (versión {doc['version']}).")
    same = True
    for country in config.COUNTRIES:
        if country != "ES":
            if doc["version"] == 2 and country in doc["coverage"]:
                p = _places(country)
                _, sig = A.published(doc, name, p["resolve"], p["locate"], country)
                kept = I.restrict(I.recent(sig, today, config.WINDOWS), p["sites"])
                print(f"{country}: {len(sig)} señales válidas, {len(kept)} en sus {len(p['sites'])} espacios")
            continue
        p = _places("ES")
        got = A.published(doc, name, p["resolve"], p["locate"])
        if got is None:
            print("ES: el fichero no cubre España.")
            continue
        same = _compare(got, _adapters(p, today)[name](), p, today) and same
    print("Iguales." if same else "Hay diferencias.")
    return same


def _compare(published: tuple[dict, list[dict]], adapted: tuple[dict, list[dict]], p: dict, today: date) -> bool:
    (cov_new, new), (cov_old, old) = published, adapted
    # Only the panel's sites count: a ZEC code a sibling also sends never shows here.
    new, old = ({s["id"]: _sorted_sites(s) for s in I.restrict(I.recent(x, today, config.WINDOWS), p["sites"])}
                for x in (new, old))
    print(f"signals.json: {len(new)} señales · adaptador: {len(old)}")
    same = True
    for k in ("label", "note"):
        if cov_new[k] != cov_old[k]:
            same = False
            print(f"coverage.{k}: {cov_new[k]!r} frente a {cov_old[k]!r}")
    a, b = (None if c["sites"] is None else set(c["sites"]) & p["sites"].keys() for c in (cov_new, cov_old))
    if a != b:
        same = False
        line = f"coverage.sites: {'todas' if a is None else len(a)} frente a {'todas' if b is None else len(b)}"
        if a is not None and b is not None:
            line += f" · solo en el fichero {sorted(a - b)[:10]} · solo en el adaptador {sorted(b - a)[:10]}"
        print(line)
    for label, ids in (("solo en signals.json", new.keys() - old.keys()), ("solo en el adaptador", old.keys() - new.keys())):
        if ids:
            same = False
            print(f"{label}: {len(ids)} · {sorted(ids)[:10]}")
    fields: dict[str, list[str]] = {}
    for i in sorted(new.keys() & old.keys()):
        x, y = new[i], old[i]
        for f in [k for k in x if k != "details"]:
            if x[f] != y.get(f):
                fields.setdefault(f, []).append(f"{i}: {x[f]!r} frente a {y.get(f)!r}")
        for k in sorted(x["details"].keys() | y["details"].keys()):
            if x["details"].get(k) != y["details"].get(k):
                fields.setdefault(f"details.{k}", []).append(f"{i}: {x['details'].get(k)!r} frente a {y['details'].get(k)!r}")
    for f, diffs in sorted(fields.items()):
        same = False
        print(f"{f} distinto en {len(diffs)}: " + " | ".join(diffs[:3]))
    return same


def light(today: date | None = None, countries=config.COUNTRIES) -> None:
    """Bring the night-light series of every site up to date (downloads from NASA; see luz.py).

    Each country is its own file. One that fails does not stop the other, but the run still fails.
    """
    failed: list[str] = []
    for country in countries:
        def one():
            sites = _sites(country)
            shapes = {c: places.polygonal(s["geometry"]) for c, s in sites.items()}
            path = config.LIGHT_FILES[country]
            path.parent.mkdir(parents=True, exist_ok=True)
            doc = luz.update(shapes, path, today or date.today())
            print(f"{country}: {len(doc['sites'])} espacios · años {doc['years'][0] if doc['years'] else '—'}-"
                  f"{doc['years'][-1] if doc['years'] else '—'} · actualizado {doc['updated']}")
        _try(country, one, failed)
    if failed:
        sys.exit(1)


def birds(source: str | None, today: date | None = None) -> None:
    """Write the birds each site was designated for, in every country (downloads the Natura 2000 release; see aves.py)."""
    sites = {c: s for country in config.COUNTRIES for c, s in _sites(country).items()}
    got = aves.update(sites, config.BIRDS_FILE, source, today)
    print(f"{got['sites']} de {len(sites)} espacios con aves · {got['species']} especies"
          + (f" · sin nombre en castellano: {', '.join(got['unnamed'])}" if got["unnamed"] else "")
          + (f" · sin nombre en francés: {', '.join(got['unnamed_fr'])}" if got["unnamed_fr"] else ""))


def communes(today: date | None = None) -> None:
    """Download France's communes and regions from the IGN once a year (see france.py)."""
    got = france.download(today=today)
    print(f"{got['regions']} regiones · {got['departments']} departamentos · {got['communes']} municipios · "
          f"{got['bytes'] / 1e6:.1f} MB en {france.REF_FILE.name}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="estado")
    ap.add_argument("command", choices=["build", "check", "luz", "aves", "communes"])
    ap.add_argument("source", nargs="?", help="check: the sibling, as in SOURCES; aves: the release zip, if already "
                                              "downloaded; luz: ES or FR, both if left out")
    ap.add_argument("signals", nargs="?", help="check: its signals.json, a path or a URL")
    ap.add_argument("--today", type=date.fromisoformat, default=None)
    args = ap.parse_args()
    if args.command == "build":
        build(args.today)
    elif args.command == "luz":
        if args.source and args.source not in config.COUNTRIES:
            ap.error(f"luz takes a country: {', '.join(config.COUNTRIES)}")
        light(args.today, [args.source] if args.source else config.COUNTRIES)
    elif args.command == "aves":
        birds(args.source, args.today)
    elif args.command == "communes":
        communes(args.today)
    elif not (args.source in SOURCES and args.signals):
        ap.error("check needs a source and its signals.json")
    else:
        sys.exit(0 if check(args.source, args.signals, args.today) else 1)


if __name__ == "__main__":
    main()
