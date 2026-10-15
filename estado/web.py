"""The public site: a page shell, the data it reads, and one RSS feed per site and per community.

One site per country, each in its own language: Spain in docs/, France in docs/fr/. Both pages run
the same app.js and app.css, kept once in docs/; each page writes in the strings of its language
(window.I18N) and its own settings (window.PAGE). The data files are the same whatever the language.
"""

from __future__ import annotations

import json
import shutil
from datetime import date, datetime
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

from shapely.geometry import mapping, shape

from . import config, i18n, page_fr
from .logo import LOGO_SVG, favicon_link

HERE = Path(__file__).parent
COMMON_CSS = (HERE / "common.css").read_text(encoding="utf-8").strip()


def _dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def build(sites: dict[str, dict], n: dict[str, dict], signals: list[dict], chains: dict, sources: dict,
          munis: list[dict], regs: list[dict], site_reg: dict[str, dict], now: datetime, today: date,
          country: str = "ES") -> None:
    st = i18n.SETTINGS[country]
    lang = st["lang"]
    docs = config.DOCS_DIR / st["dir"]
    docs.mkdir(parents=True, exist_ok=True)
    if country == "ES":
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
        "generated": now.strftime("%Y-%m-%dT%H:%MZ"), "today": today.isoformat(), "country": country,
        "kind": st["kind"],
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
    if country == "ES":  # one copy for every country's page
        for f in ("app.css", "app.js"):
            shutil.copyfile(HERE / "static" / f, docs / f)
    _rss(docs / "rss", sites, regions, signals, country)

    figures = _figures(n, signals, sources, lang)
    html = PAGE if country == "ES" else page_fr.PAGE
    for key, val in {
        "__LOGO__": LOGO_SVG, "__FAVICON__": favicon_link(*config.ACCENT), "/*__COMMON_CSS__*/": COMMON_CSS,
        "__N_SITES__": i18n.n(len(sites), lang), "__N_MUNIS__": i18n.n(sum(bool(m["sites"]) for m in munis), lang),
        "__N_REGIONS__": i18n.n(len(regs), lang),
        "__PARAMS__": _params() if country == "ES" else page_fr.params(),
        "__GENERATED__": now.strftime("%Y-%m-%d %H:%M UTC"), "__I18N__": _settings(country),
        "__VERSION__": now.strftime("%Y%m%d%H%M"), **{f"__FIG_{k.upper()}__": v for k, v in figures.items()},
    }.items():
        html = html.replace(key, val)
    (docs / "index.html").write_text(html, encoding="utf-8")


def _settings(country: str) -> str:
    """The page's strings and settings for app.js, inline: one request less, and no flash of another language."""
    js = (f"window.I18N={json.dumps(i18n.UI[i18n.LANG_BY_COUNTRY[country]], ensure_ascii=False)};"
          f"window.PAGE={json.dumps(i18n.page(country), ensure_ascii=False)};")
    return "<script>" + js.replace("</", "<\\/") + "</script>"


def _figures(n: dict[str, dict], signals: list[dict], sources: dict, lang: str = "es") -> dict[str, str]:
    rivers = [s for s in signals if s["kind"] == "river_flow"]
    wet = [s for s in signals if s["kind"] == "wetland_water" and s["details"]["current"] and s["details"]["ratio"] is not None]
    lit = sources.get("black-marble", {}).get("sites")
    return {
        "precise": i18n.n(sum(x["precise"] > 0 for x in n.values()), lang),
        "open": i18n.n(sum(x["open"] > 0 for x in n.values()), lang),
        "fire": i18n.n(sum(x["fire_ha"] > 0 for x in n.values()), lang),
        "rivers": i18n.n(len(rivers), lang),
        "wet": f"{sum(s['details']['ratio'] < 0.75 for s in wet)} de {len(wet)}" if wet else "—",
        # no measure yet is «—», never 0: a zero would read as «nothing rises»
        "light": i18n.n(len({x["code"] for s in signals if s["kind"] == "night_light" for x in s["sites"]}), lang)
                 if lit else "—",
        "light_sites": i18n.n(len(lit), lang) if lit else "—",
    }


