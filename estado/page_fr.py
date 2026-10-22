"""France's page shell, in French: what it covers, how, what it leaves out and where each figure comes from.

The text is written with plain spaces; `i18n._typo` sets the narrow no-break spaces of French typography.
"""

from __future__ import annotations

from . import config, i18n


def params() -> str:
    rows = [
        ("Sites", "ZPS (zones de protection spéciale) du réseau Natura 2000 en France métropolitaine, Corse "
                  "comprise, simplifiées à environ 300 m (0,003°)"),
        ("Communes", "IGN Admin Express COG-CARTO, simplifiées à environ 200 m ; un site compte dans une commune "
                     "s'ils partagent au moins 1 km², 10 % de la commune ou 25 % du site"),
        ("Région d'un site", "celles de ses communes ; s'il n'en touche aucune (sites marins), celle de la côte "
                             "la plus proche"),
        ("Changements d'occupation du sol", "les alertes que Centinela Natura publie dans les ZPS des "
                                            "Pyrénées-Atlantiques ; un site en compte une quand elle le touche"),
        ("Épuration et baignade", "agglomérations de 2 000 EH ou plus non conformes en 2024 selon les services de "
                                  "l'État, et baignades insuffisantes en 2025, rattachées à leur commune"),
        ("Lumière la nuit en hausse",
         f"luminosité moyenne des {config.LIGHT_RECENT} dernières années supérieure d'au moins "
         f"{config.LIGHT_MIN_RISE * 100:.0f} % et de {str(config.LIGHT_MIN_ABS).replace('.', ',')} nW/cm²/sr à celle "
         f"qu'elle aurait eue si elle avait évolué depuis {config.LIGHT_BASELINE[0]}-{config.LIGHT_BASELINE[1]} comme "
         f"la médiane des {2 * config.LIGHT_PEERS} ZPS françaises de luminosité la plus proche à l'époque ; seulement "
         f"les sites d'au moins {config.LIGHT_MIN_PIXELS} pixels VIIRS (environ 500 m chacun)"),
    ]
    body = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return i18n._typo(f'<table class="params"><tbody>{body}</tbody></table>')


