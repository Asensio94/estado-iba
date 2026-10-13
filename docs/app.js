"use strict";
// Estado de las IBA: one page, five views (home, community, site, municipality, deadlines) routed by the URL hash.

const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const num = (x, d = 0) => x == null ? "—" : Number(x).toLocaleString("es-ES", {minimumFractionDigits: d, maximumFractionDigits: d});
const fecha = s => s ? new Date(s.slice(0, 10) + "T12:00:00").toLocaleDateString("es-ES", {day: "numeric", month: "short", year: "numeric"}) : "";
const mesDe = s => new Date(s.slice(0, 7) + "-15T12:00:00").toLocaleDateString("es-ES", {month: "long", year: "numeric"});
const norm = s => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const corta = (t, n) => t.length > n ? t.slice(0, n - 1) + "…" : t;

const KIND = {
  notice: {tag: "Proyecto", theme: "Proyectos en evaluación"},
  resolution: {tag: "Resolución", theme: "Proyectos en evaluación"},
  fire: {tag: "Fuego", theme: "Fuego"},
  land_change: {tag: "Suelo", theme: "Cambios de uso del suelo"},
  wetland_water: {tag: "Agua", theme: "Agua de los humedales"},
  river_flow: {tag: "Río", theme: "Caudal de los ríos"},
  power_line: {tag: "Infraestructura", theme: "Aerogeneradores y tendidos eléctricos"},
  migration: {tag: "Migración", theme: "Migración nocturna"},
};
const PRECISION = {
  parcelas: "cruce por parcelas", municipio: "cruce por municipio", perimetro: "perímetro Sentinel-2",
  focos: "extensión de los focos", pixeles: "píxeles Sentinel-2", lamina: "lámina de agua", punto: "punto",
};
const MEANS = {
  notice: "Un anuncio de información pública abre un plazo para que cualquier persona o entidad presente alegaciones. Que un proyecto esté en evaluación no significa que vaya a hacerse.",
  resolution: "La resolución cierra el procedimiento: autoriza, deniega o archiva el proyecto. El Observatorio la empareja con el anuncio que la abrió.",
  fire: "Incendio visto por satélite. Si ya hay perímetro de Sentinel-2, las hectáreas son las quemadas dentro del espacio; si no, la extensión de los píxeles con focos, que exagera los incendios pequeños.",
  land_change: "Centinela compara la vegetación con imágenes de Sentinel-2. Una alerta no es una infracción: puede ser una obra autorizada, una corta o un cambio de cultivo. Se indica si se encontró expediente.",
  wetland_water: "Agua libre medida con Sentinel-2, comparada con la mediana del mismo mes en años anteriores.",
};
const PREC_NOTE = {
  municipio: "Este anuncio no trae parcelas: se ha cruzado el término municipal entero con el espacio, así que el proyecto puede quedar fuera.",
};
const LEVEL = {"very high": "muy alta", high: "alta", moderate: "moderada", low: "baja"};

/* Map layers: one per sibling. Colours were checked for colour-blind separation against the OSM
   tiles; each layer also has its own shape, so colour is never the only cue. The tiles stay light
   in dark mode, so the marks keep a fixed dark outline instead of following the theme. */
const OUTLINE = "#221d1a", MAP_ACCENT = "#a3336e";
const LAYERS = [
  {id: "proyectos", name: "Proyectos en evaluación", color: "#a3336e", shape: "square", source: "observatorio-alegaciones", kinds: ["notice"]},
  {id: "fuego", name: "Incendios en 12 meses", color: "#eb6834", shape: "triangle", source: "vigia-incendios", kinds: ["fire"]},
  {id: "suelo", name: "Cambios de uso del suelo", color: "#1baf7a", shape: "diamond", source: "centinela-natura", kinds: ["land_change"]},
  {id: "humedales", name: "Agua de los humedales", color: "#2a78d6", shape: "circle", source: "vigilancia-humedales", kinds: ["wetland_water"]},
  {id: "rios", name: "Caudal de los ríos", color: "#2a78d6", shape: "ring", source: "caudal-ecologico", kinds: ["river_flow"]},
  {id: "tendidos", name: "Aerogeneradores y tendidos de riesgo alto", color: "#4a3aa7", shape: "plus", source: "riesgo-tendidos-aves", kinds: ["power_line"]},
  {id: "migracion", name: "Migración esta noche", color: OUTLINE, stroke: "#fff", shape: "star", source: "sub-nocte", kinds: ["migration"]},
];
const STAR = Array.from({length: 10}, (_, i) => {
  const a = (-90 + i * 36) * Math.PI / 180, r = i % 2 ? 3.9 : 9.2;
  return `${(10 + r * Math.cos(a)).toFixed(2)},${(10.8 + r * Math.sin(a)).toFixed(2)}`;
}).join(" ");
const SHAPE = {
  square: `<rect x="3" y="3" width="14" height="14" rx="1.5"/>`,
  triangle: `<path d="M10 2 18.5 17H1.5Z"/>`,
  diamond: `<path d="M10 1.5 18.5 10 10 18.5 1.5 10Z"/>`,
  circle: `<circle cx="10" cy="10" r="7.5"/>`,
  ring: `<circle cx="10" cy="10" r="8"/><circle cx="10" cy="10" r="3.2" fill="#fff"/>`,
  plus: `<path d="M7 2h6v5h5v6h-5v5H7v-5H2V7h5z"/>`,
  star: `<polygon points="${STAR}"/>`,
};

let D, M, SHAPES, REGIONS_GEO, capa, MAPS = [];
const bySite = new Map(), byMuni = new Map(), byRegion = new Map();

