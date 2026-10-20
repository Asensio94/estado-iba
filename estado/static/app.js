"use strict";
// Estado de las IBA: one page, six views (home, community, site, municipality, deadlines, signal) routed by the URL hash.
// The same script serves every country: estado/i18n.py writes the page's strings and settings into it
// as window.I18N and window.PAGE, and the data (hub.json and the rest) is the same whatever the language.

const T = window.I18N, PAGE = window.PAGE;
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const num = (x, d = 0) => x == null ? "—" : Number(x).toLocaleString(PAGE.locale, {minimumFractionDigits: d, maximumFractionDigits: d});
const fecha = s => s ? new Date(s.slice(0, 10) + "T12:00:00").toLocaleDateString(PAGE.locale, {day: "numeric", month: "short", year: "numeric"}) : "";
const mesDe = s => new Date(s.slice(0, 7) + "-15T12:00:00").toLocaleDateString(PAGE.locale, {month: "long", year: "numeric"});
const norm = s => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const corta = (t, n) => t.length > n ? t.slice(0, n - 1) + "…" : t;
const byName = (a, b) => a.localeCompare(b, PAGE.lang);
// A string of the page's language, with {placeholders} filled in; tn picks the singular form (key_1) for one.
const t = (k, v = {}) => String(T[k] ?? k).replace(/\{(\w+)\}/g, (_, x) => v[x] ?? "");
const tn = (k, n, v = {}) => t(n === 1 && T[k + "_1"] != null ? k + "_1" : k, {n: num(n), ...v});
const pct_ = (n, d = 0) => t("pct", {n: num(n, d)});

const KIND = T.kinds, PRECISION = T.precision, MEANS = T.means, PREC_NOTE = T.prec_note, LEVEL = T.level;
const STATUS = s => esc(T.status[s.status] || s.status);

/* Map layers: one per sibling. Colours were checked for colour-blind separation against the OSM
   tiles; each layer also has its own shape, so colour is never the only cue. The tiles stay light
   in dark mode, so the marks keep a fixed dark outline instead of following the theme. */
const OUTLINE = "#221d1a", MAP_ACCENT = "#a3336e";
const LAYERS = [
  {id: "proyectos", color: "#a3336e", shape: "square", source: "observatorio-alegaciones", kinds: ["notice"]},
  {id: "fuego", color: "#eb6834", shape: "triangle", source: "vigia-incendios", kinds: ["fire"]},
  {id: "suelo", color: "#1baf7a", shape: "diamond", source: "centinela-natura", kinds: ["land_change"]},
  {id: "humedales", color: "#2a78d6", shape: "circle", source: "vigilancia-humedales", kinds: ["wetland_water"]},
  {id: "rios", color: "#2a78d6", shape: "ring", source: "caudal-ecologico", kinds: ["river_flow"]},
  {id: "tendidos", color: "#4a3aa7", shape: "plus", source: "riesgo-tendidos-aves", kinds: ["power_line"]},
  {id: "luz", color: "#e3b505", shape: "sun", source: "black-marble", kinds: ["night_light"]},
  {id: "migracion", color: OUTLINE, stroke: "#fff", shape: "star", source: "sub-nocte", kinds: ["migration"]},
  {id: "depuracion", color: "#7a5230", shape: "drop", source: "depuracion-y-bano", kinds: ["wastewater", "bathing_water"]},
].map(ly => ({...ly, name: T.layers[ly.id]}));
// The light layer is the one pale fill: it sits outside the lightness band of the others, so it
// leans on the dark outline every mark has, and on its own shape, a sun.
const SUN = Array.from({length: 16}, (_, i) => {
  const a = i * 22.5 * Math.PI / 180, r = i % 2 ? 5.6 : 9;
  return `${(10 + r * Math.cos(a)).toFixed(2)},${(10 + r * Math.sin(a)).toFixed(2)}`;
}).join(" ");
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
  sun: `<polygon points="${SUN}"/>`,
  drop: `<path d="M10 1.5C7.5 5 3.5 9.3 3.5 12.5a6.5 6.5 0 0 0 13 0C16.5 9.3 12.5 5 10 1.5Z"/>`,
};

let D, M, SHAPES, REGIONS_GEO, capa, MAPS = [];
const bySite = new Map(), byMuni = new Map(), byRegion = new Map();

function daysLeft(deadline) {
  return Math.round((new Date(deadline + "T12:00:00") - new Date(D.today + "T12:00:00")) / 864e5);
}
function dias(deadline) {
  const n = daysLeft(deadline);
  return n === 0 ? t("last_day") : tn("days_left", n);
}
const isOpen = s => s.deadline && s.deadline >= D.today && s.kind === "notice";
const siteName = c => D.sitesByCode[c]?.name || c;
const weekAgo = () => new Date(new Date(D.today + "T12:00:00") - 7 * 864e5).toISOString().slice(0, 10);
const aviso = s => `#/a/${encodeURIComponent(s.source)}/${encodeURIComponent(s.id)}`;
const regionLinks = ids => ids.map(id => D.regionsById[id]).filter(Boolean)
  .map(r => `<a href="#/ca/${esc(r.id)}">${esc(r.name)}</a>`).join(" · ");

function tag(s) {
  const k = KIND[s.kind] || {tag: s.kind};
  return `<span class="tag">${esc(k.tag)}</span>`;
}
function precTag(s) {
  return s.precision === "municipio" ? `<span class="tag prec-municipio" title="${esc(PREC_NOTE.municipio)}">${esc(t("by_muni"))}</span>` : "";
}
function value(s) {
  if (!s.value || s.value.amount == null) return "";
  const a = s.value.amount;
  return ` · ${num(a, a < 10 ? 1 : 0)} ${esc(T.units[s.value.unit] || s.value.unit)}${s.kind === "night_light" ? " " + t("more_than_expected") : ""}`;
}
function siteHa(s, code) {
  const x = (s.sites || []).find(z => z.code === code);
  return x && x.ha != null ? ` · ${t("ha_inside", {ha: num(x.ha, x.ha < 10 ? 1 : 0)})}` : "";
}

/* ---------- Home ---------- */

