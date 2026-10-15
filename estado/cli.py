"""python -m estado.cli build: read the sibling projects, turn them into signals and write docs/."""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import date, datetime, timezone
from functools import partial
from pathlib import Path

from . import adapters as A, aves, config, contract, health as H, indicators as I, luz, places, sources, web

# Name, link and what each source watches, as the site card says it.
SOURCES = {
    "observatorio-alegaciones": ("Observatorio de alegaciones", "proyectos en evaluación ambiental"),
    "vigia-incendios": ("Vigía de incendios", "incendios"),
    "centinela-natura": ("Centinela Natura", "cambios de uso del suelo"),
    "vigilancia-humedales": ("Vigilancia de humedales", "agua de sus humedales"),
    "caudal-ecologico": ("Caudal ecológico", "caudal de sus ríos frente al mínimo legal"),
    "riesgo-tendidos-aves": ("Riesgo de tendidos para aves", "aerogeneradores y tendidos peligrosos"),
    "sub-nocte": ("Sub Nocte", "migración nocturna"),
    "zona-inundable": ("Zona inundable", "edificios construidos en zona inundable"),
    "black-marble": ("NASA Black Marble", "luz artificial de noche"),
}
# sub-nocte works per city and zona-inundable per municipality, not per site
SITE_LEVEL = {k for k in SOURCES if k not in ("sub-nocte", "zona-inundable")}
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


def _places() -> dict:
    """The sites, the municipalities and communities around them, and the lookups built on both."""
    sites = I.load_sites(sources.get_json(config.SITES_URL), config.SITE_KIND)
    shapes = {c: places.polygonal(s["geometry"]) for c, s in sites.items()}
    topo = sources.get_json(config.MUNICIPALITIES_URL)
    regs = places.regions(topo)
    munis = places.municipalities(topo, sites, regs)
    return {"sites": sites, "shapes": shapes, "regs": regs, "munis": munis,
            "site_reg": places.site_regions(munis, shapes, regs),
            "resolve": partial(places.resolve, places.name_index(munis)), "locate": places.locator(munis, shapes)}


def _adapters(p: dict, today: date) -> dict:
    """How to read each sibling that does not publish its own signals.json yet (or never had another way)."""
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
        "zona-inundable": lambda: A.unpublished("Toda España"),  # signals.json only
        "black-marble": lambda: A.luz(
            json.loads(config.LIGHT_FILE.read_text(encoding="utf-8")), shapes, config.LIGHT_BASELINE,
            config.LIGHT_RECENT, config.LIGHT_MIN_RISE, config.LIGHT_MIN_ABS, config.LIGHT_MIN_PIXELS,
            config.LIGHT_PEERS),
    }


def _read(name: str, adapter, p: dict, origin: dict[str, str]):
    """The sibling's own signals.json when it publishes a valid one; its adapter otherwise."""
    doc = None if name in OWN else sources.published(name)
    if doc is not None:
        try:
            got = A.published(doc, name, p["resolve"], p["locate"])
            origin[name] = "signals.json"
            return got
        except (KeyError, TypeError, ValueError):
            traceback.print_exc()
            print(f"[{name}] signals.json no válido: se lee con su adaptador", file=sys.stderr)
    origin[name] = "adaptador"
    return adapter()


def build(today: date | None = None) -> None:
    today = today or date.today()
    failed: list[str] = []
    p = _places()
    sites, munis, regs, site_reg = p["sites"], p["munis"], p["regs"], p["site_reg"]

    origin: dict[str, str] = {}
    coverage, signals = {}, []
    for name, adapter in _adapters(p, today).items():
        got = _try(name, lambda: _read(name, adapter, p, origin), failed)
        if got:
            coverage[name], sig = got
            signals += sig
        else:
            coverage[name] = {"label": "sin datos hoy", "sites": [], "note": "La fuente no respondió en la última actualización."}
    signals = I.recent(signals, today, config.WINDOWS)
    signals = I.with_regions(I.restrict(signals, sites), {m["ine"]: m["region"] for m in munis}, site_reg)

    ids = {s["id"] for s in signals if s["source"] == "observatorio-alegaciones"}
    chains = _try("grafo-promotores", lambda: A.chains(sources.get_json(config.GRAFO_URL),
                                                         sources.get_json(config.CARTERA_URL), ids), failed) or {}

    n = I.summary(sites, signals, coverage, today)
    meta = {k: {"name": name, "url": OWN.get(k, f"{config.PAGES}/{k}/"),
                "watches": watches, "site_level": k in SITE_LEVEL, "coverage": coverage[k]}
            for k, (name, watches) in SOURCES.items()}
    web.build(sites, n, signals, chains, meta, munis, regs, site_reg, datetime.now(timezone.utc), today)
    by_kind: dict[str, int] = {}
    for s in signals:
        by_kind[s["kind"]] = by_kind.get(s["kind"], 0) + 1
    own = [k for k, v in origin.items() if v == "signals.json"]
    print(f"{len(sites)} espacios · {len(signals)} señales {by_kind} · {len(chains)} actos con promotor"
          + f" · con signals.json propio: {', '.join(own) or 'ninguno'}"
          + (f" · fallaron: {', '.join(failed)}" if failed else ""))