function daysLeft(deadline) {
  return Math.round((new Date(deadline + "T12:00:00") - new Date(D.today + "T12:00:00")) / 864e5);
}
function dias(deadline) {
  const n = daysLeft(deadline);
  return n === 0 ? "último día hoy" : n === 1 ? "queda 1 día" : `quedan ${n} días`;
}
const isOpen = s => s.deadline && s.deadline >= D.today && s.kind === "notice";
const siteName = c => D.sitesByCode[c]?.name || c;
const weekAgo = () => new Date(new Date(D.today + "T12:00:00") - 7 * 864e5).toISOString().slice(0, 10);
const regionLinks = ids => ids.map(id => D.regionsById[id]).filter(Boolean)
  .map(r => `<a href="#/ca/${esc(r.id)}">${esc(r.name)}</a>`).join(" · ");

function tag(s) {
  const k = KIND[s.kind] || {tag: s.kind};
  return `<span class="tag">${esc(k.tag)}</span>`;
}
function precTag(s) {
  return s.precision === "municipio" ? `<span class="tag prec-municipio" title="${esc(PREC_NOTE.municipio)}">por municipio</span>` : "";
}
function value(s) {
  if (!s.value || s.value.amount == null) return "";
  const a = s.value.amount;
  return ` · ${num(a, a < 10 ? 1 : 0)} ${esc(s.value.unit)}`;
}
function siteHa(s, code) {
  const x = (s.sites || []).find(z => z.code === code);
  return x && x.ha != null ? ` · ${num(x.ha, x.ha < 10 ? 1 : 0)} ha dentro` : "";
}

/* ---------- Home ---------- */

function home() {
  document.title = "Estado de las IBA";
  const open = D.signals.filter(s => isOpen(s) && s.sites.length)
    .sort((a, b) => a.deadline.localeCompare(b.deadline) || (a.precision === "parcelas" ? -1 : 1));

  $("#vista").innerHTML = `
  <div class="wrap">
    ${buscador()}
    <p class="ejemplos">Por ejemplo: <a href="#/e/ES0000014">Monfragüe</a> · <a href="#/e/ES0000024">Doñana</a> · <a href="#/m/30016">Cartagena</a> · <a href="#/ca/06">Cantabria</a></p>
    <section class="bloque-home">
      <h2 class="sec">Todo en un mapa</h2>
      <p class="sec-sub">Cada capa viene de un proyecto hermano y se activa o se apaga en la leyenda. Los espacios se colorean según lo que elijas.</p>
      <div class="controles"><label>Colorear los espacios por <select id="indicador">
        <option value="precise">Proyectos dentro, por parcelas</option>
        <option value="open">Proyectos con plazo abierto</option>
        <option value="notices">Proyectos en su municipio</option>
        <option value="fire_ha">Hectáreas quemadas en 12 meses</option>
        <option value="land">Cambios de uso (solo Cantabria)</option>
      </select></label></div>
      <div id="mapa-host" class="mapa-host grande"></div>
      <div class="leyenda" id="leyenda"></div>
    </section>
    <section class="bloque-home">
      <h2 class="sec">Por comunidad</h2>
      <p class="sec-sub">Sus ZEPA, sus plazos abiertos y lo nuevo de la semana. Canarias, Ceuta y Melilla quedan fuera del mapa de arriba.</p>
      ${comunidades()}
    </section>
    <div class="dos">
      <section class="bloque-home">
        <h2 class="sec">Plazos abiertos</h2>
        <p class="sec-sub">Proyectos que tocan una ZEPA y aún admiten alegaciones, del plazo más corto al más largo.</p>
        <ul class="lista">${open.slice(0, 7).map(s => plazoItem(s)).join("") || `<li class="vacio">Ningún plazo abierto hoy.</li>`}</ul>
        ${open.length > 7 ? `<a class="ver-mas" href="#/plazos">Ver los ${open.length} plazos abiertos</a>` : ""}
      </section>
      <section class="bloque-home">
        ${noche()}
        <h2 class="sec">Esta semana</h2>
        <p class="sec-sub">Lo nuevo en los últimos 7 días en algún espacio.</p>
        ${semana(D.signals)}
      </section>
    </div>
    <section class="bloque-home">
      <h2 class="sec">Clasificación</h2>
      <p class="sec-sub" id="ranking-sub"></p>
      <div class="ranking" id="ranking"></div>
    </section>
  </div>`;
  wireSearch();
  const sel = $("#indicador");
  sel.addEventListener("input", () => { paintHome(sel.value); ranking(sel.value); });
  mapaTodo($("#mapa-host"), scopeAll(), "Mapa de todas las ZEPA y de lo que vigila cada proyecto")
    .then(r => { if (r) { capa = r.poly; paintHome(sel.value); } });
  ranking(sel.value);
}

function comunidades() {
  const week = weekAgo();
  return `<ul class="comunidades">${D.regions.slice().sort((a, b) => a.name.localeCompare(b.name, "es")).map(r => {
    const sig = byRegion.get(r.id) || [];
    const open = sig.filter(s => isOpen(s) && s.sites.length).length;
    const nuevo = sig.filter(s => s.date >= week && s.sites.length && !["wetland_water", "migration"].includes(s.kind)).length;
    return `<li><a href="#/ca/${esc(r.id)}"><b>${esc(r.name)}</b><span class="meta">${r.sites.length} ZEPA</span>
      <span class="meta">${open ? `<span class="dias">${open} ${open === 1 ? "plazo abierto" : "plazos abiertos"}</span>` : "ningún plazo abierto"}</span>
      <span class="meta">${nuevo ? `${nuevo} ${nuevo === 1 ? "novedad" : "novedades"} esta semana` : "nada nuevo esta semana"}</span></a></li>`;
  }).join("")}</ul>`;
}

function semana(signals) {
  const week = weekAgo();
  const recent = signals.filter(s => s.date >= week && s.sites.length && !["wetland_water", "migration"].includes(s.kind))
    .sort((a, b) => b.date.localeCompare(a.date));
  const groups = {};
  for (const s of recent) (groups[KIND[s.kind]?.theme || s.kind] ||= []).push(s);
  return Object.entries(groups).map(([theme, list]) => `
    <div class="semana-tema"><h3>${esc(theme)} · ${list.length}</h3>
    <ul class="lista">${list.slice(0, 4).map(s => feedItem(s)).join("")}</ul>
    ${list.length > 4 ? `<p class="meta">y ${list.length - 4} más</p>` : ""}</div>`).join("") || `<p class="vacio">Nada nuevo esta semana.</p>`;
}

