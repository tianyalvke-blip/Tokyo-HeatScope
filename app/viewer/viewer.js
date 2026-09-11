const sourceId = 'buildings';
const extrusionLayerId = 'buildings-3d';
const outlineLayerId = 'building-outlines';
const isEmbedded = new URLSearchParams(location.search).get('embed') === '1';
if (isEmbedded) document.body.classList.add('embedded');

const map = new maplibregl.Map({
  container: 'map',
  style: {
    version: 8,
    sources: {},
    layers: [
      { id: 'background', type: 'background', paint: { 'background-color': isEmbedded ? '#0b0b0b' : '#eaf1f2' } }
    ]
  },
  center: [139.76, 35.68],
  zoom: 15,
  pitch: 60,
  bearing: -25,
  minZoom: 11,
  maxZoom: 20,
  renderWorldCopies: false,
  attributionControl: false
});

map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');

const form = document.querySelector('#grid-form');
const input = document.querySelector('#grid-id');
const button = document.querySelector('#load-button');
const status = document.querySelector('#status');
const heightSlider = document.querySelector('#height-scale');
const scaleValue = document.querySelector('#scale-value');
const originalAverage = document.querySelector('#original-average');
const scenarioAverage = document.querySelector('#scenario-average');
const heightChange = document.querySelector('#height-change');
const resetHeightButton = document.querySelector('#reset-height');

const areaSlider = document.querySelector('#area-scale');
const fpScaleValue = document.querySelector('#fp-scale-value');
const fpRequestedChange = document.querySelector('#fp-requested-change');
const fpAchievedChange = document.querySelector('#fp-achieved-change');
const fpMinGap = document.querySelector('#fp-min-gap');
const fpOriginalArea = document.querySelector('#fp-original-area');
const fpRequestedArea = document.querySelector('#fp-requested-area');
const fpAchievedArea = document.querySelector('#fp-achieved-area');
const fpAreaChange = document.querySelector('#fp-area-change');
const resetFootprintButton = document.querySelector('#reset-footprint');
const territoryToggle = document.querySelector('#territory-toggle');
const gridToggle = document.querySelector('#grid-toggle');
const clusterForm = document.querySelector('#cluster-form');
const seedInput = document.querySelector('#seed-grid');
const gridCountInput = document.querySelector('#grid-count');
const clusterButton = document.querySelector('#cluster-load-button');

let currentStudyLabel = null;
let originalAvgHeight = 0;
let heightScale = 1;
let footprintPack = null;
let areaScale = 1;
let demoRemovedIds = new Set();
let activePopup = null;
let activePopupProperties = null;
let polygonTerritories = null;
let hasPolygonTerritories = false;
let skeletonTerritories = null;
let hasSkeletonTerritories = false;

const territoryLayerIds = [
  'territories-fill',
  'territories-outline',
  'allowed-growth-fill',
  'allowed-growth-outline',
  'representative-points'
];
const gridLayerIds = ['grid-outline-fill', 'grid-outline-line'];

function setStatus(message, state = 'ready') {
  status.textContent = message;
  status.dataset.state = state;
}

