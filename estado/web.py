"""The public site: a page shell, the data it reads, and one RSS feed per site and per community."""

from __future__ import annotations

import json
import shutil
from datetime import date, datetime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

from shapely.geometry import mapping, shape

from . import config
from .logo import LOGO_SVG, favicon_link

HERE = Path(__file__).parent
COMMON_CSS = (HERE / "common.css").read_text(encoding="utf-8").strip()


def _dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def build(sites: dict[str, dict], n: dict[str, dict], signals: list[dict], chains: dict, sources: dict,
          munis: list[dict], regs: list[dict], site_reg: dict[str, dict], now: datetime, today: date) -> None:
    docs = config.DOCS_DIR
    docs.mkdir(parents=True, exist_ok=True)
    (docs / ".nojekyll").touch()
    (docs / "panel.json").unlink(missing_ok=True)  # v1 output, replaced by datos/hub.json

    site_munis: dict[str, list[list[str]]] = {}
    for m in munis:
        for c in m["sites"]:
            site_munis.setdefault(c, []).append([m["ine"], m["name"]])
    def point(geom):
        c = shape(geom).representative_point()
        return [round(c.x, 4), round(c.y, 4)]

    rows = sorted(({"code": c, "name": s["name"], "n": n[c], **site_reg[c], "point": point(s["geometry"]),
                    "munis": sorted(site_munis.get(c, []), key=lambda x: x[1])} for c, s in sites.items()),
                  key=lambda r: r["name"])
    regions = [{"id": r["id"], "name": r["name"], "official": r["official"],
                "bbox": [round(v, 2) for v in r["geom"].bounds],
                "sites": sorted(c for c, x in site_reg.items() if r["id"] in x["regions"])} for r in regs]
    signals = sorted(signals, key=lambda s: s["date"], reverse=True)
    _dump(docs / "datos" / "hub.json", {
        "generated": now.strftime("%Y-%m-%dT%H:%MZ"), "today": today.isoformat(), "kind": config.SITE_KIND,
        "sources": sources, "regions": regions, "sites": rows, "signals": signals, "chains": chains})
    _dump(docs / "datos" / "municipios.json",
          [[m["ine"], m["name"], m["province"], *m["point"], m["sites"], m["region"]] for m in munis])
    # Outlines only, at ~1 km: they frame the map, the sites carry the detail.
    _dump(docs / "comunidades.geojson", {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"id": r["id"], "name": r["name"]},
         "geometry": _rounded(mapping(r["geom"].simplify(0.01)))} for r in regs]})
    _dump(docs / "sitios.geojson", {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"code": c, "name": s["name"]}, "geometry": s["geometry"]}
        for c, s in sites.items()]})
    for f in ("app.css", "app.js"):
        shutil.copyfile(HERE / "static" / f, docs / f)
    _rss(docs / "rss", sites, regions, signals)

    figures = _figures(n, signals)
    html = PAGE
    for key, val in {
        "__LOGO__": LOGO_SVG, "__FAVICON__": favicon_link(*config.ACCENT), "/*__COMMON_CSS__*/": COMMON_CSS,
        "__N_SITES__": _es(len(sites)), "__PARAMS__": _params(), "__GENERATED__": now.strftime("%Y-%m-%d %H:%M UTC"),
        "__VERSION__": now.strftime("%Y%m%d%H%M"), **{f"__FIG_{k.upper()}__": v for k, v in figures.items()},
    }.items():
        html = html.replace(key, val)
    (docs / "index.html").write_text(html, encoding="utf-8")


def _figures(n: dict[str, dict], signals: list[dict]) -> dict[str, str]:
    rivers = [s for s in signals if s["kind"] == "river_flow"]
    wet = [s for s in signals if s["kind"] == "wetland_water" and s["details"]["current"] and s["details"]["ratio"] is not None]
    return {
        "precise": _es(sum(x["precise"] > 0 for x in n.values())),
        "open": _es(sum(x["open"] > 0 for x in n.values())),
        "fire": _es(sum(x["fire_ha"] > 0 for x in n.values())),
        "rivers": _es(len(rivers)),
        "wet": f"{sum(s['details']['ratio'] < 0.75 for s in wet)} de {len(wet)}" if wet else "—",
    }


def _es(x: float) -> str:
    return f"{x:,}".replace(",", ".")


def _rounded(geom: dict, nd: int = 3) -> dict:
    def r(c):
        return [round(c[0], nd), round(c[1], nd)] if isinstance(c[0], float | int) else [r(x) for x in c]
    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}


