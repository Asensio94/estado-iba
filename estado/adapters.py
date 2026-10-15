"""Translate what each sibling project publishes into signals (see CONTRATO.md).

A sibling that publishes its own signals.json is read with `published`. The others still have
one function each here, which reads their internal files; each returns (coverage, signals).
Municipality names are resolved to INE codes with `resolve`, a callable
(name, provinces) -> code | None built from the IGN layer (INSEE codes and IGN Admin Express in France).
"""

from __future__ import annotations

import re
import statistics
import sys
from collections import Counter
from datetime import date, timedelta
from typing import Callable

from shapely import STRtree, box
from shapely.geometry import Point

from . import config, i18n

Resolve = Callable[[str, list[str]], "str | None"]


# The bulletins name a natural person as «D. Nombre Apellidos»; companies and bodies carry no
# honorific. Many companies carry no legal form either, so the test is the honorific, not its absence.
_PERSON = re.compile(r"^\s*(D\.ª|Dª|Dña\.?|D\.|Don|Doña|Sr\.|Sra\.)\s", re.IGNORECASE)


def promoter(name: str | None) -> str | None:
    """The promoter as published, or None when it is a natural person: the panel names no one."""
    return None if not name or _PERSON.match(name) else name


def _signal(source: str, id: str, kind: str, day: str, title: str, url: str, precision: str, **kw) -> dict:
    return {"source": source, "country": kw.pop("country", "ES"), "id": id, "kind": kind, "date": day,
            "title": title, "url": url,
            "sites": kw.pop("sites", []), "municipalities": kw.pop("municipalities", []),
            "precision": precision, "deadline": kw.pop("deadline", None), "status": kw.pop("status", None),
            "value": kw.pop("value", None), "details": kw}


def _munis(resolve: Resolve, names: list[str] | None, provinces: list[str] | None) -> list[str]:
    return sorted({c for n in names or [] if (c := resolve(n, provinces or []))})


KINDS = {"notice", "resolution", "fire", "land_change", "wetland_water", "river_flow", "power_line", "migration",
         "night_light"}
REQUIRED = ("id", "kind", "date", "title", "url", "precision")
# Municipality codes: INE in Spain, INSEE in France (Corsica's departments are 2A and 2B).
MUNI_CODE = {"ES": re.compile(r"^\d{5}$"), "FR": re.compile(r"^(\d{5}|2[AB]\d{3})$")}
SCHEMA_FILE = config.DOCS_DIR / "signals.schema.json"


def schema_errors(doc: dict) -> list[str]:
    """Where a signals.json breaks the contract's JSON Schema (versions 1 and 2), as «path: message»."""
    import json

    from jsonschema import Draft202012Validator

    v = Draft202012Validator(json.loads(SCHEMA_FILE.read_text(encoding="utf-8")))
    return [f"{'/'.join(map(str, e.absolute_path)) or '(raíz)'}: {e.message}"
            for e in sorted(v.iter_errors(doc), key=lambda e: list(map(str, e.absolute_path)))]