function noche() {
  const m = D.signals.filter(s => s.kind === "migration" && s.status !== "low");
  if (!m.length) return "";
  const night = m[0].date;
  const order = {"very high": 0, high: 1, moderate: 2};
  m.sort((a, b) => order[a.status] - order[b.status] || a.details.city.localeCompare(b.details.city, "es"));
  return `<div class="panel" style="margin-bottom:22px"><h3>Esta noche · migración prevista</h3>
    <p class="meta" style="margin:0 0 6px">${fecha(night)} · según <a href="${esc(D.sources["sub-nocte"].url)}">Sub Nocte</a></p>
    <p style="margin:0;font-size:15px">${m.map(s => `${s.municipalities[0] ? `<a href="#/m/${esc(s.municipalities[0])}">${esc(s.details.city)}</a>` : esc(s.details.city)}: <b>${LEVEL[s.status] || esc(s.status)}</b>`).join(" · ")}</p></div>`;
}

function plazoItem(s, code) {
  const sites = s.sites.map(x => `<a href="#/e/${esc(x.code)}">${esc(siteName(x.code))}</a>`).join(", ");
  return `<li class="item ${daysLeft(s.deadline) <= 7 ? "urgente" : ""}">
    <div class="meta"><span class="dias">${dias(s.deadline)}</span> · hasta el ${fecha(s.deadline)} ${precTag(s)}</div>
    <div class="t"><a href="${esc(s.url)}">${esc(s.title)}</a></div>
    <div class="meta">${code ? "" : sites + " · "}${fecha(s.date)}${value(s)}${s.details.promoter ? " · " + esc(s.details.promoter) : ""}</div></li>`;
}
function feedItem(s) {
  const sites = s.sites.slice(0, 3).map(x => `<a href="#/e/${esc(x.code)}">${esc(siteName(x.code))}</a>`).join(", ") + (s.sites.length > 3 ? ` y ${s.sites.length - 3} más` : "");
  return `<li class="item"><div class="t">${tag(s)}<a href="${esc(s.url)}">${esc(s.title)}</a></div>
    <div class="meta">${sites} · ${fecha(s.date)}${value(s)} ${precTag(s)}</div></li>`;
}

const IND = {
  precise: {label: "proyectos dentro según sus parcelas", f: n => n.precise},
  open: {label: "proyectos con plazo abierto", f: n => n.open},
  notices: {label: "proyectos en su municipio", f: n => n.notices},
  fire_ha: {label: "hectáreas quemadas", f: n => n.fire_ha},
  land: {label: "alertas de cambio de uso", f: n => n.land || 0},
};

function ranking(key) {
  const f = IND[key].f;
  const rows = D.sites.filter(s => f(s.n) > 0).sort((a, b) => f(b.n) - f(a.n) || a.name.localeCompare(b.name, "es"));
  $("#ranking-sub").textContent = `Las ZEPA con algo en «${IND[key].label}», de más a menos. Cambia el criterio encima del mapa.`;
  $("#ranking").innerHTML = `<table><thead><tr><th>Espacio</th><th>Comunidad</th><th class="n">${esc(IND[key].label)}</th></tr></thead><tbody>
    ${rows.map(s => `<tr><td><a href="#/e/${esc(s.code)}">${esc(s.name)}</a></td><td class="meta">${regionLinks(s.regions)}</td><td class="n">${num(f(s.n), key === "fire_ha" ? 1 : 0)}</td></tr>`).join("")
      || `<tr><td colspan="3" class="vacio">Ningún espacio.</td></tr>`}</tbody></table>`;
}

function paintHome(key) {
  if (!capa) return;
  const f = IND[key].f;
  const max = Math.max(1, ...D.sites.map(s => f(s.n)));
  capa.eachLayer(l => {
    const v = f(D.sitesByCode[l.feature.properties.code]?.n || {}) || 0;
    l.setStyle({color: MAP_ACCENT, weight: v ? 1.2 : .6, fillColor: MAP_ACCENT, fillOpacity: .03 + .62 * Math.sqrt(v / max)});
  });
  $("#leyenda").innerHTML = `<span><i style="opacity:.15"></i>ZEPA sin nada</span><span><i style="opacity:.65"></i>máximo: ${num(max, key === "fire_ha" ? 1 : 0)} ${esc(IND[key].label)}</span>`;
}

function plazos() {
  document.title = "Plazos abiertos · Estado de las IBA";
  const open = D.signals.filter(s => isOpen(s) && s.sites.length).sort((a, b) => a.deadline.localeCompare(b.deadline));
  $("#vista").innerHTML = `<div class="wrap">
    <nav class="migas"><a href="#/">Inicio</a> › Plazos abiertos</nav>
    <div class="lugar-cab"><h2>Plazos abiertos</h2></div>
    <p class="sec-sub">${open.length} proyectos que tocan alguna ZEPA admiten alegaciones hoy. Los marcados «por municipio» no traen parcelas: puede que no entren en el espacio.</p>
    <ul class="lista">${open.map(s => plazoItem(s)).join("")}</ul></div>`;
}

/* ---------- The map of everything ---------- */

async function shapes() {
  SHAPES ||= await fetch("sitios.geojson").then(r => r.json());
  return SHAPES;
}
async function regionShapes() {
  REGIONS_GEO ||= await fetch("comunidades.geojson").then(r => r.json());
  return REGIONS_GEO;
}
function baseMap(el, opts = {}) {
  const m = L.map(el, {zoomSnap: .5, ...opts}).setView([40.2, -3.7], 5.5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 18, attribution: "© OpenStreetMap"}).addTo(m);
  MAPS.push(m);
  return m;
}

