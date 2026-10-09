# Estado de las IBA

Todo lo que los proyectos hermanos saben de un lugar, en una sola página. La web muestra, para cada espacio importante para las aves de España y para cada municipio:

- los proyectos en evaluación ambiental y quién está detrás;
- el fuego y los cambios de uso del suelo;
- el agua de sus humedales y el caudal de sus ríos;
- los tendidos peligrosos y la migración nocturna;
- los plazos de alegaciones abiertos.

No mide nada por sí mismo. Cada día reúne lo que ya publican los proyectos hermanos y enlaza cada dato a su registro.

**Web:** https://asensio94.github.io/estado-iba/

Por ahora la unidad son las **ZEPA** de la Red Natura 2000, que son datos abiertos: 658 espacios, incluidos los que son a la vez ZEC y ZEPA. Las IBA de SEO/BirdLife sustituirán a las ZEPA cuando su reutilización esté acordada. El código no depende de la capa: basta con cambiar `SITES_URL` y `SITE_KIND` en `estado/config.py`, siempre que los proyectos hermanos crucen con los mismos códigos.

## Qué se puede hacer en la web

- **Buscar un lugar.** Se escribe un espacio o cualquiera de los 8.185 municipios. La ficha de un espacio da:
  - lo que ha pasado, mes a mes;
  - lo que admite alegaciones;
  - quién promueve cada proyecto;
  - qué proyectos lo vigilan y cuáles no;
  - un canal RSS propio.
- **Ver el día.**
  - Los plazos de alegaciones que antes vencen.
  - Lo nuevo de la semana, por tema.
  - La migración prevista para esta noche.
  - Un mapa con la clasificación de los espacios según el indicador que se elija.
- **Actuar.** Cada proyecto con plazo abierto enlaza al anuncio oficial, donde se indica cómo alegar. Cada espacio tiene su canal RSS: `rss/<código>.xml`.

Las direcciones son estables y se pueden compartir: `#/e/ES0000014` (Monfragüe), `#/m/10190` (Torrejón el Rubio), `#/plazos`.

## Cómo funciona

El seguimiento de las IBA de BirdLife distingue presión, estado y respuesta. Cada proyecto hermano aporta una parte:

| Parte | Qué se ve | Fuente |
|---|---|---|
| Presión | Proyectos en información pública y sus resoluciones | [Observatorio de alegaciones](https://github.com/Asensio94/observatorio-alegaciones) |
| Presión | Incendios de los últimos 365 días, con hectáreas dentro del espacio | [Vigía de incendios](https://github.com/Asensio94/vigia-incendios) |
| Presión | Cambios de uso del suelo confirmados o provisionales | [Centinela Natura](https://github.com/Asensio94/centinela-natura) |
| Presión | Apoyos y vanos con riesgo alto para las aves | [Riesgo de tendidos para aves](https://github.com/Asensio94/riesgo-tendidos-aves) |
| Estado | Agua libre frente a la mediana del mismo mes en años anteriores | [Vigilancia de humedales](https://github.com/Asensio94/vigilancia-humedales) |
| Estado | Días por debajo del caudal ecológico mínimo en los últimos 30 días | [Caudal ecológico](https://github.com/Asensio94/caudal-ecologico) |
| Estado | Migración nocturna prevista, por ciudad | [Sub Nocte](https://github.com/Asensio94/sub-nocte) |
| Respuesta | Plazo de alegaciones abierto, con su fecha límite | Observatorio de alegaciones |
| Contexto | Sociedad promotora → grupo → empresa cotizada | [Grafo de promotores](https://github.com/Asensio94/grafo-promotores) y [Cartera de las cotizadas](https://github.com/Asensio94/cartera-cotizadas) |

1. `estado/sources.py` descarga lo que publica cada hermano.
2. `estado/adapters.py` convierte lo publicado en **señales**: un formato común con fecha, título, enlace, espacios, municipios, precisión y plazo. Lo describe [CONTRATO.md](CONTRATO.md). Cuando un hermano publique su propio `signals.json`, su adaptador se reducirá a leerlo.
3. `estado/places.py` lee los términos municipales del IGN (código INE) y los cruza con los espacios. También traduce a código INE los nombres de municipio que traen los hermanos y sitúa en espacio y municipio los puntos sueltos, como las estaciones de aforo.
4. `estado/indicators.py` calcula las cifras de cada espacio con funciones puras.
5. `estado/web.py` escribe `docs/`. La página (`estado/static/app.js`) es estática y se mueve entre vistas sin recargar.

Cada fuente se lee por separado. Si un hermano falla un día, su parte aparece como «sin datos hoy» y el resto se publica igual.

Este panel no tiene un índice compuesto. Sumar hectáreas quemadas y proyectos exigiría decidir cuánto pesa cada cosa, y esa decisión no es técnica. Los espacios se ordenan por el indicador que se elija.

### Vigilado no es lo mismo que tranquilo

Cada fuente declara qué espacios cubre. En la ficha, «no vigila este espacio» y «sin novedades» se muestran distinto, y en las cifras un espacio sin vigilancia vale `null`, no cero. Centinela solo cubre Cantabria. Los humedales son seis. Los caudales son 55 puntos del Júcar y el Guadiana. Los tendidos cubren Cantabria y el Estrecho.

### Precisión del cruce con proyectos

Si el anuncio del BOE trae la relación de parcelas, el Observatorio cruza esas parcelas con Natura 2000: es el cruce «por parcelas». Si no la trae, cruza el término municipal entero: es el cruce «por municipio», que solo es una aproximación. A 9 de octubre de 2026, de los 63 anuncios que tocan alguna ZEPA, 12 lo hacen por parcelas y 51 por municipio. La web marca cada caso. Los expedientes de Costas, por ejemplo, alcanzan las ZEPA marinas solo por estar en municipios del litoral. Por eso el orden por defecto usa el cruce por parcelas.

### Quién está detrás

Para cada anuncio se buscan las sociedades que lo mencionan en el Grafo de promotores. De ahí se sube a su grupo y, con la Cartera de las cotizadas, a la empresa cotizada. Cuando la cotizada solo se alcanza a través de otra sociedad del grupo, la web dice «por el grupo», porque el grupo es una inferencia del grafo y no un dato publicado. Las personas físicas nunca aparecen. A 9 de octubre de 2026 hay 115 anuncios con promotor identificado; en 61 cadenas se llega hasta una cotizada.

## Contraste

- Las 658 ZEPA coinciden con las de `natura.geojson`: 387 ZEPA y 271 ZEC y ZEPA.
- De los 8.185 municipios, 2.990 tienen alguna ZEPA. Un espacio solo cuenta para un municipio si lo cubre en al menos 1 km² o en el 10 % de su término. Así no cuentan las franjas que comparten los vecinos por la simplificación de los bordes.
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

## Pendiente

- Cambiar las ZEPA por las IBA cuando SEO/BirdLife lo autorice. La capa original se guardará en privado y solo se publicará la geometría simplificada.
- Que cada hermano publique su propio `signals.json` según [CONTRATO.md](CONTRATO.md).
- Enlazar el caudal a su web cuando Caudal ecológico active GitHub Pages.
- Añadir el brillo nocturno (VIIRS Black Marble) como presión.
- Indicar qué IBA no tienen ninguna ZEPA (respuesta).

## Uso

```bash
pip install -r requirements.txt
python -m pytest -q
python -m estado.cli build            # --today AAAA-MM-DD para fijar la fecha
python -m http.server -d docs
```

El workflow `diario.yml` lo ejecuta cada día a las 08:15 UTC, después de que publiquen los proyectos hermanos, y hace commit de `docs/`. GitHub Pages sirve la rama `main`, carpeta `/docs`.

## Datos que se guardan

Solo `docs/`:

- La página, con `app.js` y `app.css`.
- `datos/hub.json`, con espacios, señales y cadenas.
- `datos/municipios.json`, con el nombre, la provincia y los espacios de cada municipio.
- `sitios.geojson`, con los límites simplificados.
- Un canal RSS por espacio.

No se guarda ni se publica ninguna ubicación de especies (colonias, nidos, dormideros ni territorios). De los tendidos solo se publica cuántos elementos de riesgo hay en cada espacio, nunca qué especies los usan. Tampoco se guarda ningún dato personal: las personas físicas del Grafo se descartan.

## Fuentes y licencias

- Red Natura 2000: Agencia Europea de Medio Ambiente, vía el Vigía de incendios.
- Términos municipales: Instituto Geográfico Nacional, vía [es-atlas](https://github.com/martgnz/es-atlas) (CC BY 4.0).
- Anuncios y resoluciones: Boletín Oficial del Estado, vía el Observatorio de alegaciones.
- Focos y superficie quemada: NASA FIRMS y Copernicus Sentinel-2, vía el Vigía de incendios.
- Cambio de uso: Copernicus Sentinel-2, vía Centinela Natura.
- Agua: Copernicus Sentinel-2, vía Vigilancia de humedales.
- Caudal: SAIH del Júcar y del Guadiana y planes hidrológicos, vía Caudal ecológico.
- Tendidos: © colaboradores de OpenStreetMap, vía Riesgo de tendidos para aves.
- Migración: radares meteorológicos europeos, vía Sub Nocte.
- Sociedades y grupos: BOE y BORME, vía el Grafo de promotores y la Cartera de las cotizadas.
- Mapa: © colaboradores de OpenStreetMap.
- Código con licencia MIT.

---

Proyectos hermanos: [Observatorio de alegaciones](https://github.com/Asensio94/observatorio-alegaciones) · [Vigía de incendios](https://github.com/Asensio94/vigia-incendios) · [Centinela Natura](https://github.com/Asensio94/centinela-natura) · [Vigilancia de humedales](https://github.com/Asensio94/vigilancia-humedales) · [Caudal ecológico](https://github.com/Asensio94/caudal-ecologico) · [Sub Nocte](https://github.com/Asensio94/sub-nocte) · [Riesgo de tendidos para aves](https://github.com/Asensio94/riesgo-tendidos-aves) · [Grafo de promotores](https://github.com/Asensio94/grafo-promotores) · [Cartera de las cotizadas](https://github.com/Asensio94/cartera-cotizadas) · [Cuaderno de campo](https://github.com/Asensio94/cuaderno-campo)