def published(doc: dict, source: str, resolve: Resolve, locate: Callable,
              country: str = "ES") -> tuple[dict, list[dict]] | None:
    """One country's part of a sibling's own signals.json (CONTRATO.md, versions 1 and 2), checked and placed.

    Version 1 is all Spain. In version 2 each signal names its country and the coverage is given
    per country; a country the file gives no coverage for is not covered by it (None), and its
    signals, if any, are dropped: a fact with no coverage could not be read against what is watched.

    A signal missing a required field, or of a kind the map cannot draw, is dropped: every figure
    must be checkable. So is a municipality code not of the country's form. Municipality names
    become codes here, so a sibling need not carry the IGN layer; a «punto» signal with no place at
    all gets its sites and municipality from its point.
    """
    version = doc.get("version")
    if version not in (1, 2) or doc.get("source") != source:
        raise ValueError(f"signals.json de {doc.get('source')!r}, versión {version!r}")
    if version == 1:
        if country != "ES":
            return None
        cov, signals = doc["coverage"], doc["signals"]
    else:
        cov = doc["coverage"].get(country)
        signals = [s for s in doc["signals"] if s.get("country") == country]
        if cov is None:
            if signals:
                print(f"[{source}] signals.json: {len(signals)} señales de {country} sin cobertura, descartadas",
                      file=sys.stderr)
            return None
    out, dropped = [], 0
    for s in signals:
        if not all(s.get(k) for k in REQUIRED) or s["kind"] not in KINDS:
            dropped += 1
            continue
        details = s.get("details") or {}
        if "promoter" in details:  # whoever sends it
            details = {**details, "promoter": promoter(details["promoter"])}
        sites = [x for x in s.get("sites") or [] if x.get("code")]
        munis = sorted({c for c in s.get("municipalities") or [] if MUNI_CODE[country].match(str(c))}
                       | set(_munis(resolve, s.get("municipality_names"), s.get("provinces"))))
        if s["precision"] == "punto" and details.get("point") and not sites and not munis:
            codes, munis = locate(*details["point"])
            sites = [{"code": c} for c in codes]
        out.append({"source": source, "country": country, "id": str(s["id"]), "kind": s["kind"], "date": s["date"],
                    "title": s["title"],
                    "url": s["url"], "sites": sites, "municipalities": munis, "precision": s["precision"],
                    "deadline": s.get("deadline"), "status": s.get("status"), "value": s.get("value"),
                    "details": details})
    if dropped:
        print(f"[{source}] signals.json: {dropped} señales incompletas descartadas", file=sys.stderr)
    return {"label": cov["label"], "sites": cov.get("sites"), "note": cov.get("note", "")}, out


def observatorio(state: dict, resolve: Resolve) -> tuple[dict, list[dict]]:
    """Notices in public consultation and the resolutions paired with them.

    A notice reaches a site through its cadastral footprint when there is one, and otherwise
    through the municipalities it names. Resolutions carry no geometry: they inherit the sites of
    the notice observatorio paired them with.
    """
    src = "observatorio-alegaciones"
    out, by_id = [], {}
    for n in state["anuncios"].values():
        footprint = (n.get("footprint") or {}).get("natura") or []
        natura, precision = (footprint, "parcelas") if footprint else (n.get("natura") or [], "municipio")
        s = _signal(src, n["identificador"], "notice", n["fecha"], n["titulo"], n["url_html"], precision,
                    sites=[{"code": x.get("sitecode") or x.get("codigo")} for x in natura],
                    municipalities=_munis(resolve, n.get("municipios"), n.get("provincias")),
                    deadline=n.get("fecha_limite") or None,
                    value={"amount": n["potencia_mw"], "unit": "MW"} if n.get("potencia_mw") else None,
                    category=n.get("categoria"), promoter=promoter(n.get("promotor")),
                    file=n.get("expediente") or None, department=n.get("departamento"))
        out.append(s)
        by_id[s["id"]] = s
    for r in state["resoluciones"].values():
        paired = by_id.get(r.get("emparejado_con") or "")
        out.append(_signal(src, r["identificador"], "resolution", r["fecha"], r["titulo"], r["url_html"],
                           paired["precision"] if paired else "municipio",
                           sites=paired["sites"] if paired else [],
                           municipalities=_munis(resolve, r.get("municipios"), r.get("provincias")),
                           status=r.get("sentido_etiqueta") or r.get("sentido"),
                           value={"amount": r["potencia_mw"], "unit": "MW"} if r.get("potencia_mw") else None,
                           category=r.get("categoria"), promoter=promoter(r.get("promotor")),
                           file=r.get("expediente") or None, paired_with=paired["id"] if paired else None))
    cov = {"label": "Toda España, desde el 27 de julio de 2026",
           "sites": None, "note": "Anuncios del BOE con trámite ambiental, leídos cada mañana."}
    return cov, out


def fire_sites(p: dict, s2: dict) -> tuple[list[dict], str, float | None, str | None]:
    """The sites a fire burns in, how they were found, its hectares and the state of its perimeter.

    As on the fire's own page in vigía: once Sentinel-2 has measured the burnt area, the fire is
    in the sites that area reaches and in no other, even if its hot pixels touched one. Under
    clouds the area is only a lower bound, so the sites of the hot pixels are not ruled out and
    stay, without hectares. A perimeter with no area yet, or clouded out entirely, measured
    nothing: the hot pixels decide, and they overstate small fires (a 1 ha fire lights a 14 ha
    VIIRS pixel).
    """
    measured = s2.get("ha") is not None and not (s2.get("nublado") and not s2["ha"])
    if not measured:
        return [{"code": n["codigo"], "ha": n.get("ha")} for n in p.get("natura") or []], "focos", p.get("ha_focos"), None
    sites = [{"code": n["codigo"], "ha": n.get("ha")} for n in s2.get("natura") or []]
    if s2.get("nublado"):
        burnt = {x["code"] for x in sites}
        sites += [{"code": n["codigo"]} for n in p.get("natura") or [] if n["codigo"] not in burnt]
    return sites, "perimetro", s2["ha"], "definitivo" if s2.get("definitivo") else "provisional"