function icono(shape, color, size = 18, o = {}) {
  const body = o.double
    ? `<rect x="4" y="4" width="12" height="12" rx="1"/><rect x=".9" y=".9" width="18.2" height="18.2" rx="2.5" fill="none" stroke-width="1.4"/>`
    : SHAPE[shape];
  const text = o.text != null ? `<text x="10" y="10" dy=".35em" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-weight="600"
    font-size="${o.double ? 7.5 : 9}" fill="#fff" stroke="none">${esc(o.text)}</text>` : "";
  return `<svg viewBox="0 0 20 20" width="${size}" height="${size}" aria-hidden="true"><g fill="${color}" stroke="${o.stroke || OUTLINE}"
    stroke-width="1.5" stroke-linejoin="round">${body}</g>${text}</svg>`;
}

// What a map shows: the sites drawn, the signals placed and how a municipality or a site is matched.
function scopeAll() {
  return {kind: "all", sites: D.sites.map(s => s.code), signals: D.signals, muniOk: () => true, siteOk: () => true};
}
function scopeRegion(r) {
  const set = new Set(r.sites);
  return {kind: "region", id: r.id, sites: r.sites, signals: byRegion.get(r.id) || [], bbox: r.bbox,
          muniOk: ine => M.byIne[ine]?.region === r.id, siteOk: c => set.has(c)};
}
function scopeSite(s) {
  const munis = new Set(s.munis.map(m => m[0]));
  return {kind: "site", id: s.code, sites: [s.code], signals: bySite.get(s.code) || [],
          muniOk: ine => munis.has(ine), siteOk: c => c === s.code};
}
function scopeMuni(m) {
  return {kind: "muni", id: m.ine, sites: m.sites, signals: byMuni.get(m.ine) || [], point: m.point,
          muniOk: ine => ine === m.ine, siteOk: c => m.sites.includes(c)};
}

// Does the sibling behind a layer look at this place at all? Grey and «no cubre esta zona» when it
// does not, so an empty layer never reads as «nothing happens here».
function cubre(ly, scope, list) {
  const src = D.sources[ly.source];
  if (!src || src.coverage.label === "sin datos hoy") return {on: false, note: "sin datos hoy"};
  if (ly.id === "migracion") {
    if (scope.kind === "site") return {on: false, note: "se prevé por ciudad, no por espacio"};
    return scope.kind === "all" || list.length ? {on: true} : {on: false, note: `no cubre esta zona · ${src.coverage.label}`};
  }
  const cov = src.coverage.sites;
  if (cov == null) return {on: true};
  if (scope.kind === "all") return {on: true, note: src.coverage.label};
  return scope.sites.some(c => cov.includes(c)) ? {on: true} : {on: false, note: `no cubre esta zona · ${src.coverage.label}`};
}

function marca(latlng, html, size, title, pop, keyboard, zIndexOffset = 0) {
  return L.marker(latlng, {
    icon: L.divIcon({className: "marca", html, iconSize: [size, size], iconAnchor: [size / 2, size / 2], popupAnchor: [0, -size / 2]}),
    title, alt: title, keyboard, zIndexOffset, riseOnHover: true,
  }).bindPopup(pop, {maxWidth: 320});
}
function popup(s) {
  const sites = s.sites.slice(0, 3).map(x => `<a href="#/e/${esc(x.code)}">${esc(siteName(x.code))}</a>`).join(", ");
  const status = s.status && !["notice", "migration"].includes(s.kind) ? " · " + esc(s.status) : "";
  return `<div class="pop">${tag(s)}<a href="${esc(s.url)}">${esc(s.title)}</a>
    <div class="meta">${fecha(s.date)}${value(s)}${status}${sites ? " · " + sites : ""}</div></div>`;
}
function popupNoche(s) {
  const ine = s.municipalities[0];
  return `<div class="pop">${tag(s)}${ine ? `<a href="#/m/${esc(ine)}">${esc(s.details.city)}</a>` : esc(s.details.city)}: <b>${LEVEL[s.status] || esc(s.status)}</b>
    <div class="meta">noche del ${fecha(s.date)} · según <a href="${esc(s.url)}">Sub Nocte</a></div></div>`;
}
function popupProyectos(x) {
  const list = x.list.slice().sort((a, b) => (isOpen(b) - isOpen(a)) || b.date.localeCompare(a.date));
  const n = list.length;
  return `<div class="pop"><b><a href="${esc(x.href)}">${esc(x.name)}</a></b> · ${n} ${n === 1 ? "proyecto" : "proyectos"}
    <ul>${list.slice(0, 6).map(s => `<li>${isOpen(s) ? `<span class="dias">${dias(s.deadline)}</span> ` : ""}<a href="${esc(s.url)}">${esc(corta(s.title, 110))}</a>
      <span class="meta">${fecha(s.date)}${s.precision === "municipio" ? " · por municipio" : ""}</span></li>`).join("")}</ul>
    ${n > 6 ? `<a href="${esc(x.href)}">y ${n - 6} más</a>` : ""}</div>`;
}
function size(ly, s) {
  if (ly.id === "migracion") return {"very high": 24, high: 20}[s.status] || 16;
  if (ly.id === "fuego") return (s.value?.amount || 0) >= 100 ? 19 : 15;
  if (ly.id === "rios") return s.details.days_below ? 19 : 15;
  return 17;
}

