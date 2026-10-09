# Estado de las IBA

Una ficha por cada espacio importante para las aves de España con lo que le está pasando: proyectos en evaluación ambiental, fuego, cambios de uso del suelo y el agua de sus humedales. No mide nada por sí mismo: reúne cada día lo que ya publican los proyectos hermanos y enlaza cada cifra a su registro.

**Web:** https://asensio94.github.io/estado-iba/

Por ahora la unidad son las **ZEPA** de la Red Natura 2000 (658 espacios, incluidos los que son a la vez ZEC y ZEPA), que son datos abiertos. Las IBA de SEO/BirdLife sustituirán a las ZEPA cuando su reutilización esté acordada. El código no depende de la capa: basta con cambiar `SITES_URL` y `SITE_KIND` en `estado/config.py`, siempre que los proyectos hermanos crucen con los mismos códigos.

## Cómo funciona

El seguimiento de las IBA de BirdLife distingue presión, estado y respuesta. Este panel cubre así cada parte:

| Parte | Indicador | Fuente |
|---|---|---|
| Presión | Proyectos en información pública y sus resoluciones | [Observatorio de alegaciones](https://github.com/Asensio94/observatorio-alegaciones), `data/estado.json` |
| Presión | Incendios de los últimos 365 días, en hectáreas dentro del espacio | [Vigía de incendios](https://github.com/Asensio94/vigia-incendios), `incendios.geojson` |
| Presión | Alertas de cambio de uso confirmadas o provisionales | [Centinela Natura](https://github.com/Asensio94/centinela-natura), `alertas.geojson` |
| Estado | Agua libre frente a la mediana del mismo mes en años anteriores | [Vigilancia de humedales](https://github.com/Asensio94/vigilancia-humedales), `data/series/` |
| Respuesta | Plazo de alegaciones abierto, con su fecha límite | Observatorio de alegaciones |

1. `estado/sources.py` descarga lo publicado. Cada humedal se asigna a las ZEPA que contienen al menos el 25 % de su superficie.
2. `estado/indicators.py` calcula los indicadores de cada espacio con funciones puras. Cada indicador conserva los registros que cuenta, para que la web pueda enlazarlos.
3. `estado/web.py` escribe `docs/index.html`, `docs/panel.json` y `docs/sitios.geojson`.

Este panel no tiene un índice compuesto. Sumar hectáreas quemadas y proyectos exigiría decidir cuánto pesa cada cosa, y esa decisión no es técnica. Las fichas se ordenan por el indicador que se elija.

### Precisión del cruce con proyectos

Si el anuncio del BOE trae la relación de parcelas, el Observatorio cruza esas parcelas con Natura 2000: es el cruce «por parcelas». Si no la trae, cruza el término municipal entero: es el cruce «por municipio», que solo es una aproximación. A 9 de octubre de 2026 hay 140 cruces con ZEPA: 17 son por parcelas y 123 por municipio. Los expedientes de Costas, por ejemplo, alcanzan las ZEPA marinas por estar en municipios del litoral. Por eso la web da dos cifras separadas y ordena por defecto por el cruce por parcelas.

## Contraste

- Las 658 ZEPA coinciden con las de `natura.geojson`: 387 ZEPA y 271 ZEC y ZEPA.
- Cada humedal cae en su ZEPA esperada: Doñana ES0000024, Mar Menor ES0000260, Tablas de Daimiel ES0000013, l'Albufera ES0000471, Fuente de Piedra ES0000033 y Gallocanta ES0000017.
- Fuente de Piedra mostró el problema de las lagunas temporales: en agosto suele estar seca, así que la referencia es casi cero y el cociente salía en miles de por ciento. Cuando la referencia queda por debajo del 5 % del máximo de la serie, no se calcula el porcentaje.

## Límites

- Una ficha sin presiones no es un espacio sin problemas: solo aparecen las presiones que vigila algún proyecto hermano.
- El cambio de uso solo se vigila en Cantabria, y el agua solo en seis humedales. En el resto, la web dice que no hay vigilancia en lugar de mostrar un cero.
- El Observatorio lee el BOE desde el 27 de julio de 2026: no hay proyectos anteriores.
- Con la geometría simplificada a unos 300 m, un espacio puede ganar o perder franjas finas. Eso afecta poco a los cruces, que vienen ya hechos por cada proyecto con su geometría completa.
- Un proyecto en evaluación no es un daño: es un procedimiento abierto, que puede acabar denegado.

## Pendiente

- Cambiar las ZEPA por las IBA cuando SEO/BirdLife lo autorice: la capa original se guardará en privado y solo se publicará la geometría simplificada.
- Añadir los tendidos peligrosos cuando [Riesgo de tendidos para aves](https://github.com/Asensio94/riesgo-tendidos-aves) cubra toda España.
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

Solo `docs/`: la página, `panel.json` con las fichas y `sitios.geojson` con los límites simplificados. No se guarda ni se publica ninguna ubicación de especies (colonias, nidos, dormideros ni territorios) ni ningún dato personal.

## Fuentes y licencias

- Red Natura 2000: Agencia Europea de Medio Ambiente, vía el Vigía de incendios.
- Anuncios y resoluciones: Boletín Oficial del Estado, vía el Observatorio de alegaciones.
- Focos y superficie quemada: NASA FIRMS y Copernicus Sentinel-2, vía el Vigía de incendios.
- Cambio de uso: Copernicus Sentinel-2, vía Centinela Natura.
- Agua: Copernicus Sentinel-2, vía Vigilancia de humedales.
- Mapa: © colaboradores de OpenStreetMap.
- Código con licencia MIT.

---

Proyectos hermanos: [Observatorio de alegaciones](https://github.com/Asensio94/observatorio-alegaciones) · [Vigía de incendios](https://github.com/Asensio94/vigia-incendios) · [Centinela Natura](https://github.com/Asensio94/centinela-natura) · [Vigilancia de humedales](https://github.com/Asensio94/vigilancia-humedales) · [Sub Nocte](https://github.com/Asensio94/sub-nocte) · [Riesgo de tendidos para aves](https://github.com/Asensio94/riesgo-tendidos-aves) · [Grafo de promotores](https://github.com/Asensio94/grafo-promotores) · [Cartera de las cotizadas](https://github.com/Asensio94/cartera-cotizadas) · [Cuaderno de campo](https://github.com/Asensio94/cuaderno-campo) · [Caudal ecológico](https://github.com/Asensio94/caudal-ecologico)
