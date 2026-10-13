"""python -m estado.cli luz: artificial light at night in each site, year by year, from NASA Black Marble.

VNP46A4 is the yearly composite of VIIRS night-time radiance, corrected for moonlight, clouds
and atmosphere, on a 15″ grid (~460 × 370 m in Spain) cut into 10° tiles of 2400 × 2400 pixels.
It is free but sits behind an Earthdata Login, so the job reads EARTHDATA_USERNAME and
EARTHDATA_PASSWORD from the environment. Each year of each tile is one HDF5 file of ~90 MB:
only the years the stored series lacks are downloaded, one file at a time.

A site's radiance is the mean of the pixels whose centre falls inside it; a site too small to
hold one centre takes the pixel under its representative point.
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

import numpy as np
import requests
from shapely import contains_xy, prepare

PRODUCT, VERSION = "VNP46A4", "2"
DOI = "10.5067/VIIRS/VNP46A4.002"
LAYER = "NearNadir_Composite_Snow_Free"  # the least distorted view, without snow glare
UNIT = "nW·cm⁻²·sr⁻¹"
GOOD = (0, 1)  # quality: 0 good, 1 three nights or fewer; 2 is filled in from earlier years, 255 empty
CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
TOKEN_URL = "https://urs.earthdata.nasa.gov/api/users/find_or_create_token"
PER_DEGREE = 240  # 15″ pixels
TILE = 2400


def tile_name(h: int, v: int) -> str:
    return f"h{h:02d}v{v:02d}"


def _tiles(bounds) -> list[tuple[int, int]]:
    minx, miny, maxx, maxy = bounds
    return [(h, v) for h in range(int((minx + 180) // 10), int((maxx + 180) // 10) + 1)
            for v in range(int((90 - maxy) // 10), int((90 - miny) // 10) + 1)]


def _window(shape, h: int, v: int) -> np.ndarray:
    """Flat indices of the pixels of tile h, v whose centre is inside the shape."""
    lon0, lat0 = -180 + 10 * h, 90 - 10 * v
    minx, miny, maxx, maxy = shape.bounds
    j0, j1 = max(0, math.floor((minx - lon0) * PER_DEGREE)), min(TILE, math.ceil((maxx - lon0) * PER_DEGREE))
    i0, i1 = max(0, math.floor((lat0 - maxy) * PER_DEGREE)), min(TILE, math.ceil((lat0 - miny) * PER_DEGREE))
    if j0 >= j1 or i0 >= i1:
        return np.empty(0, dtype=np.int32)
    i, j = np.mgrid[i0:i1, j0:j1]
    inside = contains_xy(shape, lon0 + (j + 0.5) / PER_DEGREE, lat0 - (i + 0.5) / PER_DEGREE)
    return (i[inside] * TILE + j[inside]).astype(np.int32)


def _pixel(x: float, y: float) -> tuple[str, int]:
    h, v = int((x + 180) // 10), int((90 - y) // 10)
    j = min(TILE - 1, int((x + 180 - 10 * h) * PER_DEGREE))
    i = min(TILE - 1, int((90 - 10 * v - y) * PER_DEGREE))
    return tile_name(h, v), i * TILE + j


def pixel_index(shapes: dict) -> dict[str, dict[str, np.ndarray]]:
    """By tile, the flat indices of each site's pixels."""
    index: dict[str, dict[str, np.ndarray]] = {}
    for code, shape in shapes.items():
        if shape.is_empty:
            continue
        prepare(shape)
        found = False
        for h, v in _tiles(shape.bounds):
            idx = _window(shape, h, v)
            if idx.size:
                index.setdefault(tile_name(h, v), {})[code] = idx
                found = True
        if not found:
            p = shape.representative_point()
            tile, flat = _pixel(p.x, p.y)
            index.setdefault(tile, {})[code] = np.array([flat], dtype=np.int32)
    return index