def _rss(folder: Path, sites: dict[str, dict], regions: list[dict], signals: list[dict]) -> None:
    """One feed per site and one per community, newest first. No build date in the channel, so an
    unchanged place gives an unchanged file and the daily commit only touches what moved."""
    folder.mkdir(parents=True, exist_ok=True)
    by_site: dict[str, list[dict]] = {}
    by_region: dict[str, list[dict]] = {}
    for s in signals:
        for x in s["sites"]:
            by_site.setdefault(x["code"], []).append(s)
        for r in s.get("regions", []) if s["sites"] else []:  # a community feed follows its sites, like its page
            by_region.setdefault(r, []).append(s)
    for code, site in sites.items():
        _feed(folder / f"{code}.xml", site["name"], f"#/e/{code}",
              f"Proyectos, fuego, cambios de uso, agua y tendidos en {site['name']} ({code}).",
              by_site.get(code, []), lambda s, name=site["name"]: name)
    for r in regions:
        _feed(folder / f"ca-{r['id']}.xml", r["name"], f"#/ca/{r['id']}",
              f"Proyectos, fuego, cambios de uso, agua y tendidos en los espacios y municipios de {r['official']}.",
              by_region.get(r["id"], []),
              lambda s: "; ".join(sites[x["code"]]["name"] for x in s["sites"][:3]) or "Por municipio")


def _feed(path: Path, name: str, route: str, about: str, signals: list[dict], where) -> None:
    items = []
    for s in signals[:40]:
        when = datetime.fromisoformat(s["date"][:10] + "T08:00:00+00:00")
        extra = f" Plazo de alegaciones hasta el {s['deadline']}." if s["kind"] == "notice" and s["deadline"] else ""
        items.append(f"<item><title>{escape(s['title'])}</title><link>{escape(s['url'])}</link>"
                     f"<guid isPermaLink=\"false\">{escape(s['source'] + ':' + s['id'])}</guid>"
                     f"<pubDate>{format_datetime(when)}</pubDate>"
                     f"<description>{escape(where(s) + '.' + extra)}</description></item>")
    xml = ('<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0"><channel>'
           f"<title>{escape(name)} · Estado de las IBA</title><link>{config.PAGES}/estado-iba/{route}</link>"
           f"<description>{escape(about)}</description>"
           f"<language>es</language>{''.join(items)}</channel></rss>\n")
    path.write_text(xml, encoding="utf-8")


def _params() -> str:
    rows = [
        ("Espacios", f"{config.SITE_KIND} de la Red Natura 2000, simplificadas a unos 300 m (0,003°)"),
        ("Municipios", "IGN (es-atlas), unos 200 m; un espacio cuenta en un municipio si comparten al menos 1 km², el 10 % del municipio o el 25 % del espacio"),
        ("Comunidad de un espacio", "las de sus municipios; si no toca ninguno (espacios marinos e islotes), la de la costa más cercana"),
        ("Fuego", f"incendios de los últimos {config.FIRE_WINDOW_DAYS} días"),
        ("Cambio de uso", "alertas confirmadas o provisionales; no cuentan las descartadas, revertidas ni fusionadas"),
        ("Humedal en una ZEPA", "al menos el 25 % de su superficie dentro de ella"),
        ("Agua de referencia", f"mediana del mismo mes en años anteriores, con al menos {config.WETLAND_MIN_YEARS} años"),
        ("Menos agua de lo normal", "menos del 75 % de la referencia"),
        ("Laguna normalmente seca", "referencia por debajo del 5 % de su máximo: no se calcula el porcentaje"),
        ("Caudal", "días de los últimos 30 con caudal medio por debajo del mínimo mensual del plan hidrológico"),
        ("Estación de aforo en una ZEPA", "a menos de unos 500 m del espacio"),
        ("Tendido de riesgo alto", "el 10 % de apoyos y vanos con más riesgo de cada región modelada"),
        ("Edificios en zona inundable", "construidos después de 2016 en las zonas de flujo preferente, T100 o T500 del SNCZI; solo en la ficha del municipio, sin ventana de tiempo"),
        ("Depuración y baño", "aglomeraciones de más de 2.000 h-e que no cumplen la Directiva 91/271/CEE y zonas de baño insuficientes en la última temporada; solo en la ficha del municipio, sin ventana de tiempo"),
    ]
    body = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return f'<table class="params"><tbody>{body}</tbody></table>'


