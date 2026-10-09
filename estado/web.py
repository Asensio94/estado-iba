"""The public page: a map and one card per site, with every figure linked to its source."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from . import config
from .logo import LOGO_SVG, favicon_link

COMMON_CSS = Path(__file__).with_name("common.css").read_text(encoding="utf-8").strip()
FAVICON = favicon_link(*config.ACCENT)


def build(rows: list[dict], sites: dict[str, dict], now: datetime, today: date) -> None:
    docs = config.DOCS_DIR
    docs.mkdir(parents=True, exist_ok=True)
    (docs / ".nojekyll").touch()
    data = {"generated": now.strftime("%Y-%m-%dT%H:%MZ"), "today": today.isoformat(), "kind": config.SITE_KIND,
            "sites": rows}
    (docs / "panel.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    shapes = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"code": c, "name": s["name"]}, "geometry": s["geometry"]}
        for c, s in sites.items()]}
    (docs / "sitios.geojson").write_text(json.dumps(shapes, ensure_ascii=False, separators=(",", ":")),
                                         encoding="utf-8")
    figures = _figures(rows)
    html = (PAGE.replace("__LOGO__", LOGO_SVG).replace("__FAVICON__", FAVICON)
            .replace("/*__COMMON_CSS__*/", COMMON_CSS)
            .replace("__N_SITES__", _es(len(rows)))
            .replace("__FIG_PROJECTS__", _es(figures["projects"]))
            .replace("__FIG_PRECISE__", _es(figures["precise"]))
            .replace("__FIG_OPEN__", _es(figures["open"]))
            .replace("__FIG_FIRE__", _es(figures["fire"]))
            .replace("__FIG_WET__", figures["wet"])
            .replace("__PARAMS__", _params())
            .replace("__GENERATED__", data["generated"])
            .replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")))
    (docs / "index.html").write_text(html, encoding="utf-8")


def _figures(rows: list[dict]) -> dict:
    wet = [w["state"] for r in rows for w in r["wetlands"] if w["state"] and w["state"]["current"]
           and w["state"]["ratio"] is not None]
    seen, low = set(), 0
    for r in rows:
        for w in r["wetlands"]:
            st = w["state"]
            if w["slug"] in seen or not st or not st["current"] or st["ratio"] is None:
                continue
            seen.add(w["slug"])
            low += st["ratio"] < 0.75
    return {
        "projects": sum(r["n_notices"] > 0 for r in rows),
        "precise": sum(r["n_precise"] > 0 for r in rows),
        "open": sum(r["n_open"] > 0 for r in rows),
        "fire": sum(r["fire_ha"] > 0 for r in rows),
        "wet": f"{low} de {len(seen)}" if wet else "—",
    }


def _es(x: float) -> str:
    return f"{x:,}".replace(",", ".")


def _params() -> str:
    rows = [
        ("Espacios", f"{config.SITE_KIND} de la Red Natura 2000, simplificadas a unos 300 m (0,003°)"),
        ("Fuego", f"incendios de los últimos {config.FIRE_WINDOW_DAYS} días"),
        ("Cambio de uso", "alertas confirmadas o provisionales; no cuentan las descartadas, revertidas ni fusionadas"),
        ("Humedal en una ZEPA", "al menos el 25 % de su superficie dentro de ella"),
        ("Agua de referencia", f"mediana del mismo mes en años anteriores, con al menos {config.WETLAND_MIN_YEARS} años"),
        ("Dato de agua vigente", f"observación sin nubes de hace {config.WETLAND_MAX_AGE_DAYS} días o menos"),
        ("Menos agua de lo normal", "menos del 75 % de la referencia"),
        ("Laguna normalmente seca", "referencia por debajo del 5 % de su máximo: no se calcula el porcentaje"),
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
<meta name="description" content="Presiones y estado de cada área importante para las aves en España, reunidas a partir de datos públicos.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
/*__COMMON_CSS__*/
:root{--accent:#a3336e;--accent-dark:#ec8fc0}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--accent:var(--accent-dark)}}
:root[data-theme="dark"]{--accent:var(--accent-dark)}
.rotulo{font:600 14px/1.2 var(--font-title);text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}
.aviso-unidad{margin:0;max-width:72ch;font-size:15px;border-left:3px solid var(--accent);padding:2px 0 2px 12px}
main{max-width:1440px;margin:0 auto;padding:8px 16px;display:grid;grid-template-columns:minmax(0,5fr) minmax(0,6fr);gap:20px;align-items:start}
.mapa-caja{position:sticky;top:12px}
#mapa{height:calc(100vh - 90px);min-height:420px;border:1px solid var(--line);background:var(--paper)}
.leyenda{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px;color:var(--muted);padding:6px 0}
.leyenda i{display:inline-block;width:14px;height:10px;margin-right:5px;vertical-align:-1px;border:1px solid var(--accent)}
.controles{position:sticky;top:0;z-index:5;background:var(--ground);padding:8px 0 10px;display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;border-bottom:1px solid var(--line);font-size:15px}
.controles select,.controles input[type=search]{font:15px var(--font-text);background:var(--paper);color:var(--ink);border:1px solid var(--line);padding:4px 6px}
.controles input[type=search]{width:min(220px,60vw)}
.cuenta{font:13px var(--font-data);color:var(--muted)}
#fichas{display:grid;gap:10px;padding-top:10px}
details.sitio{background:var(--paper);border:1px solid var(--line);box-shadow:var(--shadow);scroll-margin-top:70px}
details.sitio[open]{border-color:var(--accent)}
details.sitio>summary{list-style:none;cursor:pointer;padding:12px 14px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 12px;align-items:baseline}
details.sitio>summary::-webkit-details-marker{display:none}
.nombre{font:600 21px/1.1 var(--font-title);letter-spacing:.01em}
.codigo{font:12.5px var(--font-data);color:var(--muted);margin-left:6px}
.chips{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:6px}
.chip{font:12.5px/1 var(--font-data);padding:4px 7px;border:1px solid var(--line);color:var(--muted);white-space:nowrap}
.chip.on{border-color:var(--accent);color:var(--ink)}
.chip.on b{color:var(--accent)}
.chip.abierto{background:var(--accent);border-color:var(--accent);color:var(--paper)}
.chip.abierto b{color:inherit}
.chip.nd{border-style:dashed}
.cuerpo{padding:0 14px 14px;display:grid;gap:12px}
.bloque h3{margin:0 0 4px;font:600 15px/1.2 var(--font-title);text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.bloque ul{margin:0;padding:0;list-style:none;display:grid;gap:6px}
.bloque li{font-size:15px;line-height:1.4;border-left:2px solid var(--line);padding-left:10px}
.bloque li.abierto{border-left-color:var(--accent)}
.meta{display:block;font:12.5px var(--font-data);color:var(--muted)}
.vacio{font-size:14.5px;color:var(--muted);margin:0}
.leaflet-container{background:var(--paper);font:13px var(--font-text)}
.leaflet-bar a,.leaflet-control-attribution{background:var(--paper)!important;color:var(--ink)!important}
.method{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px;border-top:1.5px solid var(--ink);margin-top:24px}
@media (max-width:900px){
  main{grid-template-columns:1fr}
  .mapa-caja{position:relative;top:0}
  #mapa{height:52vh}
  .method{grid-template-columns:1fr}
}
</style>
</head>
<body>
<header class="site-header">
  <div>
    <h1>__LOGO__Estado de las <span>IBA</span></h1>
    <span class="rotulo">España · __N_SITES__ espacios para las aves · cada día</span>
  </div>
  <p class="lede">Lo que les está pasando a los espacios importantes para las aves, reunido en una ficha por espacio: los proyectos que se someten a evaluación ambiental, el fuego, los cambios de uso del suelo y el agua de sus humedales. Todo sale de otros proyectos de datos abiertos y cada cifra enlaza a su origen.</p>
  <p class="aviso-unidad">Por ahora la unidad son las <b>ZEPA</b> (zonas de especial protección para las aves de la Red Natura 2000), que son datos abiertos. Las IBA de SEO/BirdLife entrarán cuando su reutilización esté acordada.</p>
  <div class="figures">
    <div><b>__FIG_PROJECTS__</b><span>ZEPA con proyectos en evaluación en su municipio</span></div>
    <div><b>__FIG_PRECISE__</b><span>con proyectos dentro según sus parcelas</span></div>
    <div><b>__FIG_OPEN__</b><span>con alegaciones abiertas hoy</span></div>
    <div><b>__FIG_FIRE__</b><span>tocadas por el fuego en 12 meses</span></div>
    <div><b>__FIG_WET__</b><span>humedales con menos agua de lo normal</span></div>
  </div>
</header>

<main>
  <div class="mapa-caja">
    <div id="mapa" role="region" aria-label="Mapa de las ZEPA"></div>
    <div class="leyenda" id="leyenda"></div>
  </div>
  <div>
    <div class="controles">
      <label>Ordenar por <select id="orden">
        <option value="precise">Proyectos dentro, por parcelas</option>
        <option value="open">Alegaciones abiertas</option>
        <option value="notices">Proyectos en evaluación</option>
        <option value="fire">Hectáreas quemadas</option>
        <option value="land">Cambios de uso</option>
        <option value="name">Nombre</option>
      </select></label>
      <label><input type="checkbox" id="solo" checked> Solo con alguna presión</label>
      <input type="search" id="buscar" placeholder="Buscar espacio o código" aria-label="Buscar espacio o código">
      <span class="cuenta" id="cuenta" aria-live="polite"></span>
    </div>
    <div id="fichas"></div>
  </div>
</main>

<section class="method" id="metodo">
  <div>
    <h2>Cómo se calcula</h2>
    <ol>
      <li>Cada día se leen los datos que ya publican otros proyectos hermanos. Este panel no vuelve a medir nada: los reúne por espacio y enlaza a cada registro.</li>
      <li><b>Proyectos.</b> El Observatorio de alegaciones lee el BOE cada mañana y cruza cada anuncio con la Red Natura 2000. Si el anuncio trae la relación de parcelas afectadas, el cruce es con esas parcelas («por parcelas»). Si no, con el término municipal completo («por municipio»), que es solo una aproximación: el proyecto puede quedar lejos del espacio. Las resoluciones aparecen cuando el Observatorio las ha emparejado con su anuncio.</li>
      <li><b>Fuego.</b> El Vigía de incendios publica cada incendio con las hectáreas que toca de cada espacio. Si ya hay superficie quemada medida con Sentinel-2, se usa esa. Si no, la extensión de los píxeles con focos, que exagera los incendios pequeños.</li>
      <li><b>Cambio de uso.</b> Centinela Natura compara cada mes la vegetación con imágenes de Sentinel-2 y abre una alerta donde cambia. Solo vigila Cantabria por ahora; en el resto de espacios la ficha dice que no hay vigilancia, no que no haya cambios.</li>
      <li><b>Agua.</b> Vigilancia de humedales mide el agua libre de seis humedales con Sentinel-2 desde 2017. La última observación sin nubes se compara con la mediana del mismo mes en los años anteriores.</li>
      <li>No hay un índice que lo resuma todo. Mezclar hectáreas quemadas con proyectos en evaluación exigiría decidir cuánto pesa cada cosa, y esa decisión no es técnica. Las fichas se ordenan por el indicador que se elija.</li>
    </ol>
    <h3>Parámetros</h3>
    __PARAMS__
  </div>
  <div>
    <h3>Presión, estado y respuesta</h3>
    <p>El seguimiento de las IBA de BirdLife International mira tres cosas: las presiones (lo que amenaza el espacio), el estado (cómo están sus aves y sus hábitats) y la respuesta (lo que se hace para protegerlo). Este panel cubre sobre todo las presiones. Del estado solo tiene, por ahora, el agua de seis humedales: el estado de las poblaciones de aves sale de censos que no son públicos a esta escala. La respuesta más directa a su alcance son las alegaciones: cada proyecto con plazo abierto lleva su fecha límite.</p>
    <h3>Lo que hay que saber antes de citarlo</h3>
    <p>Una ficha sin presiones no es un espacio sin problemas. Solo aparecen las presiones que vigila algún proyecto hermano, y algunos solo cubren una parte de España: el cambio de uso solo Cantabria, el agua solo seis humedales. Los tendidos eléctricos peligrosos, la caza, el pastoreo o las molestias humanas no están todavía. Un proyecto en evaluación tampoco es un daño: es un procedimiento abierto, que puede acabar denegado.</p>
    <h3>Datos de censos de especies</h3>
    <p>Este panel no incorpora ni publica ubicaciones de especies (colonias, nidos, dormideros ni territorios). Una ubicación precisa junto a un proyecto o un incendio puede poner en riesgo a la especie.</p>
    <h3>Datos abiertos</h3>
    <p><a href="panel.json">panel.json</a> con todas las fichas y sus registros · <a href="sitios.geojson">sitios.geojson</a> con los límites simplificados · <a href="https://github.com/Asensio94/estado-iba">código</a>. Generado el <span class="data">__GENERATED__</span>.</p>
  </div>
</section>

<footer class="site-footer">
  <p class="principle">Datos públicos, reglas a la vista y cada cifra enlazada a su fuente. Indicios, no veredictos.</p>
  <p>Red Natura 2000: Agencia Europea de Medio Ambiente, vía el Vigía de incendios · Proyectos: Boletín Oficial del Estado, vía el Observatorio de alegaciones · Focos y superficie quemada: NASA FIRMS y Copernicus Sentinel-2, vía el Vigía de incendios · Cambio de uso: Copernicus Sentinel-2, vía Centinela Natura · Agua: Copernicus Sentinel-2, vía Vigilancia de humedales · Mapa: © colaboradores de OpenStreetMap · Código con licencia MIT.</p>
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
<script>
const D = __DATA__;
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const num = (x, d = 0) => x == null ? "—" : x.toLocaleString("es-ES", {minimumFractionDigits: d, maximumFractionDigits: d});
const fecha = s => s ? new Date(s + "T12:00:00").toLocaleDateString("es-ES", {day: "numeric", month: "short", year: "numeric"}) : "";
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const byCode = Object.fromEntries(D.sites.map(s => [s.code, s]));
const nLand = s => s.land ? s.land.length : 0;
const pressured = s => s.n_notices || s.fire_ha || nLand(s);
const VALUE = {
  open: s => s.n_open, precise: s => s.n_precise, notices: s => s.n_notices, fire: s => s.fire_ha, land: s => nLand(s), name: () => 0,
};
const LEGEND = {
  open: "proyectos con alegaciones abiertas", precise: "proyectos dentro según sus parcelas", notices: "proyectos en evaluación", fire: "hectáreas quemadas en 12 meses",
  land: "alertas de cambio de uso (solo Cantabria)", name: "",
};

function chips(s) {
  const c = [];
  if (s.n_open) c.push(`<span class="chip abierto"><b>${s.n_open}</b> con alegaciones abiertas</span>`);
  c.push(`<span class="chip ${s.n_notices ? "on" : ""}"><b>${s.n_notices}</b> proyectos${s.n_notices && !s.n_precise ? " (en su municipio)" : ""}</span>`);
  c.push(`<span class="chip ${s.fire_ha ? "on" : ""}"><b>${num(s.fire_ha, s.fire_ha < 10 ? 1 : 0)}</b> ha quemadas</span>`);
  c.push(s.land ? `<span class="chip ${s.land.length ? "on" : ""}"><b>${s.land.length}</b> cambios de uso</span>`
                : `<span class="chip nd" title="Centinela Natura no vigila este espacio todavía">cambio de uso sin vigilar</span>`);
  for (const w of s.wetlands) {
    const st = w.state;
    if (st && st.current && st.ratio != null)
      c.push(`<span class="chip ${st.ratio < .75 ? "on" : ""}">${esc(w.name)}: <b>${num(st.ratio * 100)} %</b> del agua normal</span>`);
  }
  return c.join("");
}

function projectItem(p) {
  const tipo = p.kind === "anuncio" ? "Anuncio" : "Resolución";
  const extra = p.kind === "anuncio"
    ? (p.open ? `alegaciones hasta el ${fecha(p.deadline)}` : (p.deadline ? `plazo cerrado el ${fecha(p.deadline)}` : "sin plazo conocido"))
    : esc(p.outcome || "");
  const mw = p.mw ? ` · ${num(p.mw, 1)} MW` : "";
  return `<li class="${p.open ? "abierto" : ""}"><a href="${esc(p.url)}">${esc(p.title)}</a>
    <span class="meta">${tipo} · ${fecha(p.date)}${mw} · cruce por ${esc(p.precision)} · ${extra}</span></li>`;
}

function body(s) {
  const b = [];
  b.push(`<div class="bloque"><h3>Proyectos en evaluación ambiental</h3>${s.projects.length
    ? `<ul>${s.projects.map(projectItem).join("")}</ul>`
    : `<p class="vacio">Ninguno desde que el Observatorio empezó a leer el BOE.</p>`}</div>`);
  b.push(`<div class="bloque"><h3>Fuego en los últimos 12 meses</h3>${s.fires.length
    ? `<ul>${s.fires.map(f => `<li><a href="https://asensio94.github.io/vigia-incendios/#${esc(f.id)}">${esc(f.id)}</a> · ${esc(f.place || "")}
        <span class="meta">${fecha(f.date)} · ${num(f.ha, 1)} ha dentro del espacio · ${f.source === "sentinel2" ? "medido con Sentinel-2" + (f.final ? "" : " (provisional)") : "extensión de los focos"}</span></li>`).join("")}</ul>`
    : `<p class="vacio">Ningún incendio visto por satélite.</p>`}</div>`);
  b.push(`<div class="bloque"><h3>Cambios de uso del suelo</h3>${!s.land
    ? `<p class="vacio">Centinela Natura todavía no vigila este espacio.</p>`
    : s.land.length
      ? `<ul>${s.land.map(a => `<li><a href="https://asensio94.github.io/centinela-natura/#${esc(a.id)}">${esc(a.id)}</a> · ${esc(a.class || "")}
          <span class="meta">${fecha(a.date)} · ${num(a.ha, 1)} ha · ${esc(a.state)}${a.permit === "sin_expediente" ? " · sin expediente encontrado" : ""}</span></li>`).join("")}</ul>`
      : `<p class="vacio">Ninguna alerta confirmada ni provisional.</p>`}</div>`);
  if (s.wetlands.length) {
    b.push(`<div class="bloque"><h3>Agua de sus humedales</h3><ul>${s.wetlands.map(w => {
      const st = w.state;
      if (!st) return `<li>${esc(w.name)}<span class="meta">sin observaciones válidas</span></li>`;
      const ref = st.dry_ref ? "en ese mes suele estar seca: no hay referencia con la que comparar" : st.ratio != null ? `${num(st.ratio * 100)} % de lo normal en ese mes (${num(st.ref_ha)} ha, mediana de ${st.ref_years.length} años)` : "sin años suficientes para comparar";
      return `<li><a href="https://asensio94.github.io/vigilancia-humedales/">${esc(w.name)}</a>: ${num(st.water_ha)} ha de agua libre
        <span class="meta">${fecha(st.date)}${st.current ? "" : " (dato antiguo)"} · ${ref}</span></li>`;
    }).join("")}</ul></div>`);
  }
  return b.join("");
}

function card(s) {
  return `<details class="sitio" id="s-${esc(s.code)}" data-code="${esc(s.code)}">
    <summary><span><span class="nombre">${esc(s.name)}</span><span class="codigo">${esc(s.code)}</span></span>
      <span class="chips">${chips(s)}</span></summary>
    <div class="cuerpo"></div></details>`;
}

const $ = id => document.getElementById(id);
const fichas = $("fichas");
function render() {
  const key = $("orden").value, q = $("buscar").value.trim().toLowerCase(), solo = $("solo").checked;
  let list = D.sites.filter(s => (!solo || pressured(s)) && (!q || s.name.toLowerCase().includes(q) || s.code.toLowerCase().includes(q)));
  list = list.slice().sort((a, b) => key === "name" ? a.name.localeCompare(b.name, "es") : (VALUE[key](b) - VALUE[key](a)) || (b.n_open - a.n_open) || a.name.localeCompare(b.name, "es"));
  fichas.innerHTML = list.map(card).join("") || `<p class="vacio">Ningún espacio coincide.</p>`;
  $("cuenta").textContent = `${list.length} de ${D.sites.length} espacios`;
  paint(key);
}
fichas.addEventListener("toggle", e => {
  const d = e.target;
  if (d.open && !d.querySelector(".cuerpo").innerHTML) d.querySelector(".cuerpo").innerHTML = body(byCode[d.dataset.code]);
  if (d.open) highlight(d.dataset.code);
}, true);
["orden", "solo", "buscar"].forEach(id => $(id).addEventListener("input", render));

const mapa = L.map("mapa", {zoomSnap: .5}).setView([40.2, -3.7], 5.5);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 18, attribution: "© OpenStreetMap"}).addTo(mapa);
let capa, marcado;
fetch("sitios.geojson").then(r => r.json()).then(g => {
  capa = L.geoJSON(g, {
    style: () => ({color: css("--accent"), weight: 1, fillOpacity: .05}),
    onEachFeature: (f, l) => {
      l.bindTooltip(esc(f.properties.name), {sticky: true});
      l.on("click", () => open(f.properties.code));
    },
  }).addTo(mapa);
  paint($("orden").value);
});
function paint(key) {
  if (!capa) return;
  const max = Math.max(1, ...D.sites.map(VALUE[key]));
  capa.eachLayer(l => {
    const v = VALUE[key](byCode[l.feature.properties.code] || {}) || 0;
    l.setStyle({color: css("--accent"), weight: l === marcado ? 3 : 1, fillColor: css("--accent"),
                fillOpacity: key === "name" ? .08 : .04 + .6 * Math.sqrt(v / max)});
  });
  $("leyenda").innerHTML = key === "name" ? "" : `<span><i style="background:var(--accent);opacity:.2"></i>poco</span><span><i style="background:var(--accent);opacity:.65"></i>${esc(LEGEND[key])}: máximo ${num(max)}</span>`;
}
function highlight(code) {
  if (!capa) return;
  capa.eachLayer(l => { if (l.feature.properties.code === code) { marcado = l; mapa.fitBounds(l.getBounds(), {maxZoom: 10, padding: [20, 20]}); } });
  paint($("orden").value);
}
function open(code) {
  let d = $("s-" + code);
  if (!d) { $("solo").checked = false; $("buscar").value = ""; render(); d = $("s-" + code); }
  d.open = true;
  d.scrollIntoView({behavior: "smooth", block: "start"});
}
render();
</script>
</body>
</html>
"""
