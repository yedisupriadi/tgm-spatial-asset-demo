# INTERPROS Spatial Area Mapping — Design Note (not deployed)

## Objective and verified boundaries

- The authoritative INTERPROS Register is `public.spatial_id_01_area`. It contains a record PK `id`, display field `area_id`, code `subarea_code`, optional `area_size_m2`, `latitude`/`longitude`, benchmarks and drone links.
- The app's `spatial_assets` table is only a **demo proposal**, not necessarily the LCI project schema.
- An Area may be **one MultiPolygon feature containing disconnected land outlines**. Do not create a new Register row for each disconnected geometry.
- A benchmark point or latitude/longitude in the Register is not enough to derive an Area boundary.
- No migration, RLS changes, or production data writes are included in this task.

## Recommended data model (logical, not executable migration)

```text
spatial_id_01_area
  id                  UUID (governed primary key)
  area_id             text (display name)
  subarea_code        text (example: 0101)
  area_size_m2        number (source business area)
       |
       | 1 to 0..1 for each project and revision
       v
project_spatial_area_geometries  [NEW, separate governed table]
  id                  UUID
  project_id          validated project scope
  spatial_area_id     FK -> spatial_id_01_area.id
  geometry            PostGIS geometry(MultiPolygon, 4326)
  geometry_area_m2    computed from PostGIS geography
  geometry_source     DXF / survey / GIS provenance
  geometry_crs        original EPSG
  source_document_ref protected storage pointer
  revision/status     revision, reviewed/approved flags
  updated_by/at       audit trail
```

A uniqueness rule on (project_id, spatial_area_id, active_revision) prevents duplicate active boundaries. Full FK and project memberships depend on the real deployment schema; inspect before writing SQL.

### Identity lookup for imported CAD

1. Import DXF → GeoJSON, verify its CRS and plot locations.
2. Convert multiple Polygon Features for Area 0101 into a single MultiPolygon Feature.
3. Resolve `interpros_subarea_code=0101` to exactly one in-scope `spatial_id_01_area.id` UUID; compare `area_id`, project scope, and survey source.
4. Store geometry only **after** authorized review. This link belongs in the geometry table, not as a large text blob in the generic Register.
5. `GET /api/spatial/areas/:uuid/geometry` (protected) returns GeoJSON geometry produced with `ST_AsGeoJSON` and authorized Area metadata.
6. Map selection opens that Area's record. Data workspace can show **View on Map**, not raw coordinate arrays.
7. Keep `area_size_m2` from the Register and calculated `geometry_area_m2` separately; flag discrepancy instead of overwriting business data.

Use Interpros project membership and server-side permission checks for all APIs, with PostGIS/RLS defense in depth. Do not expose service-role/secret keys to Leaflet or publish sensitive boundaries in a public GitHub Pages repository.

## Raster drone imagery — only within the orthophoto footprint

A real **GeoTIFF** with embedded coordinate reference or trustworthy world file can be layered above the normal satellite map:

```text
              Leaflet
                 |
      Satellite basemap (whole region)
                 |
      Survey/drone raster (only measured extent)
                 |  XYZ PNG/WebP tiles + NoData alpha
      Area polygon overlay + selection
```

Production-quality flow:
1. Inspect TIFF raster CRS, pixel size, no-data, geotransform/rotation, boundaries, acquisition date.
2. If source is a regular TIFF lacking georeferencing, georeference it using verified control points first.
3. Reproject/warp raster to web-map compatible CRS (usually EPSG:3857), retaining transparent NoData edges.
4. Generate XYZ tiles or serve via protected tiling service (avoid loading full gigabyte TIFF in browser).
5. Overlay only where pixels exist. Expose layer toggle, opacity, date/source, and correct attribution/licensing.
6. Keep area polygons on top and test control-point alignment. Basemap imagery itself can be shifted.

A small north-up, georeferenced PNG/JPEG image with validated corner bounds may use Leaflet `L.imageOverlay` for a quick proof of concept. This is NOT a generic GeoTIFF viewer and is not suitable for rotated/warped footprints.

No real TIFF file was supplied in this work; raster overlay is a **design plan**, not an implemented feature.

## Integration release gates

1. First validate local MultiPolygon import, count=1 and parts=2.
2. Review survey/ground control and project Area identity.
3. Verify actual Supabase table schema, project scope / RLS / APIs.
4. Implement PostGIS migration in INTERPROS (not this public demo) and backfill safely.
5. Add raster imagery only when TIFF and rights to host it are supplied.
6. Release access-controlled INTERPROS map page after end-to-end acceptance.