function escapeHtml(value) {
  return String(value ?? '—')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function visitCoordinates(coordinates, bounds) {
  if (!Array.isArray(coordinates)) return;
  if (typeof coordinates[0] === 'number') {
    bounds.extend(coordinates);
    return;
  }
  coordinates.forEach((child) => visitCoordinates(child, bounds));
}

function dataBounds(featureCollection) {
  const bounds = new maplibregl.LngLatBounds();
  featureCollection.features.forEach((feature) => visitCoordinates(feature.geometry?.coordinates, bounds));
  return bounds;
}

function heightExpression() {
  return roleCase(
    ['*', ['get', 'display_height'], heightScale],
    ['get', 'display_height']
  );
}

function formatArea(value) {
  const rounded = Math.round(Number(value));
  return `${rounded.toLocaleString('en-US')} m²`;
}

function formatPct(value) {
  const number = Number(value);
  return `${number > 0 ? '+' : ''}${number.toFixed(1)}%`;
}

function roleCase(editableValue, contextValue) {
  return ['case', ['==', ['get', 'role'], 'context'], contextValue, editableValue];
}

function renderPopup(properties) {
  const original = Number(properties.display_height);
  const scenario = original * heightScale;
  const isContext = properties.role === 'context';
  const role = isContext ? 'Context (not edited)' : 'Editable';
  const hasAreas = Number.isFinite(Number(properties.original_area_m2));
  const rows = [
    `<div class="popup-title">${escapeHtml(properties.building_id)}</div>`,
    `<div class="popup-row"><span>Role</span><strong>${role}</strong></div>`
  ];
  if (isContext) {
    rows.push(`<div class="popup-row"><span>Height</span><strong>${original.toFixed(1)} m</strong></div>`);
  } else {
    rows.push(
      `<div class="popup-row"><span>Original Height</span><strong>${original.toFixed(1)} m</strong></div>`,
      `<div class="popup-row"><span>Scenario Height</span><strong>${scenario.toFixed(1)} m</strong></div>`,
      `<div class="popup-row"><span>Height Scale</span><strong>${heightScale.toFixed(2)}×</strong></div>`
    );
  }
  if (hasAreas) {
    if (isContext) {
      rows.push(`<div class="popup-row"><span>Original Area</span><strong>${formatArea(properties.original_area_m2)}</strong></div>`);
    } else {
      rows.push(
        `<div class="popup-row"><span>Original Area</span><strong>${formatArea(properties.original_area_m2)}</strong></div>`,
        `<div class="popup-row"><span>Requested Area</span><strong>${formatArea(properties.requested_area_m2)}</strong></div>`,
        `<div class="popup-row"><span>Achieved Area</span><strong>${formatArea(properties.achieved_area_m2)}</strong></div>`,
        `<div class="popup-row"><span>Achieved Ratio</span><strong>${(Number(properties.achieved_ratio) * 100).toFixed(0)}%</strong></div>`
      );
    }
  }
  if (properties.geometry_was_fragmented) {
    rows.push(`<div class="popup-row"><span>Fragment</span><strong>clipped</strong></div>`);
  }
  return rows.join('\n');
}

function updateHeightScenario() {
  scaleValue.textContent = `${heightScale.toFixed(2)}×`;
  originalAverage.textContent = originalAvgHeight ? `${originalAvgHeight.toFixed(1)} m` : '—';
  scenarioAverage.textContent = originalAvgHeight ? `${(originalAvgHeight * heightScale).toFixed(1)} m` : '—';
  const change = Math.round((heightScale - 1) * 100);
  heightChange.textContent = `${change > 0 ? '+' : ''}${change}%`;

  if (map.getLayer(extrusionLayerId)) {
    map.setPaintProperty(extrusionLayerId, 'fill-extrusion-height', heightExpression());
  }
  if (activePopup?.isOpen() && activePopupProperties) {
    activePopup.setHTML(renderPopup(activePopupProperties));
  }
}

function resetHeightScale() {
  heightScale = 1;
  heightSlider.value = '1';
  updateHeightScenario();
}

function footprintSummary() {
  const scaleKey = areaScale.toFixed(2);
  return footprintPack?.scales?.[scaleKey]?.summary ?? null;
}

function updateFootprintScenario() {
  if (!footprintPack) return;
  const scaleKey = areaScale.toFixed(2);
  fpScaleValue.textContent = `${areaScale.toFixed(2)}×`;
  const summary = footprintPack.scales[scaleKey]?.summary;
  if (!summary) return;
  fpRequestedChange.textContent = formatPct(summary.requested_change_pct);
  fpAchievedChange.textContent = formatPct(summary.achieved_change_pct);
  fpMinGap.textContent = `${footprintPack.min_building_gap} m`;
  fpOriginalArea.textContent = formatArea(summary.original_area_m2);
  fpRequestedArea.textContent = formatArea(summary.requested_area_m2);
  fpAchievedArea.textContent = formatArea(summary.achieved_area_m2);
  fpAreaChange.textContent = formatPct(summary.achieved_change_pct);

  if (map.getSource(sourceId)) {
    map.getSource(sourceId).setData(buildScenarioData());
  }
  if (activePopup?.isOpen() && activePopupProperties) {
    activePopup.setHTML(renderPopup(activePopupProperties));
  }
}

function resetFootprintScale() {
  areaScale = footprintPack?.area_scale_min ?? 1;
  areaSlider.value = String(areaScale);
  updateFootprintScenario();
}

function scenarioEntries(scaleKey) {
  const scale = footprintPack?.scales?.[scaleKey];
  if (!scale) return new Map();
  return new Map(scale.scenario.map((entry) => [entry.id, entry]));
}

function buildScenarioData() {
  const scaleKey = areaScale.toFixed(2);
  const entries = scenarioEntries(scaleKey);
  const features = [];
  for (const building of Object.values(footprintPack.buildings)) {
    const properties = { ...building.properties, role: building.role };
    let geometry;
    if (building.role === 'editable') {
      const entry = entries.get(building.properties.building_id);
      if (entry) {
        geometry = entry.geometry;
        properties.original_area_m2 = entry.original_area_m2;
        properties.requested_area_m2 = entry.requested_area_m2;
        properties.achieved_area_m2 = entry.achieved_area_m2;
        properties.requested_ratio = entry.requested_ratio;
        properties.achieved_ratio = entry.achieved_ratio;
        properties.geometry_was_fragmented = entry.geometry_was_fragmented;
      } else {
        geometry = building.original_geometry;
        properties.original_area_m2 = building.original_area_m2;
      }
    } else {
      geometry = building.original_geometry;
      properties.original_area_m2 = building.original_area_m2;
    }
    properties.demo_removed = isEmbedded && demoRemovedIds.has(building.properties.building_id);
    features.push({ type: 'Feature', geometry, properties });
  }
  return { type: 'FeatureCollection', features };
}

function randomizeEmbeddedBuildings() {
  if (!isEmbedded || !footprintPack) return;
  const ids = Object.values(footprintPack.buildings)
    .filter((building) => building.role === 'editable')
    .map((building) => building.properties.building_id);
  const count = Math.max(1, Math.round(ids.length * 0.10));
  for (let i = ids.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [ids[i], ids[j]] = [ids[j], ids[i]];
  }
  demoRemovedIds = new Set(ids.slice(0, count));
  if (map.getSource(sourceId)) map.getSource(sourceId).setData(buildScenarioData());
}

async function loadPolygonTerritories(gridIds) {
  const results = await Promise.all(
    gridIds.map(async (gridId) => {
      try {
        const response = await fetch(`./output/grid_${gridId}_polygon_territories.geojson`, { cache: 'no-store' });
        if (!response.ok) return null;
        return await response.json();
      } catch {
        return null;
      }
    })
  );
  const features = results.filter(Boolean).flatMap((collection) => collection.features ?? []);
  if (!features.length) return null;
  return { type: 'FeatureCollection', features };
}

async function loadSkeletonTerritories(gridIds) {
  const results = await Promise.all(
    gridIds.map(async (gridId) => {
      try {
        const response = await fetch(`./output/straight_skeleton_debug_${gridId}.geojson`, { cache: 'no-store' });
        if (!response.ok) return null;
        return await response.json();
      } catch {
        return null;
      }
    })
  );
  const territories = [];
  for (const collection of results) {
    if (!collection?.features) continue;
    for (const feature of collection.features) {
      if (feature.properties?.feature_type === 'growth_territory') {
        territories.push(feature);
      }
    }
  }
  if (!territories.length) return null;
  return {
    territories: { type: 'FeatureCollection', features: territories }
  };
}

function territoryCollections() {
  if (hasSkeletonTerritories && skeletonTerritories) {
    return {
      territories: skeletonTerritories.territories,
      allowed: { type: 'FeatureCollection', features: [] },
      points: { type: 'FeatureCollection', features: [] },
      skeleton: true
    };
  }
  if (hasPolygonTerritories && polygonTerritories) {
    return {
      territories: polygonTerritories,
      allowed: { type: 'FeatureCollection', features: [] },
      points: { type: 'FeatureCollection', features: [] }
    };
  }
  const territories = [];
  const allowed = [];
  const points = [];
  for (const building of Object.values(footprintPack.buildings)) {
    const properties = { building_id: building.properties.building_id, role: building.role };
    territories.push({ type: 'Feature', properties, geometry: building.territory });
    allowed.push({ type: 'Feature', properties, geometry: building.allowed_growth });
    points.push({
      type: 'Feature',
      properties,
      geometry: { type: 'Point', coordinates: building.representative_point }
    });
  }
  return {
    territories: { type: 'FeatureCollection', features: territories },
    allowed: { type: 'FeatureCollection', features: allowed },
    points: { type: 'FeatureCollection', features: points }
  };
}

function removeTerritoryLayers() {
  for (const layerId of territoryLayerIds) {
    if (map.getLayer(layerId)) map.removeLayer(layerId);
  }
  for (const sourceId of ['territories', 'allowed-growth', 'representative-points']) {
    if (map.getSource(sourceId)) map.removeSource(sourceId);
  }
}

function applyTerritoryLayers() {
  removeTerritoryLayers();
  if (!territoryToggle.checked || !footprintPack) return;
  const collections = territoryCollections();
  const skeletonMode = hasSkeletonTerritories && skeletonTerritories;
  const polygonMode = hasPolygonTerritories && polygonTerritories;
  map.addSource('territories', { type: 'geojson', data: collections.territories });
  if (skeletonMode) {
    map.addLayer({
      id: 'territories-outline',
      type: 'line',
      source: 'territories',
      paint: { 'line-color': '#0f9185', 'line-width': 1.4, 'line-opacity': 0.9 }
    });
    map.on('mouseenter', 'territories-outline', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'territories-outline', () => { map.getCanvas().style.cursor = ''; });
    map.on('click', 'territories-outline', (event) => {
      const feature = event.features?.[0];
      if (!feature) return;
      const props = feature.properties;
      const rows = [
        `<div class="popup-title">${escapeHtml(props.building_id)}</div>`,
        `<div class="popup-row"><span>Territory Area</span><strong>${formatArea(props.territory_area)}</strong></div>`,
        `<div class="popup-row"><span>Building Area</span><strong>${formatArea(props.building_area)}</strong></div>`,
        `<div class="popup-row"><span>Available Growth</span><strong>${formatArea(props.available_growth_area)}</strong></div>`
      ];
      if (Number.isFinite(Number(props.height))) {
        rows.push(`<div class="popup-row"><span>Height</span><strong>${Number(props.height).toFixed(1)} m</strong></div>`);
      }
      activePopup?.remove();
      activePopup = new maplibregl.Popup({ closeButton: true, maxWidth: '320px' })
        .setLngLat(event.lngLat)
        .setHTML(rows.join('\n'))
        .addTo(map);
      activePopup.on('close', () => { activePopup = null; });
    });
    return;
  }
  if (polygonMode) {
    map.addLayer({
      id: 'territories-fill',
      type: 'fill',
      source: 'territories',
      paint: { 'fill-color': '#8ad5cb', 'fill-opacity': 0.28 }
    });
    map.addLayer({
      id: 'territories-outline',
      type: 'line',
      source: 'territories',
      paint: { 'line-color': '#0f9185', 'line-width': 1.2, 'line-opacity': 0.75 }
    });
    map.on('mouseenter', 'territories-fill', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'territories-fill', () => { map.getCanvas().style.cursor = ''; });
    map.on('click', 'territories-fill', (event) => {
      const feature = event.features?.[0];
      if (!feature) return;
      const props = feature.properties;
      const rows = [
        `<div class="popup-title">${escapeHtml(props.building_id)}</div>`,
        `<div class="popup-row"><span>Territory Area</span><strong>${formatArea(props.territory_area)}</strong></div>`,
        `<div class="popup-row"><span>Building Area</span><strong>${formatArea(props.building_area)}</strong></div>`,
        `<div class="popup-row"><span>Available Growth</span><strong>${formatArea(props.available_growth_area)}</strong></div>`
      ];
      if (Number.isFinite(Number(props.height))) {
        rows.push(`<div class="popup-row"><span>Height</span><strong>${Number(props.height).toFixed(1)} m</strong></div>`);
      }
      activePopup?.remove();
      activePopup = new maplibregl.Popup({ closeButton: true, maxWidth: '320px' })
        .setLngLat(event.lngLat)
        .setHTML(rows.join('\n'))
        .addTo(map);
      activePopup.on('close', () => { activePopup = null; });
    });
    return;
  }
  map.addSource('allowed-growth', { type: 'geojson', data: collections.allowed });
  map.addSource('representative-points', { type: 'geojson', data: collections.points });
  map.addLayer({
    id: 'territories-fill',
    type: 'fill',
    source: 'territories',
    paint: {
      'fill-color': roleCase('#14a89a', '#71858d'),
      'fill-opacity': roleCase(0.10, 0.06)
    }
  });
  map.addLayer({
    id: 'territories-outline',
    type: 'line',
    source: 'territories',
    paint: {
      'line-color': roleCase('#14a89a', '#8fa3aa'),
      'line-width': roleCase(1.1, 0.7),
      'line-opacity': roleCase(0.55, 0.3)
    }
  });
  map.addLayer({
    id: 'allowed-growth-fill',
    type: 'fill',
    source: 'allowed-growth',
    paint: { 'fill-color': '#ffb35c', 'fill-opacity': 0.12 }
  });
  map.addLayer({
    id: 'allowed-growth-outline',
    type: 'line',
    source: 'allowed-growth',
    paint: { 'line-color': '#ff9a3d', 'line-width': 0.9, 'line-opacity': 0.5 }
  });
  map.addLayer({
    id: 'representative-points',
    type: 'circle',
    source: 'representative-points',
    paint: {
      'circle-radius': 3,
      'circle-color': '#16313a',
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 1
    }
  });
}

function ensureLayers(data) {
  if (map.getSource(sourceId)) {
    map.getSource(sourceId).setData(data);
    return;
  }
  map.addSource(sourceId, { type: 'geojson', data, generateId: true });
  map.addLayer({
    id: extrusionLayerId,
    type: 'fill-extrusion',
    source: sourceId,
    paint: {
      'fill-extrusion-height': heightExpression(),
      'fill-extrusion-base': 0,
      'fill-extrusion-color': isEmbedded ? roleCase(
        ['interpolate', ['linear'], ['get', 'display_height'],
          0, '#f1f5f9',
          18, '#dbe4ee',
          45, '#b5c2d1',
          100, '#8091a5'],
        '#9aa9b8'
      ) : roleCase(
        ['interpolate', ['linear'], ['get', 'display_height'],
          0, '#d4ebe8',
          18, '#a6d4cf',
          45, '#79b7bd',
          100, '#5f91ad'],
        '#b8c6cb'
      ),
      'fill-extrusion-opacity': 0.94,
      'fill-extrusion-vertical-gradient': true
    },
    filter: ['!=', ['get', 'demo_removed'], true]
  });
  map.addLayer({
    id: outlineLayerId,
    type: 'line',
    source: sourceId,
    paint: {
      'line-color': roleCase('#4b5563', '#9ca3af'),
      'line-width': roleCase(0.65, 0.5),
      'line-opacity': roleCase(0.28, 0.15)
    },
    filter: ['!=', ['get', 'demo_removed'], true]
  });

  map.on('mouseenter', extrusionLayerId, () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', extrusionLayerId, () => { map.getCanvas().style.cursor = ''; });
  map.on('click', extrusionLayerId, (event) => {
    const feature = event.features?.[0];
    if (!feature) return;
    activePopupProperties = feature.properties;
    activePopup?.remove();
    activePopup = new maplibregl.Popup({ closeButton: true, maxWidth: '320px' })
      .setLngLat(event.lngLat)
      .setHTML(renderPopup(activePopupProperties))
      .addTo(map);
    activePopup.on('close', () => { activePopupProperties = null; });
  });
}

function setFootprintControlsEnabled(enabled) {
  areaSlider.disabled = !enabled;
  resetFootprintButton.disabled = !enabled;
  territoryToggle.disabled = !enabled;
  gridToggle.disabled = !enabled;
}

function configureAreaSlider(pack) {
  const min = Number(pack.area_scale_min ?? 1);
  const max = Number(pack.area_scale_max ?? 2);
  const step = Number(pack.area_scale_step ?? 0.05);
  areaSlider.min = String(min);
  areaSlider.max = String(max);
  areaSlider.step = String(step);
  areaSlider.value = String(min);
}

function gridOutlineData(pack) {
  const features = (pack.grid_outlines ?? []).map((geometry) => ({
    type: 'Feature',
    properties: {},
    geometry
  }));
  if (pack.study_area) {
    features.push({ type: 'Feature', properties: {}, geometry: pack.study_area });
  }
  return { type: 'FeatureCollection', features };
}

function removeGridLayers() {
  for (const layerId of gridLayerIds) {
    if (map.getLayer(layerId)) map.removeLayer(layerId);
  }
  if (map.getSource('grid-outlines')) map.removeSource('grid-outlines');
}

function applyGridLayers() {
  removeGridLayers();
  if (!gridToggle.checked || !footprintPack) return;
  map.addSource('grid-outlines', { type: 'geojson', data: gridOutlineData(footprintPack) });
  map.addLayer({
    id: 'grid-outline-fill',
    type: 'fill',
    source: 'grid-outlines',
    paint: { 'fill-color': '#14a89a', 'fill-opacity': 0.08 }
  });
  map.addLayer({
    id: 'grid-outline-line',
    type: 'line',
    source: 'grid-outlines',
    paint: { 'line-color': '#0f9185', 'line-width': 1.3, 'line-opacity': 0.7 }
  });
}

async function loadGrid(gridId) {
  button.disabled = true;
  setStatus(`Loading footprint scenario for grid ${gridId}…`);
  try {
    const packResponse = await fetch(`./output/grid_${gridId}_footprint.json`, { cache: 'no-store' });
    if (packResponse.ok) {
      const pack = await packResponse.json();
      if (pack.buildings && pack.scales?.['1.00']) {
        await loadFootprintGrid(`Grid ${gridId}`, pack);
        return;
      }
    }
    await loadLegacyGrid(gridId);
  } catch (error) {
    footprintPack = null;
    setFootprintControlsEnabled(false);
    territoryToggle.checked = false;
    gridToggle.checked = false;
    removeTerritoryLayers();
    removeGridLayers();
    setStatus(`${error.message}. Run prepare_footprint.py for this grid first.`, 'error');
  } finally {
    button.disabled = false;
  }
}

async function loadCluster(seedGrid, gridCount) {
  clusterButton.disabled = true;
  setStatus(`Building adjacent ${gridCount} grid cluster around ${seedGrid}…`);
  try {
    const response = await fetch(`./output/cluster_${seedGrid}_${gridCount}_footprint.json`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`No footprint pack for seed ${seedGrid} × ${gridCount}`);
    const pack = await response.json();
    if (!pack.buildings || !pack.scales?.['1.00']) throw new Error(`Cluster ${seedGrid}×${gridCount} returned no scenario data`);
    await loadFootprintGrid(`${seedGrid} + ${pack.grid_count - 1} adjacent`, pack);
    history.replaceState(null, '', `?seed=${seedGrid}&count=${gridCount}`);
  } catch (error) {
    footprintPack = null;
    setFootprintControlsEnabled(false);
    territoryToggle.checked = false;
    gridToggle.checked = false;
    removeTerritoryLayers();
    removeGridLayers();
    setStatus(`${error.message}. Run prepare_footprint.py --seed-grid ${seedGrid} --grid-count ${gridCount} first.`, 'error');
  } finally {
    clusterButton.disabled = false;
  }
}

async function loadGridList(gridIds) {
  const sorted = [...gridIds].sort((a, b) => a - b);
  const base = 'gridlist_' + sorted.join('_');
  setStatus(`Loading ${sorted.length} selected grids…`);
  try {
    const response = await fetch(`./output/${base}_footprint.json`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`No footprint pack for grid list ${sorted.join(',')}`);
    const pack = await response.json();
    if (!pack.buildings || !pack.scales?.['1.00']) throw new Error('Grid list returned no scenario data');
    await loadFootprintGrid(`${sorted.length} grids`, pack);
    history.replaceState(null, '', `?grids=${sorted.join(',')}`);
  } catch (error) {
    footprintPack = null;
    setFootprintControlsEnabled(false);
    territoryToggle.checked = false;
    gridToggle.checked = false;
    removeTerritoryLayers();
    removeGridLayers();
    setStatus(`${error.message}. Run prepare_footprint.py --grid-ids "${sorted.join(',')}" first.`, 'error');
  }
}

async function loadFootprintGrid(studyLabel, pack) {
  resetHeightScale();
  footprintPack = pack;
  configureAreaSlider(pack);
  areaScale = Number(areaSlider.value);
  ensureLayers(buildScenarioData());
  const bounds = dataBounds(buildScenarioData());
  if (bounds.isEmpty()) throw new Error('Building coordinates are empty');
  map.fitBounds(bounds, { padding: isEmbedded ? 16 : 80, maxZoom: isEmbedded ? 19.4 : 18.2, pitch: isEmbedded ? 66 : 60, bearing: -25, duration: 900 });

  const gridIds = Array.isArray(pack.grid_ids) ? pack.grid_ids : [pack.grid_id];
  polygonTerritories = await loadPolygonTerritories(gridIds);
  hasPolygonTerritories = polygonTerritories !== null;
  skeletonTerritories = await loadSkeletonTerritories(gridIds);
  hasSkeletonTerritories = skeletonTerritories !== null;

  const editable = Object.values(pack.buildings).filter((building) => building.role === 'editable');
  const measured = editable.filter((building) => building.properties.height_source !== 'fallback').length;
  currentStudyLabel = studyLabel;
  originalAvgHeight = editable.reduce(
    (sum, building) => sum + Number(building.properties.display_height),
    0
  ) / editable.length;
  heightSlider.disabled = false;
  resetHeightButton.disabled = false;
  setFootprintControlsEnabled(true);
  territoryToggle.checked = isEmbedded ? false : hasSkeletonTerritories;
  gridToggle.checked = false;
  removeTerritoryLayers();
  removeGridLayers();
  if (territoryToggle.checked) applyTerritoryLayers();
  updateHeightScenario();
  updateFootprintScenario();
  if (pendingEmbeddedScenario) {
    setScenarioScale(heightSlider, pendingEmbeddedScenario.heightScale);
    setScenarioScale(areaSlider, pendingEmbeddedScenario.areaScale);
  }
  document.querySelector('#metric-grid').textContent = studyLabel;
  document.querySelector('#metric-count').textContent = `${editable.length} editable + ${pack.context_count} context`;
  document.querySelector('#metric-measured').textContent = `${Math.round(measured / editable.length * 100)}%`;
  setStatus(
    `${editable.length} editable footprints · ${pack.context_count} context constraints · ` +
    (hasSkeletonTerritories ? 'territory: straight skeleton' : (hasPolygonTerritories ? 'territory: polygon-distance' : 'no territory')) +
    ' · EPSG:4326'
  );
  notifyEmbed({ type: 'plateau:scenario-ready', grid: studyLabel, heightScale, areaScale });
  startEmbeddedScenarioLoop();
}

async function loadLegacyGrid(gridId) {
  setStatus(`Loading complete buildings for grid ${gridId}…`);
  const response = await fetch(`./output/grid_${gridId}_buildings.geojson`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`No prepared data for grid ${gridId}`);
  const data = await response.json();
  if (!data.features?.length) throw new Error(`Grid ${gridId} returned no buildings`);
  footprintPack = null;
  setFootprintControlsEnabled(false);
  territoryToggle.checked = false;
  gridToggle.checked = false;
  removeTerritoryLayers();
  removeGridLayers();
  resetHeightScale();
  ensureLayers(data);
  const bounds = dataBounds(data);
  if (bounds.isEmpty()) throw new Error('Building coordinates are empty');
  map.fitBounds(bounds, { padding: isEmbedded ? 16 : 75, maxZoom: isEmbedded ? 19.4 : 18.2, pitch: isEmbedded ? 66 : 60, bearing: -25, duration: 900 });

  const measured = data.features.filter((feature) => feature.properties.height_source !== 'fallback').length;
  currentStudyLabel = `Grid ${gridId}`;
  originalAvgHeight = data.features.reduce(
    (sum, feature) => sum + Number(feature.properties.display_height),
    0
  ) / data.features.length;
  heightSlider.disabled = false;
  resetHeightButton.disabled = false;
  updateHeightScenario();
  document.querySelector('#metric-grid').textContent = currentStudyLabel;
  document.querySelector('#metric-count').textContent = data.features.length.toLocaleString();
  document.querySelector('#metric-measured').textContent = `${Math.round(measured / data.features.length * 100)}%`;
  setStatus(`${data.features.length} complete PLATEAU footprints · EPSG:4326 · extrusion scale 1:1`);
  history.replaceState(null, '', `?grid_id=${gridId}`);
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const gridId = Number.parseInt(input.value, 10);
  if (Number.isInteger(gridId) && gridId > 0) loadGrid(gridId);
});

clusterForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const seedGrid = Number.parseInt(seedInput.value, 10);
  const gridCount = Number.parseInt(gridCountInput.value, 10);
  if (Number.isInteger(seedGrid) && seedGrid > 0 && Number.isInteger(gridCount) && gridCount >= 2) {
    loadCluster(seedGrid, gridCount);
  }
});

