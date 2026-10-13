# Estado de las IBA

Todo lo que los proyectos hermanos saben de un lugar, en una sola página y en un solo mapa. La web muestra, para cada espacio importante para las aves de España, para cada municipio y para cada comunidad autónoma:

- los proyectos en evaluación ambiental y quién está detrás;
- el fuego y los cambios de uso del suelo;
- el agua de sus humedales y el caudal de sus ríos;
- los aerogeneradores y tendidos peligrosos, la luz artificial de noche y la migración nocturna;
- los plazos de alegaciones abiertos.

Casi nada lo mide por sí mismo: cada día reúne lo que ya publican los proyectos hermanos y enlaza cada dato a su registro. La excepción es la luz de noche, que calcula una vez al mes a partir de NASA Black Marble.

**Web:** https://asensio94.github.io/estado-iba/

Por ahora la unidad son las **ZEPA** de la Red Natura 2000, que son datos abiertos: 658 espacios, incluidos los que son a la vez ZEC y ZEPA. Las IBA de SEO/BirdLife sustituirán a las ZEPA cuando su reutilización esté acordada. El código no depende de la capa: basta con cambiar `SITES_URL` y `SITE_KIND` en `estado/config.py`, siempre que los proyectos hermanos crucen con los mismos códigos.

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
- **Actuar.** Cada proyecto con plazo abierto enlaza al anuncio oficial, donde se indica cómo alegar. Cada espacio y cada comunidad tienen su canal RSS: `rss/<código>.xml` y `rss/ca-<código INE>.xml`.

Las direcciones son estables y se pueden compartir: `#/ca/11` (Extremadura), `#/e/ES0000014` (Monfragüe), `#/m/10190` (Torrejón el Rubio), `#/plazos`.

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
| Estado | Migración nocturna prevista, por ciudad | [Sub Nocte](https://github.com/Asensio94/sub-nocte) |
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

### Vigilado no es lo mismo que tranquilo

Cada fuente declara qué espacios cubre. En el mapa de cada lugar, la capa de un hermano que no mira esa zona sale en gris con la nota «no cubre esta zona». La que la mira y no tiene nada que contar dice «vigilado, sin novedades». En las cifras, un espacio sin vigilancia vale `null`, no cero. Centinela solo cubre Cantabria. Los humedales son seis. Los caudales son 55 puntos del Júcar y el Guadiana. Los aerogeneradores y tendidos cubren Cantabria y el Estrecho. La luz de noche cubre los espacios de 4 píxeles o más. La migración se prevé por ciudad, así que en la ficha de un espacio sale en gris.

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
- La luz de noche llega con retraso: la NASA publica cada año en la primavera siguiente. Las bajadas no se avisan, porque pueden ser solo un cambio a LED. En los espacios marinos, parte de la luz es de barcos de pesca.

## Pendiente

- Cambiar las ZEPA por las IBA cuando SEO/BirdLife lo autorice. La capa original se guardará en privado y solo se publicará la geometría simplificada.
- Que cada hermano publique su propio `signals.json` según [CONTRATO.md](CONTRATO.md).
- Indicar qué IBA no tienen ninguna ZEPA (respuesta).

## Uso

```bash
pip install -r requirements.txt
python -m pytest -q
python -m estado.cli build            # --today AAAA-MM-DD para fijar la fecha
python -m estado.cli check vigia-incendios signals.json   # un signals.json frente a su adaptador
python -m estado.cli luz              # serie de luz de noche; pide EARTHDATA_USERNAME y EARTHDATA_PASSWORD
python -m http.server -d docs
```

El workflow `diario.yml` lo ejecuta cada día a las 08:15 UTC, después de que publiquen los proyectos hermanos, y hace commit de `docs/`. GitHub Pages sirve la rama `main`, carpeta `/docs`. El workflow `luz.yml` actualiza la luz de noche el día 2 de cada mes con la cuenta de [Earthdata Login](https://urs.earthdata.nasa.gov/) guardada en los secretos del repositorio, y rehace el panel si ha cambiado.

## Datos que se guardan

Solo `docs/`:

- La página, con `app.js` y `app.css`.
- `datos/hub.json`, con espacios, señales y cadenas.
- `datos/municipios.json`, con el nombre, la provincia, la comunidad y los espacios de cada municipio.
- `datos/luz.json`, con el brillo medio de noche de cada espacio año a año, su número de píxeles y los ficheros de la NASA de los que sale.
- `sitios.geojson` y `comunidades.geojson`, con los límites simplificados.
- Un canal RSS por espacio y otro por comunidad.

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
- Sociedades y grupos: BOE y BORME, vía el Grafo de promotores y la Cartera de las cotizadas.
- Mapa: © colaboradores de OpenStreetMap.
- Código con licencia MIT.

---

Forma parte de un conjunto de proyectos hermanos: [Observatorio de alegaciones](https://asensio94.github.io/observatorio-alegaciones/) · [Vigía de incendios](https://asensio94.github.io/vigia-incendios/) · [Centinela Natura](https://asensio94.github.io/centinela-natura/) · [Vigilancia de humedales](https://asensio94.github.io/vigilancia-humedales/) · [Sub Nocte](https://asensio94.github.io/sub-nocte/) · [Riesgo de tendidos para aves](https://asensio94.github.io/riesgo-tendidos-aves/) · [Grafo de promotores](https://asensio94.github.io/grafo-promotores/) · [Cartera de las cotizadas](https://asensio94.github.io/cartera-cotizadas/) · [Cuaderno de campo](https://asensio94.github.io/cuaderno-campo/) · [Caudal ecológico](https://asensio94.github.io/caudal-ecologico/).
