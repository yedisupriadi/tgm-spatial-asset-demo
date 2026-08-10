# Generated Administrative Region Data

`administrative-regions.geojson` is intentionally **not committed by default** because the source boundary dataset can be large.

Generate it on Windows from the repository root:

```powershell
python .\scripts\import_regions.py
```

Expected output:

```text
data\administrative-regions.geojson
```

The generated FeatureCollection contains the administrative hierarchy from the upstream `cahyadsn/wilayah` dataset. Geometry is populated only when boundary data exists in the upstream spatial source. The application never invents missing district/village polygons.

Source: https://github.com/cahyadsn/wilayah (MIT License).
