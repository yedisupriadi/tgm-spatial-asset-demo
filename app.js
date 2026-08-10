const STORAGE_KEY = "tgm_spatial_asset_demo_v1";

const sampleAssets = [
  {
    type: "Feature",
    properties: {
      id: "demo-001",
      code: "TGM-LAND-001",
      title: "Demo Kavling A01",
      asset_type: "LAND",
      status: "AVAILABLE",
      price_idr: 1850000000,
      area_m2: 976.4,
      source: "Demo Owner",
      notes: "Sample parcel for spatial asset demonstration."
    },
    geometry: {
      type: "Polygon",
      coordinates: [[
        [106.81270, -6.30830],
        [106.81405, -6.30818],
        [106.81415, -6.30905],
        [106.81278, -6.30918],
        [106.81270, -6.30830]
      ]]
    }
  },
  {
    type: "Feature",
    properties: {
      id: "demo-002",
      code: "TGM-LAND-002",
      title: "Demo Kavling A02",
      asset_type: "LAND",
      status: "RESERVED",
      price_idr: 2250000000,
      area_m2: 1108.7,
      source: "Demo Agent",
      notes: "Reserved sample parcel."
    },
    geometry: {
      type: "Polygon",
      coordinates: [[
        [106.81420, -6.30818],
        [106.81572, -6.30805],
        [106.81580, -6.30900],
        [106.81430, -6.30905],
        [106.81420, -6.30818]
      ]]
    }
  },
  {
    type: "Feature",
    properties: {
      id: "demo-003",
      code: "TGM-HOUSE-001",
      title: "Demo House Cluster B01",
      asset_type: "HOUSE",
      status: "SOLD",
      price_idr: 3200000000,
      area_m2: 706.2,
      source: "Internal Listing",
      notes: "Sold sample house parcel."
    },
    geometry: {
      type: "Polygon",
      coordinates: [[
        [106.81285, -6.30935],
        [106.81395, -6.30925],
        [106.81402, -6.30990],
        [106.81292, -6.31000],
        [106.81285, -6.30935]
      ]]
    }
  }
];

let assets = loadAssets();
let pendingLayer = null;

const map = L.map("map", { zoomControl: true }).setView([-6.3090, 106.8142], 17);

const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 20,
  attribution: "&copy; OpenStreetMap contributors"
});

const satellite = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  {
    maxZoom: 20,
    attribution: "Tiles &copy; Esri"
  }
);

osm.addTo(map);
L.control.layers(
  { "OpenStreetMap": osm, "Satellite": satellite },
  {},
  { position: "topright" }
).addTo(map);

const assetLayer = L.geoJSON(null, {
  style: feature => getStyle(feature.properties.status),
  onEachFeature: (feature, layer) => {
    layer.bindPopup(buildPopup(feature.properties));
  }
}).addTo(map);

const editableGroup = new L.FeatureGroup();
map.addLayer(editableGroup);

const drawControl = new L.Control.Draw({
  position: "topleft",
  draw: {
    polygon: {
      allowIntersection: false,
      showArea: true,
      metric: true,
      shapeOptions: { color: "#071f40", weight: 3, fillOpacity: 0.15 }
    },
    rectangle: {
      shapeOptions: { color: "#071f40", weight: 3, fillOpacity: 0.15 }
    },
    polyline: false,
    marker: false,
    circle: false,
    circlemarker: false
  },
  edit: {
    featureGroup: editableGroup,
    edit: false,
    remove: false
  }
});
map.addControl(drawControl);

map.on(L.Draw.Event.CREATED, event => {
  pendingLayer = event.layer;
  editableGroup.addLayer(pendingLayer);

  const latlngs = extractOuterRingLatLngs(pendingLayer);
  const area = L.GeometryUtil.geodesicArea(latlngs);

  document.getElementById("assetArea").value = area.toFixed(2);
  document.getElementById("assetCode").value = nextSuggestedCode();
  showModal();
});

document.getElementById("assetForm").addEventListener("submit", event => {
  event.preventDefault();
  if (!pendingLayer) return;

  const feature = pendingLayer.toGeoJSON();
  feature.properties = {
    id: crypto.randomUUID ? crypto.randomUUID() : `asset-${Date.now()}`,
    code: document.getElementById("assetCode").value.trim(),
    title: document.getElementById("assetTitle").value.trim(),
    asset_type: document.getElementById("assetType").value,
    status: document.getElementById("assetStatus").value,
    price_idr: Number(document.getElementById("assetPrice").value || 0),
    area_m2: Number(document.getElementById("assetArea").value || 0),
    source: document.getElementById("assetSource").value.trim(),
    notes: document.getElementById("assetNotes").value.trim()
  };

  assets.push(feature);
  saveAssets();
  editableGroup.removeLayer(pendingLayer);
  pendingLayer = null;
  renderAssets();
  hideModal();
  document.getElementById("assetForm").reset();
});

