"use strict";
// Estado de las IBA: one page, three views (home, site, municipality) routed by the URL hash.

const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const num = (x, d = 0) => x == null ? "—" : Number(x).toLocaleString("es-ES", {minimumFractionDigits: d, maximumFractionDigits: d});
const fecha = s => s ? new Date(s.slice(0, 10) + "T12:00:00").toLocaleDateString("es-ES", {day: "numeric", month: "short", year: "numeric"}) : "";
const mesDe = s => new Date(s.slice(0, 7) + "-15T12:00:00").toLocaleDateString("es-ES", {month: "long", year: "numeric"});
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const norm = s => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

const KIND = {
  notice: {tag: "Proyecto", theme: "Proyectos en evaluación"},
  resolution: {tag: "Resolución", theme: "Proyectos en evaluación"},
  fire: {tag: "Fuego", theme: "Fuego"},
  land_change: {tag: "Suelo", theme: "Cambios de uso del suelo"},
  wetland_water: {tag: "Agua", theme: "Agua de los humedales"},
  river_flow: {tag: "Río", theme: "Caudal de los ríos"},
  power_line: {tag: "Tendido", theme: "Tendidos eléctricos"},
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

let D, M, SHAPES, mapa, capa;
const bySite = new Map(), byMuni = new Map();

function daysLeft(deadline) {
  return Math.round((new Date(deadline + "T12:00:00") - new Date(D.today + "T12:00:00")) / 864e5);
}
function dias(deadline) {
  const n = daysLeft(deadline);
  return n === 0 ? "último día hoy" : n === 1 ? "queda 1 día" : `quedan ${n} días`;
}
const isOpen = s => s.deadline && s.deadline >= D.today && s.kind === "notice";
const siteName = c => D.sitesByCode[c]?.name || c;

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
  const week = new Date(new Date(D.today + "T12:00:00") - 7 * 864e5).toISOString().slice(0, 10);
  const recent = D.signals.filter(s => s.date >= week && s.sites.length && s.kind !== "wetland_water")
    .sort((a, b) => b.date.localeCompare(a.date));
  const groups = {};
  for (const s of recent) (groups[KIND[s.kind]?.theme || s.kind] ||= []).push(s);

  $("#vista").innerHTML = `
  <div class="wrap">
    ${buscador()}
    <p class="ejemplos">Por ejemplo: <a href="#/e/ES0000014">Monfragüe</a> · <a href="#/e/ES0000024">Doñana</a> · <a href="#/m/30016">Cartagena</a> · <a href="#/e/ES0000013">Tablas de Daimiel</a></p>
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
        ${Object.entries(groups).map(([theme, list]) => `
          <div class="semana-tema"><h3>${esc(theme)} · ${list.length}</h3>
          <ul class="lista">${list.slice(0, 4).map(s => feedItem(s)).join("")}</ul>
          ${list.length > 4 ? `<p class="meta">y ${list.length - 4} más</p>` : ""}</div>`).join("") || `<p class="vacio">Nada nuevo esta semana.</p>`}
      </section>
    </div>
    <section class="bloque-home">
      <h2 class="sec">Todos los espacios</h2>
      <p class="sec-sub">Elige qué mirar. Cuanto más intenso el color, más hay.</p>
      <div class="controles"><label>Ver <select id="indicador">
        <option value="precise">Proyectos dentro, por parcelas</option>
        <option value="open">Proyectos con plazo abierto</option>
        <option value="notices">Proyectos en su municipio</option>
        <option value="fire_ha">Hectáreas quemadas en 12 meses</option>
        <option value="land">Cambios de uso (solo Cantabria)</option>
      </select></label></div>
      <div class="mapa-home">
        <div><div id="mapa" role="region" aria-label="Mapa de las ZEPA"></div><div class="leyenda" id="leyenda"></div></div>
        <div class="ranking" id="ranking"></div>
      </div>
    </section>
  </div>`;
  wireSearch();
  const sel = $("#indicador");
  sel.addEventListener("input", () => { paintHome(sel.value); ranking(sel.value); });
  homeMap().then(() => paintHome(sel.value));
  ranking(sel.value);
}

function noche() {
  const m = D.signals.filter(s => s.kind === "migration" && s.status !== "low");
  if (!m.length) return "";
  const night = m[0].date;
  const order = {"very high": 0, high: 1, moderate: 2};
  const LEVEL = {"very high": "muy alta", high: "alta", moderate: "moderada"};
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
  $("#ranking").innerHTML = `<table><thead><tr><th>Espacio</th><th class="n">${esc(IND[key].label)}</th></tr></thead><tbody>
    ${rows.map(s => `<tr><td><a href="#/e/${esc(s.code)}">${esc(s.name)}</a></td><td class="n">${num(f(s.n), key === "fire_ha" ? 1 : 0)}</td></tr>`).join("")
      || `<tr><td colspan="2" class="vacio">Ningún espacio.</td></tr>`}</tbody></table>`;
}