def granules(tiles: set[str], bounds, session: requests.Session) -> dict[int, dict[str, tuple[str, str]]]:
    """(file name, link) of every yearly file of these tiles, by year and tile; the newest production wins."""
    r = session.get(CMR_URL, params={"short_name": PRODUCT, "version": VERSION, "provider": "LAADS",
                                     "bounding_box": ",".join(f"{b:.4f}" for b in bounds), "page_size": 2000},
                    timeout=120)
    r.raise_for_status()
    entries = r.json()["feed"]["entry"]
    if len(entries) >= 2000:
        raise RuntimeError("CMR devolvió una página llena: hay que paginar")
    out: dict[int, dict[str, tuple[str, str]]] = {}
    for g in entries:
        url = next((l["href"] for l in g["links"] if l["href"].startswith("https://") and l["href"].endswith(".h5")), None)
        if not url:
            continue
        name = url.rsplit("/", 1)[1]
        parts = name.split(".")  # VNP46A4.A2012001.h17v04.002.2025086173349.h5
        year, tile = int(parts[1][1:5]), parts[2]
        if tile in tiles:
            have = out.setdefault(year, {}).get(tile)
            if have is None or have[0].split(".")[4] < parts[4]:
                out[year][tile] = (name, url)
    return out


def _token(session: requests.Session) -> str:
    user, password = os.environ.get("EARTHDATA_USERNAME"), os.environ.get("EARTHDATA_PASSWORD")
    if not user or not password:
        raise SystemExit("Faltan EARTHDATA_USERNAME y EARTHDATA_PASSWORD (cuenta de Earthdata Login de la NASA).")
    r = session.post(TOKEN_URL, auth=(user, password), timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"Earthdata Login no dio un token: HTTP {r.status_code}")
    return r.json()["access_token"]


