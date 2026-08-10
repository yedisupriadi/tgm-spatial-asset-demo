# Proposed Production Architecture

```text
USER
  │
  ▼
WEB APPLICATION
(Next.js / React)
  │
  ├───────────────┐
  ▼               ▼
MAP UI          DATA UI
Leaflet         Register / Forms
  │               │
  └───────┬───────┘
          ▼
     APPLICATION API
          │
          ▼
      SUPABASE
  ┌───────────────┐
  │ Auth          │
  │ PostgreSQL    │
  │ PostGIS       │
  │ Storage       │
  │ RLS Policies  │
  └───────────────┘
          │
          ▼
  SPATIAL ASSET DATA
  - projects
  - assets
  - land parcels
  - listings
  - contacts
  - documents
  - photos
  - geometry
```

## Recommended Core Entities

### projects
A portfolio/project/site container.

### spatial_assets
The business record for a land parcel, house, building, or commercial property.

### asset_geometries
Optional separate geometry history table if geometry revisions must be audited.

### contacts
Owner, agent, broker, buyer, tenant, or internal PIC.

### asset_contacts
Many-to-many relation between assets and contacts.

### asset_documents
Certificate, survey plan, tax document, offer, valuation, legal document.

### asset_photos
Property photos and field survey images.

### asset_status_history
Tracks changes such as Available → Reserved → Sold.

### regions
Reference to Indonesian province/regency/district/village master data.

## Why PostGIS

A normal latitude/longitude column is sufficient for basic points, but land parcels require real spatial geometry.

PostGIS supports:

- Point
- Polygon
- MultiPolygon
- spatial indexes
- intersects
- contains
- distance
- bounding-box queries

That is what allows the system to evolve from a simple property register into a GIS-capable asset platform.