heightSlider.addEventListener('input', () => {
  heightScale = Number(heightSlider.value);
  updateHeightScenario();
});

areaSlider.addEventListener('input', () => {
  areaScale = Number(areaSlider.value);
  updateFootprintScenario();
});

// Controlled embedding API for the HeatScope landing-page scenario demo.
// The viewer remains the source of truth: these commands update the same
// sliders and scenario functions used by direct interaction.
const heatscopeEmbedOrigins = new Set([
  'http://127.0.0.1:8200',
  'http://localhost:8200',
  'https://heatscope.cloud'
]);
let pendingEmbeddedScenario = null;
let embeddedLoopTimer = null;

function notifyEmbed(message) {
  if (window.parent === window) return;
  try {
    const parentOrigin = new URL(document.referrer).origin;
    if (heatscopeEmbedOrigins.has(parentOrigin)) window.parent.postMessage(message, parentOrigin);
  } catch { /* standalone viewer: no trusted parent to notify */ }
}

function startEmbeddedScenarioLoop() {
  if (!isEmbedded || !footprintPack) return;
  clearTimeout(embeddedLoopTimer);
  const steps = [
    { height: 0.85, area: 1.00 },
    { height: 1.05, area: 1.10 },
    { height: 1.25, area: 1.18 },
    { height: 1.05, area: 1.10 },
    { height: 0.85, area: 1.00 }
  ];
  let index = 0;
  const animateTo = (target, complete) => {
    const startHeight = heightScale;
    const startArea = areaScale;
    const startTime = performance.now();
    const duration = 1200;
    const frame = (now) => {
      const progress = Math.min(1, (now - startTime) / duration);
      const eased = progress * progress * (3 - 2 * progress);
      heightScale = startHeight + (target.height - startHeight) * eased;
      heightSlider.value = String(heightScale);
      updateHeightScenario();
      const interpolatedArea = startArea + (target.area - startArea) * eased;
      const availableArea = Math.round(interpolatedArea * 20) / 20;
      if (availableArea !== areaScale) {
        areaScale = availableArea;
        areaSlider.value = String(areaScale);
        updateFootprintScenario();
      }
      if (progress < 1) requestAnimationFrame(frame);
      else {
        heightScale = target.height;
        areaScale = target.area;
        heightSlider.value = String(heightScale);
        areaSlider.value = String(areaScale);
        updateHeightScenario();
        updateFootprintScenario();
        randomizeEmbeddedBuildings();
        complete();
      }
    };
    requestAnimationFrame(frame);
  };
  const next = () => {
    const step = steps[index];
    animateTo(step, () => {
      index = (index + 1) % steps.length;
      embeddedLoopTimer = setTimeout(next, 450);
    });
  };
  next();
}

