# Local Drone GeoTIFF Overlay — Windows/QGIS/GDAL Walkthrough

The Spatial Asset Demo already has **optional** Leaflet support for a tiled drone orthophoto. It keeps an OSM or satellite basemap beneath it, overlays the drone image only within the GeoTIFF footprint, and keeps cadastral/Area polygons clickable on top.

**Important:** the user-supplied GeoTIFF was NOT uploaded or available when this feature was developed. Actual raster alignment, blank-edge transparency, colour channels and performance must be verified with the real file.

## 0. Privacy boundary

This repository is **PUBLIC**. Files in `data/drone/`, GeoTIFFs, VRTs and world files are ignored by Git; **do not force-add them**. This is local development only. A private Interpros deployment will need authenticated raster delivery and spatial authorization. No claim is made that GitHub Pages currently displays the user's drone image.

## 1. Software and folders

Install QGIS (includes GDAL), if it is not installed, from https://qgis.org/download/ . Use **OSGeo4W Shell** to run the GDAL commands; ordinary Command Prompt may not find GDAL.

Clone or update the demo, then open OSGeo4W Shell:

```bat
cd /d "C:\YDS\TGM\tgm-spatial-asset-demo"
mkdir data\drone
gdalinfo --version
```

Replace the repository path with your local folder. Assume that your source TIFF is at:

```text
D:\Drone\0101_orthomosaic.tif
```

Replace this example path with the real filename in **all** commands below.

## 2. Inspect the source GeoTIFF

```bat
gdalinfo "D:\Drone\0101_orthomosaic.tif"
```

Verify:
- The raster has a real georeferenced CRS (e.g. EPSG:32751 for local UTM 51S or another declared CRS).
- Image size / pixel resolution / band type (ideally three 8-bit RGB bands, with valid alpha/NoData).
- Origin, pixel size and corner coordinates make sense.
- Georeferencing is not only a pixel index; never assign EPSG based on a guess.

If the image has **no** georeferencing or a local arbitrary CRS, stop and georeference it using survey control first.

## 3. Reproject to web Mercator as a temporary VRT

```bat
gdalwarp -overwrite -of VRT -t_srs EPSG:3857 -r bilinear -dstalpha "D:\Drone\0101_orthomosaic.tif" "data\drone\0101_3857.vrt"
```

The VRT is a small reference to the original TIFF, not a duplicate image. It must stay accessible from that path. `-dstalpha` creates a transparency mask for unset/NoData regions when source metadata makes those regions identifiable. If the TIFF contains opaque black/white borders with no correct NoData, they will **not** automatically disappear: investigate the raster alpha/NoData and use a surveyed mask or correctly configured nodata value instead. Do not indiscriminately set `0` as NoData if legitimate image pixels can be 0.

## 4. Generate XYZ PNG tiles

For a quick pilot:

```bat
gdal2tiles --xyz --profile=mercator --zoom=16-20 --processes=4 --webviewer=none --tiledriver=PNG "data\drone\0101_3857.vrt" "data\drone\tiles"
```

The directory must contain paths like:

```text
data\drone\tiles\20\<x>\<y>.png
```

Using `--xyz` is essential: Leaflet tile URLs use **XYZ**, not inverted-Y TMS indexing. The PNG tiles can retain transparent NoData pixels.

For large TIFFs start at `--zoom=15-18`, limit `--processes` to available RAM, and adapt the manifest zoom parameters accordingly. If GDAL reports that the raster input must be 8-bit, inspect bands and colour scaling; do not blindly cast 16-bit or scientific TIFF values to Byte.

**GDAL version note:** GDAL 3.13+ may internally remap `gdal2tiles` to the newer `gdal raster tile`. Check `gdal2tiles --help` if switches differ.

## 5. Generate an accurate bounds manifest

Run in the repo root from OSGeo4W Shell:

```bat
python scripts\build_drone_manifest.py --source "D:\Drone\0101_orthomosaic.tif" --name "Drone Orthophoto 0101" --acquired "YYYY-MM-DD" --min-zoom 16 --max-zoom 20
```

Replace `YYYY-MM-DD` with the true drone survey acquisition date. This uses `gdalinfo -json` to extract a WGS84 footprint, takes its latitude/longitude bounds and writes:

```text
data/drone/manifest.json
```

Example **format only** (not real site coordinates):

```json
{
  "name": "Drone Orthophoto 0101",
  "acquiredAt": "YYYY-MM-DD",
  "minZoom": 16,
  "maxNativeZoom": 20,
  "bounds": [[-4.27, 121.65], [-4.25, 121.68]]
}
```

Leaflet uses the fixed local template `./data/drone/tiles/{z}/{x}/{y}.png`. The bounds are a coarse bounding box, not the exact footprint shape. Alpha in PNG controls transparency around jagged/rotated actual photo coverage.

## 6. View locally

```bat
python -m http.server 5500
```

Open `http://localhost:5500/` **not** the public GitHub Pages site.

The **Drone Orthophoto** sidebar card should report its name/date when the manifest is loaded. It auto-enables the drone tiles. Use **Fit Drone** to center on the source coverage. In the upper-right Leaflet layer control:
- choose **Satellite** basemap;
- toggle **Drone Orthophoto** overlay;
- toggle **Area Boundary** overlay.

Use the sidebar opacity slider (0–100%) to visually compare drone against satellite and Area geometry.

The drone tiles cannot be seen on the public `github.io` site because the private ignored files are not deployed there.

## 7. Acceptance checks

1. Drone texture only appears where imagery exists; outside that extent satellite remains visible.
2. There is no accidental black/white background where NoData should be transparent.
3. Survey control/known road junctions align. Commercial satellite imagery can have its own positional offset; use survey ground control as truth.
4. Area 0101's MultiPolygon remains on top and its click/select popup still works.
5. Layer control toggles the drone without changing the Area records.
6. Opacity slider and survey date display work, and no tile requests return 404 at intended zoom levels (browser DevTools → Network).
7. Local image and config are NOT staged or tracked by Git: `git status --short` should not include `data/drone/`.

## Troubleshooting

| Problem | Check |
| --- | --- |
| `gdalinfo` not found | Run OSGeo4W Shell and inspect QGIS/GDAL installation. |
| "No drone layer configured" | Manifest missing at `data/drone/manifest.json`; use `python scripts/build_drone_manifest.py`. |
| Bounds error | Real GeoTIFF lacks known CRS/WGS84 footprint or manifest format was changed. |
| Drone tile blank or 404 | Confirm XYZ ordering, zoom range, path and PNG file extensions. Inspect browser Network. |
| Drone shifted | Check input CRS, georeferencing and site control points, not screenshot alignment. |
| Black/white border | Check alpha and NoData, re-run `gdalwarp` and tiling. |
| GitHub Pages shows no drone | Normal: the private `data/drone/` files are intentionally not committed. |
| Zoomed-in drone appears blurry | Higher native tile zoom requires larger tile pyramid and source resolution; never claim higher accuracy from software zoom. |

Authoritative references:
- https://gdal.org/en/stable/programs/gdalwarp.html
- https://gdal.org/en/stable/programs/gdal2tiles.html
- https://leafletjs.com/reference-1.9.4.html
