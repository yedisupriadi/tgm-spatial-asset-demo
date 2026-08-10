const STORAGE_KEY = "tgm_spatial_asset_demo_v2";
const REGION_DATA_URL = "./data/administrative-regions.geojson";

const sampleAssets = [
  { type:"Feature", properties:{id:"demo-001",code:"TGM-LAND-001",title:"Demo Kavling A01",asset_type:"LAND",status:"AVAILABLE",price_idr:1850000000,area_m2:976.4,source:"Demo Owner",notes:"Sample parcel."}, geometry:{type:"Polygon",coordinates:[[[106.81270,-6.30830],[106.81405,-6.30818],[106.81415,-6.30905],[106.81278,-6.30918],[106.81270,-6.30830]]] } },
  { type:"Feature", properties:{id:"demo-002",code:"TGM-LAND-002",title:"Demo Kavling A02",asset_type:"LAND",status:"RESERVED",price_idr:2250000000,area_m2:1108.7,source:"Demo Agent",notes:"Reserved sample parcel."}, geometry:{type:"Polygon",coordinates:[[[106.81420,-6.30818],[106.81572,-6.30805],[106.81580,-6.30900],[106.81430,-6.30905],[106.81420,-6.30818]]] } },
  { type:"Feature", properties:{id:"demo-003",code:"TGM-HOUSE-001",title:"Demo House Cluster B01",asset_type:"HOUSE",status:"SOLD",price_idr:3200000000,area_m2:706.2,source:"Internal Listing",notes:"Sold sample."}, geometry:{type:"Polygon",coordinates:[[[106.81285,-6.30935],[106.81395,-6.30925],[106.81402,-6.30990],[106.81292,-6.31000],[106.81285,-6.30935]]] } }
];

let assets = loadAssets();
let pendingLayer = null;
let selectedAssetId = null;
let editLayer = null;
let originalEditGeometry = null;
let regions = [];

const el = id => document.getElementById(id);
const map = L.map("map", { zoomControl:true }).setView([-6.3090,106.8142],17);
const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:20,attribution:"&copy; OpenStreetMap contributors"});
const satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",{maxZoom:20,attribution:"Tiles &copy; Esri"});
osm.addTo(map);
L.control.layers({OpenStreetMap:osm,Satellite:satellite},{},{position:"topright"}).addTo(map);

const assetLayer = L.geoJSON(null,{style:f=>getStyle(f.properties.status),onEachFeature:(feature,layer)=>{
  layer.bindPopup(buildPopup(feature.properties));
  layer.on("click",()=>selectAsset(feature.properties.id));
}}).addTo(map);
const regionLayer = L.geoJSON(null,{style:{color:"#486a91",weight:1.5,fillOpacity:0.05},onEachFeature:(f,l)=>l.bindTooltip(`${f.properties.code || ""} ${f.properties.name || ""}`.trim())}).addTo(map);
const editableGroup = new L.FeatureGroup().addTo(map);

map.addControl(new L.Control.Draw({position:"topleft",draw:{polygon:{allowIntersection:false,showArea:true,metric:true,shapeOptions:{color:"#071f40",weight:3,fillOpacity:0.15}},rectangle:{shapeOptions:{color:"#071f40",weight:3,fillOpacity:0.15}},polyline:false,marker:false,circle:false,circlemarker:false},edit:{featureGroup:editableGroup,edit:false,remove:false}}));

map.on(L.Draw.Event.CREATED,event=>{
  cancelGeometryEdit();
  pendingLayer=event.layer; editableGroup.addLayer(pendingLayer);
  el("assetArea").value=calculateLayerArea(pendingLayer).toFixed(2);
  el("assetCode").value=nextSuggestedCode(); el("assetId").value="";
  showModal("New Spatial Asset");
});

el("assetForm").addEventListener("submit",event=>{
  event.preventDefault();
  const id=el("assetId").value;
  const props=readFormProperties(id || (crypto.randomUUID?crypto.randomUUID():`asset-${Date.now()}`));
  if(id){
    const i=assets.findIndex(f=>f.properties.id===id); if(i<0) return;
    assets[i].properties={...assets[i].properties,...props};
  } else {
    if(!pendingLayer) return;
    const feature=pendingLayer.toGeoJSON(); feature.properties=props; assets.push(feature);
    editableGroup.removeLayer(pendingLayer); pendingLayer=null;
  }
  saveAssets(); hideModal(); el("assetForm").reset(); renderAssets(); selectAsset(props.id);
});