function setScenarioScale(control, requestedValue) {
  const value = Number(requestedValue);
  if (!Number.isFinite(value) || control.disabled) return false;
  const min = Number(control.min);
  const max = Number(control.max);
  const step = Number(control.step) || 0.01;
  const clamped = Math.min(max, Math.max(min, value));
  const snapped = Math.round((clamped - min) / step) * step + min;
  control.value = String(Number(snapped.toFixed(4)));
  control.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
}

window.addEventListener('message', (event) => {
  if (!heatscopeEmbedOrigins.has(event.origin)) return;
  const message = event.data;
  if (!message || message.type !== 'heatscope:scenario') return;
  pendingEmbeddedScenario = message;
  const heightUpdated = setScenarioScale(heightSlider, message.heightScale);
  const areaUpdated = setScenarioScale(areaSlider, message.areaScale);
  event.source?.postMessage({
    type: 'plateau:scenario-state',
    ready: !heightSlider.disabled && !areaSlider.disabled,
    heightScale,
    areaScale,
    heightUpdated,
    areaUpdated
  }, event.origin);
});

resetHeightButton.addEventListener('click', resetHeightScale);
resetFootprintButton.addEventListener('click', resetFootprintScale);
territoryToggle.addEventListener('change', applyTerritoryLayers);
gridToggle.addEventListener('change', applyGridLayers);

