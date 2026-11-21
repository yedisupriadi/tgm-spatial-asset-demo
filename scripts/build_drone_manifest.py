#!/usr/bin/env python3
"""Create a LOCAL-only drone XYZ overlay manifest from a georeferenced GeoTIFF.

Requires GDAL command-line tools on PATH (e.g., OSGeo4W Shell).
Never adds drone imagery to GitHub.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


def bounds_from_gdalinfo(info: dict) -> list[list[float]]:
    """GDAL wgs84Extent Polygon uses GeoJSON [lon,lat] coordinate order."""
    extent = info.get("wgs84Extent")
    if not isinstance(extent, dict) or extent.get("type") != "Polygon":
        raise ValueError("GeoTIFF has no usable WGS84 extent. Confirm source CRS/georeferencing.")
    rings = extent.get("coordinates")
    if not isinstance(rings, list) or not rings or len(rings[0]) < 4:
        raise ValueError("Missing GeoTIFF WGS84 footprint vertices.")
    pts = rings[0]
    if not all(
        isinstance(p, list) and len(p) >= 2
        and isinstance(p[0], (int, float)) and isinstance(p[1], (int, float))
        and -180 <= p[0] <= 180 and -85.06 <= p[1] <= 85.06
        for p in pts
    ):
        raise ValueError("GeoTIFF WGS84 footprint contains invalid coordinates.")
    south, north = min(p[1] for p in pts), max(p[1] for p in pts)
    west, east = min(p[0] for p in pts), max(p[0] for p in pts)
    if south >= north or west >= east:
        raise ValueError("GeoTIFF WGS84 footprint has zero/invalid extent.")
    if east - west >= 180:
        raise ValueError("Antimeridian-spanning rasters require a separate tiling strategy.")
    return [[round(south, 8), round(west, 8)], [round(north, 8), round(east, 8)]]


def build_manifest(info: dict, name: str, acquired: str, zmin: int, zmax: int) -> dict:
    if zmin < 0 or zmax > 22 or zmin > zmax:
        raise ValueError("Zoom range must satisfy 0 <= min <= max <= 22")
    return {
        "name": name,
        "acquiredAt": acquired,
        "minZoom": zmin,
        "maxNativeZoom": zmax,
        "bounds": bounds_from_gdalinfo(info)
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Original georeferenced TIFF")
    parser.add_argument("--name", default="Drone Orthophoto")
    parser.add_argument("--acquired", default="", help="Acquisition date, e.g. 2026-11-21")
    parser.add_argument("--min-zoom", type=int, default=15)
    parser.add_argument("--max-zoom", type=int, default=19)
    parser.add_argument("--output", type=Path, default=Path("data/drone/manifest.json"))
    args = parser.parse_args(argv)
    try:
        if not args.source.is_file():
            raise ValueError("TIFF file does not exist: " + str(args.source))
        try:
            proc = subprocess.run(["gdalinfo", "-json", str(args.source)],
                                  capture_output=True, text=True, check=True)
        except FileNotFoundError as exc:
            raise ValueError("gdalinfo command unavailable. Use OSGeo4W Shell / GDAL.") from exc
        except subprocess.CalledProcessError as exc:
            raise ValueError("gdalinfo could not read input: " + exc.stderr[:400]) from exc
        info = json.loads(proc.stdout)
        manifest = build_manifest(info, args.name, args.acquired, args.min_zoom, args.max_zoom)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print("Wrote LOCAL drone manifest:", args.output)
        print(json.dumps(manifest, indent=2))
        print("TILES NOT INCLUDED: produce XYZ PNG tiles under data/drone/tiles first.")
        return 0
    except (ValueError, json.JSONDecodeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
