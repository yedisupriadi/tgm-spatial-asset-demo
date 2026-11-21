# TGM Spatial Asset Demo

Prototype **Spatial Asset / Land Parcel Management System** untuk mengelola tanah, rumah, bangunan, dan aset lain langsung pada peta.

## Current Phase

`ARCHITECTURE → MVP DEVELOPMENT`

Demo tetap dapat berjalan tanpa database menggunakan browser `localStorage`, tetapi repository sekarang sudah disiapkan untuk **Supabase PostgreSQL + PostGIS**.

## Current Features

- Leaflet interactive map
- OpenStreetMap + satellite basemap
- Asset types: Land, House, Building, Commercial
- Status: Available, Reserved, Sold
- Add asset by drawing polygon / rectangle
- Click asset polygon to select it
- Edit asset attributes
- Edit polygon geometry by moving vertices
- Automatic polygon area calculation
- Filter assets
- Export GeoJSON
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
  └─ Geometry (Polygon)
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
- Invalid/open/curved polylines are skipped or rejected; no geometry is guessed from a screenshot.
- Generated parcels have provisional `CAD-<handle>` IDs and `UNVERIFIED` status.
- Select **Import GeoJSON** in the sidebar. Browser data is localStorage-only, **not** Supabase.
- Do not commit confidential survey DWGs or parcel coordinates to this public demo.

Full instructions: [CAD import guide](docs/cad-import.md).

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

`spatial_assets.geometry` uses `Polygon`.

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