function home() {
  document.title = T.title;
  const open = D.signals.filter(s => isOpen(s) && s.sites.length)
    .sort((a, b) => a.deadline.localeCompare(b.deadline) || (a.precision === "parcelas" ? -1 : 1));

  $("#vista").innerHTML = `
  <div class="wrap">
    ${buscador()}
    <p class="ejemplos">${T.examples}</p>
    <section class="bloque-home">
      <h2 class="sec">${t("h_map")}</h2>
      <p class="sec-sub">${t("map_sub")}</p>
      <div class="controles"><label>${t("color_by")} <select id="indicador">
        ${Object.entries(T.indicators).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("\n        ")}
      </select></label></div>
      <div id="mapa-host" class="mapa-host grande"></div>
      <div class="leyenda" id="leyenda"></div>
    </section>
    <section class="bloque-home">
      <h2 class="sec">${t("h_regions")}</h2>
      <p class="sec-sub">${t("regions_sub", {kind: D.kind})}</p>
      ${comunidades()}
    </section>
    <div class="dos">
      <section class="bloque-home">
        <h2 class="sec">${t("h_deadlines")}</h2>
        <p class="sec-sub">${t("deadlines_sub", {kind: D.kind})}</p>
        <ul class="lista">${open.slice(0, 7).map(s => plazoItem(s)).join("") || `<li class="vacio">${t("no_deadline")}</li>`}</ul>
        ${open.length > 7 ? `<a class="ver-mas" href="#/plazos">${t("see_deadlines", {n: open.length})}</a>` : ""}
      </section>
      <section class="bloque-home">
        ${noche()}
        <h2 class="sec">${t("h_week")}</h2>
        <p class="sec-sub">${t("week_sub")}</p>
        ${semana(D.signals)}
      </section>
    </div>
    <section class="bloque-home">
      <h2 class="sec">${t("h_ranking")}</h2>
      <p class="sec-sub" id="ranking-sub"></p>
      <div class="ranking" id="ranking"></div>
    </section>
  </div>`;
  wireSearch();
  const sel = $("#indicador");
  sel.addEventListener("input", () => { paintHome(sel.value); ranking(sel.value); });
  mapaTodo($("#mapa-host"), scopeAll(), t("map_all_label", {kind: D.kind}))
    .then(r => { if (r) { capa = r.poly; paintHome(sel.value); } });
  ranking(sel.value);
}

function comunidades() {
  const week = weekAgo();
  // «none open» only where someone watches the consultations; elsewhere it would claim what no one checked
  const consults = !D.sources["observatorio-alegaciones"]?.coverage.absent;
  return `<ul class="comunidades">${D.regions.slice().sort((a, b) => byName(a.name, b.name)).map(r => {
    const sig = byRegion.get(r.id) || [];
    const open = sig.filter(s => isOpen(s) && s.sites.length).length;
    const nuevo = sig.filter(s => s.date >= week && s.sites.length && !["wetland_water", "migration"].includes(s.kind)).length;
    return `<li><a href="#/ca/${esc(r.id)}"><b>${esc(r.name)}</b><span class="meta">${r.sites.length} ${esc(D.kind)}</span>
      ${consults ? `<span class="meta">${open ? `<span class="dias">${tn("n_open", open)}</span>` : t("none_open")}</span>` : ""}
      <span class="meta">${nuevo ? tn("n_new_week", nuevo) : t("nothing_new_week")}</span></a></li>`;
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
    ${list.length > 4 ? `<p class="meta">${t("and_more", {n: list.length - 4})}</p>` : ""}</div>`).join("") || `<p class="vacio">${t("nothing_new")}</p>`;
}

function noche() {
  const m = D.signals.filter(s => s.kind === "migration" && s.status !== "low");
  if (!m.length) return "";
  const night = m[0].date;
  const order = {"very high": 0, high: 1, moderate: 2};
  m.sort((a, b) => order[a.status] - order[b.status] || byName(a.details.city, b.details.city));
  return `<div class="panel" style="margin-bottom:22px"><h3>${t("h_tonight")}</h3>
    <p class="meta" style="margin:0 0 6px">${fecha(night)} · ${t("according_to")} <a href="${esc(D.sources["sub-nocte"].url)}">Sub Nocte</a></p>
    <p style="margin:0;font-size:15px">${m.map(s => `${s.municipalities[0] ? `<a href="#/m/${esc(s.municipalities[0])}">${esc(s.details.city)}</a>` : esc(s.details.city)}: <b>${LEVEL[s.status] || STATUS(s)}</b>`).join(" · ")}</p></div>`;
}

function plazoItem(s, code) {
  const sites = s.sites.map(x => `<a href="#/e/${esc(x.code)}">${esc(siteName(x.code))}</a>`).join(", ");
  return `<li class="item ${daysLeft(s.deadline) <= 7 ? "urgente" : ""}">
    <div class="meta"><span class="dias">${dias(s.deadline)}</span> · ${t("until", {date: fecha(s.deadline)})} ${precTag(s)}</div>
    <div class="t"><a href="${aviso(s)}">${esc(s.title)}</a></div>
    <div class="meta">${code ? "" : sites + " · "}${fecha(s.date)}${value(s)}${s.details.promoter ? " · " + esc(s.details.promoter) : ""}</div></li>`;
}
function feedItem(s) {
  const sites = s.sites.slice(0, 3).map(x => `<a href="#/e/${esc(x.code)}">${esc(siteName(x.code))}</a>`).join(", ") + (s.sites.length > 3 ? " " + t("and_more", {n: s.sites.length - 3}) : "");
  return `<li class="item"><div class="t">${tag(s)}<a href="${aviso(s)}">${esc(s.title)}</a></div>
    <div class="meta">${sites} · ${fecha(s.date)}${value(s)} ${precTag(s)}</div></li>`;
}

const IND = {
  precise: {f: n => n.precise},
  open: {f: n => n.open},
  notices: {f: n => n.notices},
  fire_ha: {f: n => n.fire_ha},
  land: {f: n => n.land || 0},
  light: {f: n => n.light || 0},
};
for (const k in IND) IND[k].label = T.indicator_labels[k];

function ranking(key) {
  const f = IND[key].f;
  const rows = D.sites.filter(s => f(s.n) > 0).sort((a, b) => f(b.n) - f(a.n) || byName(a.name, b.name));
  $("#ranking-sub").textContent = t("ranking_sub", {kind: D.kind, label: IND[key].label});
  $("#ranking").innerHTML = `<table><thead><tr><th>${t("th_site")}</th><th>${t("th_region")}</th><th class="n">${esc(IND[key].label)}</th></tr></thead><tbody>
    ${rows.map(s => `<tr><td><a href="#/e/${esc(s.code)}">${esc(s.name)}</a></td><td class="meta">${regionLinks(s.regions)}</td><td class="n">${num(f(s.n), key === "fire_ha" ? 1 : 0)}</td></tr>`).join("")
      || `<tr><td colspan="3" class="vacio">${t("no_site")}</td></tr>`}</tbody></table>`;
}

