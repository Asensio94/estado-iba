# Estado de las IBA

Todo lo que los proyectos hermanos saben de un lugar, en una sola página y en un solo mapa. La web muestra, para cada espacio importante para las aves de España, para cada municipio y para cada comunidad autónoma:

- los proyectos en evaluación ambiental y quién está detrás;
- el fuego y los cambios de uso del suelo;
- el agua de sus humedales y el caudal de sus ríos;
- los aerogeneradores y tendidos peligrosos, la luz artificial de noche y la migración nocturna;
- los plazos de alegaciones abiertos.

Casi nada lo mide por sí mismo: cada día reúne lo que ya publican los proyectos hermanos y enlaza cada dato a su registro. La excepción es la luz de noche, que calcula una vez al mes a partir de NASA Black Marble.

**Web:** https://asensio94.github.io/estado-iba/ · en francés, para Francia: https://asensio94.github.io/estado-iba/fr/

**Por ahora, cada ficha es una ZEPA, no una IBA.** Las IBA (*Important Bird and Biodiversity Areas*, áreas importantes para las aves y la biodiversidad) son un inventario científico de BirdLife International, que en España lleva SEO/BirdLife; no son una figura legal. Las **ZEPA** (zonas de especial protección para las aves, Directiva Aves) son la figura legal de la Red Natura 2000 que suele coincidir, en todo o en parte, con las IBA, y sus límites son datos abiertos: 658 espacios, incluidos los que son a la vez ZEC (zona especial de conservación, Directiva Hábitats) y ZEPA. En Francia la misma figura se llama ZPS. Los límites oficiales de las IBA no se usan todavía: sustituirán a las ZEPA cuando BirdLife autorice por escrito su reutilización. El código no depende de la capa: basta con cambiar `SITES_URL` y `SITE_KIND` en `estado/config.py`, siempre que los proyectos hermanos crucen con los mismos códigos.

> **Estado: activo.** Se actualiza solo y sigue en desarrollo.

## Francia

Desde la ola 0, el país es una dimensión más. Francia tiene su propia web, en francés, en `/estado-iba/fr/`, con las mismas reglas que la de España: cada dato enlazado a su fuente y el método, las exclusiones y los límites explicados en la propia página.

