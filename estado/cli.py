"""python -m estado.cli build: read the sibling projects, compute the panel and write docs/."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone

from . import config, indicators as I, sources, web


def build(today: date | None = None) -> None:
    today = today or date.today()
    sites = I.load_sites(sources.get_json(config.SITES_URL), config.SITE_KIND)
    codes = set(sites)
    proj = I.projects(sources.get_json(config.PROJECTS_URL), codes, today)
    fire = I.fires(sources.get_json(config.FIRES_URL), codes, today, config.FIRE_WINDOW_DAYS)
    watched = {f["properties"]["codigo"] for f in sources.get_json(config.LAND_SITES_URL)["features"]}
    land = I.land_change(sources.get_json(config.LAND_URL), watched, codes, config.LAND_STATES)
    wet: dict[str, list[dict]] = {}
    for meta, rows, inside in sources.wetlands(sites):
        st = I.wetland_state(rows, today, config.WETLAND_QUALITY, config.WETLAND_MIN_YEARS,
                             config.WETLAND_MAX_AGE_DAYS)
        for code in inside:
            wet.setdefault(code, []).append({**meta, "state": st})
    rows = I.panel(sites, proj, fire, land, wet)
    web.build(rows, sites, datetime.now(timezone.utc), today)
    print(f"{len(rows)} sitios · {sum(r['n_notices'] > 0 for r in rows)} con proyectos · "
          f"{sum(r['fire_ha'] > 0 for r in rows)} con fuego · {len(land)} vigilados por centinela · "
          f"{len(wet)} con humedal")


def main() -> None:
    ap = argparse.ArgumentParser(prog="estado")
    ap.add_argument("command", choices=["build"])
    ap.add_argument("--today", type=date.fromisoformat, default=None)
    args = ap.parse_args()
    if args.command == "build":
        build(args.today)


if __name__ == "__main__":
    main()