def _rounded(geom: dict, nd: int = 3) -> dict:
    def r(c):
        return [round(c[0], nd), round(c[1], nd)] if isinstance(c[0], float | int) else [r(x) for x in c]
    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}


def _rss(folder: Path, sites: dict[str, dict], regions: list[dict], signals: list[dict], country: str = "ES") -> None:
    """One feed per site and one per community (region in France), newest first, in the country's language.
    No build date in the channel, so an unchanged place gives an unchanged file and the daily commit
    only touches what moved."""
    lang = i18n.LANG_BY_COUNTRY[country]
    T, home = i18n.PY[lang], config.PAGES + i18n.SETTINGS[country]["route"]
    folder.mkdir(parents=True, exist_ok=True)
    by_site: dict[str, list[dict]] = {}
    by_region: dict[str, list[dict]] = {}
    for s in signals:
        for x in s["sites"]:
            by_site.setdefault(x["code"], []).append(s)
        for r in s.get("regions", []) if s["sites"] else []:  # a community feed follows its sites, like its page
            by_region.setdefault(r, []).append(s)
    for code, site in sites.items():
        _feed(folder / f"{code}.xml", site["name"], f"#/e/{code}", T["feed_site"].format(name=site["name"], code=code),
              by_site.get(code, []), lambda s, name=site["name"]: name, lang, home)
    for r in regions:
        _feed(folder / f"ca-{r['id']}.xml", r["name"], f"#/ca/{r['id']}", T["feed_region"].format(name=r["official"]),
              by_region.get(r["id"], []),
              lambda s: "; ".join(sites[x["code"]]["name"] for x in s["sites"][:3]) or T["feed_by_muni"], lang, home)