document.getElementById("cancelModalBtn").addEventListener("click", cancelPendingAsset);
document.getElementById("cancelFormBtn").addEventListener("click", cancelPendingAsset);
document.getElementById("statusFilter").addEventListener("change", renderAssets);
document.getElementById("typeFilter").addEventListener("change", renderAssets);
document.getElementById("fitAllBtn").addEventListener("click", fitAll);
document.getElementById("exportBtn").addEventListener("click", exportGeoJSON);

renderAssets();
fitAll();

function loadAssets() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (Array.isArray(stored) && stored.length) return stored;
  } catch (error) {
    console.warn("Could not read local assets:", error);
  }
  return structuredClone ? structuredClone(sampleAssets) : JSON.parse(JSON.stringify(sampleAssets));
}

function saveAssets() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(assets));
}

function renderAssets() {
  const status = document.getElementById("statusFilter").value;
  const type = document.getElementById("typeFilter").value;

  const filtered = assets.filter(feature => {
    const p = feature.properties;
    const statusMatch = status === "ALL" || p.status === status;
    const typeMatch = type === "ALL" || p.asset_type === type;
    return statusMatch && typeMatch;
  });

  assetLayer.clearLayers();
  assetLayer.addData({ type: "FeatureCollection", features: filtered });
  updateStats();
}

function updateStats() {
  const count = status => assets.filter(f => f.properties.status === status).length;
  document.getElementById("statTotal").textContent = assets.length;
  document.getElementById("statAvailable").textContent = count("AVAILABLE");
  document.getElementById("statReserved").textContent = count("RESERVED");
  document.getElementById("statSold").textContent = count("SOLD");
}

function getStyle(status) {
  const color = {
    AVAILABLE: "#2e8b57",
    RESERVED: "#d8a028",
    SOLD: "#c94d4d"
  }[status] || "#53718f";

  return {
    color,
    fillColor: color,
    weight: 2.5,
    fillOpacity: 0.34
  };
}

function buildPopup(p) {
  const statusColor = {
    AVAILABLE: "#2e8b57",
    RESERVED: "#d8a028",
    SOLD: "#c94d4d"
  }[p.status] || "#53718f";

  return `
    <div class="asset-popup">
      <div class="popup-code">${escapeHtml(p.code || "-")}</div>
      <h3>${escapeHtml(p.title || "Untitled Asset")}</h3>
      <span class="status-chip" style="background:${statusColor}">${escapeHtml(p.status || "-")}</span>
      <div class="popup-grid">
        <span>Type</span><span>${escapeHtml(p.asset_type || "-")}</span>
        <span>Area</span><span>${formatNumber(p.area_m2)} m²</span>
        <span>Price</span><span>${formatIDR(p.price_idr)}</span>
        <span>Source</span><span>${escapeHtml(p.source || "-")}</span>
      </div>
      ${p.notes ? `<p class="muted">${escapeHtml(p.notes)}</p>` : ""}
    </div>
  `;
}

function fitAll() {
  if (!assets.length) return;
  const all = L.geoJSON({ type: "FeatureCollection", features: assets });
  const bounds = all.getBounds();
  if (bounds.isValid()) map.fitBounds(bounds.pad(0.2));
}

function extractOuterRingLatLngs(layer) {
  const latlngs = layer.getLatLngs();
  if (!Array.isArray(latlngs)) return [];
  if (latlngs.length && latlngs[0] instanceof L.LatLng) return latlngs;
  if (latlngs.length && Array.isArray(latlngs[0])) return latlngs[0];
  return [];
}

function nextSuggestedCode() {
  const serial = String(assets.length + 1).padStart(3, "0");
  return `TGM-LAND-${serial}`;
}

function showModal() {
  const modal = document.getElementById("assetModal");
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.getElementById("assetTitle").focus(), 0);
}

function hideModal() {
  const modal = document.getElementById("assetModal");
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
}

function cancelPendingAsset() {
  if (pendingLayer) {
    editableGroup.removeLayer(pendingLayer);
    pendingLayer = null;
  }
  hideModal();
  document.getElementById("assetForm").reset();
}

function exportGeoJSON() {
  const payload = {
    type: "FeatureCollection",
    features: assets
  };

  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/geo+json"
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `tgm-spatial-assets-${new Date().toISOString().slice(0, 10)}.geojson`;
  a.click();
  URL.revokeObjectURL(url);
}

function formatIDR(value) {
  const n = Number(value || 0);
  if (!n) return "-";
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0
  }).format(n);
}

function formatNumber(value) {
  return new Intl.NumberFormat("id-ID", {
    maximumFractionDigits: 2
  }).format(Number(value || 0));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
