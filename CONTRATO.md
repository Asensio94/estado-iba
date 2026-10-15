# Contrato de señales

Estado de las IBA reúne lo que publican los proyectos hermanos. Para no depender del formato interno de cada uno, todo se traduce a **señales**: cada señal es un hecho con fecha, lugar y enlace a su registro original. Una señal puede ser un anuncio del BOE, un incendio, una alerta de cambio de uso, una medida de agua o caudal, un tendido peligroso o el recuento de edificios nuevos en zona inundable de un municipio.

Cada proyecto publica sus señales en `signals.json`, en la raíz de su web: `https://asensio94.github.io/<proyecto>/signals.json`. Estado de las IBA lo busca en cada actualización. Mientras un proyecto no lo publique, o si el fichero no se puede leer, el hub traduce sus ficheros internos como hasta ahora (`estado/adapters.py`).

## `signals.json`

```json
{
  "source": "vigia-incendios",
  "version": 1,
  "generated": "2026-10-09T07:02Z",
  "coverage": {
    "label": "Toda España",
    "sites": null,
    "note": "Focos VIIRS de NASA FIRMS; superficie quemada con Sentinel-2 cuando la hay."
  },
  "signals": [
    {
      "id": "F2026-0812",
      "kind": "fire",
      "date": "2026-08-01",
      "title": "Incendio en Navalmoral de la Mata",
      "url": "https://asensio94.github.io/vigia-incendios/#F2026-0812",
      "sites": [{"code": "ES0000014", "ha": 12.5}],
      "municipalities": ["10131"],
      "precision": "perimetro",
      "deadline": null,
      "status": "definitivo",
      "value": {"amount": 12.5, "unit": "ha"},
      "details": {}
    }
  ]
}
```

| Campo | Obligatorio | Qué es |
|---|---|---|
| `id` | sí | Identificador estable dentro del proyecto. El hub lo combina con `source`. |
| `kind` | sí | Tipo de hecho: `notice`, `resolution`, `fire`, `land_change`, `wetland_water`, `river_flow`, `power_line`, `migration`, `flood_building`, `night_light`. |
| `date` | sí | Fecha del hecho (`AAAA-MM-DD`): publicación, detección o medida. |
| `title` | sí | Una línea legible, en español. |
| `url` | sí | Enlace directo al registro: la web del proyecto con su ancla o la fuente oficial. |
| `sites` | no | Espacios Natura 2000 que toca, por `SITECODE`, con hectáreas si se conocen. |
| `municipalities` | no | Códigos INE de 5 cifras. |
| `municipality_names` | no | Nombres de municipio, si el proyecto no tiene los códigos INE. El hub los resuelve con la capa del IGN. |
| `provinces` | no | Provincias de esos municipios, para distinguir homónimos (Villanueva, Granada…). |
| `precision` | sí | Cómo se ha cruzado con el lugar: `parcelas`, `municipio`, `perimetro`, `focos`, `punto`, `lamina`, `pixeles`, `radar`. Una señal `punto` sin espacios ni municipios los recibe del hub, a partir de `details.point`. |
| `deadline` | no | Fecha límite para actuar (alegaciones). Si no es nula, la señal aparece en «Plazos abiertos». |
| `status` | no | Estado propio del proyecto (`confirmada`, `provisional`, `definitivo`…). |
| `value` | no | La magnitud principal, con su unidad. |
| `details` | no | Campos propios del proyecto que la ficha puede mostrar (promotor, potencia, clase de cambio…). Con `details.point` (`[lon, lat]`) la señal se dibuja en el mapa; sin él no se dibuja, salvo los anuncios, que se cuentan en sus municipios. |

`coverage.sites` es `null` cuando el proyecto vigila toda España, o la lista de `SITECODE` que vigila. Con eso el mapa distingue «vigilado, sin novedades» de «no cubre esta zona».

## Qué entra

- Lo vigente: los hechos que el proyecto da por buenos hoy. Una alerta descartada no es una señal.
- El hub aplica sus propias ventanas de tiempo, sea quien sea quien envíe la señal: los incendios, 365 días.
- El `id` es estable entre ejecuciones, para que los enlaces y los RSS no cambien.
- Una señal sin un campo obligatorio, o de un tipo que no está en la lista, se descarta.
- Los recuentos (`flood_building`) no tienen ventana: son un inventario, y su `date` es la fecha del dato de origen. Un recuento a cero no es una señal y se descarta.

