"""The words of each country's site, one dictionary per language (the pattern of humedales/i18n.py).

Country is a dimension of the data, language one of the page: the data (hub.json and the rest) is
the same whatever the language, and each country's page is written in its own. Spain's page is in
Spanish, France's in French.

UI holds every string app.js shows; web.py writes it into the page as window.I18N, along with the
country's settings as window.PAGE. PY holds what Python writes itself: feeds, coverage labels and
the night-light titles.

French typography: a narrow no-break space (U+202F) before « : ; ! ? % » and inside « », and as the
thousands separator. The French strings are written with plain spaces and `_typo` sets them, so the
dictionary stays readable and no space is forgotten.
"""

from __future__ import annotations

import re

LANG_BY_COUNTRY = {"ES": "es", "FR": "fr"}
COUNTRIES = tuple(LANG_BY_COUNTRY)
_NNBSP = " "

# What each country's page needs to know about itself.
SETTINGS = {
    "ES": {"lang": "es", "locale": "es-ES", "kind": "ZEPA", "center": [40.2, -3.7], "zoom": 5.5, "dir": "",
           "shared": "", "route": "/estado-iba/"},
    "FR": {"lang": "fr", "locale": "fr-FR", "kind": "ZPS", "center": [46.6, 2.4], "zoom": 5.5, "dir": "fr",
           "shared": "../", "route": "/estado-iba/fr/"},
}


def n(x: float, lang: str = "es") -> str:
    """An integer with the thousands separator of the language: 1.234 (es), 1 234 (fr)."""
    s = f"{round(x):,}"
    return s.replace(",", _NNBSP if lang == "fr" else ".")


def d(x: float, nd: int, lang: str = "es") -> str:
    """A decimal number with a comma, as both languages write it."""
    whole, _, frac = f"{x:,.{nd}f}".partition(".")
    whole = whole.replace(",", _NNBSP if lang == "fr" else ".")
    return f"{whole},{frac}" if frac else whole


def p(x: float, lang: str = "es") -> str:
    """A percentage: «15 %» in Spanish, «15 %» with a narrow no-break space in French."""
    return f"{n(x, lang)}{_NNBSP if lang == 'fr' else ' '}%"


