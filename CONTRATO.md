# Contrato de señales

Estado de las IBA reúne lo que publican los proyectos hermanos. Para no depender del formato interno de cada uno, todo se traduce a **señales**: cada señal es un hecho con fecha, lugar y enlace a su registro original. Una señal puede ser un anuncio del BOE, un incendio, una alerta de cambio de uso, una medida de agua o caudal, o un tendido peligroso.

Hoy esa traducción la hace estado-iba (`estado/adapters.py`). Cuando un proyecto publique su propio `signals.json` con este formato, su adaptador se reduce a leerlo.

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
| `kind` | sí | Tipo de hecho: `notice`, `resolution`, `fire`, `land_change`, `wetland_water`, `river_flow`, `power_line`, `migration`. |
| `date` | sí | Fecha del hecho (`AAAA-MM-DD`): publicación, detección o medida. |
| `title` | sí | Una línea legible, en español. |
| `url` | sí | Enlace directo al registro: la web del proyecto con su ancla o la fuente oficial. |
| `sites` | no | Espacios Natura 2000 que toca, por `SITECODE`, con hectáreas si se conocen. |
| `municipalities` | no | Códigos INE de 5 cifras. |
| `precision` | sí | Cómo se ha cruzado con el lugar: `parcelas`, `municipio`, `perimetro`, `focos`, `punto`, `cuenca`. |
| `deadline` | no | Fecha límite para actuar (alegaciones). Si no es nula, la señal aparece en «Plazos abiertos». |
| `status` | no | Estado propio del proyecto (`confirmada`, `provisional`, `definitivo`…). |
| `value` | no | La magnitud principal, con su unidad. |
| `details` | no | Campos propios del proyecto que la ficha puede mostrar (promotor, potencia, clase de cambio…). |

`coverage.sites` es `null` cuando el proyecto vigila toda España, o la lista de `SITECODE` que vigila. Con eso la ficha distingue «vigilado y sin novedades» de «no vigilado».

## Llaves comunes

- **Espacio:** el `SITECODE` de Natura 2000 de la Agencia Europea de Medio Ambiente. Cuando entren las IBA, se añadirá su código de BirdLife con el mismo mecanismo.
- **Municipio:** el código INE de 5 cifras. La capa de municipios sale del IGN (`es-atlas`), con la que estado-iba resuelve los nombres de municipio que traen los anuncios del BOE.
- **Anuncio:** el identificador del BOE (`BOE-B-AAAA-NNNNN`). Es la llave para seguir el hilo del proyecto al promotor y a su grupo empresarial.

## Reglas

- Nada de ubicaciones de especies: ni colonias, ni nidos, ni dormideros, ni territorios.
- Nada de datos personales: los promotores que son personas físicas no se nombran.
- Una señal sin `url` no se publica: cada cifra tiene que poder comprobarse.
