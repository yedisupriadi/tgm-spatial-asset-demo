#!/usr/bin/env python3
"""Explicitly group several non-overlapping Polygon features into one Area MultiPolygon.

Run only after checking that all selected parts belong to the same Area ID.
This helper never uploads input or output files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyproj import Geod
from shapely.geometry import MultiPolygon, shape
from shapely.validation import explain_validity

GEOD = Geod(ellps="WGS84")


def group_area(feature_collection: dict, area_code: str, area_title: str) -> dict:
    if feature_collection.get("type") != "FeatureCollection":
        raise ValueError("Input must be a GeoJSON FeatureCollection")
    features = feature_collection.get("features")
    if not isinstance(features, list) or len(features) < 2:
        raise ValueError("Expected at least two Polygon Features to group")
    if not area_code.strip() or not area_title.strip():
        raise ValueError("Area code and title must be nonempty")
    if any(f.get("type") != "Feature" or f.get("geometry", {}).get("type") != "Polygon"
           for f in features):
        raise ValueError("All input features must be Polygon Features")
    polys = [shape(f["geometry"]) for f in features]
    multi = MultiPolygon(polys)
    if not multi.is_valid or multi.area <= 0:
        raise ValueError("Combined geometry invalid: " + explain_validity(multi))
    area, _ = GEOD.geometry_area_perimeter(multi)
    source_props = features[0].get("properties") or {}
    result = {
        "type": "Feature",
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [f["geometry"]["coordinates"] for f in features]
        },
        "properties": {
            "id": "area-" + area_code,
            "code": area_code,
            "title": area_title,
            "interpros_subarea_code": area_code,
            "asset_type": "LAND",
            "status": "UNVERIFIED",
            "area_m2": round(abs(area), 2),
            "geometry_parts": len(polys),
            "cad_handles": [
                f.get("properties", {}).get("cad_handle")
                for f in features
                if f.get("properties", {}).get("cad_handle")
            ],
            "source": source_props.get("source"),
            "source_crs": source_props.get("source_crs"),
            "notes": "CAD geometry group, not a legal land area. Link by authoritative Interpros Area UUID after review."
        }
    }
    return {"type": "FeatureCollection", "features": [result]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--area-code", required=True)
    parser.add_argument("--area-title", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    source = json.loads(args.input.read_text(encoding="utf-8"))
    result = group_area(source, args.area_code.strip(), args.area_title.strip())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Created 1 MultiPolygon Area with", result["features"][0]["properties"]["geometry_parts"], "parts")
    print("Geometric area (not cadastral/legal):", result["features"][0]["properties"]["area_m2"], "m2")
    print("Output:", args.output)


if __name__ == "__main__":
    main()