function paintHome(key) {
  if (!capa) return;
  const f = IND[key].f;
  const max = Math.max(1, ...D.sites.map(s => f(s.n)));
  capa.eachLayer(l => {
    const v = f(D.sitesByCode[l.feature.properties.code]?.n || {}) || 0;
    l.setStyle({color: MAP_ACCENT, weight: v ? 1.2 : .6, fillColor: MAP_ACCENT, fillOpacity: .03 + .62 * Math.sqrt(v / max)});
  });
  $("#leyenda").innerHTML = `<span><i style="opacity:.15"></i>${t("legend_none", {kind: D.kind})}</span><span><i style="opacity:.65"></i>${t("legend_max")}: ${num(max, key === "fire_ha" ? 1 : 0)} ${esc(IND[key].label)}</span>`;
}

function plazos() {
  document.title = `${t("h_deadlines")} · ${T.title}`;
  const open = D.signals.filter(s => isOpen(s) && s.sites.length).sort((a, b) => a.deadline.localeCompare(b.deadline));
  $("#vista").innerHTML = `<div class="wrap">
    <nav class="migas"><a href="#/">${t("home")}</a> › ${t("h_deadlines")}</nav>
    <div class="lugar-cab"><h2>${t("h_deadlines")}</h2></div>
    <p class="sec-sub">${t("deadlines_page_sub", {n: open.length, kind: D.kind})}</p>
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
  const m = L.map(el, {zoomSnap: .5, ...opts}).setView(PAGE.center, PAGE.zoom);
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
// does not, so an empty layer never reads as «nothing happens here». A sibling that does not watch
// this country at all says so in its coverage (absent).
function cubre(ly, scope, list) {
  const src = D.sources[ly.source];
  if (!src || src.coverage.failed) return {on: false, note: t("no_data_today")};
  if (src.coverage.absent) return {on: false, note: src.coverage.label};
  const away = {on: false, note: `${t("not_covered")} · ${src.coverage.label}`};
  if (ly.id === "migracion") {
    if (scope.kind === "site") return {on: false, note: t("by_city")};
    return scope.kind === "all" || list.length ? {on: true} : away;
  }
  const cov = src.coverage.sites;
  if (cov == null) return {on: true};
  if (scope.kind === "all") return {on: true, note: src.coverage.label};
  return scope.sites.some(c => cov.includes(c)) ? {on: true} : away;
}

function marca(latlng, html, size, title, pop, keyboard, zIndexOffset = 0) {
  return L.marker(latlng, {
    icon: L.divIcon({className: "marca", html, iconSize: [size, size], iconAnchor: [size / 2, size / 2], popupAnchor: [0, -size / 2]}),
    title, alt: title, keyboard, zIndexOffset, riseOnHover: true,
  }).bindPopup(pop, {maxWidth: 320});
}
function popup(s) {
  const sites = s.sites.slice(0, 3).map(x => `<a href="#/e/${esc(x.code)}">${esc(siteName(x.code))}</a>`).join(", ");
  const status = s.status && !["notice", "migration"].includes(s.kind) ? " · " + STATUS(s) : "";
  return `<div class="pop">${tag(s)}<a href="${aviso(s)}">${esc(s.title)}</a>
    <div class="meta">${fecha(s.date)}${value(s)}${status}${sites ? " · " + sites : ""}</div></div>`;
}
function popupNoche(s) {
  const ine = s.municipalities[0];
  return `<div class="pop">${tag(s)}${ine ? `<a href="#/m/${esc(ine)}">${esc(s.details.city)}</a>` : esc(s.details.city)}: <b>${LEVEL[s.status] || STATUS(s)}</b>
    <div class="meta">${t("night_of", {date: fecha(s.date)})} · ${t("according_to")} <a href="${esc(s.url)}">Sub Nocte</a></div></div>`;
}
function popupProyectos(x) {
  const list = x.list.slice().sort((a, b) => (isOpen(b) - isOpen(a)) || b.date.localeCompare(a.date));
  const n = list.length;
  return `<div class="pop"><b><a href="${esc(x.href)}">${esc(x.name)}</a></b> · ${tn("n_projects", n)}
    <ul>${list.slice(0, 6).map(s => `<li>${isOpen(s) ? `<span class="dias">${dias(s.deadline)}</span> ` : ""}<a href="${aviso(s)}">${esc(corta(s.title, 110))}</a>
      <span class="meta">${fecha(s.date)}${s.precision === "municipio" ? " · " + t("by_muni") : ""}</span></li>`).join("")}</ul>
    ${n > 6 ? `<a href="${esc(x.href)}">${t("and_more", {n: n - 6})}</a>` : ""}</div>`;
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
      const title = `${x.name}: ${tn("n_projects", n)}${open ? `, ${t("n_with_deadline", {n: open})}` : ""}`;
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
    <div class="capas"><h3>${t("h_layers")}</h3><ul></ul>
    <p class="meta">${t("layers_note")}</p></div></div>`;
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
    const notes = [open ? `${t("n_with_deadline", {n: open})}: ${t("double_border")}` : "", c.on && !list.length ? t("watched_nothing") : "", c.note || ""].filter(Boolean);
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
    <input id="q" type="search" autocomplete="off" placeholder="${esc(t("search"))}" aria-label="${esc(t("search"))}"
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
    const term = norm(q.value.trim());
    sel = -1;
    if (term.length < 2) { out.hidden = true; q.setAttribute("aria-expanded", "false"); return; }
    await munis();
    const score = k => k.startsWith(term) ? 0 : k.includes(" " + term) || k.includes("/" + term) || k.includes("-" + term) ? 1 : k.includes(term) ? 2 : 9;
    const regs = D.regions.map(r => ({r, s: Math.min(score(norm(r.name)), score(norm(r.official)))})).filter(x => x.s < 9);
    const sites = D.sites.map(s => ({s, r: s.code.toLowerCase() === term ? -1 : score(norm(s.name))})).filter(x => x.r < 9);
    const ms = M.map(m => ({m, r: score(m.key)})).filter(x => x.r < 9);
    regs.sort((a, b) => a.s - b.s);
    sites.sort((a, b) => a.r - b.r || byName(a.s.name, b.s.name));
    ms.sort((a, b) => a.r - b.r || a.m.name.length - b.m.name.length);
    const items = [
      ...regs.slice(0, 3).map(({r}) => `<li><a role="option" href="#/ca/${esc(r.id)}"><span class="tipo">${t("t_region")}</span><span>${esc(r.name)}</span><span class="extra">${r.sites.length} ${esc(D.kind)}</span></a></li>`),
      ...sites.slice(0, 6).map(({s}) => `<li><a role="option" href="#/e/${esc(s.code)}"><span class="tipo">${t("th_site")}</span><span>${esc(s.name)}</span><span class="extra">${esc(s.code)}</span></a></li>`),
      ...ms.slice(0, 8).map(({m}) => `<li><a role="option" href="#/m/${esc(m.ine)}"><span class="tipo">${t("t_muni")}</span><span>${esc(m.name)}</span><span class="extra">${esc(m.province || D.regionsById[m.region]?.name || "")}</span></a></li>`),
    ];
    out.innerHTML = items.join("") || `<li class="vacio" style="padding:8px 14px">${t("no_results")}</li>`;
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
  return `<div class="ranking tabla"><table><thead><tr><th>${t("th_site")}</th><th class="n">${t("th_projects")}</th><th class="n">${t("th_parcels")}</th>
    <th class="n">${t("th_open")}</th><th class="n">${t("th_burnt")}</th></tr></thead><tbody>
    ${sites.map(s => `<tr><td><a href="#/e/${esc(s.code)}">${esc(s.name)}</a></td><td class="n">${num(s.n.notices)}</td><td class="n">${num(s.n.precise)}</td>
      <td class="n">${num(s.n.open)}</td><td class="n">${num(s.n.fire_ha, s.n.fire_ha ? 1 : 0)}</td></tr>`).join("")}</tbody></table></div>`;
}

