"""Build administrative region GeoJSON from cahyadsn/wilayah.

Uses only Python standard library.

Source repository (MIT):
https://github.com/cahyadsn/wilayah

Output:
  data/administrative-regions.geojson

Important:
- wilayah.sql provides hierarchy codes/names down to village level.
- wilayah_level_1_2.sql provides spatial path data for province and regency/city.
- We do NOT invent geometry for district/village rows when the source has none.
"""

from __future__ import annotations

import ast
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT = DATA_DIR / "administrative-regions.geojson"

WILAYAH_URL = "https://raw.githubusercontent.com/cahyadsn/wilayah/master/db/wilayah.sql"
BOUNDARY_URL = "https://raw.githubusercontent.com/cahyadsn/wilayah/master/db/wilayah_level_1_2.sql"


def download_text(url: str) -> str:
    print(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "TGM-Spatial-Asset-Demo/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read().decode("utf-8", errors="replace")


def level_from_code(code: str) -> str:
    parts = code.split(".")
    return {1: "PROVINCE", 2: "REGENCY", 3: "DISTRICT"}.get(len(parts), "VILLAGE")


def parent_from_code(code: str) -> str | None:
    parts = code.split(".")
    return ".".join(parts[:-1]) if len(parts) > 1 else None


def parse_hierarchy(sql: str) -> dict[str, dict]:
    # Expected source pairs look like ('11','ACEH') / ('11.01','KAB. SIMEULUE').
    pattern = re.compile(r"\('([0-9.]+)'\s*,\s*'((?:[^']|'')*)'\)")
    rows: dict[str, dict] = {}
    for code, raw_name in pattern.findall(sql):
        name = raw_name.replace("''", "'")
        rows[code] = {
            "code": code,
            "name": name,
            "level": level_from_code(code),
            "parent_code": parent_from_code(code),
            "source": "cahyadsn/wilayah",
        }
    return rows


def split_sql_values(row: str) -> list[str]:
    values, current, in_quote = [], [], False
    i = 0
    while i < len(row):
        ch = row[i]
        if ch == "'":
            if in_quote and i + 1 < len(row) and row[i + 1] == "'":
                current.extend(["'", "'"])
                i += 2
                continue
            in_quote = not in_quote
            current.append(ch)
        elif ch == "," and not in_quote:
            values.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    values.append("".join(current).strip())
    return values


def unquote(value: str) -> str | None:
    value = value.strip()
    if value.upper() == "NULL":
        return None
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def to_number(value: str | None):
    if value is None or value == "":
        return None
    try:
        n = float(value)
        return int(n) if n.is_integer() else n
    except ValueError:
        return None


def path_to_multipolygon(raw_path: str | None):
    if not raw_path:
        return None
    try:
        rings = json.loads(raw_path)
    except json.JSONDecodeError:
        # Fallback for JSON-like arrays.
        rings = ast.literal_eval(raw_path)

    polygons = []
    for ring in rings:
        if not isinstance(ring, list) or len(ring) < 3:
            continue
        converted = []
        for point in ring:
            if isinstance(point, list) and len(point) >= 2:
                lat, lng = point[0], point[1]
                converted.append([lng, lat])  # GeoJSON uses longitude, latitude.
        if len(converted) < 3:
            continue
        if converted[0] != converted[-1]:
            converted.append(converted[0])
        polygons.append([converted])

    return {"type": "MultiPolygon", "coordinates": polygons} if polygons else None


def parse_boundaries(sql: str) -> dict[str, dict]:
    result = {}
    for raw_line in sql.splitlines():
        line = raw_line.strip()
        if not line.startswith("('"):
            continue
        line = line.rstrip(",;")
        if line.startswith("(") and line.endswith(")"):
            line = line[1:-1]
        values = split_sql_values(line)
        if len(values) < 11:
            continue
        code = unquote(values[0])
        if not code:
            continue
        result[code] = {
            "name": unquote(values[1]),
            "capital": unquote(values[2]),
            "latitude": to_number(unquote(values[3])),
            "longitude": to_number(unquote(values[4])),
            "area_km2": to_number(unquote(values[7])),
            "population": to_number(unquote(values[8])),
            "geometry": path_to_multipolygon(unquote(values[9])),
        }
    return result


def main() -> None:
    hierarchy_sql = download_text(WILAYAH_URL)
    boundary_sql = download_text(BOUNDARY_URL)

    regions = parse_hierarchy(hierarchy_sql)
    boundaries = parse_boundaries(boundary_sql)

    features = []
    for code, row in sorted(regions.items()):
        spatial = boundaries.get(code, {})
        properties = {
            **row,
            "capital": spatial.get("capital"),
            "latitude": spatial.get("latitude"),
            "longitude": spatial.get("longitude"),
            "area_km2": spatial.get("area_km2"),
            "population": spatial.get("population"),
            "source_reference": "Kepmendagri dataset referenced by cahyadsn/wilayah",
        }
        features.append({
            "type": "Feature",
            "properties": properties,
            "geometry": spatial.get("geometry"),
        })

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )

    with_geometry = sum(1 for f in features if f["geometry"])
    print(f"Created {OUTPUT}")
    print(f"Total administrative rows: {len(features):,}")
    print(f"Rows with source geometry: {with_geometry:,}")
    print("District/village geometry remains null unless supplied by the source dataset.")


if __name__ == "__main__":
    main()