- **Espacios.** Las 407 ZPS (*zones de protection spéciale*) de la Francia metropolitana, Córcega incluida, del mismo servicio de la Agencia Europea de Medio Ambiente y simplificadas igual (unos 300 m). Los departamentos de ultramar no tienen espacios Natura 2000. Las IBA de Francia esperan, como las de España, al permiso por escrito de BirdLife.
- **Communes, departamentos y regiones.** IGN Admin Express COG-CARTO (Licence Ouverte 2.0). `python -m estado.cli communes` las descarga una vez al año, cuando el IGN publica el código oficial geográfico nuevo, las simplifica a unos 200 m como los municipios españoles y las guarda en `estado/ref/communes_fr.json.gz` (unos 4 MB). Cada commune se identifica por su código INSEE (Córcega usa `2A` y `2B`). Un espacio cuenta en una commune con la misma regla que en España.
- **Qué se vigila hoy.** La luz de noche (NASA Black Marble), comparada con las ZPS francesas que eran igual de oscuras, no con las españolas, y las aves de cada espacio. Los demás proyectos hermanos leen fuentes españolas: sus capas salen en gris con «Pas en France». En la portada no se dice «ninguna consulta abierta» donde nadie mira las consultas.
- **Datos aparte.** Francia escribe en `docs/fr/` sus propios `datos/hub.json`, `datos/municipios.json`, `datos/luz.json`, `sitios.geojson`, `comunidades.geojson` (regiones) y RSS. Los códigos no se mezclan nunca: `13004` es Arles para el INSEE y Albaladejo para el INE. Lo único compartido es `docs/datos/aves.json`, por `SITECODE`, con el nombre de cada especie en las dos lenguas.
- **Lengua.** Los textos de cada web están en `estado/i18n.py`, por lengua, con el mismo patrón que `humedales/i18n.py`: la página los lleva dentro (`window.I18N`) y `app.js` es el mismo para los dos países. En francés, un espacio fino de no separación (U+202F) antes de `: ; ! ? %`, dentro de `« »` y como separador de miles. Los datos no dependen de la lengua.
- **Contrato v2.** Cada señal lleva `country` y la cobertura va por país. Un `signals.json` sin `country` (v1) se sigue leyendo como España. `check` valida las dos versiones con [`signals.schema.json`](signals.schema.json). Detalle en [CONTRATO.md](CONTRATO.md#versión-2-varios-países).
- Si Francia falla en una actualización, España se publica igual.

## Qué se puede hacer en la web

- **Verlo todo en un mapa.** La portada tiene un mapa de España con una capa por proyecto hermano, que se enciende y se apaga en la leyenda. Los espacios se colorean según el indicador que se elija.
- **Buscar un lugar.** Se escribe un espacio, una comunidad o cualquiera de los 8.185 municipios. Cada lugar tiene su propio mapa con las mismas capas. La ficha de un espacio da además:
  - lo que ha pasado, mes a mes;
  - lo que admite alegaciones;
  - quién promueve cada proyecto;
  - un canal RSS propio.
- **Ver una comunidad.** Su mapa, sus plazos abiertos, lo nuevo de la semana y la tabla de sus espacios, con los marinos y los islotes aparte.
- **Ver el día.**
  - Los plazos de alegaciones que antes vencen.
  - Lo nuevo de la semana, por tema.
  - La migración prevista para esta noche.
  - La clasificación de los espacios según el indicador que se elija.
- **Cada aviso, su ficha.** Pulsar un aviso abre su ficha aquí mismo, sin salir de la página: datos, fotos de antes y después si las hay, mapa, espacios y municipios. De ahí se puede ir al proyecto que lo publica o al boletín, en otra pestaña. Cualquier enlace a otra web se abre en otra pestaña.
- **Actuar.** Cada proyecto con plazo abierto lleva en su ficha al anuncio oficial, donde se indica cómo alegar. Cada espacio y cada comunidad tienen su canal RSS: `rss/<código>.xml` y `rss/ca-<código INE>.xml`.

Las direcciones son estables y se pueden compartir: `#/ca/11` (Extremadura), `#/e/ES0000014` (Monfragüe), `#/m/10190` (Torrejón el Rubio), `#/plazos`, y cada aviso en `#/a/<proyecto>/<id>`, como `#/a/centinela-natura/CN-202609-001`.

### El mapa

Cada capa tiene su color y también su forma, para que no dependa solo del color:

| Capa | Marca |
|---|---|
| Proyectos en evaluación | cuadrado con el número de proyectos; borde doble si alguno tiene plazo abierto |
| Incendios | triángulo, mayor desde 100 ha |
| Cambios de uso del suelo | rombo |
| Agua de los humedales | círculo |
| Caudal de los ríos | anillo, mayor si ha bajado del mínimo |
| Aerogeneradores y tendidos de riesgo alto | cruz |
| Luz de noche en aumento | sol |
| Migración esta noche | estrella, mayor cuanto más alta |

Los anuncios no traen coordenadas. Por eso los proyectos se cuentan en cada municipio que nombran y, si no nombran ninguno, en el espacio. Los aerogeneradores y tendidos se marcan en un punto interior del espacio con el número de elementos de riesgo, nunca en cada aerogenerador o apoyo.

Fuera de la ficha de un municipio, el mapa muestra lo que toca alguna ZEPA, igual que las listas de debajo. En la ficha de un municipio aparece todo lo que lo nombra.

## Cómo funciona

El seguimiento de las IBA de BirdLife distingue presión, estado y respuesta. Cada proyecto hermano aporta una parte:

| Parte | Qué se ve | Fuente |
|---|---|---|
| Presión | Proyectos en información pública y sus resoluciones | [Observatorio de alegaciones](https://github.com/Asensio94/observatorio-alegaciones) |
| Presión | Incendios de los últimos 365 días, con hectáreas dentro del espacio | [Vigía de incendios](https://github.com/Asensio94/vigia-incendios) |
| Presión | Cambios de uso del suelo confirmados o provisionales | [Centinela Natura](https://github.com/Asensio94/centinela-natura) |
| Presión | Aerogeneradores, apoyos y tramos de línea con riesgo alto para las aves | [Riesgo de tendidos para aves](https://github.com/Asensio94/riesgo-tendidos-aves) |
| Presión | Subida de la luz artificial de noche frente a 2012-2014 | [NASA Black Marble](https://blackmarble.gsfc.nasa.gov/), calculada aquí cada mes |
| Estado | Agua libre frente a la mediana del mismo mes en años anteriores | [Vigilancia de humedales](https://github.com/Asensio94/vigilancia-humedales) |
| Estado | Días por debajo del caudal ecológico mínimo en los últimos 30 días | [Caudal ecológico](https://github.com/Asensio94/caudal-ecologico) |
| Referencia | Aves de cada ZEPA: época del año y parte de la población española que acoge | [Natura 2000](https://doi.org/10.2909/d713bff7-0cdf-4f0d-acd1-dc3c63af237e), Agencia Europea de Medio Ambiente, CC BY 4.0 |
| Estado | Migración nocturna prevista, por ciudad | [Sub Nocte](https://github.com/Asensio94/sub-nocte) |
| Contexto | Edificios construidos después de 2016 en zona inundable, por municipio | [Zona inundable](https://github.com/Asensio94/zona-inundable) |
| Presión | Depuradoras que no cumplen la directiva y zonas de baño insuficientes, por municipio | [Depuración y baño](https://github.com/Asensio94/depuracion-y-bano) |
| Respuesta | Plazo de alegaciones abierto, con su fecha límite | Observatorio de alegaciones |
| Contexto | Sociedad promotora → grupo → empresa cotizada | [Grafo de promotores](https://github.com/Asensio94/grafo-promotores) y [Cartera de las cotizadas](https://github.com/Asensio94/cartera-cotizadas) |

1. `estado/sources.py` descarga lo que publica cada hermano.
2. Todo se convierte en **señales**: un formato común con fecha, título, enlace, espacios, municipios, precisión y plazo. Lo describe [CONTRATO.md](CONTRATO.md). Si un hermano publica su propio `signals.json`, se lee ese; si no, o si no se puede leer, `estado/adapters.py` traduce sus ficheros internos.
3. `estado/places.py` lee los términos municipales y las comunidades autónomas del IGN (código INE) y los cruza con los espacios. También traduce a código INE los nombres de municipio que traen los hermanos y sitúa en espacio y municipio los puntos sueltos, como las estaciones de aforo.
4. `estado/indicators.py` calcula las cifras de cada espacio con funciones puras.
5. `estado/web.py` escribe `docs/`. La página (`estado/static/app.js`) es estática y se mueve entre vistas sin recargar.

Cada fuente se lee por separado. Si un hermano falla un día, su parte aparece como «sin datos hoy» y el resto se publica igual.

Este panel no tiene un índice compuesto. Sumar hectáreas quemadas y proyectos exigiría decidir cuánto pesa cada cosa, y esa decisión no es técnica. Los espacios se ordenan por el indicador que se elija.

### Luz de noche

La luz artificial desorienta a las aves que migran de noche y a los pollos de pardela que salen al mar, y atrae y mata insectos. Es la única presión que este panel mide por sí mismo, porque ningún proyecto hermano la cubre.

- **Dato.** NASA Black Marble, producto anual VNP46A4 (versión 2): la radiancia de noche del satélite VIIRS, corregida de luna, nubes y atmósfera, en una rejilla de 15″ (unos 460 × 350 m en la Península). Se usa la capa *near nadir* sin nieve, la menos deformada. Los píxeles rellenados con años anteriores no cuentan.
- **Cálculo.** El brillo de un espacio es la media de los píxeles cuyo centro cae dentro. Un espacio sin ningún centro dentro toma el píxel de su punto interior. `python -m estado.cli luz` descarga solo los años que faltan (cada año de cada tesela de 10° es un HDF5 de unos 90 MB) y guarda la serie en `docs/datos/luz.json`.
- **Deriva.** El producto sube y baja de un año a otro en todo el país a la vez, y más cuanto más oscuro es el sitio. En 2025, la mediana de los espacios con 0,02-0,2 nW/cm²/sr casi duplica su brillo de 2012-2014; los muy iluminados, en cambio, bajan. Comparar cada espacio solo consigo mismo daría avisos en media España.
- **Señal.** Se compara la media de los dos últimos años con la de 2012-2014, y con lo que cambiaron los 50 espacios que más se le parecían en brillo entonces (25 por cada lado). Hay señal si el espacio queda al menos un 25 % y al menos 0,2 nW/cm²/sr por encima de lo que tendría si hubiera cambiado como la mediana de esos 50. Cerca de la oscuridad, un cambio pequeño es un porcentaje enorme. No se juzgan los espacios de menos de 4 píxeles ni los que no tenían ninguna luz en 2012-2014, porque no hay porcentaje de nada.
- **LED.** El sensor apenas ve la luz azul de los LED blancos. Cuando un pueblo cambia sus farolas de sodio por LED, el satélite lo ve más oscuro aunque no lo esté. Por eso solo se avisa de las subidas, que son reales y, si acaso, se quedan cortas.

### Aves de cada espacio

Cada ficha dice qué aves dieron valor al espacio, para que cada presión se lea sabiendo qué hay en juego.

- **Dato.** La tabla SPECIES de la base de datos de Natura 2000 (final de 2024, revisión 1), que la Agencia Europea de Medio Ambiente publica cada año con licencia CC BY 4.0. Recoge el formulario oficial de cada espacio tal como lo envió el Estado.
- **Qué se muestra.** Para cada especie, la época en que está (todo el año, cría, inverna o en paso) y qué parte de las que hay en España acoge el espacio: más del 15 % (A), entre el 2 y el 15 % (B) o menos del 2 % (C). Una especie en varias filas, por ejemplo cría e inverna, toma la mejor. Algunos formularios dejan la parte en blanco pero valoran el espacio para la especie: salen aparte, «sin porcentaje». Otros, sobre todo en Canarias, solo nombran las especies sin evaluar nada: salen al final, «sin evaluar». Las de población poco significativa (D) solo se cuentan.
- **Qué no se muestra.** Ni el número de parejas o ejemplares del formulario ni ninguna ubicación dentro del espacio. Las filas que el Estado marca como sensibles no se publican (la base pública ya retira la mayoría), ni las de especies que el formulario da por desaparecidas.
- **Nombres.** `estado/aves_es.tsv` da el nombre en castellano de cada código de especie de la Directiva Aves: 181 del Atlas de las aves reproductoras del MITECO, 58 del Listado de especies silvestres en régimen de protección especial (Real Decreto 139/2011) y 28 puestos a mano para especies que no crían en España o que han cambiado de nombre científico. `estado/aves_fr.tsv` da el francés de las 217 especies de las ZPS francesas: la etiqueta francesa de Wikidata (CC0), que sigue la lista de la Commission de l'avifaune française, revisada a mano, y 34 puestas a mano para subespecies y nombres científicos antiguos del formulario. La API de TAXREF del Muséum ya no responde.
- `python -m estado.cli aves` descarga la base (unos 30 MB) y escribe `docs/datos/aves.json` para los dos países. En Francia, la parte de la población es la de Francia. Se ejecuta a mano cuando sale una versión nueva, cambiando antes `ZIP_URL` y `VERSION` en `estado/aves.py`.

### Vigilado no es lo mismo que tranquilo

Cada fuente declara qué espacios cubre. En el mapa de cada lugar, la capa de un hermano que no mira esa zona sale en gris con la nota «no cubre esta zona». La que la mira y no tiene nada que contar dice «vigilado, sin novedades». En las cifras, un espacio sin vigilancia vale `null`, no cero. Centinela solo cubre Cantabria. Los humedales son seis. Los caudales son 55 puntos del Júcar y el Guadiana. Los aerogeneradores y tendidos cubren Cantabria y el Estrecho. La luz de noche cubre los espacios de 4 píxeles o más. La migración se prevé por ciudad, así que en la ficha de un espacio sale en gris. Los edificios en zona inundable se cuentan por municipio y solo salen en la ficha de cada municipio. Lo mismo pasa con las depuradoras y las zonas de baño: su punto es el núcleo urbano o la playa, no el vertido, y por eso no se cruzan con los espacios.

### Comunidades autónomas

- Un municipio pertenece a la comunidad de su provincia. Los 65 terrenos que comparten varios municipios (código INE 53xxx, como las Bardenas Reales) no tienen provincia: van a la comunidad en la que cae su interior.
- Un espacio pertenece a las comunidades de sus municipios. 64 ZEPA están en más de una. Los 44 espacios que no tocan ningún municipio (marinos e islotes) van a la comunidad de la costa más cercana, y la web los muestra aparte.
- Una señal va a las comunidades de sus espacios, recortadas por las de los municipios que nombra. Si un anuncio de Navarra toca una ZEPA que Navarra comparte con Aragón, cuenta solo en Navarra.
- Ceuta y Melilla aparecen como ciudades autónomas. Gibraltar viene en la capa del IGN y se descarta.

### Precisión del cruce con proyectos

Si el anuncio del BOE trae la relación de parcelas, el Observatorio cruza esas parcelas con Natura 2000: es el cruce «por parcelas». Si no la trae, cruza el término municipal entero: es el cruce «por municipio», que solo es una aproximación. A 9 de octubre de 2026, de los 63 anuncios que tocan alguna ZEPA, 12 lo hacen por parcelas y 51 por municipio. La web marca cada caso. Los expedientes de Costas, por ejemplo, alcanzan las ZEPA marinas solo por estar en municipios del litoral. Por eso el orden por defecto usa el cruce por parcelas.

### Quién está detrás

Para cada anuncio se buscan las sociedades que lo mencionan en el Grafo de promotores. De ahí se sube a su grupo y, con la Cartera de las cotizadas, a la empresa cotizada. Cuando la cotizada solo se alcanza a través de otra sociedad del grupo, la web dice «por el grupo», porque el grupo es una inferencia del grafo y no un dato publicado. Las personas físicas nunca aparecen. A 9 de octubre de 2026 hay 115 anuncios con promotor identificado; en 61 cadenas se llega hasta una cotizada.

## Contraste

- Las 658 ZEPA coinciden con las de `natura.geojson`: 387 ZEPA y 271 ZEC y ZEPA.
- De los 8.185 municipios, 3.010 tienen alguna ZEPA. Un espacio solo cuenta para un municipio si se solapan en al menos 1 km², en el 10 % del término o en el 25 % del espacio. Así no cuentan las franjas que comparten los vecinos por la simplificación de los bordes, pero sí cuenta una colonia pequeña dentro de un término grande.
- Nombres de municipio:
  - En los anuncios del Observatorio, el 85 % de los nombres se traducen a código INE.
  - En los incendios, 128 de 137.
  - Los que no se traducen se quedan sin municipio, pero conservan su espacio.
  - «Granada» va a Granada y no a La Granada: el nombre exacto gana al que solo coincide sin artículo.
- Cada humedal cae en su ZEPA esperada:

  | Humedal | ZEPA |
  |---|---|
  | Doñana | ES0000024 |
  | Mar Menor | ES0000260 |
  | Tablas de Daimiel | ES0000013 |
  | l'Albufera | ES0000471 |
  | Fuente de Piedra | ES0000033 |
  | Gallocanta | ES0000017 |
- Fuente de Piedra mostró el problema de las lagunas temporales. En agosto suele estar seca, así que la referencia es casi cero y el cociente salía en miles de por ciento. Cuando la referencia queda por debajo del 5 % del máximo de la serie, no se calcula el porcentaje.
- Los hermanos cruzan con toda la Red Natura. Los códigos de ZEC que no son ZEPA se descartan para que no aparezcan como códigos sueltos. Si la señal nombra un municipio, se sigue viendo en él.

## Límites

- Que no aparezca algo no significa que no ocurra: solo se ve lo que vigila algún proyecto hermano.
- El Observatorio lee el BOE desde el 27 de julio de 2026: no hay proyectos anteriores. Tampoco lee aún los boletines autonómicos.
- La traducción de nombres a código INE falla con algunas denominaciones cooficiales y con homónimos sin provincia.
- Con la geometría simplificada a unos 300 m, un espacio puede ganar o perder franjas finas. Eso afecta poco a los cruces, porque cada proyecto los hace ya con su geometría completa. Sí afecta a las estaciones de aforo y a los tendidos, que se sitúan aquí.
- Un proyecto en evaluación no es un daño: es un procedimiento abierto, que puede acabar denegado.
- La cadena de propiedad es tan buena como el Grafo y la Cartera: un promotor no identificado no significa que no lo haya.
- Las aves de cada espacio son las del formulario oficial, que cada comunidad actualiza cuando puede: algunas listas son antiguas o incompletas, y la parte de la población española depende de los censos que se usaron.
- La luz de noche llega con retraso: la NASA publica cada año en la primavera siguiente. Las bajadas no se avisan, porque pueden ser solo un cambio a LED. En los espacios marinos, parte de la luz es de barcos de pesca.

### Salud de los proyectos hermanos

Cada día a las 11:00 UTC, `salud.yml` revisa todos los proyectos hermanos, no solo los que lee el panel:

1. Busca los workflows programados de cada repositorio. Avisa si su última ejecución falló o si GitHub los ha apagado. GitHub apaga los cron de un repositorio público tras 60 días sin actividad, y a los 45 ya sale un aviso.
2. Valida el `signals.json` publicado contra el contrato: campos, fechas y tipos. Un tipo que el contrato no recoge es un problema, porque el panel lo descarta sin avisar.
3. Comprueba que el `signals.json` no esté viejo según el ritmo de cada proyecto (`SIBLINGS` en `estado/config.py`).

Si encuentra algo, abre el issue «Salud de los proyectos hermanos». Cuando cambia la lista de problemas, lo comenta, y así avisa a quien vigile el repositorio. Si la lista no cambia, actualiza el informe sin avisar. Cuando ya no hay nada, lo cierra.

## Pendiente

- Cambiar las ZEPA por las IBA cuando SEO/BirdLife lo autorice. La capa original se guardará en privado y solo se publicará la geometría simplificada.
- Que cada hermano publique su propio `signals.json` según [CONTRATO.md](CONTRATO.md).
- `water_status` (estado de las masas de agua, de caudal-ecologico) se queda fuera del contrato por ahora: son casi 3.000 puntos. Si entra, mejor como una cifra por espacio.
- Indicar qué IBA no tienen ninguna ZEPA (respuesta).

## Uso

```bash
pip install -r requirements.txt
python -m pytest -q
python -m estado.cli build            # --today AAAA-MM-DD para fijar la fecha
python -m estado.cli check vigia-incendios signals.json   # un signals.json frente a su adaptador
python -m estado.cli validate vigia-incendios signals.json  # un signals.json frente al contrato
GITHUB_TOKEN=... python -m estado.cli health              # salud de todos los hermanos (--issue: actualiza el issue)
python -m estado.cli luz              # luz de noche de España y Francia (o: luz ES, luz FR); pide EARTHDATA_USERNAME y EARTHDATA_PASSWORD
python -m estado.cli aves             # aves de cada espacio desde Natura 2000 (o: aves <zip ya descargado>)
python -m estado.cli communes         # una vez al año: communes, departamentos y regiones de Francia del IGN
python -m http.server -d docs
```

El workflow `diario.yml` lo ejecuta cada día a las 08:15 UTC, después de que publiquen los proyectos hermanos, y hace commit de `docs/` (España) y `docs/fr/` (Francia). GitHub Pages sirve la rama `main`, carpeta `/docs`. El workflow `luz.yml` actualiza la luz de noche el día 2 de cada mes con la cuenta de [Earthdata Login](https://urs.earthdata.nasa.gov/) guardada en los secretos del repositorio, y rehace el panel si ha cambiado la de cualquiera de los dos países. Si falla un país, el otro se guarda igual y el workflow queda en rojo.

## Datos que se guardan

Solo `docs/`:

- La página, con `app.js` y `app.css`.
- `datos/hub.json`, con espacios, señales y cadenas.
- `datos/municipios.json`, con el nombre, la provincia, la comunidad y los espacios de cada municipio.
- `datos/luz.json`, con el brillo medio de noche de cada espacio año a año, su número de píxeles y los ficheros de la NASA de los que sale.
- `datos/aves.json`, con las aves de cada espacio: código de especie, épocas y parte de la población española, sin cifras.
- `sitios.geojson` y `comunidades.geojson`, con los límites simplificados.
- Un canal RSS por espacio y otro por comunidad.
- `fr/`, lo mismo para Francia, salvo `app.js`, `app.css` y `aves.json`, que se comparten.

No se guarda ni se publica ninguna ubicación de especies (colonias, nidos, dormideros ni territorios). De los aerogeneradores y tendidos solo se publica cuántos elementos de riesgo hay en cada espacio, nunca qué especies los usan. Tampoco se guarda ningún dato personal: las personas físicas del Grafo se descartan.

## Fuentes y licencias

- Red Natura 2000: Agencia Europea de Medio Ambiente, vía el Vigía de incendios.
- Términos municipales, provincias y comunidades: Instituto Geográfico Nacional, vía [es-atlas](https://github.com/martgnz/es-atlas) (CC BY 4.0).
- Anuncios y resoluciones: Boletín Oficial del Estado, vía el Observatorio de alegaciones.
- Focos y superficie quemada: NASA FIRMS y Copernicus Sentinel-2, vía el Vigía de incendios.
- Cambio de uso: Copernicus Sentinel-2, vía Centinela Natura.
- Agua: Copernicus Sentinel-2, vía Vigilancia de humedales.
- Caudal: SAIH del Júcar y del Guadiana y planes hidrológicos, vía Caudal ecológico.
- Aerogeneradores y tendidos: © colaboradores de OpenStreetMap, vía Riesgo de tendidos para aves.
- Migración: radares meteorológicos europeos, vía Sub Nocte.
- Luz de noche: NASA Black Marble, VNP46A4 versión 2 ([doi:10.5067/VIIRS/VNP46A4.002](https://doi.org/10.5067/VIIRS/VNP46A4.002)), datos abiertos de la NASA.
- Zonas inundables: SNCZI (MITECO) y Catastro, vía Zona inundable.
- Depuración y zonas de baño: informe de España a la AEMA (Directiva 91/271/CEE) y Náyade, vía Depuración y baño.
- Sociedades y grupos: BOE y BORME, vía el Grafo de promotores y la Cartera de las cotizadas.
- Francia: ZPS de la Agencia Europea de Medio Ambiente (CC BY 4.0); communes, departamentos y regiones de IGN Admin Express COG-CARTO (Licence Ouverte 2.0); nombres franceses de las aves de Wikidata (CC0).
- Mapa: © colaboradores de OpenStreetMap.
- Código con licencia MIT.

---

Forma parte de [Terra Aperta](https://asensio94.github.io/terra-aperta/), un conjunto de proyectos hermanos de datos abiertos sobre naturaleza: [Sub Nocte](https://github.com/Asensio94/sub-nocte) · [Vigía de incendios](https://github.com/Asensio94/vigia-incendios) · [Centinela Natura](https://github.com/Asensio94/centinela-natura) · [Estado de las IBA](https://github.com/Asensio94/estado-iba) · [Riesgo de tendidos para aves](https://github.com/Asensio94/riesgo-tendidos-aves) · [Observatorio de alegaciones](https://github.com/Asensio94/observatorio-alegaciones) · [Grafo de promotores](https://github.com/Asensio94/grafo-promotores) · [Vigilancia de humedales](https://github.com/Asensio94/vigilancia-humedales) · [Caudal ecológico](https://github.com/Asensio94/caudal-ecologico) · [Acuíferos de Francia](https://github.com/Asensio94/acuiferos-francia) · [Depuración y baño](https://github.com/Asensio94/depuracion-y-bano) · [Construir en zona inundable](https://github.com/Asensio94/zona-inundable).