// Projects carry no point of their own: they are counted at each municipality they name (or at
// the site, when the notice names none), so one square can stand for several projects.
function marcadores(ly, list, scope) {
  const kb = scope.kind !== "all";  // hundreds of tab stops on the national map; the lists below are the keyboard view
  if (ly.id === "proyectos") {
    const at = new Map();
    const put = (key, point, name, href, s) => {
      if (!point) return;
      const x = at.get(key) || {point, name, href, list: []};
      x.list.push(s);
      at.set(key, x);
    };
    for (const s of list) {
      let ines = s.municipalities.filter(i => M.byIne[i] && scope.muniOk(i));
      // Cut by its parcels, a project can touch a site from a municipality that shares only a sliver with it.
      if (!ines.length && scope.kind === "site") ines = s.municipalities.filter(i => M.byIne[i]);
      if (ines.length) for (const i of ines) put("m" + i, M.byIne[i].point, M.byIne[i].name, "#/m/" + i, s);
      else for (const x of s.sites) if (scope.siteOk(x.code)) {
        const st = D.sitesByCode[x.code];
        put("e" + x.code, st?.point, st?.name, "#/e/" + x.code, s);
      }
    }
    return [...at.values()].map(x => {
      const n = x.list.length, open = x.list.filter(isOpen).length, px = n >= 10 ? 26 : 22;
      const latlng = [x.point[1], x.point[0]];
      const title = `${x.name}: ${n} ${n === 1 ? "proyecto" : "proyectos"}${open ? `, ${open} con plazo abierto` : ""}`;
      // Big squares go under the other marks, so a wetland or a fire on the same spot stays visible.
      return {latlng, marker: marca(latlng, icono("square", ly.color, px, {text: n, double: open > 0}), px, title, popupProyectos(x), kb, -500)};
    });
  }
  return list.filter(s => s.details?.point).map(s => {
    const px = size(ly, s), latlng = [s.details.point[1], s.details.point[0]];
    return {latlng, marker: marca(latlng, icono(ly.shape, ly.color, px, {stroke: ly.stroke}), px, s.title,
                                  ly.id === "migracion" ? popupNoche(s) : popup(s), kb)};
  });
}

function savedLayers() {
  try { return JSON.parse(localStorage.getItem("estado-iba.capas")) || {}; } catch { return {}; }
}
function saveLayer(id, on) {
  try { localStorage.setItem("estado-iba.capas", JSON.stringify({...savedLayers(), [id]: on})); } catch { /* private mode */ }
}

async function mapaTodo(host, scope, label) {
  await Promise.all([munis(), shapes(), regionShapes()]);
  if (!host?.isConnected) return null;  // the reader moved on while the data loaded
  host.innerHTML = `<div class="mapa-todo"><div class="lienzo" role="region" aria-label="${esc(label)}"></div>
    <div class="capas"><h3>Capas</h3><ul></ul>
    <p class="meta">En gris, lo que ningún proyecto vigila aquí. Que no aparezca algo no significa que no ocurra.</p></div></div>`;
  const map = baseMap($(".lienzo", host), {scrollWheelZoom: scope.kind === "all"});

  const outlines = scope.kind === "all" ? REGIONS_GEO.features
    : scope.kind === "region" ? REGIONS_GEO.features.filter(f => f.properties.id === scope.id) : [];
  if (outlines.length) L.geoJSON({type: "FeatureCollection", features: outlines}, {interactive: false,
    style: {color: OUTLINE, weight: scope.kind === "all" ? .8 : 1.6, opacity: .5, dashArray: "4 4", fill: false}}).addTo(map);
  const inScope = new Set(scope.sites);
  const poly = L.geoJSON({type: "FeatureCollection", features: SHAPES.features.filter(f => inScope.has(f.properties.code))}, {
    style: {color: MAP_ACCENT, weight: scope.kind === "site" ? 2.2 : 1, fillColor: MAP_ACCENT, fillOpacity: scope.kind === "site" ? .16 : .1},
    onEachFeature: (f, l) => {
      l.bindTooltip(esc(f.properties.name), {sticky: true});
      if (scope.kind !== "site") l.on("click", () => { location.hash = "#/e/" + f.properties.code; });
    },
  }).addTo(map);

  const saved = savedLayers(), groups = {}, rows = [], pts = [];
  rows.push(`<li class="capa base"><span></span><svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><rect x="2" y="4" width="16" height="12"
    fill="${MAP_ACCENT}" fill-opacity=".25" stroke="${MAP_ACCENT}" stroke-width="1.5"/></svg><span class="nombre">${esc(D.kind)}</span>
    <span class="n">${num(scope.sites.length)}</span></li>`);
  for (const ly of LAYERS) {
    // Away from a municipality the map shows what touches a ZEPA, like the lists under it.
    const list = scope.signals.filter(s => ly.kinds.includes(s.kind)
      && (ly.id === "migracion" ? s.status !== "low" : scope.kind === "muni" || s.sites.length > 0));
    const c = cubre(ly, scope, list);
    const marks = c.on ? marcadores(ly, list, scope) : [];
    const on = marks.length > 0 && saved[ly.id] !== false;
    groups[ly.id] = L.layerGroup(marks.map(x => x.marker));
    if (on) groups[ly.id].addTo(map);
    pts.push(...marks.map(x => x.latlng));
    const open = ly.id === "proyectos" ? list.filter(isOpen).length : 0;
    const notes = [open ? `${open} con plazo abierto: borde doble` : "", c.on && !list.length ? "vigilado, sin novedades" : "", c.note || ""].filter(Boolean);
    rows.push(`<li class="capa${c.on ? "" : " no-cubre"}"><label>
      <input type="checkbox" data-capa="${ly.id}" ${on ? "checked" : ""} ${marks.length ? "" : "disabled"}>
      ${icono(ly.shape, ly.color, 18, {stroke: ly.stroke})}<span class="nombre">${esc(ly.name)}</span>
      <span class="n">${c.on ? num(list.length) : ""}</span>${notes.length ? `<small>${esc(notes.join(" · "))}</small>` : ""}</label></li>`);
  }
  $(".capas ul", host).innerHTML = rows.join("");
  host.querySelectorAll("input[data-capa]").forEach(i => i.addEventListener("change", () => {
    const g = groups[i.dataset.capa];
    if (i.checked) g.addTo(map); else map.removeLayer(g);
    saveLayer(i.dataset.capa, i.checked);
  }));

  let bounds = null, pad = {};
  if (scope.kind === "region") {
    const b = scope.bbox;
    bounds = L.latLngBounds([[b[1], b[0]], [b[3], b[2]]]);
    pad = {padding: [8, 8]};
  } else if (scope.kind !== "all") {
    bounds = L.latLngBounds(pts);
    if (poly.getLayers().length) bounds.extend(poly.getBounds());
    if (scope.point) bounds.extend([scope.point[1], scope.point[0]]);
    pad = {padding: [16, 16], maxZoom: 12};
  }
  // Framed without animation: an animated zoom waits for the next frame, which never comes in a
  // hidden tab. Built while hidden, the map measured 0×0, so it is framed again once it shows.
  const lienzo = $(".lienzo", host);
  let framed = false;
  const frame = () => {
    if (framed || !lienzo.clientWidth) return;
    framed = true;
    map.invalidateSize({animate: false});
    if (bounds?.isValid()) map.fitBounds(bounds, {...pad, animate: false});
  };
  frame();
  const ro = new ResizeObserver(() => {
    if (!lienzo.isConnected) return ro.disconnect();
    map.invalidateSize({animate: false});
    frame();
  });
  ro.observe(lienzo);
  return {map, poly};
}