def vigia(fc: dict, resolve: Resolve, today: date, window_days: int) -> tuple[dict, list[dict]]:
    """Fires of the last window_days, with the hectares inside each Natura site (see fire_sites)."""
    since = (today - timedelta(days=window_days)).isoformat()
    out = []
    for f in fc["features"]:
        p = f["properties"]
        day = p["primera"][:10]
        if day < since:
            continue
        sites, precision, ha, status = fire_sites(p, p.get("perimetro_s2") or {})
        place = p.get("lugar") or {}
        out.append(_signal("vigia-incendios", p["id"], "fire", day,
                           f"Incendio en {place.get('municipio') or 'lugar sin identificar'}",
                           f"{config.PAGES}/vigia-incendios/#{p['id']}", precision, sites=sites,
                           municipalities=_munis(resolve, [place["municipio"]] if place.get("municipio") else [],
                                                 [place.get("provincia")] if place.get("provincia") else []),
                           status=status,
                           value={"amount": ha, "unit": "ha"} if ha else None,
                           province=place.get("provincia"), point=p.get("centro")))
    cov = {"label": "Toda España", "sites": None,
           "note": f"Focos VIIRS de NASA FIRMS de los últimos {window_days} días; superficie quemada con Sentinel-2 cuando la hay."}
    return cov, out


def centinela(fc: dict, watched: list[str], resolve: Resolve, states: set[str]) -> tuple[dict, list[dict]]:
    """Land-cover change alerts in the sites centinela watches (Cantabria for now)."""
    out = []
    for f in fc["features"]:
        p = f["properties"]
        if p["estado"] not in states:
            continue
        base = f"{config.PAGES}/centinela-natura/"
        out.append(_signal("centinela-natura", p["id"], "land_change", p["detectada"],
                           p.get("clase_nombre") or "Cambio de cubierta", base + "#" + p["id"], "pixeles",
                           sites=[{"code": e["codigo"]} for e in p.get("espacios") or []],
                           municipalities=_munis(resolve, p.get("municipios"), ["Cantabria"]),
                           status=p["estado"], value={"amount": p["ha"], "unit": "ha"},
                           permit=p.get("cruce_nombre"),
                           before=base + p["foto_antes"] if p.get("foto_antes") else None,
                           after=base + p["foto_despues"] if p.get("foto_despues") else None,
                           before_date=p.get("fecha_antes"), after_date=p.get("fecha_despues"),
                           cover=(p.get("cubierta_previa") or {}).get("nombre"),
                           history=[[h["fecha"], h["estado"]] for h in p.get("historial") or []],
                           parcels=p.get("n_parcelas"),
                           # Centinela also watches the ZEC, which this panel does not draw: named here so an
                           # alert outside every ZEPA still says which Natura 2000 site it falls in.
                           natura=[[e["codigo"], e.get("nombre"), e.get("tipo")] for e in p.get("espacios") or []],
                           point=p["centro"][::-1] if p.get("centro") else None))  # centinela stores [lat, lon]
    cov = {"label": "Cantabria", "sites": sorted(watched),
           "note": "Cambios de vegetación con Sentinel-2, revisados cada mes."}
    return cov, out