PAGE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
__FAVICON__
<title>Estado de las IBA</title>
<meta name="description" content="Qué les está pasando a los espacios importantes para las aves de España: proyectos, fuego, cambios de uso, agua, ríos y tendidos, con cada dato enlazado a su fuente.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
/*__COMMON_CSS__*/
</style>
<link rel="stylesheet" href="app.css?v=__VERSION__">
</head>
<body>
<header class="site-header">
  <div>
    <h1><a href="#/">__LOGO__Estado de las <span>IBA</span></a></h1>
    <span class="rotulo">España · __N_SITES__ espacios para las aves · cada día</span>
  </div>
  <p class="lede">Qué les está pasando a los espacios importantes para las aves: los proyectos que se someten a evaluación ambiental, el fuego, los cambios de uso del suelo, el agua de sus humedales y ríos y los tendidos peligrosos. Busca un espacio, tu municipio o tu comunidad para ver todo lo que hay, quién está detrás y qué puedes hacer.</p>
  <p class="aviso-unidad">Por ahora la unidad son las <b>ZEPA</b> (zonas de especial protección para las aves de la Red Natura 2000), que son datos abiertos. Las IBA de SEO/BirdLife entrarán cuando su reutilización esté acordada.</p>
  <div class="figures">
    <div><b>__FIG_PRECISE__</b><span>ZEPA con proyectos dentro, según sus parcelas</span></div>
    <div><b>__FIG_OPEN__</b><span>con alegaciones abiertas hoy</span></div>
    <div><b>__FIG_FIRE__</b><span>tocadas por el fuego en 12 meses</span></div>
    <div><b>__FIG_RIVERS__</b><span>puntos de río bajo el caudal mínimo en 30 días</span></div>
    <div><b>__FIG_WET__</b><span>humedales con menos agua de lo normal</span></div>
  </div>
</header>

<main id="vista">
  <div class="wrap"><p class="vacio">Cargando…</p>
  <noscript><p>Esta página necesita JavaScript. Los datos están en <a href="datos/hub.json">datos/hub.json</a>.</p></noscript></div>
</main>

<section class="method" id="metodo">
  <div>
    <h2>Cómo se calcula</h2>
    <ol>
      <li>Cada día se leen los datos que ya publican los proyectos hermanos y se traducen a <b>señales</b>: hechos con fecha, lugar y enlace a su registro. Este panel no vuelve a medir nada. El formato está en <a href="https://github.com/Asensio94/estado-iba/blob/main/CONTRATO.md">CONTRATO.md</a>.</li>
      <li><b>Proyectos.</b> El Observatorio de alegaciones lee el BOE cada mañana. Si el anuncio trae las parcelas afectadas, el cruce con los espacios es con esas parcelas; si no, con el término municipal entero, que es solo una aproximación y se marca «por municipio».</li>
      <li><b>Quién está detrás.</b> El Grafo de promotores relaciona cada acto del BOE con las sociedades que aparecen en él y estas con su grupo, a partir del BORME. La Cartera de las cotizadas relaciona sociedades con empresas cotizadas por sus cuentas anuales. Cuando la cotizada se alcanza a través de otra sociedad del grupo, se indica.</li>
      <li><b>Fuego, suelo, agua, ríos y tendidos.</b> Vigía de incendios, Centinela Natura, Vigilancia de humedales, Caudal ecológico y Riesgo de tendidos para aves publican cada hecho con su lugar. Aquí se agrupan por espacio y municipio.</li>
      <li><b>Zona inundable.</b> Zona inundable cuenta, municipio a municipio, los edificios del Catastro construidos después de 2016 dentro de las zonas inundables del SNCZI. Es un inventario, no un hecho con fecha: sale solo en la ficha de cada municipio, sin mapa ni ventana de tiempo.</li>
      <li><b>Depuración y baño.</b> Depuración y baño señala las aglomeraciones urbanas cuya depuración no cumple la directiva europea, según el último informe de España a la Agencia Europea de Medio Ambiente, y las zonas de baño insuficientes de la última temporada. Salen en la ficha de cada municipio, con una gota en el mapa. El punto es el núcleo urbano, no el vertido, así que no se cruza con los espacios.</li>
      <li><b>Municipios.</b> Los nombres de municipio que traen los anuncios se resuelven al código INE con la capa del IGN; los homónimos se desempatan por provincia y, si no, se dejan sin resolver.</li>
      <li>No hay un índice que lo resuma todo: mezclar hectáreas quemadas con proyectos exigiría decidir cuánto pesa cada cosa, y esa decisión no es técnica.</li>
    </ol>
    <h3>Parámetros</h3>
    __PARAMS__
  </div>
  <div>
    <h3>Presión, estado y respuesta</h3>
    <p>El seguimiento de las IBA de BirdLife International mira las presiones, el estado y la respuesta. Este panel cubre sobre todo las presiones (proyectos, fuego, cambios de uso, tendidos). Del estado tiene el agua de seis humedales y el caudal de 55 puntos de río; el estado de las poblaciones de aves sale de censos que no son públicos a esta escala. La respuesta más directa a su alcance son las alegaciones: cada proyecto con plazo abierto lleva su fecha límite.</p>
    <h3>Lo que hay que saber antes de citarlo</h3>
    <p>Una ficha sin novedades no es un espacio sin problemas: solo aparece lo que vigila algún proyecto hermano, y varios cubren solo una parte de España. En el mapa de cada lugar, las capas que no cubren esa zona salen en gris con la nota «no cubre esta zona». Un proyecto en evaluación no es un daño: es un procedimiento abierto que puede acabar denegado. Una relación entre sociedades es un indicio sacado de registros públicos, no una acusación.</p>
    <h3>Datos de especies y personas</h3>
    <p>No se incorpora ni se publica ninguna ubicación de especies (colonias, nidos, dormideros ni territorios), ni datos de personas físicas.</p>
    <h3>Datos abiertos</h3>
    <p><a href="datos/hub.json">hub.json</a> con todas las señales y fichas · <a href="datos/municipios.json">municipios.json</a> · <a href="sitios.geojson">sitios.geojson</a> · <a href="comunidades.geojson">comunidades.geojson</a> · un feed RSS por espacio en <span class="data">rss/&lt;código&gt;.xml</span> y por comunidad en <span class="data">rss/ca-&lt;código INE&gt;.xml</span> · <a href="https://github.com/Asensio94/estado-iba">código</a>. Actualizado el <span class="data">__GENERATED__</span>.</p>
  </div>