/* ---------- Search ---------- */

function buscador() {
  return `<div class="buscador" role="search">
    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>
    <input id="q" type="search" autocomplete="off" placeholder="Busca un espacio, un municipio o una comunidad" aria-label="Busca un espacio, un municipio o una comunidad"
      aria-controls="resultados" aria-expanded="false">
    <ul class="resultados" id="resultados" role="listbox" hidden></ul></div>`;
}
async function munis() {
  if (!M) {
    const rows = await fetch("datos/municipios.json").then(r => r.json());
    M = rows.map(([ine, name, province, lon, lat, sites, region]) => ({ine, name, province, point: [lon, lat], sites, region, key: norm(name)}));
    M.byIne = Object.fromEntries(M.map(m => [m.ine, m]));
  }
  return M;
}
function wireSearch() {
  const q = $("#q"), out = $("#resultados");
  let sel = -1;
  q.addEventListener("focus", () => munis(), {once: true});
  q.addEventListener("input", async () => {
    const t = norm(q.value.trim());
    sel = -1;
    if (t.length < 2) { out.hidden = true; q.setAttribute("aria-expanded", "false"); return; }
    await munis();
    const score = k => k.startsWith(t) ? 0 : k.includes(" " + t) || k.includes("/" + t) ? 1 : k.includes(t) ? 2 : 9;
    const regs = D.regions.map(r => ({r, s: Math.min(score(norm(r.name)), score(norm(r.official)))})).filter(x => x.s < 9);
    const sites = D.sites.map(s => ({s, r: s.code.toLowerCase() === t ? -1 : score(norm(s.name))})).filter(x => x.r < 9);
    const ms = M.map(m => ({m, r: score(m.key)})).filter(x => x.r < 9);
    regs.sort((a, b) => a.s - b.s);
    sites.sort((a, b) => a.r - b.r || a.s.name.localeCompare(b.s.name, "es"));
    ms.sort((a, b) => a.r - b.r || a.m.name.length - b.m.name.length);
    const items = [
      ...regs.slice(0, 3).map(({r}) => `<li><a role="option" href="#/ca/${esc(r.id)}"><span class="tipo">Comunidad</span><span>${esc(r.name)}</span><span class="extra">${r.sites.length} ZEPA</span></a></li>`),
      ...sites.slice(0, 6).map(({s}) => `<li><a role="option" href="#/e/${esc(s.code)}"><span class="tipo">Espacio</span><span>${esc(s.name)}</span><span class="extra">${esc(s.code)}</span></a></li>`),
      ...ms.slice(0, 8).map(({m}) => `<li><a role="option" href="#/m/${esc(m.ine)}"><span class="tipo">Municipio</span><span>${esc(m.name)}</span><span class="extra">${esc(m.province || D.regionsById[m.region]?.name || "")}</span></a></li>`),
    ];
    out.innerHTML = items.join("") || `<li class="vacio" style="padding:8px 14px">Sin resultados.</li>`;
    out.hidden = false;
    q.setAttribute("aria-expanded", "true");
  });
  q.addEventListener("keydown", e => {
    const links = [...out.querySelectorAll("a")];
    if (!links.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + links.length) % links.length;
      links.forEach((a, i) => a.setAttribute("aria-selected", i === sel));
      links[sel].scrollIntoView({block: "nearest"});
    } else if (e.key === "Enter") {
      e.preventDefault();
      location.hash = (links[Math.max(sel, 0)]).getAttribute("href");
    } else if (e.key === "Escape") out.hidden = true;
  });
  document.addEventListener("click", e => { if (!e.target.closest(".buscador")) out.hidden = true; });
}

/* ---------- Community ---------- */

function tablaEspacios(sites) {
  return `<div class="ranking tabla"><table><thead><tr><th>Espacio</th><th class="n">Proyectos</th><th class="n">Por parcelas</th>
    <th class="n">Plazo abierto</th><th class="n">Ha quemadas</th></tr></thead><tbody>
    ${sites.map(s => `<tr><td><a href="#/e/${esc(s.code)}">${esc(s.name)}</a></td><td class="n">${num(s.n.notices)}</td><td class="n">${num(s.n.precise)}</td>
      <td class="n">${num(s.n.open)}</td><td class="n">${num(s.n.fire_ha, s.n.fire_ha ? 1 : 0)}</td></tr>`).join("")}</tbody></table></div>`;
}