def humedales(wetlands: list[tuple[dict, list[dict], set[str]]], state_of: Callable[[list[dict]], dict | None]
              ) -> tuple[dict, list[dict]]:
    """The latest surface-water state of each watched wetland, as one signal per wetland."""
    out, watched = [], set()
    for meta, rows, inside in wetlands:
        watched |= inside
        st = state_of(rows)
        if not st:
            continue
        if st["dry_ref"]:
            title = f"{meta['name']}: {st['water_ha']:.0f} ha de agua; en ese mes suele estar seca"
        elif st["ratio"] is not None:
            title = f"{meta['name']}: {st['ratio'] * 100:.0f} % del agua normal en ese mes"
        else:
            title = f"{meta['name']}: {st['water_ha']:.0f} ha de agua"
        out.append(_signal("vigilancia-humedales", meta["slug"], "wetland_water", st["date"], title,
                           f"{config.PAGES}/vigilancia-humedales/", "lamina",
                           sites=[{"code": c} for c in sorted(inside)],
                           value={"amount": st["water_ha"], "unit": "ha"}, status="vigente" if st["current"] else "antiguo",
                           **{k: st[k] for k in ("ratio", "ref_ha", "ref_years", "dry_ref", "current")}, name=meta["name"],
                           point=meta.get("point")))
    cov = {"label": "Seis humedales", "sites": sorted(watched),
           "note": "Agua libre con Sentinel-2 desde 2017, frente a la mediana del mismo mes en años anteriores."}
    return cov, out


def chains(grafo: dict, cartera: dict, ids: set[str]) -> dict[str, list[dict]]:
    """Who is behind each BOE act: company → business group → listed company.

    Grafo links BOE acts to companies (by the act ids each company appears in) and companies to
    groups; cartera links companies to listed companies through their consolidated accounts or the
    sole-shareholder chain in BORME. A listed company reached only through another member of the
    group is marked as such: the group itself is grafo's inference, not a published fact.
    Natural persons (PF- keys) never appear.
    """
    socs = grafo["sociedades"]
    by_act: dict[str, set[str]] = {}
    for key, s in socs.items():
        for act in s.get("actos_boe") or []:
            if act in ids:
                by_act.setdefault(act, set()).add(key)
    for inst in grafo["instalaciones"].values():
        holders = [t for t in inst.get("titulares") or [] if t in socs]
        for act in inst.get("actos") or []:
            if act["id"] in ids:
                by_act.setdefault(act["id"], set()).update(holders)
    group_of = {m: g for g in grafo["grupos"] for m in g["sociedades"]}
    listed_of: dict[str, dict] = {}
    for c in cartera["cotizadas"]:
        for s in c["sociedades"]:
            listed_of.setdefault(s["id"], c)
    grafo_url = f"{config.PAGES}/grafo-promotores/"
    out: dict[str, list[dict]] = {}
    for act, keys in by_act.items():
        for key in sorted(k for k in keys if not k.startswith("PF-")):
            links = [{"name": (socs[key].get("nombres") or [key])[0], "role": "promotor", "url": grafo_url}]
            g = group_of.get(key)
            if g:
                root = socs.get(socs[key].get("grupo") or "", {})
                root_name = (root.get("nombres") or [g["id"][2:]])[0]
                links.append({"name": f"grupo {root_name} ({len(g['sociedades'])} sociedades)",
                              "role": "grupo", "url": grafo_url})
            c, via = listed_of.get(key), "directa"
            if not c and g:
                c = next((listed_of[m] for m in g["sociedades"] if m in listed_of), None)
                via = "por el grupo"
            if c:
                links.append({"name": c["nombre"], "role": "cotizada", "via": via,
                              "url": f"{config.PAGES}/cartera-cotizadas/#c={c['id']}&t=sociedades"})
            out.setdefault(act, []).append({"links": links})
    return out


def caudal(stations: list[dict], flows: dict[str, list[dict]], requirements: list[dict], locate: Callable,
           today: date, window_days: int = 30) -> tuple[dict, list[dict]]:
    """Days below the legal minimum flow in the last window_days, one signal per station.

    The minimum is the ordinary-regime monthly value of the basin plan. Only days with a reading
    count; a station with no day below the minimum gives no signal.
    """
    req = {r["station_id"]: r for r in requirements if r.get("regime") == "ordinary" and not r.get("valid_to")}
    since = (today - timedelta(days=window_days)).isoformat()
    out, watched = [], set()
    for st in stations:
        r = req.get(st["station_id"])
        if r:
            watched.update(locate(float(st["lon"]), float(st["lat"]))[0])
        rows = [x for x in flows.get(st["station_id"], []) if x["date"] >= since and x.get("q_mean") not in (None, "")]
        if not r or not rows:
            continue
        below = [x for x in rows if float(x["q_mean"]) < float(r[f"m{int(x['date'][5:7]):02d}"])]
        if not below:
            continue
        last = max(rows, key=lambda x: x["date"])
        lon, lat = float(st["lon"]), float(st["lat"])
        sites, munis = locate(lon, lat)
        out.append(_signal("caudal-ecologico", st["station_id"], "river_flow", last["date"],
                           f"{st['name']}: {len(below)} de {len(rows)} días por debajo del caudal mínimo",
                           f"{config.PAGES}/caudal-ecologico/", "punto",
                           sites=[{"code": c} for c in sites], municipalities=munis,
                           value={"amount": float(last["q_mean"]), "unit": "m³/s"},
                           minimum=float(r[f"m{int(last['date'][5:7]):02d}"]), days_below=len(below),
                           days=len(rows), river=st.get("river"), point=[lon, lat]))
    cov = {"label": f"{len(req)} puntos del Júcar y el Guadiana", "sites": sorted(watched),
           "note": "Caudal diario de los SAIH frente al caudal ecológico mínimo del plan hidrológico."}
    return cov, out