async function shapes() {
  SHAPES ||= await fetch("sitios.geojson").then(r => r.json());
  return SHAPES;
}
function baseMap(el, opts = {}) {
  const m = L.map(el, {zoomSnap: .5, ...opts}).setView([40.2, -3.7], 5.5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 18, attribution: "© OpenStreetMap"}).addTo(m);
  return m;
}
async function homeMap() {
  const g = await shapes();
  if (!$("#mapa")) return;
  mapa = baseMap("mapa");
  capa = L.geoJSON(g, {
    onEachFeature: (f, l) => {
      l.bindTooltip(esc(f.properties.name), {sticky: true});
      l.on("click", () => { location.hash = "#/e/" + f.properties.code; });
    },
  }).addTo(mapa);
}
function paintHome(key) {
  if (!capa) return;
  const f = IND[key].f;
  const max = Math.max(1, ...D.sites.map(s => f(s.n)));
  const accent = css("--accent");
  capa.eachLayer(l => {
    const v = f(D.sitesByCode[l.feature.properties.code]?.n || {}) || 0;
    l.setStyle({color: accent, weight: v ? 1.2 : .6, fillColor: accent, fillOpacity: .03 + .62 * Math.sqrt(v / max)});
  });
  $("#leyenda").innerHTML = `<span><i style="opacity:.15"></i>nada</span><span><i style="opacity:.65"></i>máximo: ${num(max, key === "fire_ha" ? 1 : 0)} ${esc(IND[key].label)}</span>`;
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

/* ---------- Search ---------- */

function buscador() {
  return `<div class="buscador" role="search">
    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>
    <input id="q" type="search" autocomplete="off" placeholder="Busca un espacio o un municipio" aria-label="Busca un espacio o un municipio"
      aria-controls="resultados" aria-expanded="false">
    <ul class="resultados" id="resultados" role="listbox" hidden></ul></div>`;
}
async function munis() {
  if (!M) {
    const rows = await fetch("datos/municipios.json").then(r => r.json());
    M = rows.map(([ine, name, province, lon, lat, sites]) => ({ine, name, province, point: [lon, lat], sites, key: norm(name)}));
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
    const score = k => k.startsWith(t) ? 0 : k.includes(" " + t) ? 1 : k.includes(t) ? 2 : 9;
    const sites = D.sites.map(s => ({s, r: s.code.toLowerCase() === t ? -1 : score(norm(s.name))})).filter(x => x.r < 9);
    const ms = M.map(m => ({m, r: score(m.key)})).filter(x => x.r < 9);
    sites.sort((a, b) => a.r - b.r || a.s.name.localeCompare(b.s.name, "es"));
    ms.sort((a, b) => a.r - b.r || a.m.name.length - b.m.name.length);
    const items = [
      ...sites.slice(0, 6).map(({s}) => `<li><a role="option" href="#/e/${esc(s.code)}"><span class="tipo">Espacio</span><span>${esc(s.name)}</span><span class="extra">${esc(s.code)}</span></a></li>`),
      ...ms.slice(0, 8).map(({m}) => `<li><a role="option" href="#/m/${esc(m.ine)}"><span class="tipo">Municipio</span><span>${esc(m.name)}</span><span class="extra">${esc(m.province)}</span></a></li>`),
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
function vigilancia(code) {
  return `<ul class="vigilancia">${Object.entries(D.sources).filter(([, src]) => src.site_level).map(([id, src]) => {
    const on = src.coverage.sites == null || src.coverage.sites.includes(code);
    return `<li><span class="${on ? "si" : "no"}" aria-hidden="true">${on ? "✓" : "—"}</span>
      <span><a href="${esc(src.url)}">${esc(src.name)}</a>: ${on ? esc(src.watches) : "no vigila este espacio"}</span>
      <small>${esc(src.coverage.label)}</small></li>`;
  }).join("")}</ul>`;
}
function hilo(list) {
  const chains = list.filter(s => s.kind === "notice" && D.chains?.[s.id]).flatMap(s => D.chains[s.id].map(c => ({s, c})));
  if (!chains.length) return "";
  return `<div class="panel"><h3>Quién está detrás</h3><ul class="hilo">${chains.map(({s, c}) => `<li>
    <div class="cadena">${c.links.map(l => `<span>${l.url ? `<a href="${esc(l.url)}">${esc(l.name)}</a>` : esc(l.name)}${l.via === "por el grupo" ? ` <small class="meta">(por el grupo)</small>` : ""}</span>`).join("")}</div>
    <span class="meta">${esc(s.title.slice(0, 90))}…</span></li>`).join("")}</ul></div>`;
}
async function siteView(code) {
  const s = D.sitesByCode[code];
  if (!s) return notFound();
  document.title = `${s.name} · Estado de las IBA`;
  const list = (bySite.get(code) || []).slice().sort((a, b) => b.date.localeCompare(a.date));
  const open = list.filter(isOpen).sort((a, b) => a.deadline.localeCompare(b.deadline));
  $("#vista").innerHTML = `<div class="wrap">
    <nav class="migas"><a href="#/">Inicio</a> › Espacio</nav>
    <div class="lugar-cab"><h2>${esc(s.name)}</h2>
      <span class="codigo">${esc(s.code)} · ${esc(D.kind)} de la Red Natura 2000</span>
      ${s.munis.length ? `<ul class="municipios" aria-label="Municipios">${s.munis.map(([ine, name]) => `<li><a href="#/m/${esc(ine)}">${esc(name)}</a></li>`).join("")}</ul>` : ""}
    </div>
    <div class="lugar">
      <div>
        ${open.length ? `<div class="actuar"><h3>Puedes alegar</h3>
          <p>${open.length === 1 ? "Un proyecto que toca este espacio admite alegaciones" : `${open.length} proyectos que tocan este espacio admiten alegaciones`}. Cualquier persona o entidad puede presentarlas.</p>
          <ul class="lista">${open.map(x => plazoItem(x, code)).join("")}</ul></div>` : ""}
        <section class="cronologia"><h2 class="sec">Qué ha pasado</h2>${timeline(list, code)}</section>
      </div>
      <aside>
        <div id="mapa-lugar" role="img" aria-label="Límites del espacio"></div>
        <div class="panel"><h3>Qué se vigila aquí</h3>${vigilancia(code)}
          <p class="meta" style="margin:8px 0 0">Que no aparezca algo no significa que no ocurra: solo se ve lo que vigila algún proyecto.</p></div>
        ${hilo(list)}
        <div class="panel rss"><h3>Recibe los avisos</h3>
          <p style="margin:0 0 6px">Suscríbete con tu lector de noticias para enterarte de cada novedad en este espacio:</p>
          <a href="rss/${esc(code)}.xml">rss/${esc(code)}.xml</a></div>
      </aside>
    </div></div>`;
  window.scrollTo(0, 0);
  const g = await shapes();
  const f = g.features.find(x => x.properties.code === code);
  if (!f || !$("#mapa-lugar")) return;
  const m = baseMap("mapa-lugar", {scrollWheelZoom: false});
  const l = L.geoJSON(f, {style: {color: css("--accent"), weight: 2, fillOpacity: .15}}).addTo(m);
  m.fitBounds(l.getBounds(), {padding: [12, 12]});
  for (const x of list) if (x.details.point) L.circleMarker([x.details.point[1], x.details.point[0]], {radius: 6, color: css("--ink"), weight: 1.5, fillColor: css("--accent"), fillOpacity: .9}).bindTooltip(esc(x.title)).addTo(m);
}

/* ---------- Municipality ---------- */

function resumen(n) {
  const parts = [`${n.notices} ${n.notices === 1 ? "proyecto" : "proyectos"}`];
  if (n.open) parts.push(`${n.open} con plazo abierto`);
  if (n.fire_ha) parts.push(`${num(n.fire_ha, 1)} ha quemadas`);
  if (n.land) parts.push(`${n.land} ${n.land === 1 ? "cambio de uso" : "cambios de uso"}`);
  return parts.join(" · ");
}

async function muniView(ine) {
  await munis();
  const m = M.byIne[ine];
  if (!m) return notFound();
  document.title = `${m.name} · Estado de las IBA`;
  const list = (byMuni.get(ine) || []).slice().sort((a, b) => b.date.localeCompare(a.date));
  const open = list.filter(isOpen).sort((a, b) => a.deadline.localeCompare(b.deadline));
  const sites = m.sites.map(c => D.sitesByCode[c]).filter(Boolean);
  $("#vista").innerHTML = `<div class="wrap">
    <nav class="migas"><a href="#/">Inicio</a> › Municipio</nav>
    <div class="lugar-cab"><h2>${esc(m.name)}</h2><span class="codigo">${esc(m.province)} · INE ${esc(ine)}</span></div>
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
}

function notFound() {
  $("#vista").innerHTML = `<div class="wrap"><nav class="migas"><a href="#/">Inicio</a></nav><p class="vacio">No encuentro ese lugar.</p></div>`;
}

/* ---------- Router ---------- */

function route() {
  if (mapa) { mapa.remove(); mapa = capa = null; }
  const h = location.hash.replace(/^#\/?/, "");
  const [kind, id] = h.split("/");
  document.body.classList.toggle("en-lugar", Boolean(kind));  // away from home the header shrinks to its title
  if (kind === "e" && id) return siteView(decodeURIComponent(id));
  if (kind === "m" && id) return muniView(decodeURIComponent(id));
  if (kind === "plazos") return plazos();
  if (/^ES[0-9A-Z]{7}$/.test(h)) { location.replace("#/e/" + h); return; }  // old v1 anchors
  home();
}

fetch("datos/hub.json").then(r => r.json()).then(data => {
  D = data;
  D.sitesByCode = Object.fromEntries(D.sites.map(s => [s.code, s]));
  for (const s of D.signals) {
    for (const x of s.sites) { if (!bySite.has(x.code)) bySite.set(x.code, []); bySite.get(x.code).push(s); }
    for (const c of s.municipalities) { if (!byMuni.has(c)) byMuni.set(c, []); byMuni.get(c).push(s); }
  }
  window.addEventListener("hashchange", route);
  route();
});