function regionView(id) {
  const r = D.regionsById[id];
  if (!r) return notFound();
  document.title = `${r.name} · Estado de las IBA`;
  const list = (byRegion.get(id) || []).filter(s => s.sites.length).sort((a, b) => b.date.localeCompare(a.date));
  const open = list.filter(s => isOpen(s) && s.sites.length).sort((a, b) => a.deadline.localeCompare(b.deadline));
  const sites = r.sites.map(c => D.sitesByCode[c]).sort((a, b) => a.name.localeCompare(b.name, "es"));
  const land = sites.filter(s => !s.marine), sea = sites.filter(s => s.marine);
  const kind = ["18", "19"].includes(id) ? "Ciudad autónoma" : "Comunidad autónoma";
  $("#vista").innerHTML = `<div class="wrap">
    <nav class="migas"><a href="#/">Inicio</a> › Comunidad</nav>
    <div class="lugar-cab"><h2>${esc(r.name)}</h2>
      <span class="codigo">${kind}${r.official !== r.name ? " · " + esc(r.official) : ""} · ${sites.length} ZEPA · INE ${esc(id)}</span></div>
    <div id="mapa-host" class="mapa-host"></div>
    <div class="dos">
      <section class="bloque-home">
        ${open.length ? `<div class="actuar"><h3>Puedes alegar</h3>
          <p>${open.length === 1 ? "Un proyecto que toca una ZEPA de la comunidad admite alegaciones" : `${open.length} proyectos que tocan ZEPA de la comunidad admiten alegaciones`}.</p>
          <ul class="lista">${open.map(x => plazoItem(x)).join("")}</ul></div>` : `<h2 class="sec">Plazos abiertos</h2><p class="vacio">Ningún plazo abierto hoy.</p>`}
      </section>
      <section class="bloque-home">
        <h2 class="sec">Esta semana</h2>
        <p class="sec-sub">Lo nuevo en los últimos 7 días en sus espacios.</p>
        ${semana(list)}
      </section>
    </div>
    <section class="bloque-home">
      <h2 class="sec">Sus espacios</h2>
      <p class="sec-sub">Las ZEPA que tocan algún municipio de ${esc(r.name)}. Las que comparte con otra comunidad salen en las dos.</p>
      ${land.length ? tablaEspacios(land) : `<p class="vacio">Ninguna ZEPA toca tierra aquí.</p>`}
      ${sea.length ? `<h3 class="mes">En el mar o en islotes</h3>
        <p class="sec-sub">No tocan ningún término municipal del IGN; van con la comunidad de la costa más cercana.</p>${tablaEspacios(sea)}` : ""}
    </section>
    <div class="lugar">
      <div>${hilo(list)}</div>
      <aside><div class="panel rss"><h3>Recibe los avisos</h3>
        <p style="margin:0 0 6px">Cada novedad en los espacios y municipios de ${esc(r.name)}, en tu lector de noticias:</p>
        <a href="rss/ca-${esc(id)}.xml">rss/ca-${esc(id)}.xml</a></div></aside>
    </div></div>`;
  window.scrollTo(0, 0);
  mapaTodo($("#mapa-host"), scopeRegion(r), `Mapa de ${r.name}`);
}

/* ---------- Site ---------- */

function timeline(list, code, empty = "Ningún registro todavía en los proyectos que vigilan este espacio.") {
  if (!list.length) return `<p class="vacio">${esc(empty)}</p>`;
  let html = "", month = "";
  for (const s of list) {
    const m = s.date.slice(0, 7);
    if (m !== month) { html += `${month ? "</ul>" : ""}<h3 class="mes">${esc(mesDe(s.date))}</h3><ul class="lista">`; month = m; }
    html += signalItem(s, code);
  }
  return html + "</ul>";
}
function signalItem(s, code) {
  const d = s.details || {};
  const extra = [];
  if (s.kind === "notice") extra.push(s.deadline ? (s.deadline >= D.today ? `alegaciones hasta el ${fecha(s.deadline)}` : `plazo cerrado el ${fecha(s.deadline)}`) : "sin plazo conocido");
  if (s.status && s.kind !== "notice") extra.push(esc(s.status));
  if (d.promoter) extra.push(esc(d.promoter));
  if (d.permit) extra.push(esc(d.permit));
  if (PRECISION[s.precision] && s.kind !== "wetland_water") extra.push(PRECISION[s.precision]);
  const fotos = d.before && d.after ? `<div class="fotos">
      <figure><img loading="lazy" src="${esc(d.before)}" alt="Antes"><figcaption>antes · ${fecha(d.before_date)}</figcaption></figure>
      <figure><img loading="lazy" src="${esc(d.after)}" alt="Después"><figcaption>después · ${fecha(d.after_date)}</figcaption></figure></div>` : "";
  const means = MEANS[s.kind] ? `<details class="significa"><summary>¿Qué significa?</summary><p>${esc(MEANS[s.kind])}${s.precision === "municipio" ? " " + esc(PREC_NOTE.municipio) : ""}</p></details>` : "";
  return `<li class="item ${isOpen(s) ? "urgente" : ""}">
    <div class="t">${tag(s)}<a href="${esc(s.url)}">${esc(s.title)}</a></div>
    <div class="meta">${fecha(s.date)}${code ? siteHa(s, code) : ""}${value(s)} · ${extra.join(" · ")}</div>${fotos}${means}</li>`;
}
function hilo(list) {
  const chains = list.filter(s => s.kind === "notice" && D.chains?.[s.id]).flatMap(s => D.chains[s.id].map(c => ({s, c})));
  if (!chains.length) return "";
  return `<div class="panel"><h3>Quién está detrás</h3><ul class="hilo">${chains.map(({s, c}) => `<li>
    <div class="cadena">${c.links.map(l => `<span>${l.url ? `<a href="${esc(l.url)}">${esc(l.name)}</a>` : esc(l.name)}${l.via === "por el grupo" ? ` <small class="meta">(por el grupo)</small>` : ""}</span>`).join("")}</div>
    <span class="meta">${esc(s.title.slice(0, 90))}…</span></li>`).join("")}</ul></div>`;
}
function siteView(code) {
  const s = D.sitesByCode[code];
  if (!s) return notFound();
  document.title = `${s.name} · Estado de las IBA`;
  const list = (bySite.get(code) || []).slice().sort((a, b) => b.date.localeCompare(a.date));
  const open = list.filter(isOpen).sort((a, b) => a.deadline.localeCompare(b.deadline));
  $("#vista").innerHTML = `<div class="wrap">
    <nav class="migas"><a href="#/">Inicio</a> › ${regionLinks(s.regions)} › Espacio</nav>
    <div class="lugar-cab"><h2>${esc(s.name)}</h2>
      <span class="codigo">${esc(s.code)} · ${esc(D.kind)} de la Red Natura 2000${s.marine ? " · en el mar o en islotes" : ""}</span>
      ${s.munis.length ? `<ul class="municipios" aria-label="Municipios">${s.munis.map(([ine, name]) => `<li><a href="#/m/${esc(ine)}">${esc(name)}</a></li>`).join("")}</ul>` : ""}
    </div>
    <div id="mapa-host" class="mapa-host"></div>
    <div class="lugar">
      <div>
        ${open.length ? `<div class="actuar"><h3>Puedes alegar</h3>
          <p>${open.length === 1 ? "Un proyecto que toca este espacio admite alegaciones" : `${open.length} proyectos que tocan este espacio admiten alegaciones`}. Cualquier persona o entidad puede presentarlas.</p>
          <ul class="lista">${open.map(x => plazoItem(x, code)).join("")}</ul></div>` : ""}
        <section class="cronologia"><h2 class="sec">Qué ha pasado</h2>${timeline(list, code)}</section>
      </div>
      <aside>
        ${hilo(list)}
        <div class="panel rss"><h3>Recibe los avisos</h3>
          <p style="margin:0 0 6px">Suscríbete con tu lector de noticias para enterarte de cada novedad en este espacio:</p>
          <a href="rss/${esc(code)}.xml">rss/${esc(code)}.xml</a></div>
      </aside>
    </div></div>`;
  window.scrollTo(0, 0);
  mapaTodo($("#mapa-host"), scopeSite(s), `Mapa de ${s.name}`);
}