def subnocte(forecast: list[dict], resolve: Resolve, today: date) -> tuple[dict, list[dict]]:
    """Tonight's nocturnal migration forecast for the Spanish cities with a usable radar."""
    rows = [r for r in forecast if r.get("country") == "ES" and r.get("night", "")[:10] >= today.isoformat()]
    if rows:
        first = min(r["night"] for r in rows)
        rows = [r for r in rows if r["night"] == first]
    label = {"very high": "muy alta", "high": "alta", "moderate": "moderada", "low": "baja"}
    out = []
    for r in rows:
        ine = resolve(r["city"], [])
        out.append(_signal("sub-nocte", f"{r['city']}-{r['night'][:10]}", "migration", r["night"][:10],
                           f"{r['city']}: migración nocturna {label.get(r['level'], r['level'])} prevista",
                           f"{config.PAGES}/sub-nocte/", "radar", municipalities=[ine] if ine else [],
                           status=r["level"], city=r["city"],
                           point=[float(r["lon"]), float(r["lat"])] if r.get("lon") else None))
    cov = {"label": "Ciudades con radar meteorológico", "sites": [],
           "note": "Previsión de paso de aves migratorias por la noche, a partir de radares y meteorología."}
    return cov, out


# How a title names each element type of the ranking, wind turbines first: they are the main point.
ELEMENTS = (("turbine", "aerogenerador", "aerogeneradores"), ("pylon", "apoyo", "apoyos"),
            ("line", "tramo de línea", "tramos de línea"))


def elements(count: Counter) -> str:
    """A count by element type in one Spanish phrase, wind turbines first: "3 aerogeneradores, 40 apoyos y 1 tramo
    de línea". A type the ranking does not write today still counts, as "otros elementos"."""
    known = [(count.get(t, 0), one, many) for t, one, many in ELEMENTS]
    known.append((sum(count.values()) - sum(n for n, _, _ in known), "otro elemento", "otros elementos"))
    parts = [f"{n} {one if n == 1 else many}" for n, one, many in known if n]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " y " + parts[-1]


def tendidos(regions: dict[str, tuple[list[dict], str]], shapes: dict, high_share: float = 0.1
             ) -> tuple[dict, list[dict]]:
    """High-risk wind turbines, pylons and line segments inside each site, per modelled region.

    High risk is the top high_share of risk_max within the region. Only counts are published: the
    per-element species lists stay in the source project.
    """
    codes = list(shapes)
    tree = STRtree([shapes[c] for c in codes])
    out, watched = [], set()
    for region, (rows, day) in regions.items():
        rows = [r for r in rows if r.get("risk_max") not in (None, "")]
        if not rows:
            continue
        lons, lats = [float(r["lon"]) for r in rows], [float(r["lat"]) for r in rows]
        watched |= {codes[i] for i in tree.query(box(min(lons), min(lats), max(lons), max(lats)), predicate="intersects")}
        cut = sorted(float(r["risk_max"]) for r in rows)[int(len(rows) * (1 - high_share))]
        count: dict[str, Counter] = {}
        for r in rows:
            if float(r["risk_max"]) >= cut:
                for i in tree.query(Point(float(r["lon"]), float(r["lat"])), predicate="intersects"):
                    count.setdefault(codes[i], Counter())[r.get("type")] += 1
        for code, kinds in count.items():
            n = sum(kinds.values())
            c = shapes[code].representative_point()  # the count belongs to the site, not to any one pylon
            out.append(_signal("riesgo-tendidos-aves", f"{region}-{code}", "power_line", day,
                               f"{elements(kinds)} de riesgo alto para las aves dentro del espacio",
                               # the site's own page: the region's map only draws its top elements
                               f"{config.PAGES}/riesgo-tendidos-aves/{region}/sites/{code}.es.html", "punto",
                               sites=[{"code": code}], value={"amount": n, "unit": "elementos"}, region=region,
                               point=[round(c.x, 4), round(c.y, 4)]))
    cov = {"label": "Cantabria y el Estrecho", "sites": sorted(watched),
           "note": "Riesgo de colisión y electrocución de cada aerogenerador, apoyo y tramo de línea de "
                   "OpenStreetMap, modelado cada mes."}
    return cov, out