function regionView(id) {
  const r = D.regionsById[id];
  if (!r) return notFound();
  document.title = `${r.name} · ${T.title}`;
  const list = (byRegion.get(id) || []).filter(s => s.sites.length).sort((a, b) => b.date.localeCompare(a.date));
  const open = list.filter(s => isOpen(s) && s.sites.length).sort((a, b) => a.deadline.localeCompare(b.deadline));
  const sites = r.sites.map(c => D.sitesByCode[c]).sort((a, b) => byName(a.name, b.name));
  const land = sites.filter(s => !s.marine), sea = sites.filter(s => s.marine);
  const kind = (T.region_kinds || {})[id] || t("region_kind");
  $("#vista").innerHTML = `<div class="wrap">
    <nav class="migas"><a href="#/">${t("home")}</a> › ${t("t_region")}</nav>
    <div class="lugar-cab"><h2>${esc(r.name)}</h2>
      <span class="codigo">${kind}${r.official !== r.name ? " · " + esc(r.official) : ""} · ${sites.length} ${esc(D.kind)} · ${t("code_office")} ${esc(id)}</span></div>
    <div id="mapa-host" class="mapa-host"></div>
    <div class="dos">
      <section class="bloque-home">
        ${open.length ? `<div class="actuar"><h3>${t("h_act")}</h3>
          <p>${tn("act_region", open.length, {kind: D.kind})}.</p>
          <ul class="lista">${open.map(x => plazoItem(x)).join("")}</ul></div>` : `<h2 class="sec">${t("h_deadlines")}</h2><p class="vacio">${t("no_deadline")}</p>`}
      </section>
      <section class="bloque-home">
        <h2 class="sec">${t("h_week")}</h2>
        <p class="sec-sub">${t("week_sub_region")}</p>
        ${semana(list)}
      </section>
    </div>
    <section class="bloque-home">
      <h2 class="sec">${t("h_its_sites")}</h2>
      <p class="sec-sub">${t("its_sites_sub", {kind: D.kind, name: esc(r.name)})}</p>
      ${land.length ? tablaEspacios(land) : `<p class="vacio">${t("no_land_site", {kind: D.kind})}</p>`}
      ${sea.length ? `<h3 class="mes">${t("h_sea")}</h3>
        <p class="sec-sub">${t("sea_sub")}</p>${tablaEspacios(sea)}` : ""}
    </section>
    <div class="lugar">
      <div>${hilo(list)}</div>
      <aside><div class="panel rss"><h3>${t("h_rss")}</h3>
        <p style="margin:0 0 6px">${t("rss_region", {name: esc(r.name)})}</p>
        <a href="rss/ca-${esc(id)}.xml">rss/ca-${esc(id)}.xml</a></div></aside>
    </div></div>`;
  window.scrollTo(0, 0);
  mapaTodo($("#mapa-host"), scopeRegion(r), t("map_of", {name: r.name}));
}

/* ---------- Site ---------- */

