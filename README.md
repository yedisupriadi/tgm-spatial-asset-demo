# TGM Spatial Asset Demo

Prototype **Spatial Asset / Land Parcel Management System** untuk mengelola tanah, rumah, bangunan, dan aset lain langsung pada peta.

## Current Phase

`ARCHITECTURE → MVP DEVELOPMENT`

Demo tetap dapat berjalan tanpa database menggunakan browser `localStorage`, tetapi repository sekarang sudah disiapkan untuk **Supabase PostgreSQL + PostGIS**.

## Current Features

- Leaflet interactive map
- OpenStreetMap + satellite basemap
- Optional **local drone orthophoto XYZ layer** with layer toggle, opacity and Fit Drone (manifest-driven; no GeoTIFF data committed)
- Asset types: Land, House, Building, Commercial
- Status: Available, Reserved, Sold, Unverified
- Add asset by drawing polygon / rectangle
- Click asset polygon to select it
- Edit asset attributes
- Edit polygon geometry by moving vertices
- Automatic polygon area calculation
- Filter assets
- Import/Export GeoJSON (Polygon and MultiPolygon; optional replace/append local records)
- Administrative boundary layer selector
- Indonesian administrative hierarchy importer
- Supabase/PostGIS schema with RLS and spatial indexes

## Important Spatial Concept

Dua jenis geometry sengaja dipisahkan.

### 1. Administrative Region Geometry

Referensi wilayah:

```text
Province
  └─ Regency / City
      └─ District
          └─ Village
```

User aplikasi **tidak mengedit** boundary administratif.

### 2. Asset Geometry

Geometry tanah/bangunan milik record `spatial_assets`.

```text
Spatial Asset Row
  ├─ Asset Code
  ├─ Type
  ├─ Status
  ├─ Price
  ├─ Region
  └─ Geometry (Polygon or MultiPolygon)
```

Geometry ini dapat dibuat dan diedit user.

Flow edit:

```text
SELECT ASSET
   ↓
EDIT GEOMETRY
   ↓
MOVE POLYGON VERTICES
   ↓
SAVE
   ↓
CALCULATE AREA
   ↓
UPDATE ASSET GEOMETRY
```

Local demo menyimpan update ke `localStorage`. Production mode akan mengirim geometry GeoJSON ke Supabase/PostGIS.

## CAD DWG / DXF Parcel Import (Experimental)

A CAD conversion tool and validated GeoJSON browser import have been added:

- `scripts/cad_parcels_to_geojson.py` reads DXF directly, or DWG **only when the ODA File Converter is installed**.
- Conversion requires an **explicit, surveyor-confirmed source CRS** and one or more selected closed-polyline parcel layers.
- Invalid/open polylines are rejected; CAD bulge arcs on closed loops are tessellated with explicit tolerance.
- Generated parcels have provisional `CAD-<handle>` IDs and `UNVERIFIED` status.
- Select **Import GeoJSON** in the sidebar. Browser data is localStorage-only, **not** Supabase.
- Do not commit confidential survey DWGs or parcel coordinates to this public demo.

Full instructions: [CAD import guide](docs/cad-import.md).

- To represent disjoint CAD outlines as **one** Area / register record, use `scripts/group_geojson_area.py` and import the resulting single MultiPolygon Feature.
- The demo disables vertex editing for MultiPolygon: edit source CAD/GIS and re-import with **Replace current local map** after backing up local data.
- Existing project Spatial ID - Area integration and drone GeoTIFF overlay are proposed only, not deployed. See [Interpros spatial linkage design](docs/interpros-spatial-linkage.md).

## Drone GeoTIFF / Orthophoto Overlay (Local Pilot)

The viewer now supports optional XYZ drone tiles over the existing satellite basemap.
No drone imagery or private project coordinates are included in this public repository.

- Use GDAL (available via QGIS/OSGeo4W) to inspect GeoTIFF, warp to EPSG:3857 with alpha, and generate XYZ PNG tiles.
- Generate `data/drone/manifest.json` from the real GeoTIFF WGS84 extent using `scripts/build_drone_manifest.py`.
- Test on `http://localhost:5500`, not on public GitHub Pages. `data/drone/` is intentionally gitignored.
- Use **Fit Drone**, **Drone Orthophoto** layer control, and **opacity** to compare overlay with satellite and CAD boundaries.

Complete commands and QA checklist: [Drone overlay guide](docs/drone-overlay.md).

## Run Locally on Windows

Open **PowerShell** inside the repository folder.

```powershell
python -m http.server 5500
```

Then open:

```text
http://localhost:5500
```

### Verify

1. Three sample asset polygons should appear.
2. Click a polygon.
3. `Edit Data` and `Edit Geometry` become active.
4. Click `Edit Geometry`.
5. Move one or more polygon vertices.
6. Save through the Leaflet edit toolbar.
7. The parcel area is recalculated.
8. Refresh the browser; the changed polygon should remain.

## Indonesian Region Data

Source reference:

- `cahyadsn/wilayah`
- MIT License
- administrative codes/names based on the Kepmendagri dataset identified by that repository.

The upstream repository contains hierarchy codes/names down to district and village. Its spatial `wilayah_level_1_2` dataset provides boundaries for province and regency/city. We therefore **do not invent missing district/village polygons**.

Generate region data:

```powershell
python .\scripts\import_regions.py
```

Expected file:

```text
data\administrative-regions.geojson
```

Reload the application and use **Administrative Boundaries** in the sidebar.

## Supabase / PostGIS

Schema:

```text
supabase/schema.sql
```

Main tables:

```text
administrative_regions
spatial_assets
```

`administrative_regions.boundary` uses `MultiPolygon`.

`spatial_assets.geometry` uses `MultiPolygon` in the proposed new-install schema (single Polygons are converted via `ST_Multi`). Existing databases require a reviewed migration.

Spatial GiST indexes are included.

The SQL also includes authenticated RLS policies and database functions that convert PostGIS geometry to/from GeoJSON for Leaflet.

## Supabase Security

Never store a Supabase `service_role` / secret key in this public repository.

`supabase-config.js` is intentionally disabled. Later it should contain only frontend-safe project configuration, while the app uses Supabase Auth + RLS.

## Production Architecture

```text
USER
  │
  ▼
WEB APP
Leaflet + Asset Forms
  │
  ├─ CRUD asset data
  ├─ Draw polygon
  ├─ Edit polygon
  └─ Region layers
  │
  ▼
SUPABASE
  ├─ Auth
  ├─ PostgreSQL
  ├─ PostGIS
  ├─ RLS
  └─ Storage (future photos/documents)
```

## Next Development Step

1. Select/create the Supabase project for this system.
2. Enable/deploy PostGIS schema.
3. Add Supabase authentication.
4. Replace local asset adapter with Supabase RPC/Data API.
5. Import administrative region master data.
6. Add asset photos, owner/contact, certificate/legal data, and document attachments.