PAGE = i18n._typo("""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
__FAVICON__
<title>État des IBA · France</title>
<meta name="description" content="Ce qui arrive aux zones de protection spéciale pour les oiseaux en France : la lumière artificielle la nuit, l'épuration et la baignade, les changements d'occupation du sol dans les Pyrénées-Atlantiques, avec chaque donnée reliée à sa source.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
/*__COMMON_CSS__*/
</style>
<link rel="stylesheet" href="../app.css?v=__VERSION__">
<link rel="alternate" hreflang="es" href="https://asensio94.github.io/estado-iba/">
</head>
<body>
<header class="site-header">
  <div>
    <h1><a href="#/">__LOGO__État des <span>IBA</span></a></h1>
    <span class="rotulo">France métropolitaine · __N_SITES__ ZPS · chaque jour · <a href="../" hreflang="es" lang="es">España</a></span>
  </div>
  <p class="lede">Ce qui arrive aux sites importants pour les oiseaux. En France, ce tableau de bord suit la lumière artificielle la nuit, mesurée par satellite sur chaque zone de protection spéciale, l'épuration des agglomérations et la qualité des baignades dans tout le pays, et les changements d'occupation du sol dans les Pyrénées-Atlantiques, avec les oiseaux qui font la valeur de chaque site. Les autres pressions suivies en Espagne (projets, feu, eau des zones humides, débit des rivières, éoliennes et lignes électriques) arriveront quand une source ouverte permettra de les suivre ici. Cherchez un site, votre commune ou votre région.</p>
  <p class="aviso-unidad">L'unité est la <b>ZPS</b> (zone de protection spéciale de Natura 2000), une donnée ouverte. Les IBA de BirdLife International, dont la LPO est le partenaire en France, entreront quand leur réutilisation sera accordée.</p>
  <div class="figures">
    <div><b>__FIG_LIGHT__</b><span>ZPS où la lumière la nuit augmente plus que dans les sites aussi sombres</span></div>
    <div><b>__FIG_LIGHT_SITES__</b><span>ZPS assez grandes pour mesurer leur lumière</span></div>
    <div><b>__N_MUNIS__</b><span>communes qui touchent une ZPS</span></div>
    <div><b>__N_REGIONS__</b><span>régions</span></div>
  </div>
</header>

<main id="vista">
  <div class="wrap"><p class="vacio">Chargement…</p>
  <noscript><p>Cette page a besoin de JavaScript. Les données sont dans <a href="datos/hub.json">datos/hub.json</a>.</p></noscript></div>
</main>

<section class="method" id="metodo">
  <div>
    <h2>Méthode</h2>
    <ol>
      <li>Chaque jour, les données que publient les projets frères sont traduites en <b>signaux</b> : des faits avec une date, un lieu et un lien vers leur source. Le format, le même pour l'Espagne et la France, est décrit dans <a href="https://github.com/Asensio94/estado-iba/blob/main/CONTRATO.md">CONTRATO.md</a> et dans un <a href="https://github.com/Asensio94/estado-iba/blob/main/signals.schema.json">schéma JSON</a> : chaque signal porte son pays, et chaque commune son code INSEE.</li>
      <li><b>Ce qui est couvert en France aujourd'hui.</b> La lumière la nuit et les oiseaux de chaque site partout ; l'épuration et la baignade dans toute la France ; les changements d'occupation du sol dans les ZPS des Pyrénées-Atlantiques. Un projet frère n'entre en France que s'il publie ses signaux dans la version 2 du format, avec la France parmi les pays couverts. Les autres lisent pour l'instant des sources espagnoles (le Bulletin officiel de l'État, les débits des bassins espagnols…) : sur la carte de chaque lieu, leurs couches apparaissent en gris avec la mention « pas en France ». Ce n'est pas l'absence de problèmes, c'est l'absence de suivi.</li>
      <li><b>Lumière la nuit.</b> Une fois par mois, les images annuelles Black Marble de la NASA (satellite VIIRS, pixels d'environ 500 m) sont téléchargées et la luminosité moyenne de chaque site est calculée année par année. Comme le produit monte et descend d'une année sur l'autre dans tout le pays à la fois, chaque site est comparé aux ZPS françaises qui étaient aussi sombres en 2012-2014 : la France a ses propres références, distinctes de celles de l'Espagne. Seules les hausses sont signalées : le capteur voit à peine la lumière bleue des LED blanches, donc une baisse peut n'être que le changement des lampadaires, et une hausse est plutôt sous-estimée. Dans les sites marins, une partie de la lumière vient des navires.</li>
      <li><b>Changements d'occupation du sol.</b> <a href="https://asensio94.github.io/centinela-natura/fr/">Centinela Natura</a> compare chaque mois la végétation des ZPS des Pyrénées-Atlantiques sur les images Copernicus Sentinel-2 et signale les pertes, avec une image avant et après. Une alerte n'est pas une infraction : ce peut être un chantier autorisé, une coupe ou un changement de culture. Seul ce département est suivi : ailleurs, la couche reste grise.</li>
      <li><b>Épuration et baignade.</b> <a href="https://asensio94.github.io/depuracion-y-bano/fr/">Depuración y baño</a> reprend, pour chaque agglomération d'assainissement de 2 000 EH ou plus, le verdict de conformité réglementaire 2024 que publient les services de l'État sur le portail de l'assainissement collectif (directive 91/271/CEE), en métropole et outre-mer. Seules les agglomérations non conformes deviennent des signaux, rattachées à leur commune : elles apparaissent dans la fiche d'un site quand cette commune touche la ZPS, sans que le rejet soit forcément dans le site. Les baignades classées insuffisantes en 2025 (Agence européenne pour l'environnement et ministère de la Santé) suivent la même règle. L'assainissement non collectif et les agglomérations plus petites n'entrent pas : il n'en existe pas de données nationales ouvertes.</li>
      <li><b>Oiseaux de chaque site.</b> Ce sont ceux du formulaire officiel de chaque ZPS dans la base Natura 2000 que publie l'Agence européenne pour l'environnement une fois par an. Pour chaque espèce sont indiquées la période de présence (toute l'année, reproduction, hivernage ou passage) et la part de la population française qu'accueille le site : plus de 15 %, entre 2 et 15 % ou moins de 2 %. Les populations non significatives sont seulement comptées. Les noms français sont ceux de Wikidata, qui suivent la liste de la Commission de l'avifaune française, vérifiés à la main ; pour les sous-espèces et les noms anciens du formulaire, ils ont été donnés à la main.</li>
      <li><b>Communes et régions.</b> Elles viennent d'IGN Admin Express (COG-CARTO), téléchargé une fois par an avec le code officiel géographique. Les communes sont identifiées par leur code INSEE (2A et 2B en Corse), qui ne se mélange jamais avec les codes INE espagnols : chaque pays a ses propres fichiers.</li>
      <li>Il n'y a pas d'indice qui résume tout : mêler des hectares brûlés et des projets exigerait de décider combien pèse chaque chose, et cette décision n'est pas technique.</li>
    </ol>
    <h3>Paramètres</h3>
    __PARAMS__
  </div>
  <div>
    <h3>Pression, état et réponse</h3>
    <p>Le suivi des IBA de BirdLife International regarde les pressions, l'état et la réponse. En France, ce tableau de bord couvre pour l'instant trois pressions : la lumière artificielle la nuit, les eaux usées mal épurées (avec les baignades insuffisantes) et, dans un département, les changements d'occupation du sol. L'état des populations d'oiseaux vient de comptages qui ne sont pas publics à cette échelle ; à titre de référence, chaque fiche dit quels oiseaux ont donné sa valeur au site, selon son formulaire officiel.</p>
    <h3>Ce qui est laissé de côté</h3>
    <p>Les départements d'outre-mer n'ont pas de sites Natura 2000 : seule la France métropolitaine, Corse comprise, a des fiches de site. Les agglomérations et les baignades d'outre-mer sont dans les données ouvertes, mais ne touchent aucune ZPS. Les zones spéciales de conservation (directive Habitats) ne sont pas des sites pour les oiseaux et n'entrent pas. Les IBA de BirdLife attendent son accord écrit : rien n'en est tiré tant qu'il n'est pas donné. Les sites trop petits pour quelques pixels VIIRS n'ont pas de mesure de lumière.</p>
    <h3>À savoir avant de le citer</h3>
    <p>Une fiche sans nouveautés n'est pas un site sans problèmes : n'apparaît que ce qu'un projet frère suit, et en France c'est pour l'instant la lumière la nuit, l'épuration et la baignade, et le sol dans les Pyrénées-Atlantiques. Une agglomération non conforme dans une commune du site ne prouve pas que ses eaux arrivent dans le site. Une hausse de lumière est une mesure satellite moyenne sur le site, pas l'identification d'une source précise.</p>
    <h3>Données sur les espèces et les personnes</h3>
    <p>Aucune localisation d'espèces (colonies, nids, dortoirs ou territoires) n'est intégrée ni publiée, ni aucune donnée sur des personnes physiques. Des oiseaux de chaque site ne sont publiés que l'espèce, la période et la part de la population française, jamais le nombre d'individus, et les lignes que l'État marque comme sensibles sont écartées.</p>
    <h3>Données ouvertes</h3>
    <p><a href="datos/hub.json">hub.json</a> avec tous les signaux et les fiches · <a href="datos/municipios.json">municipios.json</a> avec les communes · <a href="datos/luz.json">luz.json</a> avec la lumière de chaque site, année par année · <a href="../datos/aves.json">aves.json</a> avec les oiseaux de chaque site, commun à l'Espagne et à la France · <a href="sitios.geojson">sitios.geojson</a> · <a href="comunidades.geojson">comunidades.geojson</a> avec les régions · un flux RSS par site dans <span class="data">rss/&lt;code&gt;.xml</span> et par région dans <span class="data">rss/ca-&lt;code INSEE&gt;.xml</span> · <a href="https://github.com/Asensio94/estado-iba/blob/main/signals.schema.json">signals.schema.json</a> · <a href="https://github.com/Asensio94/estado-iba">code</a>. Mis à jour le <span class="data">__GENERATED__</span>.</p>
  </div>
</section>

<footer class="site-footer">
  <p class="principle">Données publiques, règles visibles et chaque chiffre relié à sa source. Des indices, pas des verdicts.</p>
  <p>Réseau Natura 2000 et oiseaux de chaque site : Agence européenne pour l'environnement (CC BY 4.0) · Noms des oiseaux : Wikidata (CC0), d'après la liste de la Commission de l'avifaune française · Communes, départements et régions : IGN Admin Express (Licence Ouverte 2.0) · Lumière la nuit : NASA Black Marble (VIIRS) · Changements d'occupation du sol : Copernicus Sentinel-2 · Épuration : portail de l'assainissement collectif, ministère de la Transition écologique (Licence Ouverte) · Baignades : Agence européenne pour l'environnement et ministère de la Santé (Licence Ouverte) · Carte : © contributeurs d'OpenStreetMap · Code sous licence MIT.</p>
  <nav aria-label="Projets frères"><ul class="siblings">
    <li><a href="https://asensio94.github.io/observatorio-alegaciones/" lang="es">Observatorio de alegaciones</a></li>
    <li><a href="https://asensio94.github.io/vigia-incendios/" lang="es">Vigía de incendios</a></li>
    <li><a href="https://asensio94.github.io/centinela-natura/fr/">Centinela Natura</a></li>
    <li><a href="https://asensio94.github.io/vigilancia-humedales/" lang="es">Vigilancia de humedales</a></li>
    <li><a href="https://asensio94.github.io/sub-nocte/">Sub Nocte</a></li>
    <li><a href="https://asensio94.github.io/riesgo-tendidos-aves/" lang="es">Riesgo de tendidos para aves</a></li>
    <li><a href="https://asensio94.github.io/grafo-promotores/" lang="es">Grafo de promotores</a></li>
    <li><a href="https://asensio94.github.io/cartera-cotizadas/" lang="es">Cartera de las cotizadas</a></li>
    <li><a href="https://asensio94.github.io/cuaderno-campo/" lang="es">Cuaderno de campo</a></li>
    <li><a href="https://asensio94.github.io/caudal-ecologico/" lang="es">Caudal ecológico</a></li>
    <li><a href="https://asensio94.github.io/depuracion-y-bano/fr/">Depuración y baño</a></li>
    <li aria-current="page"><a href="https://asensio94.github.io/estado-iba/fr/">État des IBA</a></li>
  </ul></nav>
</footer>

<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
__I18N__
<script src="../app.js?v=__VERSION__"></script>
</body>
</html>
""")