def _download(url: str, token: str, session: requests.Session, path: Path) -> None:
    # requests drops the Authorization header when the archive redirects to the signed copy elsewhere.
    for attempt in range(3):
        try:
            with session.get(url, headers={"Authorization": f"Bearer {token}"}, stream=True, timeout=300) as r:
                r.raise_for_status()
                if "html" in r.headers.get("Content-Type", ""):
                    raise SystemExit(f"{path.name}: el archivo pidió iniciar sesión; el token no vale para LAADS")
                with open(path, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            return
        except requests.RequestException as e:
            final = isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code < 500
            if final or attempt == 2:
                raise
            time.sleep(15 * (attempt + 1))


def _scalar(x):
    x = np.asarray(x).ravel()
    return x[0].item() if x.size else None


def read(path: Path) -> np.ndarray:
    """A tile's radiance, flat, with NaN where there is no good value.

    Datasets are found by name, wherever the HDF-EOS groups put them; scale and fill come from
    the file. When the file carries its own lat/lon, the grid the job assumes is checked against it.
    """
    import h5py

    with h5py.File(path, "r") as f:
        names: dict[str, str] = {}

        def visit(name, obj):  # h5py stops at the first non-None return
            if isinstance(obj, h5py.Dataset):
                names[name.rsplit("/", 1)[-1]] = name

        f.visititems(visit)
        if LAYER not in names:
            raise ValueError(f"{path.name}: no hay {LAYER}; datasets: {sorted(names)}")
        ds = f[names[LAYER]]
        raw = ds[()]
        if raw.shape != (TILE, TILE):
            raise ValueError(f"{path.name}: {LAYER} mide {raw.shape}")
        scale, offset = _scalar(ds.attrs.get("scale_factor", 1.0)), _scalar(ds.attrs.get("add_offset", 0.0))
        fill = _scalar(ds.attrs["_FillValue"]) if "_FillValue" in ds.attrs else None
        values = raw.astype(np.float64) * scale + offset
        bad = ~np.isfinite(values)
        if fill is not None:
            bad |= raw == fill
        quality = names.get(LAYER + "_Quality")
        if quality:
            bad |= ~np.isin(f[quality][()], GOOD)
        _check_grid(f, names, path.name)
        values[bad] = np.nan
        print(f"{path.name}: {raw.dtype} × {scale} (relleno {fill}) · {1 - bad.mean():.1%} de píxeles válidos",
              file=sys.stderr)
        return values.ravel()


def _check_grid(f, names: dict[str, str], name: str) -> None:
    """The file's lat/lon must describe the 10° tile of 2400 steps the job assumes.

    NASA's files list the pixels' top-left corners (the first latitude is the tile's edge),
    other tools write their centres: either is the same grid, anything else is not.
    """
    tile = name.split(".")[2]
    h, v = int(tile[1:3]), int(tile[4:6])
    edges = {"lat": (90 - 10 * v, -1), "lon": (-180 + 10 * h, 1)}
    for axis, (edge, sign) in edges.items():
        if axis not in names:
            continue
        a = np.asarray(f[names[axis]][()], dtype=np.float64).ravel()
        step = (a[-1] - a[0]) / (a.size - 1) if a.size > 1 else 0.0
        first = (a[0] - edge) * PER_DEGREE * sign
        if a.size != TILE or abs(step * PER_DEGREE - sign) > 1e-6 or min(abs(first), abs(first - 0.5)) > 0.05:
            raise ValueError(f"{name}: la rejilla no es la esperada ({axis} de {a[0]} a {a[-1]} en {a.size} pasos, "
                             f"borde {edge})")


def _dump(doc: dict) -> str:
    """One year of files and one site per line, so a commit shows what changed."""
    out = []
    for k, v in doc.items():
        if isinstance(v, dict) and v:
            rows = ",\n".join(f"  {json.dumps(a)}: {json.dumps(x, ensure_ascii=False)}" for a, x in v.items())
            out.append(f" {json.dumps(k)}: {{\n{rows}\n }}")
        else:
            out.append(f" {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}")
    return "{\n" + ",\n".join(out) + "\n}\n"


def update(shapes: dict, path: Path, today: date, session: requests.Session | None = None, *,
           list_files=granules, download=_download, read_tile=read, token=_token) -> dict:
    """Bring the stored series up to date and write it; returns the document.

    A year is downloaded when it is missing, when NASA reprocessed one of its files, or when the
    sites changed (then every year is, so all figures come from the same pixels). The file is
    written after each year: a run cut short keeps what it finished.
    """
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", "estado-iba (+https://github.com/Asensio94/estado-iba)")
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    index = pixel_index(shapes)
    pixels: dict[str, int] = {}
    for by_site in index.values():
        for code, idx in by_site.items():
            pixels[code] = pixels.get(code, 0) + int(idx.size)
    xs = [b for s in shapes.values() if not s.is_empty for b in (s.bounds[0], s.bounds[2])]
    ys = [b for s in shapes.values() if not s.is_empty for b in (s.bounds[1], s.bounds[3])]
    files = list_files(set(index), (min(xs), min(ys), max(xs), max(ys)), session)
    ready = {y: t for y, t in files.items() if set(index) <= t.keys()}
    for y in sorted(files.keys() - ready.keys()):
        print(f"{y}: faltan teselas en la NASA ({sorted(set(index) - files[y].keys())}); se espera", file=sys.stderr)

    same = {c: s["pixels"] for c, s in old.get("sites", {}).items()} == pixels
    series = {c: dict(zip(old["years"], s["radiance"])) for c, s in old["sites"].items()} if same else {}
    used = dict(old.get("granules", {})) if same else {}
    todo = [y for y in sorted(ready) if used.get(str(y)) != sorted(n for n, _ in ready[y].values())]
    years = sorted(set(ready) | ({int(y) for y in used} if same else set()))
    print(f"{len(pixels)} espacios en {len(index)} teselas · años por descargar: {todo or 'ninguno'}", file=sys.stderr)

    def write() -> dict:
        done = [y for y in years if str(y) in used]
        doc = {"product": f"{PRODUCT} v{VERSION}", "doi": DOI, "layer": LAYER, "unit": UNIT,
               "updated": today.isoformat(), "years": done, "granules": {str(y): used[str(y)] for y in done},
               "sites": {c: {"pixels": pixels[c], "radiance": [series.get(c, {}).get(y) for y in done]}
                         for c in sorted(pixels)}}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_dump(doc), encoding="utf-8")
        return doc

    if not todo:  # nothing new: the file and its date stay as they are
        return old if same else write()
    bearer = token(session)
    for y in todo:
        sums, counts = dict.fromkeys(pixels, 0.0), dict.fromkeys(pixels, 0)
        for tile in sorted(index):
            name, url = ready[y][tile]
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / name
                download(url, bearer, session, p)
                values = read_tile(p)
            for code, idx in index[tile].items():
                v = values[idx]
                ok = ~np.isnan(v)
                sums[code] += float(v[ok].sum())
                counts[code] += int(ok.sum())
        for code in pixels:
            series.setdefault(code, {})[y] = round(sums[code] / counts[code], 3) if counts[code] else None
        used[str(y)] = sorted(n for n, _ in ready[y].values())
        doc = write()
        print(f"{y}: hecho", file=sys.stderr)
    return doc