function timeline(list, code, empty = t("timeline_empty")) {
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
  if (s.kind === "notice") extra.push(s.deadline ? (s.deadline >= D.today ? t("comments_until", {date: fecha(s.deadline)}) : t("closed_on", {date: fecha(s.deadline)})) : t("no_known_deadline"));
  if (s.status && s.kind !== "notice") extra.push(STATUS(s));
  if (d.promoter) extra.push(esc(d.promoter));
  if (d.permit) extra.push(esc(d.permit));
  if (s.kind === "night_light") extra.push(t("light_line", {now: num(d.radiance, 2), before: num(d.baseline, 2), expected: num(d.expected, 2)}));
  else if (PRECISION[s.precision] && !["wetland_water", "flood_building", "wastewater", "bathing_water"].includes(s.kind)) extra.push(PRECISION[s.precision]);
  const fotos = d.before && d.after ? `<div class="fotos">
      <figure><img loading="lazy" src="${esc(d.before)}" alt="${esc(t("Before"))}"><figcaption>${t("before")} · ${fecha(d.before_date)}</figcaption></figure>
      <figure><img loading="lazy" src="${esc(d.after)}" alt="${esc(t("After"))}"><figcaption>${t("after")} · ${fecha(d.after_date)}</figcaption></figure></div>` : "";
  const means = MEANS[s.kind] ? `<details class="significa"><summary>${t("what_means")}</summary><p>${esc(MEANS[s.kind])}${s.precision === "municipio" && s.kind !== "flood_building" ? " " + esc(PREC_NOTE.municipio) : ""}</p></details>` : "";
  return `<li class="item ${isOpen(s) ? "urgente" : ""}">
    <div class="t">${tag(s)}<a href="${aviso(s)}">${esc(s.title)}</a></div>
    <div class="meta">${fecha(s.date)}${code ? siteHa(s, code) : ""}${value(s)} · ${extra.join(" · ")}</div>${fotos}${means}</li>`;
}
function hilo(list) {
  const chains = list.filter(s => s.kind === "notice" && D.chains?.[s.id]).flatMap(s => D.chains[s.id].map(c => ({s, c})));
  if (!chains.length) return "";
  return `<div class="panel"><h3>${t("h_behind")}</h3><ul class="hilo">${chains.map(({s, c}) => `<li>
    <div class="cadena">${c.links.map(l => `<span>${l.url ? `<a href="${esc(l.url)}">${esc(l.name)}</a>` : esc(l.name)}${l.via === "por el grupo" ? ` <small class="meta">(${t("via_group")})</small>` : ""}</span>`).join("")}</div>
    <span class="meta">${esc(s.title.slice(0, 90))}…</span></li>`).join("")}</ul></div>`;
}
function siteView(code) {
  const s = D.sitesByCode[code];
  if (!s) return notFound();
  document.title = `${s.name} · ${T.title}`;
  const list = (bySite.get(code) || []).slice().sort((a, b) => b.date.localeCompare(a.date));
  const open = list.filter(isOpen).sort((a, b) => a.deadline.localeCompare(b.deadline));
  $("#vista").innerHTML = `<div class="wrap">
    <nav class="migas"><a href="#/">${t("home")}</a> › ${regionLinks(s.regions)} › ${t("th_site")}</nav>
    <div class="lugar-cab"><h2>${esc(s.name)}</h2>
      <span class="codigo">${esc(s.code)} · ${t("site_kind_line", {kind: D.kind})}${s.marine ? " · " + t("at_sea") : ""}</span>
      ${s.munis.length ? `<ul class="municipios" aria-label="${esc(t("munis"))}">${s.munis.map(([ine, name]) => `<li><a href="#/m/${esc(ine)}">${esc(name)}</a></li>`).join("")}</ul>` : ""}
    </div>
    <div id="mapa-host" class="mapa-host"></div>
    <div class="lugar">
      <div>
        ${open.length ? `<div class="actuar"><h3>${t("h_act")}</h3>
          <p>${tn("act_site", open.length)}. ${t("anyone_can")}</p>
          <ul class="lista">${open.map(x => plazoItem(x, code)).join("")}</ul></div>` : ""}
        <section class="cronologia"><h2 class="sec">${t("h_happened")}</h2>${timeline(list, code)}</section>
        <section class="aves" id="aves-panel" hidden></section>
      </div>
      <aside>
        ${hilo(list)}
        <div class="panel luz" id="luz-panel" hidden></div>
        <div class="panel rss"><h3>${t("h_rss")}</h3>
          <p style="margin:0 0 6px">${t("rss_site")}</p>
          <a href="rss/${esc(code)}.xml">rss/${esc(code)}.xml</a></div>
      </aside>
    </div></div>`;
  window.scrollTo(0, 0);
  mapaTodo($("#mapa-host"), scopeSite(s), t("map_of", {name: s.name}));
  luzPanel(code);
  avesPanel(code, s.name);
}

/* Birds: the species the site was designated for, from its Natura 2000 form, read only when a site is opened. */
// aves.json holds every country's sites and each species' name in every language of the panel.
let AVES;
const SEASON = T.season, GRADE = T.grade;
async function avesPanel(code, name) {
  const host = $("#aves-panel");
  if (!host) return;
  try { AVES ||= await fetch(PAGE.shared + "datos/aves.json").then(r => r.json()); } catch { return; }
  const x = AVES.sites[code];
  if (!x || !host.isConnected) return;
  const sdf = `https://natura2000.eea.europa.eu/Natura2000/SDF.aspx?site=${encodeURIComponent(code)}`;
  const li = (AVES.languages || ["es"]).indexOf(PAGE.lang) + 1;
  const item = ([sp, seasons]) => {
    const sci = AVES.species[sp][0], es = (li && AVES.species[sp][li]) || sci;
    return `<li><span class="ave">${esc(es)}</span>${es !== sci ? ` <i class="meta">${esc(sci)}</i>` : ""}
      <span class="meta">· ${[...seasons].map(k => SEASON[k]).join(", ") || t("no_season")}</span></li>`;
  };
  const groups = Object.keys(GRADE).map(g => [g, x.birds.filter(b => b[2] === g)]).filter(([, l]) => l.length);
  const block = ([g, l]) => {
    const head = `${GRADE[g]} <span class="meta">· ${tn("n_species", l.length)}</span>`;
    const ul = `<ul class="aves-lista">${l.map(item).join("")}</ul>`;
    // A long tail of small shares is folded, so the species the site matters most for come first.
    return g !== groups[0][0] && "CN".includes(g) && l.length > 12
      ? `<details><summary><h3 class="aves-grado">${head}</h3></summary>${ul}</details>`
      : `<h3 class="aves-grado">${head}</h3>${ul}`;
  };
  const other = x.other ? `<p class="meta">${tn("other_species", x.other)}</p>` : "";
  host.hidden = false;
  host.innerHTML = `<h2 class="sec">${t("h_birds")}</h2>
    <p class="sec-sub">${t("birds_sub", {name: esc(name), kind: esc(D.kind)})}</p>
    ${groups.length ? groups.map(block).join("") : `<p class="vacio">${t("no_birds")}</p>`}
    ${other}
    <p class="meta fuente">${t("birds_source", {version: esc(AVES.version.replace("end", T.release_end).replace(" rev1", ""))})} ·
      <a href="${sdf}">${t("official_form")}</a> · <a href="https://doi.org/${esc(AVES.doi)}">${t("data")}</a> · ${t("bird_names")} · <a href="${PAGE.shared}datos/aves.json">aves.json</a></p>`;
}

// The round number just above v and the decimals it needs: 0.69 -> 0.8, 3.2 -> 4, 0.21 -> 0.25.
function redondo(v) {
  const e = Math.floor(Math.log10(v)), step = 10 ** e;
  const m = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10].find(k => k * step >= v - 1e-12);
  return [m * step, Math.max(0, -e + (m % 1 ? 1 : 0) - (m === 10 ? 1 : 0))];
}