</section>

<footer class="site-footer">
  <p class="principle">Datos públicos, reglas a la vista y cada cifra enlazada a su fuente. Indicios, no veredictos.</p>
  <p>Red Natura 2000: Agencia Europea de Medio Ambiente · Municipios: Instituto Geográfico Nacional (es-atlas) · Anuncios y resoluciones: Boletín Oficial del Estado · Sociedades: BORME y cuentas anuales · Focos y superficie quemada: NASA FIRMS y Copernicus Sentinel-2 · Cambio de uso y agua: Copernicus Sentinel-2 · Caudales: SAIH del Júcar y SIRA del Guadiana · Tendidos: OpenStreetMap · Migración: radares meteorológicos europeos · Zonas inundables: SNCZI (MITECO) y Catastro · Depuración: informe de España a la AEMA (Directiva 91/271/CEE) · Zonas de baño: Náyade · Mapa: © colaboradores de OpenStreetMap · Código con licencia MIT.</p>
  <nav aria-label="Proyectos hermanos"><ul class="siblings">
    <li><a href="https://asensio94.github.io/observatorio-alegaciones/">Observatorio de alegaciones</a></li>
    <li><a href="https://asensio94.github.io/vigia-incendios/">Vigía de incendios</a></li>
    <li><a href="https://asensio94.github.io/centinela-natura/">Centinela Natura</a></li>
    <li><a href="https://asensio94.github.io/vigilancia-humedales/">Vigilancia de humedales</a></li>
    <li><a href="https://asensio94.github.io/sub-nocte/">Sub Nocte</a></li>
    <li><a href="https://asensio94.github.io/riesgo-tendidos-aves/">Riesgo de tendidos para aves</a></li>
    <li><a href="https://asensio94.github.io/grafo-promotores/">Grafo de promotores</a></li>
    <li><a href="https://asensio94.github.io/cartera-cotizadas/">Cartera de las cotizadas</a></li>
    <li><a href="https://asensio94.github.io/cuaderno-campo/">Cuaderno de campo</a></li>
    <li><a href="https://asensio94.github.io/caudal-ecologico/">Caudal ecológico</a></li>
    <li aria-current="page"><a href="https://asensio94.github.io/estado-iba/">Estado de las IBA</a></li>
  </ul></nav>
</footer>

<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script src="app.js?v=__VERSION__"></script>
</body>
</html>
"""