El contrato también está escrito como JSON Schema en [`signals.schema.json`](signals.schema.json), para validarlo con cualquier herramienta. Si la tabla y el esquema no dicen lo mismo, falla un test de estado-iba.

Para comprobar un fichero antes de publicarlo, desde estado-iba:

```bash
python -m estado.cli validate vigia-incendios ruta/a/signals.json   # ¿cumple el contrato?
python -m estado.cli check vigia-incendios ruta/a/signals.json      # ¿dice lo mismo que el adaptador?
```

`validate` es estricto: un campo que no está en el contrato, una fecha mal escrita o un `kind` nuevo son errores. El panel, en cambio, lee con tolerancia: descarta la señal que no cumple y publica el resto. Por eso, si un proyecto necesita un tipo nuevo, primero se añade aquí, al esquema y a `adapters.KINDS`, y la web aprende a mostrarlo. Hasta entonces, el panel descarta esas señales.

Cada día, `salud.yml` valida el `signals.json` publicado de cada hermano y lo cuenta en el issue «Salud de los proyectos hermanos».

`check` compara el fichero con lo que el adaptador lee hoy de la web del proyecto y enumera las diferencias tal como las vería el panel.

## Tipos

| `kind` | Proyecto | Qué cuenta |
|---|---|---|
| `notice` | observatorio-alegaciones | Anuncio del BOE con trámite ambiental en información pública. |
| `resolution` | observatorio-alegaciones | Resolución que cierra el procedimiento de un anuncio. |
| `fire` | vigia-incendios | Incendio visto por satélite, con hectáreas por espacio. |
| `land_change` | centinela-natura | Alerta de cambio de cubierta vegetal. |
| `wetland_water` | vigilancia-humedales | Agua libre de un humedal frente a su referencia mensual. |
| `river_flow` | caudal-ecologico | Días bajo el caudal ecológico mínimo en una estación de aforo. |
| `power_line` | riesgo-tendidos-aves | Apoyos y vanos de riesgo alto dentro de un espacio. |
| `migration` | sub-nocte | Migración nocturna prevista en una ciudad. |
| `flood_building` | zona-inundable | Edificios construidos después de 2016 dentro de las zonas inundables del SNCZI (zona de flujo preferente, T100 y T500), uno por municipio (`precision: "municipio"`, sin `details.point`). `value` es ese número, en `edificios`; `details` lleva el recuento por zona (`zfp`, `t100`, `t500`), el total de edificios en zona inundable y el ritmo anual antes y después de 2016. `date` es la fecha del dato del Catastro. |
| `night_light` | estado-iba (NASA Black Marble) | Luz artificial de noche de un espacio que ha subido más que la de los espacios que eran igual de oscuros (satélite VIIRS, píxeles de unos 500 m, `precision: "pixeles"`). `value` es esa subida de más, en `%`. No llega por `signals.json`: el hub la calcula con datos abiertos de la NASA. |

## Llaves comunes

- **Espacio:** el `SITECODE` de Natura 2000 de la Agencia Europea de Medio Ambiente. Cuando entren las IBA, se añadirá su código de BirdLife con el mismo mecanismo.
- **Municipio:** el código INE de 5 cifras. La capa de municipios sale del IGN (`es-atlas`), con la que estado-iba resuelve los nombres de municipio que traen los anuncios del BOE.
- **Comunidad autónoma:** el código INE de 2 cifras. No hace falta enviarla: el hub la deduce de los espacios y los municipios y la añade a cada señal como `regions`.
- **Anuncio:** el identificador del BOE (`BOE-B-AAAA-NNNNN`). Es la llave para seguir el hilo del proyecto al promotor y a su grupo empresarial.

## Reglas

- Nada de ubicaciones de especies: ni colonias, ni nidos, ni dormideros, ni territorios.
- Nada de datos personales: los promotores que son personas físicas no se nombran. Los boletines las presentan con tratamiento («D.», «Dña.»); el hub deja sin promotor a quien llegue así, lo envíe quien lo envíe.
- Una señal sin `url` no se publica: cada cifra tiene que poder comprobarse.