def _feed(path: Path, name: str, route: str, about: str, signals: list[dict], where, lang: str = "es",
          home: str = f"{config.PAGES}/estado-iba/") -> None:
    T = i18n.PY[lang]
    items = []
    for s in signals[:40]:
        when = datetime.fromisoformat(s["date"][:10] + "T08:00:00+00:00")
        extra = T["feed_deadline"].format(date=s["deadline"]) if s["kind"] == "notice" and s["deadline"] else ""
        items.append(f"<item><title>{escape(s['title'])}</title><link>{home}#/a/{quote(s['source'], safe='')}/{quote(s['id'], safe='')}</link>"
                     f"<guid isPermaLink=\"false\">{escape(s['source'] + ':' + s['id'])}</guid>"
                     f"<pubDate>{format_datetime(when)}</pubDate>"
                     f"<description>{escape(where(s) + '.' + extra)}</description></item>")
    xml = ('<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0"><channel>'
           f"<title>{escape(T['feed_title'].format(name=name))}</title><link>{home}{route}</link>"
           f"<description>{escape(about)}</description>"
           f"<language>{lang}</language>{''.join(items)}</channel></rss>\n")
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
        ("Aerogenerador o tendido de riesgo alto",
         "el 10 % de aerogeneradores, apoyos y tramos de línea con más riesgo de cada región modelada"),
        ("Luz de noche en aumento",
         f"brillo medio de los {config.LIGHT_RECENT} últimos años al menos un {config.LIGHT_MIN_RISE * 100:.0f} % y "
         f"{str(config.LIGHT_MIN_ABS).replace('.', ',')} nW/cm²/sr por encima del que tendría si hubiera cambiado "
         f"desde {config.LIGHT_BASELINE[0]}-{config.LIGHT_BASELINE[1]} como la mediana de los "
         f"{2 * config.LIGHT_PEERS} espacios más parecidos en brillo de entonces; solo espacios de "
         f"{config.LIGHT_MIN_PIXELS} píxeles VIIRS o más (unos 500 m cada uno)"),
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
<meta name="description" content="Qué les está pasando a los espacios importantes para las aves de España: proyectos, fuego, cambios de uso, agua, ríos, aerogeneradores, tendidos y luz de noche, con cada dato enlazado a su fuente.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
/*__COMMON_CSS__*/
</style>
<link rel="stylesheet" href="app.css?v=__VERSION__">
<link rel="alternate" hreflang="fr" href="https://asensio94.github.io/estado-iba/fr/">
</head>
<body>
<header class="site-header">
  <div>
    <h1><a href="#/">__LOGO__Estado de las <span>IBA</span></a></h1>
    <span class="rotulo">España · __N_SITES__ espacios para las aves · cada día · <a href="fr/" hreflang="fr" lang="fr">France</a></span>
  </div>
  <p class="lede">Qué les está pasando a los espacios importantes para las aves: los proyectos que se someten a evaluación ambiental, el fuego, los cambios de uso del suelo, el agua de sus humedales y ríos, los aerogeneradores y tendidos peligrosos y la luz artificial de noche. Busca un espacio, tu municipio o tu comunidad para ver todo lo que hay, quién está detrás y qué puedes hacer.</p>
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
      <li>Cada día se leen los datos que ya publican los proyectos hermanos y se traducen a <b>señales</b>: hechos con fecha, lugar y enlace a su registro. Este panel no vuelve a medir nada, salvo la luz de noche. El formato está en <a href="https://github.com/Asensio94/estado-iba/blob/main/CONTRATO.md">CONTRATO.md</a>.</li>
      <li><b>Proyectos.</b> El Observatorio de alegaciones lee el BOE cada mañana. Si el anuncio trae las parcelas afectadas, el cruce con los espacios es con esas parcelas; si no, con el término municipal entero, que es solo una aproximación y se marca «por municipio».</li>
      <li><b>Quién está detrás.</b> El Grafo de promotores relaciona cada acto del BOE con las sociedades que aparecen en él y estas con su grupo, a partir del BORME. La Cartera de las cotizadas relaciona sociedades con empresas cotizadas por sus cuentas anuales. Cuando la cotizada se alcanza a través de otra sociedad del grupo, se indica.</li>
      <li><b>Fuego, suelo, agua, ríos, aerogeneradores y tendidos.</b> Vigía de incendios, Centinela Natura, Vigilancia de humedales, Caudal ecológico y Riesgo de tendidos para aves publican cada hecho con su lugar. Aquí se agrupan por espacio y municipio.</li>
      <li><b>Zona inundable.</b> Zona inundable cuenta, municipio a municipio, los edificios del Catastro construidos después de 2016 dentro de las zonas inundables del SNCZI. Es un inventario, no un hecho con fecha: sale solo en la ficha de cada municipio, sin mapa ni ventana de tiempo.</li>
      <li><b>Depuración y baño.</b> Depuración y baño señala las aglomeraciones urbanas cuya depuración no cumple la directiva europea, según el último informe de España a la Agencia Europea de Medio Ambiente, y las zonas de baño insuficientes de la última temporada. Salen en la ficha de cada municipio, con una gota en el mapa. El punto es el núcleo urbano, no el vertido, así que no se cruza con los espacios.</li>
      <li><b>Luz de noche.</b> Una vez al mes se descargan de la NASA las imágenes anuales de Black Marble (satélite VIIRS, píxeles de unos 500 m) y se calcula el brillo medio de cada espacio año a año. Como el producto sube y baja de un año a otro en todo el país a la vez, cada espacio se compara con los que eran igual de oscuros en 2012-2014. Solo se avisa de las subidas: el sensor apenas ve la luz azul de los LED blancos, así que una bajada puede ser solo el cambio de farolas y una subida, si acaso, se queda corta. En los espacios marinos, parte de la luz es de barcos.</li>
      <li><b>Aves de cada espacio.</b> Son las del formulario oficial de cada ZEPA en la base de datos de Natura 2000 que publica la Agencia Europea de Medio Ambiente una vez al año. Para cada especie se dice en qué época está (todo el año, cría, inverna o en paso) y qué parte de las que hay en España acoge el espacio: más del 15 %, entre el 2 y el 15 % o menos del 2 %. Las de población poco significativa solo se cuentan. Los nombres en castellano son los del MITECO.</li>
      <li><b>Municipios.</b> Los nombres de municipio que traen los anuncios se resuelven al código INE con la capa del IGN; los homónimos se desempatan por provincia y, si no, se dejan sin resolver.</li>
      <li>No hay un índice que lo resuma todo: mezclar hectáreas quemadas con proyectos exigiría decidir cuánto pesa cada cosa, y esa decisión no es técnica.</li>
    </ol>
    <h3>Parámetros</h3>
    __PARAMS__
  </div>
  <div>
    <h3>Presión, estado y respuesta</h3>
    <p>El seguimiento de las IBA de BirdLife International mira las presiones, el estado y la respuesta. Este panel cubre sobre todo las presiones (proyectos, fuego, cambios de uso, aerogeneradores, tendidos y luz de noche). Del estado tiene el agua de seis humedales y el caudal de 55 puntos de río; el estado de las poblaciones de aves sale de censos que no son públicos a esta escala. Como referencia, cada ficha dice qué aves dieron al espacio su valor, según su formulario oficial. La respuesta más directa a su alcance son las alegaciones: cada proyecto con plazo abierto lleva su fecha límite.</p>
    <h3>Lo que hay que saber antes de citarlo</h3>
    <p>Una ficha sin novedades no es un espacio sin problemas: solo aparece lo que vigila algún proyecto hermano, y varios cubren solo una parte de España. En el mapa de cada lugar, las capas que no cubren esa zona salen en gris con la nota «no cubre esta zona». Un proyecto en evaluación no es un daño: es un procedimiento abierto que puede acabar denegado. Una relación entre sociedades es un indicio sacado de registros públicos, no una acusación.</p>
    <h3>Datos de especies y personas</h3>
    <p>No se incorpora ni se publica ninguna ubicación de especies (colonias, nidos, dormideros ni territorios), ni datos de personas físicas. De las aves de cada espacio solo se publica la especie, la época y la parte de la población española, nunca el número de ejemplares, y se dejan fuera las filas que el Estado marca como sensibles.</p>
    <h3>Datos abiertos</h3>
    <p><a href="datos/hub.json">hub.json</a> con todas las señales y fichas · <a href="datos/municipios.json">municipios.json</a> · <a href="datos/luz.json">luz.json</a> con la luz de noche de cada espacio, año a año · <a href="datos/aves.json">aves.json</a> con las aves de cada espacio · <a href="sitios.geojson">sitios.geojson</a> · <a href="comunidades.geojson">comunidades.geojson</a> · un feed RSS por espacio en <span class="data">rss/&lt;código&gt;.xml</span> y por comunidad en <span class="data">rss/ca-&lt;código INE&gt;.xml</span> · <a href="https://github.com/Asensio94/estado-iba">código</a>. Actualizado el <span class="data">__GENERATED__</span>.</p>
  </div>
</section>

<footer class="site-footer">
  <p class="principle">Datos públicos, reglas a la vista y cada cifra enlazada a su fuente. Indicios, no veredictos.</p>
  <p>Red Natura 2000 y aves de cada espacio: Agencia Europea de Medio Ambiente (CC BY 4.0) · Nombres de aves: MITECO · Municipios: Instituto Geográfico Nacional (es-atlas) · Anuncios y resoluciones: Boletín Oficial del Estado · Sociedades: BORME y cuentas anuales · Focos y superficie quemada: NASA FIRMS y Copernicus Sentinel-2 · Cambio de uso y agua: Copernicus Sentinel-2 · Caudales: SAIH del Júcar y SIRA del Guadiana · Aerogeneradores y tendidos: OpenStreetMap · Luz de noche: NASA Black Marble (VIIRS) · Migración: radares meteorológicos europeos · Zonas inundables: SNCZI (MITECO) y Catastro · Depuración: informe de España a la AEMA (Directiva 91/271/CEE) · Zonas de baño: Náyade · Mapa: © colaboradores de OpenStreetMap · Código con licencia MIT.</p>
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
__I18N__
<script src="app.js?v=__VERSION__"></script>
</body>
</html>
"""
