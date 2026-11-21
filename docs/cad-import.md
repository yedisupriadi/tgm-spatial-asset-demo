# CAD Parcel Import — DWG / DXF to GeoJSON

The browser demo **cannot decode DWG directly**. Convert CAD geometry to WGS84 GeoJSON, then select **Import GeoJSON** in the sidebar. The web browser stores imported data only in localStorage; it is **not** written to Supabase.

## Source requirements

1. Identify the surveyor-confirmed source CRS (EPSG or PROJ definition). A drawing in arbitrary/local coordinates requires surveyed control points and georeferencing first. **Never guess CRS.**
2. Put each legal parcel outline in a separate **closed LWPOLYLINE / 2D POLYLINE** in modelspace. Put parcel boundaries on known CAD layers.
3. Closed 2D polylines with CAD bulge arcs are supported: curved edges are flattened to straight segments at a configurable 0.02-unit default tolerance. A repeated initial/final vertex is recognized as closure even if AutoCAD's closed flag is off. Truly open, mesh, unsupported 3D, INSERT/block-only and invalid polygons remain rejected.
4. Parcel identity `CAD-<handle>` is provisional, not a cadastral/legal parcel number. Cross-reference official IDs, area and ownership before publishing.

## Windows walkthrough

Install Python and run from the repository root:

```powershell
python -m pip install -r scripts/requirements-cad.txt
python scripts/cad_parcels_to_geojson.py --input "C:\\survey\\0101.dxf" --list-layers
```

For a DWG, first **SAVEAS DXF** in AutoCAD, or install the **ODA File Converter** and check its integration with `ezdxf.addons.odafc`, then use the original DWG path in these commands. The importer never uploads the source CAD file.

After confirming the actual survey CRS and layer name:

```powershell
python scripts/cad_parcels_to_geojson.py --input "C:\\survey\\0101.dxf" --source-crs "EPSG:XXXX" --layer "PARCEL_BOUNDARY" --output "data\\survey-parcels.geojson"
```

Replace `EPSG:XXXX` and `PARCEL_BOUNDARY` with **verified values**, not examples. Multiple `--layer` arguments are allowed.

For drawings whose units are metres, `--flatten-tolerance 0.02` approximates curved edges to roughly 2 cm; this is not an independent survey accuracy claim. Arc tessellation is enabled by default, but source metadata and resulting areas must still be checked.

The command prints selected layer counts, imported/ignored entity counts, and stores a FeatureCollection of WGS84 [longitude, latitude] polygons. Compare imported positions with survey control points and independent basemap data. Coordinates inside the valid WGS84 range alone do **not** establish positional accuracy.

## Combine multiple CAD outlines into one Area record

When an **authoritative Area ID** comprises multiple disjoint polygons, preserve them as one GeoJSON `MultiPolygon` Feature rather than creating two Area records or connecting their boundaries with an invented line.

```powershell
python scripts/group_geojson_area.py --input "data\\survey-parcels.geojson" --area-code "0101" --area-title "0101 WORKSHOP AND OFFICE AREA" --output "data\\area-0101.geojson"
```

This grouping requires an explicit Area code and rejects intersecting/overlapping parts that would form an invalid MultiPolygon. Review source membership before grouping: **never automatically group different legal lots simply because they share a DXF layer**. The output retains source CAD handles as provenance and marks the geometry UNVERIFIED. The `interpros_subarea_code` is only a candidate lookup field; synchronization must resolve a matching, project-scoped `spatial_id_01_area.id` UUID and validate it.

## Browser test

1. Open the demo page, choose **Replace current local map** (export a backup first, and confirm replacement if real records exist), click **Import GeoJSON**, select the generated file.
2. The map fits the imported record(s): one MultiPolygon Feature with two parts counts as **one** asset, not two. Imported assets use unverified geometry status.
3. Refresh the page to check local persistence; use **Export GeoJSON** for a local backup. Vertex editing is intentionally disabled for MultiPolygon geometry.
4. The app accepts Polygon or MultiPolygon, and rejects malformed geometry, unexpected CRS coordinate ranges, duplicate asset codes, and excessive import size. Source-provided positive `area_m2` is preserved during import; editing a polygon in the browser recalculates an approximate area, so certified final values should come from a project-governed backend calculation. The Python pipeline additionally checks polygon topology; browser import is **not** a replacement for GIS/survey QA.

## Security and deployment

- Do not commit private DWG/DXF, client coordinates, survey files, title certificates, or ownership details to this **public** repository without authorization.
- All writes are browser-local until an authenticated Supabase adapter is implemented.
- The SQL schema in this repo is **proposed**, not deployed. Production needs an explicit migration for the `UNVERIFIED` status and project-scoped authorization.
- Do not treat calculated polygon area as legal cadastral area.
- For INTERPROS, integrate the validated map as a protected domain module behind project membership and governed read/write APIs; do not iframe the public static demo as if it were secured.

## Automated smoke test

```powershell
python -m unittest discover -s tests -p "test_cad_import.py"
```

Reference: https://ezdxf.readthedocs.io/en/stable/addons/odafc.html
