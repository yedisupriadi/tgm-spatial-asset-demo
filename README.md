# TGM Spatial Asset Demo

A lightweight proof-of-concept for managing **land parcels, houses, and other property assets on an interactive map**.

This starter is intentionally simple:

- no build tools
- no npm install
- no online database yet
- data is saved to browser `localStorage`
- geometry is stored as GeoJSON in the demo
- a Supabase/PostGIS starter schema is included for the next development phase

## Demo Features

- Interactive Leaflet map
- OpenStreetMap and satellite basemap
- Sample land parcels
- Status classification:
  - Available
  - Reserved
  - Sold
- Asset filters
- Click a polygon to see:
  - asset code
  - title
  - asset type
  - area
  - price
  - source
- Draw new polygon or rectangle
- Automatic approximate area calculation
- Save new parcel in browser
- Export all assets as GeoJSON

## Run on Windows

### Option A - simplest

Open `index.html` in Chrome or Edge.

Internet access is required because Leaflet and map tiles are loaded from public CDN/tile services.

### Option B - recommended local server

Open **PowerShell** in this folder.

If Python is installed:

```powershell
python -m http.server 5500
```

Then open:

```text
http://localhost:5500
```

Expected result: the Spatial Asset Demo dashboard loads and shows several sample parcels.

## Verify It Works

1. The map is visible.
2. Three sample polygons appear.
3. Click one polygon and a popup appears.
4. Use the polygon drawing tool on the left side of the map.
5. Draw a parcel.
6. Fill in the form.
7. Click **Save Asset**.
8. Refresh the page.
9. The parcel should remain because it was saved to browser `localStorage`.
10. Click **Export GeoJSON** to download the spatial dataset.

## Folder Structure

```text
tgm-spatial-asset-demo/
├─ index.html
├─ styles.css
├─ app.js
├─ README.md
├─ supabase/
│  └─ schema.sql
└─ docs/
   └─ architecture.md
```

## Development Direction

### MVP

- User authentication
- Supabase database
- PostGIS polygon storage
- CRUD asset register
- Map + table synchronization
- Asset status
- Price
- area
- seller / source
- photos
- project / portfolio relation
- audit trail
- role-based access

### Phase 2

- Indonesian administrative region relation
- drawing and editing polygons
- document attachments
- SHM / SHGB / certificate metadata
- contact/owner register
- spatial search
- nearby infrastructure
- map clustering
- valuation history
- change history

### Future

- cadastral survey imports
- GeoJSON / KML / SHP import
- project opportunity pipeline
- mobile field survey
- GPS capture
- drone / orthophoto overlay
- BIM / GIS integration
- portfolio analytics
- AI-assisted property search and data extraction

## Important Production Note

Do not expose Supabase `service_role` keys in frontend code.

The production application should use:

- Supabase Auth
- Row Level Security
- project/company membership tables
- controlled storage buckets
- validation for geometry and uploaded documents
- server-side logic for privileged operations