def _sorted_sites(s: dict) -> dict:
    return {**s, "sites": sorted(s["sites"], key=lambda x: x["code"])}


def check(name: str, where: str, today: date | None = None) -> bool:
    """Compare a sibling's signals.json (a path or a URL) with what its adapter reads today.

    Meant for the sibling's author before publishing: both sides go through the same reading as
    in a build and keep only the panel's sites, so any difference is one the panel would show. The adapter reads what is live, so
    a file made from newer data differs by the newest facts.
    """
    today = today or date.today()
    doc = sources.get_json(where) if where.startswith("http") else json.loads(Path(where).read_text(encoding="utf-8"))
    p = _places()
    cov_new, new = A.published(doc, name, p["resolve"], p["locate"])
    cov_old, old = _adapters(p, today)[name]()
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
    print("Iguales." if same else "Hay diferencias.")
    return same


def light(today: date | None = None) -> None:
    """Bring the night-light series of every site up to date (downloads from NASA; see luz.py)."""
    sites = I.load_sites(sources.get_json(config.SITES_URL), config.SITE_KIND)
    shapes = {c: places.polygonal(s["geometry"]) for c, s in sites.items()}
    doc = luz.update(shapes, config.LIGHT_FILE, today or date.today())
    print(f"{len(doc['sites'])} espacios · años {doc['years'][0] if doc['years'] else '—'}-"
          f"{doc['years'][-1] if doc['years'] else '—'} · actualizado {doc['updated']}")


def birds(source: str | None, today: date | None = None) -> None:
    """Write the birds each site was designated for (downloads the Natura 2000 release; see aves.py)."""
    sites = I.load_sites(sources.get_json(config.SITES_URL), config.SITE_KIND)
    got = aves.update(sites, config.BIRDS_FILE, source, today)
    print(f"{got['sites']} de {len(sites)} espacios con aves · {got['species']} especies"
          + (f" · sin nombre en castellano: {', '.join(got['unnamed'])}" if got["unnamed"] else ""))


def validate(name: str, where: str) -> bool:
    """A signals.json (a path or a URL) against the contract, strictly. Needs no network for a path."""
    doc = sources.get_json(where) if where.startswith("http") else json.loads(Path(where).read_text(encoding="utf-8"))
    rep = contract.validate(doc, name)
    n = len(doc.get("signals") or []) if isinstance(doc, dict) else 0
    print(f"{name}: {n} señales")
    for line in contract.describe(rep):
        print(f"- {line}")
    print("Cumple el contrato." if rep.ok else "No cumple el contrato.")
    return rep.ok


def health(today: date, issue: bool) -> bool:
    """Check every sibling; with --issue, keep the health issue of this repository up to date."""
    token = os.environ.get("GITHUB_TOKEN")
    findings = H.check(today, token, set(SOURCES) - OWN.keys())
    body = H.report(findings, list(config.SIBLINGS), today)
    print(body)
    if issue:
        repository = os.environ.get("GITHUB_REPOSITORY", f"{config.OWNER}/estado-iba")
        if not token:
            sys.exit("health --issue needs GITHUB_TOKEN")
        print(f"\nIssue: {H.sync_issue(findings, body, repository, token)}")
    return not any(f.level == "error" for f in findings)


def main() -> None:
    ap = argparse.ArgumentParser(prog="estado")
    ap.add_argument("command", choices=["build", "check", "validate", "health", "luz", "aves"])
    ap.add_argument("source", nargs="?", 
                    help="check, validate: the sibling's repository name; aves: the release zip, if already downloaded")
    ap.add_argument("signals", nargs="?", help="check, validate: its signals.json, a path or a URL")
    ap.add_argument("--today", type=date.fromisoformat, default=None)
    ap.add_argument("--issue", action="store_true", help="health: open, update or close the health issue")
    args = ap.parse_args()
    if args.command == "build":
        build(args.today)
    elif args.command == "luz":
        light(args.today)
    elif args.command == "aves":
        birds(args.source, args.today)
    elif args.command == "health":
        ok = health(args.today or datetime.now(timezone.utc).date(), args.issue)
        sys.exit(0 if ok or args.issue else 1)  # with --issue the alert is the issue, not a red run
    elif not (args.source and args.signals):
        ap.error(f"{args.command} needs a source and its signals.json")
    elif args.command == "validate":
        sys.exit(0 if validate(args.source, args.signals) else 1)
    elif args.source not in SOURCES:
        ap.error(f"check: {args.source} is not one of the panel's sources")
    else:
        sys.exit(0 if check(args.source, args.signals, args.today) else 1)


if __name__ == "__main__":
    main()
