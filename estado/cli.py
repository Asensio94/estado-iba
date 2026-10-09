"""python -m estado.cli build: read the sibling projects, turn them into signals and write docs/."""

from __future__ import annotations

import argparse
import sys
import traceback
from datetime import date, datetime, timezone
from functools import partial

from shapely import make_valid
from shapely.geometry import shape

from . import adapters as A, config, indicators as I, places, sources, web

# Name, link and what each source watches, as the site card says it.
SOURCES = {
    "observatorio-alegaciones": ("Observatorio de alegaciones", "proyectos en evaluación ambiental"),
    "vigia-incendios": ("Vigía de incendios", "incendios"),
    "centinela-natura": ("Centinela Natura", "cambios de uso del suelo"),
    "vigilancia-humedales": ("Vigilancia de humedales", "agua de sus humedales"),
    "caudal-ecologico": ("Caudal ecológico", "caudal de sus ríos frente al mínimo legal"),
    "riesgo-tendidos-aves": ("Riesgo de tendidos para aves", "tendidos peligrosos"),
    "sub-nocte": ("Sub Nocte", "migración nocturna"),
}
SITE_LEVEL = {k for k in SOURCES if k != "sub-nocte"}  # sub-nocte works per city, not per site


def _try(name: str, fn, failed: list[str]):
    """Run one source; a sibling that is down today must not take the whole panel with it."""
    try:
        return fn()
    except Exception:  # noqa: BLE001 - any failure of one source is reported, not fatal
        traceback.print_exc()
        print(f"[{name}] sin datos hoy", file=sys.stderr)
        failed.append(name)
        return None


def build(today: date | None = None) -> None:
    today = today or date.today()
    failed: list[str] = []
    sites = I.load_sites(sources.get_json(config.SITES_URL), config.SITE_KIND)
    shapes = {c: make_valid(shape(s["geometry"])) for c, s in sites.items()}
    munis = places.municipalities(sources.get_json(config.MUNICIPALITIES_URL), sites)
    idx = places.name_index(munis)
    resolve = partial(places.resolve, idx)
    locate = places.locator(munis, shapes)

    results = {
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
    }
    coverage, signals = {}, []
    for name, fn in results.items():
        got = _try(name, fn, failed)
        if got:
            coverage[name], sig = got
            signals += sig
        else:
            coverage[name] = {"label": "sin datos hoy", "sites": [], "note": "La fuente no respondió en la última actualización."}
    signals = I.restrict(signals, sites)

    ids = {s["id"] for s in signals if s["source"] == "observatorio-alegaciones"}
    chains = _try("grafo-promotores", lambda: A.chains(sources.get_json(config.GRAFO_URL),
                                                         sources.get_json(config.CARTERA_URL), ids), failed) or {}

    n = I.summary(sites, signals, coverage, today)
    meta = {k: {"name": name, "url": f"{config.PAGES}/{k}/" if k != "caudal-ecologico" else "https://github.com/Asensio94/caudal-ecologico",
                "watches": watches, "site_level": k in SITE_LEVEL, "coverage": coverage[k]}
            for k, (name, watches) in SOURCES.items()}
    web.build(sites, n, signals, chains, meta, munis, datetime.now(timezone.utc), today)
    by_kind: dict[str, int] = {}
    for s in signals:
        by_kind[s["kind"]] = by_kind.get(s["kind"], 0) + 1
    print(f"{len(sites)} espacios · {len(signals)} señales {by_kind} · {len(chains)} actos con promotor"
          + (f" · fallaron: {', '.join(failed)}" if failed else ""))


def main() -> None:
    ap = argparse.ArgumentParser(prog="estado")
    ap.add_argument("command", choices=["build"])
    ap.add_argument("--today", type=date.fromisoformat, default=None)
    args = ap.parse_args()
    if args.command == "build":
        build(args.today)


if __name__ == "__main__":
    main()