def luz(doc: dict, shapes: dict, baseline: tuple[int, int], recent: int, min_rise: float, min_abs: float,
        min_pixels: int, peers: int, country: str = "ES") -> tuple[dict, list[dict]]:
    """Sites where artificial light at night has grown more than in sites as dark as they were (NASA Black Marble).

    «Before» is the mean of the baseline years and «now» the mean of the last `recent` ones, so one
    odd year makes no signal. The product drifts from year to year across the whole country at once
    (in 2025 nearly every dark site reads brighter), and the drift depends on how dark a site is. So
    each site is set against the `peers` sites on each side of it in baseline brightness: what it
    would read now had it changed like their median is what it is held to, by min_rise and by min_abs.

    Only rises count: VIIRS does not see the blue of white LEDs, so a town that swaps sodium lamps
    for LEDs reads darker without being so, while a rise is, if anything, short. A site of fewer than
    min_pixels pixels is not judged, and neither is one with no light at all in the baseline: there is
    no share of nothing.

    Each country has its own file and is held to its own sites; titles and coverage are in its language.
    """
    lang = i18n.LANG_BY_COUNTRY[country]
    T = i18n.PY[lang]

    def pc(x: int) -> str:
        return f"{x}{chr(0x202f) if lang == 'fr' else ' '}%"

    years = doc["years"]
    before = [i for i, y in enumerate(years) if baseline[0] <= y <= baseline[1]]
    now = [i for i in range(len(years))[-recent:] if i not in before]
    level: dict[str, tuple[float, float]] = {}
    for code, s in doc["sites"].items():
        r = s["radiance"]
        if code not in shapes or s["pixels"] < min_pixels or not before or len(now) < recent \
                or any(r[i] is None for i in before + now):
            continue
        level[code] = (sum(r[i] for i in before) / len(before), sum(r[i] for i in now) / len(now))
    order = sorted(level, key=lambda c: level[c][0])
    out = []
    for i, code in enumerate(order):
        ref, cur = level[code]
        near = [level[o] for o in order[max(0, i - peers):i + peers + 1] if o != code and level[o][0] > 0]
        if ref <= 0 or not near:
            continue
        drift = statistics.median(c / r for r, c in near)
        expected = ref * drift
        if cur - expected < min_abs or cur / expected - 1 < min_rise:
            continue
        pct, common, over = (round(100 * (x - 1)) for x in (cur / ref, drift, cur / expected))
        them = T["light_up"].format(pct=pc(common)) if common >= 0 else T["light_down"].format(pct=pc(-common))
        c = shapes[code].representative_point()
        out.append(_signal("black-marble", code, "night_light", f"{years[-1]}-12-31",
                           T["light_title"].format(pct=pc(pct), b0=baseline[0], b1=baseline[1], them=them),
                           f"https://doi.org/{doc['doi']}", "pixeles", country=country, sites=[{"code": code}], value={"amount": over, "unit": "%"},
                           radiance=round(cur, 2), baseline=round(ref, 2), expected=round(expected, 2),
                           pixels=doc["sites"][code]["pixels"], years=[years[now[0]], years[now[-1]]],
                           point=[round(c.x, 4), round(c.y, 4)]))
    span = f"{years[0]}-{years[-1]}" if years else T["light_no_years"]
    cov = {"label": T["light_label"], "sites": sorted(level), "baseline": list(baseline), "recent": recent,
           "note": T["light_note"].format(span=span)}
    return cov, out
