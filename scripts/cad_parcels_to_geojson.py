#!/usr/bin/env python3
"""Import closed CAD parcel polylines to WGS84 GeoJSON without guessing CRS.

Requirements: pip install -r scripts/requirements-cad.txt
DWG reading additionally requires the ODA File Converter installed locally.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import ezdxf
from pyproj import CRS, Geod, Transformer
from shapely.geometry import Polygon
from shapely.validation import explain_validity

GEOD = Geod(ellps="WGS84")


def open_cad(path: Path):
    if not path.is_file():
        raise ValueError(f"CAD file not found: {path}")
    if path.suffix.lower() == ".dxf":
        return ezdxf.readfile(str(path))
    if path.suffix.lower() == ".dwg":
        try:
            from ezdxf.addons import odafc
            if not odafc.is_installed():
                raise RuntimeError("ODA File Converter is not installed")
            return odafc.readfile(str(path))
        except Exception as exc:
            raise ValueError(
                "Cannot decode DWG. Install ODA File Converter or use AutoCAD SAVEAS DXF. "
                f"Decoder detail: {exc}"
            ) from exc
    raise ValueError("Input must be .dwg (ODA required) or .dxf")


def entity_ring(entity):
    """Straight closed 2D polylines only; curves and meshes must be preprocessed."""
    kind = entity.dxftype()
    if kind == "LWPOLYLINE":
        if not entity.closed:
            return None, "open polyline"
        if any(abs(b) > 1e-12 for _, _, b in entity.get_points("xyb")):
            return None, "curve/bulge segment"
        vertices = entity.vertices_in_wcs()
    elif kind == "POLYLINE":
        if not entity.is_closed:
            return None, "open polyline"
        if entity.is_3d_polyline or entity.is_polygon_mesh or entity.is_poly_face_mesh:
            return None, "3D/mesh polyline"
        if any(abs(v.dxf.get("bulge", 0)) > 1e-12 for v in entity.vertices):
            return None, "curve/bulge segment"
        vertices = entity.points_in_wcs()
    else:
        return None, "unsupported entity"
    points = [(float(p.x), float(p.y)) for p in vertices]
    if len(set(points)) < 3:
        return None, "fewer than 3 distinct vertices"
    if points[0] != points[-1]:
        points.append(points[0])
    return points, None


def list_layers(path: Path):
    document = open_cad(path)
    total = Counter(e.dxf.layer for e in document.modelspace())
    closed = Counter(
        e.dxf.layer for e in document.modelspace()
        if e.dxftype() in ("LWPOLYLINE", "POLYLINE")
        and (e.closed if e.dxftype() == "LWPOLYLINE" else e.is_closed)
    )
    print("Layer\tEntities\tClosed polylines")
    for name in sorted(total):
        print(f"{name}\t{total[name]}\t{closed[name]}")


def convert(path: Path, source_crs: str, layers: list[str]):
    transformer = Transformer.from_crs(
        CRS.from_user_input(source_crs), CRS.from_epsg(4326), always_xy=True
    )
    selected = {s.casefold() for s in layers}
    features, skipped = [], Counter()
    matched = 0
    for entity in open_cad(path).modelspace():
        if entity.dxf.layer.casefold() not in selected:
            continue
        matched += 1
        ring, error = entity_ring(entity)
        if error:
            skipped[error] += 1
            continue
        coords = [transformer.transform(x, y) for x, y in ring]
        if any(
            not (-180 <= lon <= 180 and -90 <= lat <= 90)
            for lon, lat in coords
        ):
            skipped["invalid longitude/latitude"] += 1
            continue
        polygon = Polygon(coords)
        if not polygon.is_valid or polygon.area <= 0:
            skipped[f"invalid polygon: {explain_validity(polygon)}"] += 1
            continue
        area_m2, _ = GEOD.geometry_area_perimeter(polygon)
        if not abs(area_m2) > 0:
            skipped["zero geodesic area"] += 1
            continue
        handle = entity.dxf.handle
        features.append({
            "type": "Feature",
            "properties": {
                "id": f"cad-{handle}",
                "code": f"CAD-{handle}",
                "title": f"CAD Parcel {handle}",
                "asset_type": "LAND",
                "status": "UNVERIFIED",
                "area_m2": round(abs(area_m2), 2),
                "source": path.name,
                "source_crs": source_crs,
                "cad_layer": entity.dxf.layer,
                "cad_handle": handle,
                "provisional_code": True,
                "notes": "CAD boundary only: verify parcel ID, legal area and sales status.",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[round(lon, 9), round(lat, 9)] for lon, lat in coords]
                ],
            },
        })
    if not matched:
        raise ValueError(f"No modelspace entities in selected layer(s): {', '.join(layers)}")
    if not features:
        raise ValueError(f"No valid closed parcel boundaries. Skipped: {dict(skipped)}")
    return {"type": "FeatureCollection", "features": features}, matched, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--list-layers", action="store_true")
    parser.add_argument("--source-crs", help="Surveyor-confirmed EPSG/PROJ definition")
    parser.add_argument("--layer", action="append", default=[], help="Repeat for multiple parcel layers")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.list_layers:
            list_layers(args.input)
            return 0
        if not args.source_crs or not args.layer or not args.output:
            parser.error("conversion requires --source-crs, --layer and --output (CRS is never guessed)")
        result, matched, skipped = convert(args.input, args.source_crs, args.layer)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Saved {len(result['features'])} valid polygons from {matched} CAD entities to {args.output}")
        print(f"Skipped: {dict(skipped)}")
        print("IMPORTANT: CAD handles are provisional IDs. Verify location, area and legal information.")
        return 0
    except (ValueError, ezdxf.DXFError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