def _typo(v):
    """French typography over a string, or every string of a dict or list."""
    if isinstance(v, dict):
        return {k: _typo(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_typo(x) for x in v]
    if not isinstance(v, str):
        return v
    v = re.sub(r" ([:;!?%»])", _NNBSP + r"\1", v)
    return v.replace("« ", "«" + _NNBSP)


_ES = {
    "title": "Estado de las IBA",
    "examples": 'Por ejemplo: <a href="#/e/ES0000014">Monfragüe</a> · <a href="#/e/ES0000024">Doñana</a> · '
                '<a href="#/m/30016">Cartagena</a> · <a href="#/ca/06">Cantabria</a>',
    "h_map": "Todo en un mapa",
    "map_sub": "Cada capa viene de un proyecto hermano (la luz de noche, de la NASA) y se activa o se apaga en la "
               "leyenda. Los espacios se colorean según lo que elijas.",
    "color_by": "Colorear los espacios por",
    "h_regions": "Por comunidad",
    "regions_sub": "Sus {kind}, sus plazos abiertos y lo nuevo de la semana. Canarias, Ceuta y Melilla quedan fuera "
                   "del mapa de arriba.",
    "h_deadlines": "Plazos abiertos",
    "deadlines_sub": "Proyectos que tocan una {kind} y aún admiten alegaciones, del plazo más corto al más largo.",
    "no_deadline": "Ningún plazo abierto hoy.",
    "see_deadlines": "Ver los {n} plazos abiertos",
    "h_week": "Esta semana",
    "week_sub": "Lo nuevo en los últimos 7 días en algún espacio.",
    "h_ranking": "Clasificación",
    "map_all_label": "Mapa de todas las {kind} y de lo que vigila cada proyecto",
    "last_day": "último día hoy",
    "days_left": "quedan {n} días", "days_left_1": "queda {n} día",
    "by_muni": "por municipio",
    "more_than_expected": "más de lo esperable",
    "ha_inside": "{ha} ha dentro",
    "n_open": "{n} plazos abiertos", "n_open_1": "{n} plazo abierto",
    "none_open": "ningún plazo abierto",
    "n_new_week": "{n} novedades esta semana", "n_new_week_1": "{n} novedad esta semana",
    "nothing_new_week": "nada nuevo esta semana",
    "and_more": "y {n} más",
    "nothing_new": "Nada nuevo esta semana.",
    "h_tonight": "Esta noche · migración prevista",
    "according_to": "según",
    "until": "hasta el {date}",
    "ranking_sub": "Las {kind} con algo en «{label}», de más a menos. Cambia el criterio encima del mapa.",
    "th_site": "Espacio",
    "th_region": "Comunidad",
    "no_site": "Ningún espacio.",
    "legend_none": "{kind} sin nada",
    "legend_max": "máximo",
    "home": "Inicio",
    "deadlines_page_sub": "{n} proyectos que tocan alguna {kind} admiten alegaciones hoy. Los marcados «por "
                          "municipio» no traen parcelas: puede que no entren en el espacio.",
    "no_data_today": "sin datos hoy",
    "not_covered": "no cubre esta zona",
    "by_city": "se prevé por ciudad, no por espacio",
    "night_of": "noche del {date}",
    "n_projects": "{n} proyectos", "n_projects_1": "{n} proyecto",
    "n_with_deadline": "{n} con plazo abierto",
    "h_layers": "Capas",
    "layers_note": "En gris, lo que ningún proyecto vigila aquí. Que no aparezca algo no significa que no ocurra.",
    "double_border": "borde doble",
    "watched_nothing": "vigilado, sin novedades",
    "search": "Busca un espacio, un municipio o una comunidad",
    "t_region": "Comunidad",
    "t_muni": "Municipio",
    "no_results": "Sin resultados.",
    "th_projects": "Proyectos",
    "th_parcels": "Por parcelas",
    "th_open": "Plazo abierto",
    "th_burnt": "Ha quemadas",
    "region_kind": "Comunidad autónoma",
    "region_kinds": {"18": "Ciudad autónoma", "19": "Ciudad autónoma"},
    "code_office": "INE",
    "h_act": "Puedes alegar",
    "act_region": "{n} proyectos que tocan {kind} de la comunidad admiten alegaciones",
    "act_region_1": "Un proyecto que toca una {kind} de la comunidad admite alegaciones",
    "week_sub_region": "Lo nuevo en los últimos 7 días en sus espacios.",
    "h_its_sites": "Sus espacios",
    "its_sites_sub": "Las {kind} que tocan algún municipio de {name}. Las que comparte con otra comunidad salen en "
                     "las dos.",
    "no_land_site": "Ninguna {kind} toca tierra aquí.",
    "h_sea": "En el mar o en islotes",
    "sea_sub": "No tocan ningún término municipal del IGN; van con la comunidad de la costa más cercana.",
    "h_rss": "Recibe los avisos",
    "rss_region": "Cada novedad en los espacios y municipios de {name}, en tu lector de noticias:",
    "map_of": "Mapa de {name}",
    "timeline_empty": "Ningún registro todavía en los proyectos que vigilan este espacio.",
    "comments_until": "alegaciones hasta el {date}",
    "closed_on": "plazo cerrado el {date}",
    "no_known_deadline": "sin plazo conocido",
    "light_line": "{now} nW/cm²/sr frente a {before}; como los igual de oscuros, {expected} · píxeles VIIRS de unos "
                  "500 m",
    "Before": "Antes", "After": "Después", "before": "antes", "after": "después",
    "what_means": "¿Qué significa?",
    "h_behind": "Quién está detrás",
    "via_group": "por el grupo",
    "pct": "{n} %",
    # Site
    "site_kind_line": "{kind} de la Red Natura 2000",
    "at_sea": "en el mar o en islotes",
    "munis": "Municipios",
    "act_site": "{n} proyectos que tocan este espacio admiten alegaciones",
    "act_site_1": "Un proyecto que toca este espacio admite alegaciones",
    "anyone_can": "Cualquier persona o entidad puede presentarlas.",
    "h_happened": "Qué ha pasado",
    "rss_site": "Suscríbete con tu lector de noticias para enterarte de cada novedad en este espacio:",
    # Birds
    "season": {"p": "todo el año", "r": "cría", "w": "inverna", "c": "en paso"},
    "grade": {"A": "Más del 15 % de las de España", "B": "Entre el 2 y el 15 %", "C": "Menos del 2 %",
              "X": "Importantes aquí, sin porcentaje en el formulario",
              "N": "Presentes, sin evaluar en el formulario"},
    "no_season": "época sin indicar",
    "n_species": "{n} especies", "n_species_1": "{n} especie",
    "other_species": "Y otras {n} especies presentes con una población poco significativa aquí o sin evaluar.",
    "other_species_1": "Y otra especie presente con una población poco significativa aquí o sin evaluar.",
    "h_birds": "Sus aves",
    "birds_sub": "Las especies que da el formulario oficial de {name} como {kind}: qué parte de las que hay en "
                 "España acoge cada una y en qué época del año.",
    "no_birds": "El formulario no atribuye a este espacio ninguna población significativa de aves.",
    "birds_source": 'Formulario normalizado de datos de Natura 2000 (Agencia Europea de Medio Ambiente, {version}), '
                    '<a href="https://creativecommons.org/licenses/by/4.0/deed.es">CC BY 4.0</a>',
    "release_end": "final de ",
    "official_form": "ficha oficial",
    "data": "datos",
    "bird_names": "nombres en castellano del MITECO",
    # Night light
    "light_source": "NASA Black Marble (VIIRS), píxeles de unos 500 m",
    "product": "producto",
    "light_small": "Con {n} píxeles de unos 500 m, el espacio es demasiado pequeño o le faltan años para leer una "
                   "tendencia.",
    "light_small_1": "Con {n} píxel de unos 500 m, el espacio es demasiado pequeño o le faltan años para leer una "
                     "tendencia.",
    "light_same": "lo mismo",
    "light_more": "un {pct} más",
    "light_less": "un {pct} menos",
    "no_value": "sin dato",
    "light_peers_down": "En los espacios que eran igual de oscuros bajó un {drift}: aquí hay un {over} más luz de "
                        "la esperable.",
    "light_peers_up": "En los espacios que eran igual de oscuros subió un {drift}: aquí hay un {over} más luz de la "
                      "esperable.",
    "light_peers_none": "Cada espacio se compara con los que eran igual de oscuros, porque el producto de la NASA "
                        "sube y baja de un año a otro en todo el país a la vez.",
    "light_mean": "Brillo medio en {span}: {value} nW/cm²/sr, {delta} que en {base}.",
    "light_led": "Una bajada puede ser solo el cambio a LED, que el satélite apenas ve.",
    "see_data": "Ver los datos",
    "year": "Año",
    "light_chart": "Brillo medio de noche en el espacio, de {from} a {to}",
    "mean": "media",
    # Municipality
    "no_province": "Sin provincia: tierra en común de varios municipios",
    "act_muni": "{n} proyectos en este municipio admiten alegaciones",
    "act_muni_1": "Un proyecto en este municipio admite alegaciones",
    "h_names": "Lo que nombra a {name}",
    "muni_empty": "Ningún anuncio, incendio ni alerta vigilados nombra este municipio todavía.",
    "h_sites_in_muni": "Espacios en el municipio",
    "no_site_in_muni": "Ninguna {kind} entra en este municipio.",
    # Summary of a place
    "ha_burnt": "{ha} ha quemadas",
    "n_land": "{n} cambios de uso", "n_land_1": "{n} cambio de uso",
    "light_more_peers": "{pct} más luz de noche que otros espacios igual de oscuros",
    "that_place": "ese lugar",
    "that_signal": "ese aviso",
    "not_found": "No encuentro {what}.",
    # Signal
    "fields": {
        "comments": "Alegaciones", "promoter": "Promotor", "status": "Estado", "area": "Superficie",
        "cover": "Antes era", "permit": "Expediente", "parcels": "Parcelas catastrales que toca",
        "history": "Historia", "province": "Provincia", "water": "Agua libre", "normal": "Lo normal en ese mes",
        "flow": "Caudal", "minimum": "Caudal mínimo legal", "days_below": "Días por debajo",
        "high_risk": "Elementos de riesgo alto", "light_now": "Brillo reciente", "light_before": "Brillo en 2012-2014",
        "light_expected": "Esperable, como los igual de oscuros", "pixels": "Píxeles VIIRS",
        "migration": "Migración prevista", "precision": "Precisión",
    },
    "normal_value": "{ha} ha (mediana de {from}-{to})",
    "x_of_y": "{x} de {y}",
    "read_notice": "Leer el anuncio en el boletín",
    "see_nasa": "Ver el producto de la NASA",
    "see_in": "Ver en {name}",
    "signal": "Aviso",
    "where_is": "Dónde está",
    "light_series": "La serie de 2012 a hoy, en la ficha de {name}",
    "h_data": "Datos",
    "h_where": "Dónde",
    "in_no_site": "No cae dentro de ninguna {kind}.",
    "other_natura": "Otros espacios Natura 2000",
    "h_from": "De dónde sale",
    "watches": "vigila",
    "summary_here": "Aquí se resume; el original tiene todo el detalle.",
    # Shared maps
    "kinds": {
        "notice": {"tag": "Proyecto", "theme": "Proyectos en evaluación"},
        "resolution": {"tag": "Resolución", "theme": "Proyectos en evaluación"},
        "fire": {"tag": "Fuego", "theme": "Fuego"},
        "land_change": {"tag": "Suelo", "theme": "Cambios de uso del suelo"},
        "wetland_water": {"tag": "Agua", "theme": "Agua de los humedales"},
        "river_flow": {"tag": "Río", "theme": "Caudal de los ríos"},
        "power_line": {"tag": "Infraestructura", "theme": "Aerogeneradores y tendidos eléctricos"},
        "migration": {"tag": "Migración", "theme": "Migración nocturna"},
        "flood_building": {"tag": "Inundable", "theme": "Edificios en zona inundable"},
        "night_light": {"tag": "Luz", "theme": "Luz artificial de noche"},
        "wastewater": {"tag": "Depuración", "theme": "Depuración y baño"},
        "bathing_water": {"tag": "Baño", "theme": "Depuración y baño"},
    },
    "precision": {
        "parcelas": "cruce por parcelas", "municipio": "cruce por municipio", "perimetro": "perímetro Sentinel-2",
        "focos": "extensión de los focos", "pixeles": "píxeles Sentinel-2", "lamina": "lámina de agua",
        "punto": "punto",
    },
    "means": {
        "notice": "Un anuncio de información pública abre un plazo para que cualquier persona o entidad presente "
                  "alegaciones. Que un proyecto esté en evaluación no significa que vaya a hacerse.",
        "resolution": "La resolución cierra el procedimiento: autoriza, deniega o archiva el proyecto. El Observatorio "
                      "la empareja con el anuncio que la abrió.",
        "fire": "Incendio visto por satélite. Si ya hay perímetro de Sentinel-2, las hectáreas son las quemadas dentro "
                "del espacio; si no, la extensión de los píxeles con focos, que exagera los incendios pequeños.",
        "land_change": "Centinela compara la vegetación con imágenes de Sentinel-2. Una alerta no es una infracción: "
                       "puede ser una obra autorizada, una corta o un cambio de cultivo. Se indica si se encontró "
                       "expediente.",
        "wetland_water": "Agua libre medida con Sentinel-2, comparada con la mediana del mismo mes en años anteriores.",
        "flood_building": "Edificios del Catastro construidos después de 2016 dentro de las zonas inundables "
                          "cartografiadas por el SNCZI (flujo preferente, 100 y 500 años). Es un recuento del municipio "
                          "entero, no un hecho de un día: la fecha es la de los datos del Catastro.",
        "wastewater": "Aglomeración urbana cuya depuración no cumple la directiva europea de aguas residuales según el "
                      "último informe de España a la Agencia Europea de Medio Ambiente. Es un indicio: el punto es el "
                      "núcleo urbano, no el vertido, y la fecha es la de la situación informada.",
        "bathing_water": "Zona de baño clasificada como insuficiente en la última temporada por la calidad "
                         "microbiológica del agua. Las temporadas cuentan los años con esa misma clasificación.",
        "night_light": "Brillo medio de noche de los píxeles del espacio en las imágenes anuales del satélite VIIRS "
                       "(NASA Black Marble), de media en los dos últimos años frente a los tres primeros, y comparado "
                       "con lo que cambiaron los espacios que eran igual de oscuros: el producto sube y baja de un año "
                       "a otro en todo el país a la vez. El sensor apenas ve la luz azul de los LED blancos: una subida "
                       "es real y, si acaso, se queda corta; una bajada puede ser solo el cambio de farolas, por eso no "
                       "se avisa de las bajadas.",
    },
    "prec_note": {
        "municipio": "Este anuncio no trae parcelas: se ha cruzado el término municipal entero con el espacio, así que "
                     "el proyecto puede quedar fuera.",
    },
    "level": {"very high": "muy alta", "high": "alta", "moderate": "moderada", "low": "baja"},
    # Statuses the siblings send as canonical values, which are Spanish words.
    "status": {"provisional": "provisional", "definitivo": "definitivo", "confirmada": "confirmada"},
    "layers": {
        "proyectos": "Proyectos en evaluación", "fuego": "Incendios en 12 meses", "suelo": "Cambios de uso del suelo",
        "humedales": "Agua de los humedales", "rios": "Caudal de los ríos",
        "tendidos": "Aerogeneradores y tendidos de riesgo alto", "luz": "Luz de noche en aumento",
        "migracion": "Migración esta noche", "depuracion": "Depuración y baño",
    },
    "indicators": {
        "precise": "Proyectos dentro, por parcelas", "open": "Proyectos con plazo abierto",
        "notices": "Proyectos en su municipio", "fire_ha": "Hectáreas quemadas en 12 meses",
        "land": "Cambios de uso (solo Cantabria)", "light": "Más luz artificial de noche",
    },
    "indicator_labels": {
        "precise": "proyectos dentro según sus parcelas", "open": "proyectos con plazo abierto",
        "notices": "proyectos en su municipio", "fire_ha": "hectáreas quemadas", "land": "alertas de cambio de uso",
        "light": "% más luz de noche que otros igual de oscuros",
    },
}

_FR = {
    "title": "État des IBA",
    "examples": 'Par exemple : <a href="#/e/FR9310019">Camargue</a> · <a href="#/e/FR2510048">Baie du Mont '
                'Saint-Michel</a> · <a href="#/m/13004">Arles</a> · <a href="#/ca/53">Bretagne</a>',
    "h_map": "Tout sur une carte",
    "map_sub": "Chaque couche vient d'un projet frère (la lumière nocturne, de la NASA) et s'allume ou s'éteint dans "
               "la légende. Les sites se colorent selon ce que vous choisissez.",
    "color_by": "Colorer les sites selon",
    "h_regions": "Par région",
    "regions_sub": "Leurs {kind}, leurs consultations ouvertes et les nouveautés de la semaine. L'outre-mer n'y est "
                   "pas : Natura 2000 ne s'y applique pas.",
    "h_deadlines": "Consultations ouvertes",
    "deadlines_sub": "Projets qui touchent une {kind} et qu'on peut encore commenter, du délai le plus court au plus "
                     "long.",
    "no_deadline": "Aucun projet frère ne suit encore les consultations publiques en France.",
    "see_deadlines": "Voir les {n} consultations ouvertes",
    "h_week": "Cette semaine",
    "week_sub": "Les nouveautés des 7 derniers jours dans un site.",
    "h_ranking": "Classement",
    "map_all_label": "Carte de toutes les {kind} et de ce que suit chaque projet",
    "last_day": "dernier jour aujourd'hui",
    "days_left": "il reste {n} jours", "days_left_1": "il reste {n} jour",
    "by_muni": "par commune",
    "more_than_expected": "de plus que prévu",
    "ha_inside": "{ha} ha dedans",
    "n_open": "{n} consultations ouvertes", "n_open_1": "{n} consultation ouverte",
    "none_open": "aucune consultation ouverte",
    "n_new_week": "{n} nouveautés cette semaine", "n_new_week_1": "{n} nouveauté cette semaine",
    "nothing_new_week": "rien de neuf cette semaine",
    "and_more": "et {n} de plus",
    "nothing_new": "Rien de neuf cette semaine.",
    "h_tonight": "Cette nuit · migration prévue",
    "according_to": "selon",
    "until": "jusqu'au {date}",
    "ranking_sub": "Les {kind} concernées par « {label} », de la plus à la moins touchée. Changez le critère au-dessus "
                   "de la carte.",
    "th_site": "Site",
    "th_region": "Région",
    "no_site": "Aucun site.",
    "legend_none": "{kind} sans rien",
    "legend_max": "maximum",
    "home": "Accueil",
    "deadlines_page_sub": "{n} projets qui touchent une {kind} sont ouverts aux observations aujourd'hui. Ceux marqués "
                          "« par commune » ne donnent pas de parcelles : ils peuvent ne pas entrer dans le site.",
    "no_data_today": "pas de données aujourd'hui",
    "not_covered": "ne couvre pas cette zone",
    "by_city": "prévue par ville, pas par site",
    "night_of": "nuit du {date}",
    "n_projects": "{n} projets", "n_projects_1": "{n} projet",
    "n_with_deadline": "{n} avec consultation ouverte",
    "h_layers": "Couches",
    "layers_note": "En gris, ce qu'aucun projet ne suit ici. Que rien n'apparaisse ne veut pas dire que rien ne se "
                   "passe.",
    "double_border": "double bordure",
    "watched_nothing": "suivi, rien de neuf",
    "search": "Cherchez un site, une commune ou une région",
    "t_region": "Région",
    "t_muni": "Commune",
    "no_results": "Aucun résultat.",
    "th_projects": "Projets",
    "th_parcels": "Par parcelles",
    "th_open": "Consultation ouverte",
    "th_burnt": "Ha brûlés",
    "region_kind": "Région",
    "region_kinds": {"94": "Collectivité de Corse"},
    "code_office": "INSEE",
    "h_act": "Vous pouvez participer",
    "act_region": "{n} projets qui touchent des {kind} de la région sont ouverts aux observations",
    "act_region_1": "Un projet qui touche une {kind} de la région est ouvert aux observations",
    "week_sub_region": "Les nouveautés des 7 derniers jours dans ses sites.",
    "h_its_sites": "Ses sites",
    "its_sites_sub": "Les {kind} qui touchent une commune de {name}. Celles partagées avec une autre région "
                     "apparaissent dans les deux.",
    "no_land_site": "Aucune {kind} ne touche la terre ici.",
    "h_sea": "En mer ou sur des îlots",
    "sea_sub": "Elles ne touchent aucune commune de l'IGN ; elles vont avec la région de la côte la plus proche.",
    "h_rss": "Recevez les alertes",
    "rss_region": "Chaque nouveauté dans les sites et les communes de {name}, dans votre lecteur de flux :",
    "map_of": "Carte de {name}",
    "timeline_empty": "Rien encore dans les projets qui suivent ce site.",
    "comments_until": "observations jusqu'au {date}",
    "closed_on": "consultation close le {date}",
    "no_known_deadline": "pas de délai connu",
    "light_line": "{now} nW/cm²/sr contre {before} ; comme les sites aussi sombres, {expected} · pixels VIIRS "
                  "d'environ 500 m",
    "Before": "Avant", "After": "Après", "before": "avant", "after": "après",
    "what_means": "Qu'est-ce que cela veut dire ?",
    "h_behind": "Qui est derrière",
    "via_group": "par le groupe",
    "pct": "{n} %",
    "site_kind_line": "{kind} du réseau Natura 2000",
    "at_sea": "en mer ou sur des îlots",
    "munis": "Communes",
    "act_site": "{n} projets qui touchent ce site sont ouverts aux observations",
    "act_site_1": "Un projet qui touche ce site est ouvert aux observations",
    "anyone_can": "Toute personne ou association peut en déposer.",
    "h_happened": "Ce qui s'est passé",
    "rss_site": "Abonnez-vous avec votre lecteur de flux pour suivre chaque nouveauté dans ce site :",
    "season": {"p": "toute l'année", "r": "reproduction", "w": "hivernage", "c": "de passage"},
    "grade": {"A": "Plus de 15 % de celles de France", "B": "Entre 2 et 15 %", "C": "Moins de 2 %",
              "X": "Importantes ici, sans pourcentage dans le formulaire",
              "N": "Présentes, non évaluées dans le formulaire"},
    "no_season": "période non précisée",
    "n_species": "{n} espèces", "n_species_1": "{n} espèce",
    "other_species": "Et {n} autres espèces présentes avec une population peu significative ici ou non évaluée.",
    "other_species_1": "Et une autre espèce présente avec une population peu significative ici ou non évaluée.",
    "h_birds": "Ses oiseaux",
    "birds_sub": "Les espèces que le formulaire officiel de {name} donne pour cette {kind} : quelle part de celles de "
                 "France chacune y trouve et à quelle période de l'année.",
    "no_birds": "Le formulaire n'attribue à ce site aucune population significative d'oiseaux.",
    "birds_source": "Formulaire standard de données Natura 2000 (Agence européenne pour l'environnement, {version}), "
                    '<a href="https://creativecommons.org/licenses/by/4.0/deed.fr">CC BY 4.0</a>',
    "release_end": "fin ",
    "official_form": "fiche officielle",
    "data": "données",
    "bird_names": "noms français de TAXREF (MNHN)",
    "light_source": "NASA Black Marble (VIIRS), pixels d'environ 500 m",
    "product": "produit",
    "light_small": "Avec {n} pixels d'environ 500 m, le site est trop petit ou il manque des années pour lire une "
                   "tendance.",
    "light_small_1": "Avec {n} pixel d'environ 500 m, le site est trop petit ou il manque des années pour lire une "
                     "tendance.",
    "light_same": "autant",
    "light_more": "{pct} de plus",
    "light_less": "{pct} de moins",
    "no_value": "pas de valeur",
    "light_peers_down": "Dans les sites qui étaient aussi sombres, elle a baissé de {drift} : ici, il y a {over} de "
                        "lumière de plus que prévu.",
    "light_peers_up": "Dans les sites qui étaient aussi sombres, elle a augmenté de {drift} : ici, il y a {over} de "
                      "lumière de plus que prévu.",
    "light_peers_none": "Chaque site est comparé à ceux qui étaient aussi sombres, car le produit de la NASA monte et "
                        "descend d'une année à l'autre dans tout le pays à la fois.",
    "light_mean": "Luminosité moyenne en {span} : {value} nW/cm²/sr, {delta} qu'en {base}.",
    "light_led": "Une baisse peut n'être que le passage aux LED, que le satellite voit à peine.",
    "see_data": "Voir les données",
    "year": "Année",
    "light_chart": "Luminosité nocturne moyenne du site, de {from} à {to}",
    "mean": "moyenne",
    "no_province": "Sans département",
    "act_muni": "{n} projets dans cette commune sont ouverts aux observations",
    "act_muni_1": "Un projet dans cette commune est ouvert aux observations",
    "h_names": "Ce qui nomme {name}",
    "muni_empty": "Aucun avis, incendie ni alerte suivis ne nomme encore cette commune.",
    "h_sites_in_muni": "Sites dans la commune",
    "no_site_in_muni": "Aucune {kind} n'entre dans cette commune.",
    "ha_burnt": "{ha} ha brûlés",
    "n_land": "{n} changements d'occupation du sol", "n_land_1": "{n} changement d'occupation du sol",
    "light_more_peers": "{pct} de lumière nocturne de plus que d'autres sites aussi sombres",
    "that_place": "ce lieu",
    "that_signal": "cette alerte",
    "not_found": "Introuvable : {what}.",
    "fields": {
        "comments": "Observations", "promoter": "Porteur du projet", "status": "État", "area": "Surface",
        "cover": "Avant, c'était", "permit": "Dossier", "parcels": "Parcelles cadastrales touchées",
        "history": "Historique", "province": "Département", "water": "Eau libre", "normal": "La normale de ce mois",
        "flow": "Débit", "minimum": "Débit minimal légal", "days_below": "Jours en dessous",
        "high_risk": "Éléments à risque élevé", "light_now": "Luminosité récente",
        "light_before": "Luminosité en 2012-2014", "light_expected": "Attendue, comme les sites aussi sombres",
        "pixels": "Pixels VIIRS", "migration": "Migration prévue", "precision": "Précision",
    },
    "normal_value": "{ha} ha (médiane de {from}-{to})",
    "x_of_y": "{x} sur {y}",
    "read_notice": "Lire l'avis",
    "see_nasa": "Voir le produit de la NASA",
    "see_in": "Voir sur {name}",
    "signal": "Alerte",
    "where_is": "Où c'est",
    "light_series": "La série de 2012 à aujourd'hui, sur la fiche de {name}",
    "h_data": "Données",
    "h_where": "Où",
    "in_no_site": "Ne tombe dans aucune {kind}.",
    "other_natura": "Autres sites Natura 2000",
    "h_from": "D'où ça vient",
    "watches": "suit",
    "summary_here": "Ici on résume ; l'original a tout le détail.",
    "kinds": {
        "notice": {"tag": "Projet", "theme": "Projets en évaluation"},
        "resolution": {"tag": "Décision", "theme": "Projets en évaluation"},
        "fire": {"tag": "Feu", "theme": "Feu"},
        "land_change": {"tag": "Sol", "theme": "Changements d'occupation du sol"},
        "wetland_water": {"tag": "Eau", "theme": "Eau des zones humides"},
        "river_flow": {"tag": "Rivière", "theme": "Débit des rivières"},
        "power_line": {"tag": "Infrastructure", "theme": "Éoliennes et lignes électriques"},
        "migration": {"tag": "Migration", "theme": "Migration nocturne"},
        "flood_building": {"tag": "Inondable", "theme": "Bâtiments en zone inondable"},
        "night_light": {"tag": "Lumière", "theme": "Lumière artificielle la nuit"},
        "wastewater": {"tag": "Épuration", "theme": "Épuration et baignade"},
        "bathing_water": {"tag": "Baignade", "theme": "Épuration et baignade"},
    },
    "precision": {
        "parcelas": "croisement par parcelles", "municipio": "croisement par commune",
        "perimetro": "périmètre Sentinel-2", "focos": "étendue des foyers", "pixeles": "pixels Sentinel-2",
        "lamina": "plan d'eau", "punto": "point",
    },
    "means": {
        "notice": "Un avis d'enquête ou de consultation publique ouvre un délai pendant lequel toute personne ou "
                  "association peut déposer des observations. Qu'un projet soit en évaluation ne veut pas dire qu'il "
                  "se fera.",
        "resolution": "La décision clôt la procédure : elle autorise, refuse ou classe le projet.",
        "fire": "Incendie vu par satellite. S'il y a déjà un périmètre Sentinel-2, les hectares sont ceux brûlés dans "
                "le site ; sinon, l'étendue des pixels en feu, qui exagère les petits incendies.",
        "land_change": "On compare la végétation sur des images Sentinel-2. Une alerte n'est pas une infraction : ce "
                       "peut être un chantier autorisé, une coupe ou un changement de culture.",
        "wetland_water": "Eau libre mesurée avec Sentinel-2, comparée à la médiane du même mois les années "
                         "précédentes.",
        "flood_building": "Bâtiments du cadastre espagnol construits après 2016 dans les zones inondables "
                          "cartographiées par le SNCZI (lit majeur, crues de 100 et 500 ans). C'est un décompte de "
                          "toute la commune, pas un fait daté : la date est celle des données du cadastre.",
        "wastewater": "Agglomération d'assainissement de 2 000 EH ou plus déclarée non conforme à la directive "
                      "européenne sur les eaux résiduaires urbaines par les services de l'État (conformité "
                      "réglementaire 2024, portail de l'assainissement collectif). Le titre dit sur quoi elle ne l'est "
                      "pas : équipement, performance ou collecte. C'est le verdict de l'État, pas celui de la "
                      "Commission européenne, et il porte sur une année ; la date est celle de sa dernière mise à "
                      "jour.",
        "bathing_water": "Zone de baignade classée insuffisante la dernière saison pour la qualité microbiologique de "
                         "l'eau, d'après l'Agence européenne pour l'environnement et le ministère de la Santé. Les "
                         "saisons comptent les années avec ce même classement.",
        "night_light": "Luminosité nocturne moyenne des pixels du site dans les images annuelles du satellite VIIRS "
                       "(NASA Black Marble), en moyenne sur les deux dernières années face aux trois premières, et "
                       "comparée à l'évolution des sites qui étaient aussi sombres : le produit monte et descend d'une "
                       "année à l'autre dans tout le pays à la fois. Le capteur voit à peine la lumière bleue des LED "
                       "blanches : une hausse est réelle et plutôt sous-estimée ; une baisse peut n'être que le "
                       "changement des lampadaires, c'est pourquoi les baisses ne sont pas signalées.",
    },
    "prec_note": {
        "municipio": "Cet avis ne donne pas de parcelles : on a croisé toute la commune avec le site, le projet peut "
                     "donc être en dehors.",
    },
    "level": {"very high": "très forte", "high": "forte", "moderate": "modérée", "low": "faible"},
    "status": {"provisional": "provisoire", "definitivo": "définitif", "confirmada": "confirmée"},
    "layers": {
        "proyectos": "Projets en évaluation", "fuego": "Incendies sur 12 mois",
        "suelo": "Changements d'occupation du sol", "humedales": "Eau des zones humides",
        "rios": "Débit des rivières", "tendidos": "Éoliennes et lignes à risque élevé",
        "luz": "Lumière nocturne en hausse", "migracion": "Migration cette nuit",
        "depuracion": "Épuration et baignade",
    },
    # Only what some source watches site by site in France.
    "indicators": {
        "light": "Plus de lumière artificielle la nuit",
        "land": "Changements d'occupation du sol (Pyrénées-Atlantiques seulement)",
    },
    "indicator_labels": {
        "precise": "projets dedans selon leurs parcelles", "open": "projets avec consultation ouverte",
        "notices": "projets dans leur commune", "fire_ha": "hectares brûlés",
        "land": "alertes de changement d'occupation du sol",
        "light": "% de lumière nocturne de plus que d'autres sites aussi sombres",
    },
}

UI = {"es": _ES, "fr": _typo(_FR)}

# What Python writes itself, per language.
_PY_ES = {
    "feed_title": "{name} · Estado de las IBA",
    "feed_site": "Proyectos, fuego, cambios de uso, agua, aerogeneradores, tendidos y luz de noche en {name} ({code}).",
    "feed_region": "Proyectos, fuego, cambios de uso, agua, aerogeneradores, tendidos y luz de noche en los espacios y "
                   "municipios de {name}.",
    "feed_by_muni": "Por municipio",
    "feed_deadline": " Plazo de alegaciones hasta el {date}.",
    "no_data": "sin datos hoy",
    "no_data_note": "La fuente no respondió en la última actualización.",
    "absent": "No cubre España",
    "absent_note": "Este proyecto todavía no publica datos de España.",
    "sources": {
        "observatorio-alegaciones": ("Observatorio de alegaciones", "proyectos en evaluación ambiental"),
        "vigia-incendios": ("Vigía de incendios", "incendios"),
        "centinela-natura": ("Centinela Natura", "cambios de uso del suelo"),
        "vigilancia-humedales": ("Vigilancia de humedales", "agua de sus humedales"),
        "caudal-ecologico": ("Caudal ecológico", "caudal de sus ríos frente al mínimo legal"),
        "riesgo-tendidos-aves": ("Riesgo de tendidos para aves", "aerogeneradores y tendidos peligrosos"),
        "sub-nocte": ("Sub Nocte", "migración nocturna"),
        "zona-inundable": ("Zona inundable", "edificios construidos en zona inundable"),
        "black-marble": ("NASA Black Marble", "luz artificial de noche"),
        "depuracion-y-bano": ("Depuración y baño", "depuradoras que no cumplen y zonas de baño insuficientes"),
    },
    "light_title": "La luz artificial de noche ha subido un {pct} desde {b0}-{b1}; en los espacios igual de oscuros, "
                   "{them}",
    "light_up": "subió un {pct}", "light_down": "bajó un {pct}",
    "light_label": "Toda España",
    "light_no_years": "sin años todavía",
    "light_note": "Brillo medio de noche de los píxeles VIIRS de cada espacio, un dato por año ({span}), comparado con "
                  "los espacios que eran igual de oscuros. Solo se avisa de las subidas: el sensor no ve bien la luz "
                  "azul de los LED blancos.",
}
_PY_FR = {
    "feed_title": "{name} · État des IBA",
    "feed_site": "Lumière artificielle la nuit, épuration et baignade et, quand une source les couvre, projets, feu, "
                 "changements d'occupation du sol, eau, éoliennes et lignes électriques sur {name} ({code}).",
    "feed_region": "Lumière artificielle la nuit, épuration et baignade et, quand une source les couvre, projets, feu, "
                   "changements d'occupation du sol, eau, éoliennes et lignes électriques dans les sites et les "
                   "communes de {name}.",
    "feed_by_muni": "Par commune",
    "feed_deadline": " Observations jusqu'au {date}.",
    "no_data": "pas de données aujourd'hui",
    "no_data_note": "La source n'a pas répondu lors de la dernière mise à jour.",
    "absent": "Pas en France",
    "absent_note": "Ce projet ne publie encore aucune donnée sur la France.",
    "sources": {
        "observatorio-alegaciones": ("Observatorio de alegaciones", "les projets en évaluation environnementale"),
        "vigia-incendios": ("Vigía de incendios", "les incendies"),
        "centinela-natura": ("Centinela Natura", "les changements d'occupation du sol"),
        "vigilancia-humedales": ("Vigilancia de humedales", "l'eau de ses zones humides"),
        "caudal-ecologico": ("Caudal ecológico", "le débit de ses rivières face au minimum légal"),
        "riesgo-tendidos-aves": ("Riesgo de tendidos para aves", "les éoliennes et lignes électriques dangereuses"),
        "sub-nocte": ("Sub Nocte", "la migration nocturne"),
        "zona-inundable": ("Zona inundable", "les bâtiments construits en zone inondable"),
        "black-marble": ("NASA Black Marble", "la lumière artificielle la nuit"),
        "depuracion-y-bano": ("Depuración y baño", "les stations d'épuration non conformes et les baignades "
                                                   "insuffisantes"),
    },
    "light_title": "La lumière artificielle la nuit a augmenté de {pct} depuis {b0}-{b1} ; dans les sites aussi "
                   "sombres, elle {them}",
    "light_up": "a augmenté de {pct}", "light_down": "a baissé de {pct}",
    "light_label": "Toute la France métropolitaine",
    "light_no_years": "pas encore d'années",
    "light_note": "Luminosité nocturne moyenne des pixels VIIRS de chaque site, une valeur par an ({span}), comparée "
                  "aux sites qui étaient aussi sombres. Seules les hausses sont signalées : le capteur voit mal la "
                  "lumière bleue des LED blanches.",
}
PY = {"es": _PY_ES, "fr": _typo(_PY_FR)}


def page(country: str) -> dict:
    """What app.js reads as window.PAGE."""
    s = SETTINGS[country]
    return {"lang": s["lang"], "country": country, "locale": s["locale"], "center": s["center"], "zoom": s["zoom"],
            "shared": s["shared"]}