/* ---------- Municipality ---------- */

async function muniView(ine) {
  await munis();
  const m = M.byIne[ine];
  if (!m) return notFound();
  document.title = `${m.name} · Estado de las IBA`;
  const list = (byMuni.get(ine) || []).slice().sort((a, b) => b.date.localeCompare(a.date));
  const open = list.filter(isOpen).sort((a, b) => a.deadline.localeCompare(b.deadline));
  const sites = m.sites.map(c => D.sitesByCode[c]).filter(Boolean);
  $("#vista").innerHTML = `<div class="wrap">
    <nav class="migas"><a href="#/">Inicio</a> › ${m.region ? regionLinks([m.region]) + " › " : ""}Municipio</nav>
    <div class="lugar-cab"><h2>${esc(m.name)}</h2><span class="codigo">${esc(m.province || "Sin provincia: tierra en común de varios municipios")} · INE ${esc(ine)}</span></div>
    <div id="mapa-host" class="mapa-host"></div>
    <div class="lugar">
      <div>
        ${open.length ? `<div class="actuar"><h3>Puedes alegar</h3>
          <p>${open.length === 1 ? "Un proyecto en este municipio admite alegaciones" : `${open.length} proyectos en este municipio admiten alegaciones`}.</p>
          <ul class="lista">${open.map(x => plazoItem(x)).join("")}</ul></div>` : ""}
        <section class="cronologia"><h2 class="sec">Lo que nombra a ${esc(m.name)}</h2>${timeline(list, null, "Ningún anuncio, incendio ni alerta vigilados nombra este municipio todavía.")}</section>
      </div>
      <aside>
        <div class="panel"><h3>Espacios en el municipio</h3>
        ${sites.length ? `<ul class="lista">${sites.map(s => `<li class="item"><div class="t"><a href="#/e/${esc(s.code)}">${esc(s.name)}</a></div>
          <div class="meta">${resumen(s.n)}</div></li>`).join("")}</ul>`
          : `<p class="vacio">Ninguna ZEPA entra en este municipio.</p>`}</div>
      </aside>
    </div></div>`;
  window.scrollTo(0, 0);
  mapaTodo($("#mapa-host"), scopeMuni(m), `Mapa de ${m.name}`);
}

function resumen(n) {
  const parts = [`${n.notices} ${n.notices === 1 ? "proyecto" : "proyectos"}`];
  if (n.open) parts.push(`${n.open} con plazo abierto`);
  if (n.fire_ha) parts.push(`${num(n.fire_ha, 1)} ha quemadas`);
  if (n.land) parts.push(`${n.land} ${n.land === 1 ? "cambio de uso" : "cambios de uso"}`);
  return parts.join(" · ");
}

function notFound() {
  $("#vista").innerHTML = `<div class="wrap"><nav class="migas"><a href="#/">Inicio</a></nav><p class="vacio">No encuentro ese lugar.</p></div>`;
}

/* ---------- Router ---------- */

function route() {
  for (const m of MAPS) m.remove();
  MAPS = [];
  capa = null;
  const h = location.hash.replace(/^#\/?/, "");
  const [kind, id] = h.split("/");
  document.body.classList.toggle("en-lugar", Boolean(kind));  // away from home the header shrinks to its title
  if (kind === "e" && id) return siteView(decodeURIComponent(id));
  if (kind === "m" && id) return muniView(decodeURIComponent(id));
  if (kind === "ca" && id) return regionView(decodeURIComponent(id));
  if (kind === "plazos") return plazos();
  if (/^ES[0-9A-Z]{7}$/.test(h)) { location.replace("#/e/" + h); return; }  // old v1 anchors
  home();
}

const push = (map, key, s) => { if (!map.has(key)) map.set(key, []); map.get(key).push(s); };
fetch("datos/hub.json").then(r => r.json()).then(data => {
  D = data;
  D.sitesByCode = Object.fromEntries(D.sites.map(s => [s.code, s]));
  D.regionsById = Object.fromEntries(D.regions.map(r => [r.id, r]));
  for (const s of D.signals) {
    for (const x of s.sites) push(bySite, x.code, s);
    for (const c of s.municipalities) push(byMuni, c, s);
    for (const r of s.regions || []) push(byRegion, r, s);
  }
  window.addEventListener("hashchange", route);
  route();
});