/* Night light: the site's yearly series, read from luz.json only when a site is opened. */
let LUZ;
async function luzPanel(code) {
  const host = $("#luz-panel"), cov = D.sources["black-marble"]?.coverage;
  if (!host || !cov?.baseline) return;
  try { LUZ ||= await fetch("datos/luz.json").then(r => r.json()); } catch { return; }  // one file per country: its sites are held to their own peers
  const x = LUZ.sites[code];
  if (!x || !host.isConnected) return;
  const years = LUZ.years, r = x.radiance, src = `<p class="meta fuente">${t("light_source")} ·
    <a href="https://doi.org/${esc(LUZ.doi)}">${t("product")}</a> · <a href="datos/luz.json">luz.json</a></p>`;
  host.hidden = false;
  if (!cov.sites.includes(code)) {
    host.innerHTML = `<h3>${KIND.night_light.theme}</h3><p class="vacio">${tn("light_small", x.pixels)}</p>${src}`;
    return;
  }
  const [b0, b1] = cov.baseline, mean = a => a.reduce((t, v) => t + v, 0) / a.length;
  const ref = mean(r.filter((_, i) => years[i] >= b0 && years[i] <= b1)), now = r.slice(-cov.recent);
  const cur = mean(now), pct = Math.round(100 * (cur / ref - 1)), span = `${years.at(-cov.recent)}-${years.at(-1)}`;
  const delta = pct === 0 ? t("light_same") : t(pct > 0 ? "light_more" : "light_less", {pct: t("pct", {n: Math.abs(pct)})});
  const caption = i => r[i] == null ? `${years[i]}: ${t("no_value")}` : `${years[i]}: ${num(r[i], 2)} nW/cm²/sr`;
  const sig = (bySite.get(code) || []).find(s => s.kind === "night_light"), d = sig?.details;
  const drift = d && Math.round(100 * (d.expected / d.baseline - 1));
  const peers = sig
    ? t(drift < 0 ? "light_peers_down" : "light_peers_up", {drift: pct_(Math.abs(drift)), over: pct_(sig.value.amount)})
    : t("light_peers_none");
  host.innerHTML = `<h3>${KIND.night_light.theme}</h3>
    <p style="margin:0 0 6px">${t("light_mean", {span, value: `<b>${num(cur, 2)}</b>`, delta, base: `${b0}-${b1}`})}${pct < 0 ? " " + t("light_led") : ""} ${peers}</p>
    <div class="luz-graf"></div>
    <p class="meta luz-dato" aria-live="polite">${caption(years.length - 1)}</p>
    <details><summary>${t("see_data")}</summary><table class="luz-tabla"><thead><tr><th>${t("year")}</th><th class="n">nW/cm²/sr</th></tr></thead>
      <tbody>${years.map((y, i) => `<tr><td>${y}</td><td class="n">${num(r[i], 2)}</td></tr>`).join("")}</tbody></table></details>${src}`;
  // Drawn at the box's own width (it changes once the map settles), so text and points keep their size.
  const graf = $(".luz-graf", host), out = $(".luz-dato", host);
  let drawn = 0;
  const ro = new ResizeObserver(() => {
    if (!graf.isConnected) return ro.disconnect();
    const w = Math.round(graf.clientWidth);
    if (w && w !== drawn) graf.innerHTML = luzChart(years, r, ref, `${b0}-${b1}`, cur > ref, drawn = w);
  });
  ro.observe(graf);
  const show = i => {
    const cruz = $(".cruz", graf);
    for (const p of graf.querySelectorAll(".pt")) p.classList.toggle("on", p.dataset.i === String(i));
    cruz.setAttribute("x1", cruz.dataset["x" + i]); cruz.setAttribute("x2", cruz.dataset["x" + i]);
    cruz.style.visibility = "visible";
    out.textContent = caption(i);
  };
  graf.addEventListener("pointerover", e => { if (e.target.dataset.i != null) show(+e.target.dataset.i); });
  graf.addEventListener("pointerleave", () => {
    for (const p of graf.querySelectorAll(".pt")) p.classList.remove("on");
    const cruz = $(".cruz", graf);
    if (cruz) cruz.style.visibility = "hidden";
    out.textContent = caption(years.length - 1);
  });
}
function luzChart(years, r, ref, base, above, W) {
  const H = 120, L = 34, R = 8, T = 10, B = 20;
  const [top, dec] = redondo(Math.max(ref, ...r.filter(v => v != null)) * 1.05 || 1);
  const x = i => L + (W - L - R) * (years.length > 1 ? i / (years.length - 1) : .5);
  const y = v => T + (H - T - B) * (1 - v / top);
  let d = "", pen = false;
  r.forEach((v, i) => {
    if (v == null) { pen = false; return; }
    d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
    pen = true;
  });
  const step = (W - L - R) / Math.max(1, years.length - 1);
  const xs = years.map((_, i) => `data-x${i}="${x(i).toFixed(1)}"`).join(" ");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(t("light_chart", {from: years[0], to: years.at(-1)}))}">
    <line class="eje-l" x1="${L}" x2="${W - R}" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}"/>
    <line class="ref" x1="${L}" x2="${W - R}" y1="${y(ref).toFixed(1)}" y2="${y(ref).toFixed(1)}"/>
    <text class="eje" x="${W - R}" y="${(y(ref) + (above ? 13 : -5)).toFixed(1)}" text-anchor="end">${t("mean")} ${esc(base)}</text>
    <text class="eje" x="${L - 6}" y="${(y(top) + 4).toFixed(1)}" text-anchor="end">${num(top, dec)}</text>
    <text class="eje" x="${L - 6}" y="${(y(0) + 4).toFixed(1)}" text-anchor="end">0</text>
    <text class="eje" x="${x(0).toFixed(1)}" y="${H - 4}" text-anchor="start">${years[0]}</text>
    <text class="eje" x="${x(years.length - 1).toFixed(1)}" y="${H - 4}" text-anchor="end">${years.at(-1)}</text>
    <line class="cruz" ${xs} x1="0" x2="0" y1="${T}" y2="${y(0).toFixed(1)}" style="visibility:hidden"/>
    <path class="linea" d="${d}"/>
    ${r.map((v, i) => v == null ? "" : `<circle class="pt" data-i="${i}" cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="4"/>`).join("")}
    ${years.map((_, i) => `<rect class="col" data-i="${i}" x="${(x(i) - step / 2).toFixed(1)}" y="${T}" width="${step.toFixed(1)}" height="${(y(0) - T).toFixed(1)}"/>`).join("")}
  </svg>`;
}

/* ---------- Municipality ---------- */

async function muniView(ine) {
  await munis();
  const m = M.byIne[ine];
  if (!m) return notFound();
  document.title = `${m.name} · ${T.title}`;
  const list = (byMuni.get(ine) || []).slice().sort((a, b) => b.date.localeCompare(a.date));
  const open = list.filter(isOpen).sort((a, b) => a.deadline.localeCompare(b.deadline));
  const sites = m.sites.map(c => D.sitesByCode[c]).filter(Boolean);
  $("#vista").innerHTML = `<div class="wrap">
    <nav class="migas"><a href="#/">${t("home")}</a> › ${m.region ? regionLinks([m.region]) + " › " : ""}${t("t_muni")}</nav>
    <div class="lugar-cab"><h2>${esc(m.name)}</h2><span class="codigo">${esc(m.province || t("no_province"))} · ${t("code_office")} ${esc(ine)}</span></div>
    <div id="mapa-host" class="mapa-host"></div>
    <div class="lugar">
      <div>
        ${open.length ? `<div class="actuar"><h3>${t("h_act")}</h3>
          <p>${tn("act_muni", open.length)}.</p>
          <ul class="lista">${open.map(x => plazoItem(x)).join("")}</ul></div>` : ""}
        <section class="cronologia"><h2 class="sec">${t("h_names", {name: esc(m.name)})}</h2>${timeline(list, null, t("muni_empty"))}</section>
      </div>
      <aside>
        <div class="panel"><h3>${t("h_sites_in_muni")}</h3>
        ${sites.length ? `<ul class="lista">${sites.map(s => `<li class="item"><div class="t"><a href="#/e/${esc(s.code)}">${esc(s.name)}</a></div>
          <div class="meta">${resumen(s.n)}</div></li>`).join("")}</ul>`
          : `<p class="vacio">${t("no_site_in_muni", {kind: D.kind})}</p>`}</div>
      </aside>
    </div></div>`;
  window.scrollTo(0, 0);
  mapaTodo($("#mapa-host"), scopeMuni(m), t("map_of", {name: m.name}));
}

function resumen(n) {
  const parts = [tn("n_projects", n.notices)];
  if (n.open) parts.push(t("n_with_deadline", {n: n.open}));
  if (n.fire_ha) parts.push(t("ha_burnt", {ha: num(n.fire_ha, 1)}));
  if (n.land) parts.push(tn("n_land", n.land));
  if (n.light) parts.push(t("light_more_peers", {pct: pct_(n.light)}));
  return parts.join(" · ");
}

function notFound(what = t("that_place")) {
  document.title = T.title;
  $("#vista").innerHTML = `<div class="wrap"><nav class="migas"><a href="#/">${t("home")}</a></nav><p class="vacio">${t("not_found", {what: esc(what)})}</p></div>`;
}

/* ---------- Signal ---------- */

// What each kind of signal carries, as label and value, so its page reads the same whoever sent it.
function datos(s) {
  const d = s.details || {}, out = [];
  const add = (k, v) => { if (v != null && v !== "") out.push([k, v]); };
  const F = T.fields;
  if (s.kind === "notice") add(F.comments, s.deadline ? (s.deadline >= D.today ? `${t("until", {date: fecha(s.deadline)})} (${dias(s.deadline)})` : t("closed_on", {date: fecha(s.deadline)})) : t("no_known_deadline"));
  if (["notice", "resolution"].includes(s.kind)) add(F.promoter, esc(d.promoter));
  if (s.kind === "land_change") {
    add(F.status, STATUS(s));
    add(F.area, `${num(s.value?.amount, 2)} ha`);
    add(F.cover, esc(d.cover));
    add(F.permit, esc(d.permit));
    add(F.parcels, d.parcels != null ? num(d.parcels) : null);
    if (d.history?.length) add(F.history, d.history.map(([f, e]) => `${fecha(f)}: ${esc(e)}`).join(" · "));
  } else if (s.kind === "fire") {
    add(F.area, s.value ? `${num(s.value.amount, 1)} ha` : null);
    add(F.province, esc(d.province));
    add(F.status, STATUS(s));
  } else if (s.kind === "wetland_water") {
    add(F.water, `${num(s.value?.amount, 0)} ha`);
    add(F.normal, d.ref_ha != null ? t("normal_value", {ha: num(d.ref_ha, 0), from: d.ref_years?.[0], to: d.ref_years?.at(-1)}) : null);
  } else if (s.kind === "river_flow") {
    add(F.flow, `${num(s.value?.amount, 2)} m³/s`);
    add(F.minimum, d.minimum != null ? `${num(d.minimum, 2)} m³/s` : null);
    add(F.days_below, d.days != null ? t("x_of_y", {x: num(d.days_below), y: num(d.days)}) : null);
  } else if (s.kind === "power_line") {
    add(F.high_risk, num(s.value?.amount));
  } else if (s.kind === "night_light") {
    add(F.light_now, `${num(d.radiance, 2)} nW/cm²/sr (${d.years?.join("-")})`);
    add(F.light_before, `${num(d.baseline, 2)} nW/cm²/sr`);
    add(F.light_expected, `${num(d.expected, 2)} nW/cm²/sr`);
    add(F.pixels, num(d.pixels));
  } else if (s.kind === "migration") {
    add(F.migration, LEVEL[s.status] || STATUS(s));
  } else {
    add(F.status, STATUS(s));
  }
  if (s.kind !== "night_light") add(F.precision, PRECISION[s.precision]);  // its pixels are VIIRS, said above
  return out;
}

async function avisoView(source, id) {
  const s = D.signals.find(x => x.source === source && x.id === id);
  if (!s) return notFound(t("that_signal"));
  await munis();
  if (!location.hash.startsWith(aviso(s))) return;  // the reader moved on while the data loaded
  const d = s.details || {}, src = D.sources[s.source] || {name: s.source};
  document.title = `${s.title.slice(0, 70)} · ${T.title}`;
  const site = s.sites.length === 1 ? D.sitesByCode[s.sites[0].code] : null;
  const zepas = s.sites.map(x => `<li><a href="#/e/${esc(x.code)}">${esc(siteName(x.code))}</a>${x.ha != null ? ` <span class="meta">${t("ha_inside", {ha: num(x.ha, x.ha < 10 ? 1 : 0)})}</span>` : ""}</li>`).join("");
  const otros = (d.natura || []).filter(([c]) => !D.sitesByCode[c]);
  const munisHtml = s.municipalities.filter(i => M.byIne[i]).map(i => `<li><a href="#/m/${esc(i)}">${esc(M.byIne[i].name)}</a></li>`).join("");
  const fotos = d.before && d.after ? `<div class="fotos grandes">
      <figure><img src="${esc(d.before)}" alt="${esc(t("Before"))}, ${esc(fecha(d.before_date))}"><figcaption>${t("before")} · ${fecha(d.before_date)}</figcaption></figure>
      <figure><img src="${esc(d.after)}" alt="${esc(t("After"))}, ${esc(fecha(d.after_date))}"><figcaption>${t("after")} · ${fecha(d.after_date)}</figcaption></figure></div>` : "";
  const original = ["notice", "resolution"].includes(s.kind) ? t("read_notice")
    : s.kind === "night_light" ? t("see_nasa") : t("see_in", {name: src.name});
  $("#vista").innerHTML = `<div class="wrap">
    <nav class="migas"><a href="#/">${t("home")}</a> › ${s.regions?.length ? regionLinks(s.regions) + " › " : ""}${site ? `<a href="#/e/${esc(site.code)}">${esc(site.name)}</a> › ` : ""}${esc((KIND[s.kind] || {}).tag || t("signal"))}</nav>
    <div class="aviso-cab">${tag(s)} <span class="meta">${fecha(s.date)} · ${t("according_to")} ${esc(src.name)}</span>
      <h2>${esc(s.title)}</h2></div>
    <div class="lugar">
      <div>
        ${fotos}
        <div class="lienzo aviso-mapa" id="aviso-mapa" role="region" aria-label="${esc(t("where_is"))}"></div>
        ${MEANS[s.kind] ? `<p class="significa-txt">${esc(MEANS[s.kind])}${s.precision === "municipio" ? " " + esc(PREC_NOTE.municipio) : ""}</p>` : ""}
        ${s.kind === "night_light" && site ? `<p><a href="#/e/${esc(site.code)}">${t("light_series", {name: esc(site.name)})}</a></p>` : ""}
      </div>
      <aside>
        <div class="panel"><h3>${t("h_data")}</h3><dl class="datos">${datos(s).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("")}</dl></div>
        <div class="panel"><h3>${t("h_where")}</h3>
          ${zepas ? `<p class="meta" style="margin:0 0 4px">${esc(D.kind)}</p><ul class="lista-simple">${zepas}</ul>`
            : `<p style="margin:0 0 6px">${t("in_no_site", {kind: esc(D.kind)})}</p>`}
          ${otros.length ? `<p class="meta" style="margin:8px 0 4px">${t("other_natura")}</p><ul class="lista-simple">${otros.map(([c, n, t]) => `<li>${esc(n || c)} <span class="meta">${esc(t || "")} ${esc(c)}</span></li>`).join("")}</ul>` : ""}
          ${munisHtml ? `<p class="meta" style="margin:8px 0 4px">${t("munis")}</p><ul class="municipios">${munisHtml}</ul>` : ""}</div>
        <div class="panel"><h3>${t("h_from")}</h3>
          <p style="margin:0 0 6px">${esc(src.name)}${src.watches ? ` ${t("watches")} ${esc(src.watches)}` : ""}. ${t("summary_here")}</p>
          <a class="fuera" href="${esc(s.url)}" target="_blank" rel="noopener">${esc(original)}</a></div>
        ${hilo([s])}
      </aside>
    </div></div>`;
  window.scrollTo(0, 0);
  avisoMapa(s);
}

async function avisoMapa(s) {
  await shapes();
  const el = $("#aviso-mapa");
  if (!el?.isConnected) return;
  const map = baseMap(el, {scrollWheelZoom: false});
  const codes = new Set(s.sites.map(x => x.code));
  const poly = L.geoJSON({type: "FeatureCollection", features: SHAPES.features.filter(f => codes.has(f.properties.code))}, {
    style: {color: MAP_ACCENT, weight: 2, fillColor: MAP_ACCENT, fillOpacity: .12},
    onEachFeature: (f, l) => { l.bindTooltip(esc(f.properties.name), {sticky: true}); l.on("click", () => { location.hash = "#/e/" + f.properties.code; }); },
  }).addTo(map);
  const ly = LAYERS.find(x => x.kinds.includes(s.kind));
  // Projects carry no point: they sit at the municipalities they name.
  const pts = s.details?.point ? [[s.details.point[1], s.details.point[0]]]
    : s.municipalities.filter(i => M.byIne[i]).map(i => [M.byIne[i].point[1], M.byIne[i].point[0]]);
  for (const p of pts) {
    const px = 22;
    L.marker(p, {icon: L.divIcon({className: "marca", html: icono(ly?.shape || "circle", ly?.color || MAP_ACCENT, px, {stroke: ly?.stroke}),
      iconSize: [px, px], iconAnchor: [px / 2, px / 2]}), title: s.title, alt: s.title, keyboard: false}).addTo(map);
  }
  const b = poly.getBounds();
  for (const p of pts) b.extend(p);
  if (b.isValid()) map.fitBounds(b, {padding: [24, 24], maxZoom: pts.length && !codes.size ? 13 : 14});
}

/* ---------- Router ---------- */

function route() {
  for (const m of MAPS) m.remove();
  MAPS = [];
  capa = null;
  const h = location.hash.replace(/^#\/?/, "");
  const [kind, id, more] = h.split("/");
  document.body.classList.toggle("en-lugar", Boolean(kind));  // away from home the header shrinks to its title
  if (kind === "e" && id) return siteView(decodeURIComponent(id));
  if (kind === "m" && id) return muniView(decodeURIComponent(id));
  if (kind === "ca" && id) return regionView(decodeURIComponent(id));
  if (kind === "plazos") return plazos();
  if (kind === "a" && id && more) return avisoView(decodeURIComponent(id), decodeURIComponent(more));
  if (/^[A-Z]{2}[0-9A-Z]{7}$/.test(h) && D.sitesByCode[h]) { location.replace("#/e/" + h); return; }  // old v1 anchors
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

// A link to another site opens in a new tab: the reader never loses their place here.
document.addEventListener("click", e => {
  const a = e.target.closest?.("a[href]");
  if (a && a.origin !== location.origin && !a.target) { a.target = "_blank"; a.rel = "noopener"; }
}, true);