["cancelModalBtn","cancelFormBtn"].forEach(id=>el(id).addEventListener("click",cancelForm));
el("statusFilter").addEventListener("change",renderAssets);
el("typeFilter").addEventListener("change",renderAssets);
el("fitAllBtn").addEventListener("click",fitAll);
el("exportBtn").addEventListener("click",exportGeoJSON);
el("editDataBtn").addEventListener("click",openSelectedAssetForm);
el("editGeometryBtn").addEventListener("click",startGeometryEdit);
el("saveGeometryBtn").addEventListener("click",saveGeometryEdit);
el("cancelGeometryBtn").addEventListener("click",cancelGeometryEdit);
el("regionLevel").addEventListener("change",renderRegions);

init();

async function init(){setDataMode();renderAssets();fitAll();await loadRegions();}
function setDataMode(){const cfg=window.TGM_SUPABASE||{};el("dataMode").textContent=cfg.enabled?"Supabase configuration detected (DB adapter is next step)":"Local demo mode";}
function loadAssets(){try{const s=JSON.parse(localStorage.getItem(STORAGE_KEY));if(Array.isArray(s)&&s.length)return s;}catch(e){}return JSON.parse(JSON.stringify(sampleAssets));}
function saveAssets(){localStorage.setItem(STORAGE_KEY,JSON.stringify(assets));}
function selectAsset(id){selectedAssetId=id;el("editDataBtn").disabled=!id;el("editGeometryBtn").disabled=!id||!!editLayer;}
function renderAssets(){
  const status=el("statusFilter").value,type=el("typeFilter").value;
  const filtered=assets.filter(f=>(status==="ALL"||f.properties.status===status)&&(type==="ALL"||f.properties.asset_type===type));
  assetLayer.clearLayers();assetLayer.addData({type:"FeatureCollection",features:filtered});updateStats();
}
function updateStats(){const count=s=>assets.filter(f=>f.properties.status===s).length;el("statTotal").textContent=assets.length;el("statAvailable").textContent=count("AVAILABLE");el("statReserved").textContent=count("RESERVED");el("statSold").textContent=count("SOLD");}
function openSelectedAssetForm(){const f=assets.find(x=>x.properties.id===selectedAssetId);if(!f)return;const p=f.properties;el("assetId").value=p.id;el("assetCode").value=p.code||"";el("assetType").value=p.asset_type||"LAND";el("assetTitle").value=p.title||"";el("assetStatus").value=p.status||"AVAILABLE";el("assetPrice").value=p.price_idr||"";el("assetArea").value=p.area_m2||"";el("assetSource").value=p.source||"";el("assetNotes").value=p.notes||"";showModal("Edit Asset Data");}
function startGeometryEdit(){
  const f=assets.find(x=>x.properties.id===selectedAssetId);if(!f)return;
  cancelGeometryEdit();originalEditGeometry=JSON.parse(JSON.stringify(f.geometry));assetLayer.clearLayers();
  editLayer=L.geoJSON(f,{style:getStyle(f.properties.status)}).getLayers()[0];editableGroup.addLayer(editLayer);
  if(editLayer.editing) editLayer.editing.enable();
  el("saveGeometryBtn").disabled=false;el("cancelGeometryBtn").disabled=false;el("editGeometryBtn").disabled=true;el("editDataBtn").disabled=true;
  if(editLayer.getBounds) map.fitBounds(editLayer.getBounds().pad(.3));
}
function saveGeometryEdit(){
  if(!editLayer||!selectedAssetId)return;
  const i=assets.findIndex(f=>f.properties.id===selectedAssetId);if(i<0)return;
  assets[i].geometry=editLayer.toGeoJSON().geometry;assets[i].properties.area_m2=Number(calculateLayerArea(editLayer).toFixed(2));
  saveAssets();finishGeometryEdit();renderAssets();selectAsset(selectedAssetId);
}
function cancelGeometryEdit(){if(editLayer&&selectedAssetId&&originalEditGeometry){const i=assets.findIndex(f=>f.properties.id===selectedAssetId);if(i>=0)assets[i].geometry=originalEditGeometry;}finishGeometryEdit();if(selectedAssetId)selectAsset(selectedAssetId);renderAssets();}
function finishGeometryEdit(){if(editLayer){if(editLayer.editing)editLayer.editing.disable();editableGroup.removeLayer(editLayer);}editLayer=null;originalEditGeometry=null;el("saveGeometryBtn").disabled=true;el("cancelGeometryBtn").disabled=true;el("editDataBtn").disabled=!selectedAssetId;el("editGeometryBtn").disabled=!selectedAssetId;}
function readFormProperties(id){return{id,code:el("assetCode").value.trim(),title:el("assetTitle").value.trim(),asset_type:el("assetType").value,status:el("assetStatus").value,price_idr:Number(el("assetPrice").value||0),area_m2:Number(el("assetArea").value||0),source:el("assetSource").value.trim(),notes:el("assetNotes").value.trim()};}
function cancelForm(){if(pendingLayer){editableGroup.removeLayer(pendingLayer);pendingLayer=null;}hideModal();el("assetForm").reset();}
function showModal(title){el("modalTitle").textContent=title;el("assetModal").classList.remove("hidden");el("assetModal").setAttribute("aria-hidden","false");}
function hideModal(){el("assetModal").classList.add("hidden");el("assetModal").setAttribute("aria-hidden","true");}
function calculateLayerArea(layer){const ll=extractOuterRingLatLngs(layer);return ll.length?L.GeometryUtil.geodesicArea(ll):0;}
function extractOuterRingLatLngs(layer){const a=layer.getLatLngs();if(!Array.isArray(a))return[];if(a.length&&a[0] instanceof L.LatLng)return a;if(a.length&&Array.isArray(a[0]))return a[0];return[];}
function nextSuggestedCode(){return `TGM-LAND-${String(assets.length+1).padStart(3,"0")}`;}
function getStyle(status){const c={AVAILABLE:"#2e8b57",RESERVED:"#d8a028",SOLD:"#c94d4d"}[status]||"#53718f";return{color:c,fillColor:c,weight:2.5,fillOpacity:.34};}
function buildPopup(p){return `<div class="asset-popup"><div class="popup-code">${esc(p.code||"-")}</div><h3>${esc(p.title||"Untitled Asset")}</h3><div class="popup-grid"><span>Status</span><span>${esc(p.status||"-")}</span><span>Type</span><span>${esc(p.asset_type||"-")}</span><span>Area</span><span>${fmt(p.area_m2)} m²</span><span>Price</span><span>${idr(p.price_idr)}</span></div><p class="muted">Click polygon, then use Edit Data / Edit Geometry.</p></div>`;}
function fitAll(){if(!assets.length)return;const b=L.geoJSON({type:"FeatureCollection",features:assets}).getBounds();if(b.isValid())map.fitBounds(b.pad(.2));}
function exportGeoJSON(){const blob=new Blob([JSON.stringify({type:"FeatureCollection",features:assets},null,2)],{type:"application/geo+json"});const u=URL.createObjectURL(blob),a=document.createElement("a");a.href=u;a.download=`tgm-spatial-assets-${new Date().toISOString().slice(0,10)}.geojson`;a.click();URL.revokeObjectURL(u);}
async function loadRegions(){try{const r=await fetch(REGION_DATA_URL,{cache:"no-store"});if(!r.ok)return;const fc=await r.json();regions=Array.isArray(fc.features)?fc.features:[];renderRegions();}catch(e){console.info("Region GeoJSON not generated yet. Run scripts/import_regions.py.");}}
function renderRegions(){const level=el("regionLevel").value;regionLayer.clearLayers();if(level==="OFF")return;regionLayer.addData({type:"FeatureCollection",features:regions.filter(f=>f.properties.level===level&&f.geometry)});}
function fmt(v){return new Intl.NumberFormat("id-ID",{maximumFractionDigits:2}).format(Number(v||0));}
function idr(v){return Number(v||0)?new Intl.NumberFormat("id-ID",{style:"currency",currency:"IDR",maximumFractionDigits:0}).format(Number(v)):"-";}
function esc(v){return String(v).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");}