map.on('load', async () => {
  try {
    const params = new URLSearchParams(location.search);
    const gridsParam = params.get('grids');
    if (gridsParam) {
      const gridIds = gridsParam.split(',').map((value) => Number.parseInt(value.trim(), 10));
      if (gridIds.every((value) => Number.isInteger(value) && value > 0) && gridIds.length > 1) {
        await loadGridList(gridIds);
        return;
      }
    }
    const seedParam = Number.parseInt(params.get('seed'), 10);
    const countParam = Number.parseInt(params.get('count'), 10);
    if (Number.isInteger(seedParam) && seedParam > 0 && Number.isInteger(countParam) && countParam >= 2) {
      seedInput.value = seedParam;
      gridCountInput.value = countParam;
      await loadCluster(seedParam, countParam);
      return;
    }
    const configResponse = await fetch('./output/viewer_config.json', { cache: 'no-store' });
    if (!configResponse.ok) throw new Error('viewer_config.json is missing');
    const config = await configResponse.json();
    const requested = Number.parseInt(params.get('grid_id'), 10);
    const gridId = Number.isInteger(requested) ? requested : config.default_grid_id;
    input.value = gridId;
    await loadGrid(gridId);
  } catch (error) {
    setStatus(`${error.message}. Generate the grid data before opening the viewer.`, 'error');
  }
});
