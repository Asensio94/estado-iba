"""Night light: pixels of each site, reading a Black Marble tile and keeping the series up to date."""
import json
from datetime import date

import h5py
import numpy as np
import pytest
import requests
from shapely import box

from estado import luz as L

P = 1 / L.PER_DEGREE
# Tile h17v04 starts at 10° W, 50° N: a box of 3 × 2 pixels just inside its corner.
SITE = box(-10 + 2 * P, 50 - 4 * P, -10 + 5 * P, 50 - 2 * P)


def test_a_site_takes_the_pixels_whose_centre_is_inside():
    idx = L.pixel_index({"ES1": SITE})
    assert list(idx) == ["h17v04"]
    assert sorted(idx["h17v04"]["ES1"]) == [2 * 2400 + 2, 2 * 2400 + 3, 2 * 2400 + 4, 3 * 2400 + 2, 3 * 2400 + 3, 3 * 2400 + 4]


def test_a_site_across_two_tiles_and_a_site_smaller_than_a_pixel():
    tiny = box(-3.0001, 40.0001, -3.0, 40.0002)
    idx = L.pixel_index({"ES2": box(-10 - P, 45, -10 + P, 45 + P), "ES3": tiny})
    assert sorted(idx) == ["h16v04", "h17v04"]  # one pixel on each side of 10° W
    assert len(idx["h16v04"]["ES2"]) == len(idx["h17v04"]["ES2"]) == 1
    tile, flat = L._pixel(tiny.representative_point().x, tiny.representative_point().y)
    assert tile == "h17v04" and idx[tile]["ES3"].tolist() == [flat]


def _tile(path, h=17, v=4, value=12, lat0=None):
    raw = np.full((2400, 2400), value, dtype=np.uint16)
    raw[0, 0] = 65535
    quality = np.zeros((2400, 2400), dtype=np.uint8)
    quality[0, 1], quality[0, 2], quality[0, 3] = 1, 2, 255
    with h5py.File(path, "w") as f:
        g = f.create_group("HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields")
        d = g.create_dataset(L.LAYER, data=raw)
        d.attrs["scale_factor"], d.attrs["add_offset"], d.attrs["_FillValue"] = np.array([0.1]), 0.0, np.uint16(65535)
        g.create_dataset(L.LAYER + "_Quality", data=quality)
        lat0 = 90 - 10 * v - P / 2 if lat0 is None else lat0
        g.create_dataset("lat", data=lat0 - np.arange(2400) * P)
        g.create_dataset("lon", data=-180 + 10 * h + P / 2 + np.arange(2400) * P)


def test_reading_a_tile_scales_and_drops_empty_or_filled_pixels(tmp_path):
    p = tmp_path / "VNP46A4.A2020001.h17v04.002.2025086173349.h5"
    _tile(p)
    v = L.read(p)
    assert v.shape == (2400 * 2400,)
    assert np.isnan(v[[0, 2, 3]]).all()  # fill value, filled in from other years, empty
    assert v[1] == pytest.approx(1.2) and v[4] == pytest.approx(1.2)


def test_lat_lon_as_corners_or_centres_pass_but_another_grid_is_refused(tmp_path):
    p = tmp_path / "VNP46A4.A2020001.h17v04.002.2025086173349.h5"
    _tile(p, lat0=50.0)  # what NASA's files carry: the top-left corner of each pixel
    assert L.read(p).shape == (2400 * 2400,)
    _tile(p, lat0=49.0)
    with pytest.raises(ValueError, match="rejilla"):
        L.read(p)


def _run(path, files, values, today=date(2026, 10, 13)):
    """update with the NASA side faked: `files` is year -> production, `values` year -> radiance."""
    got = []

    def list_files(tiles, bounds, session):
        return {y: {t: (f"VNP46A4.A{y}001.{t}.002.{prod}.h5", f"https://x/{y}/{t}") for t in tiles}
                for y, prod in files.items()}

    def download(url, token, session, p):
        got.append(url)
        p.write_bytes(b"")

    def read_tile(p):
        return np.full(2400 * 2400, values[int(p.name.split(".")[1][1:5])])

    doc = L.update({"ES1": SITE}, path, today, session=requests.Session(), list_files=list_files, download=download,
                   read_tile=read_tile, token=lambda s: "t")
    return doc, got


def test_only_missing_or_reprocessed_years_are_downloaded(tmp_path):
    path = tmp_path / "luz.json"
    doc, got = _run(path, {2012: "1", 2013: "1"}, {2012: 0.5, 2013: 0.7})
    assert doc["years"] == [2012, 2013] and len(got) == 2
    assert doc["sites"] == {"ES1": {"pixels": 6, "radiance": [0.5, 0.7]}}
    assert json.loads(path.read_text(encoding="utf-8")) == doc

    doc, got = _run(path, {2012: "1", 2013: "1"}, {}, today=date(2026, 11, 13))
    assert got == [] and doc["updated"] == "2026-10-13"  # nothing new: not even the date changes

    doc, got = _run(path, {2012: "1", 2013: "2", 2014: "1"}, {2013: 0.9, 2014: 1.1})
    assert got == ["https://x/2013/h17v04", "https://x/2014/h17v04"]
    assert doc["sites"]["ES1"]["radiance"] == [0.5, 0.9, 1.1]
