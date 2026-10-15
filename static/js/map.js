'use strict';

// 지도는 Leaflet, 경계선은 공개 GeoJSON, 장소는 Flask API에서 불러옵니다.
const GEO_BASES = [
  '/static/geo/',
  'https://cdn.jsdelivr.net/gh/KnellBalm/kr-admin-geojson@main/',
  'https://raw.githubusercontent.com/KnellBalm/kr-admin-geojson/main/'
];
// 대한민국 전국 17개 시·도: DB에 등록되지 않은 시·도도 GeoJSON 경계에서 자동 보충합니다.
// 특별시·광역시·특별자치시는 구·군 단위, 세종은 읍·면·동 단위로 펼쳐집니다.
const METRO_CODES = new Set(['11', '26', '27', '28', '29', '30', '31', '36']);
// 도는 북쪽부터 남쪽으로, 특별시·광역시는 행정구역 코드 순서로 배치합니다.
const REGION_ORDER = ['41', '42', '51', '43', '44', '45', '52', '46', '47', '48', '50',
  '11', '26', '27', '28', '29', '30', '31', '36'];
let sejongEmdCache = null;

const CATEGORIES = {
  tourism: {emoji: '📷', label: '관광지'},
  food: {emoji: '🍜', label: '맛집'},
  event: {emoji: '🎉', label: '행사'}
};
const $ = (selector) => document.querySelector(selector);
const regionIconAliases = {'강원도': '강원특별자치도', '전라북도': '전북특별자치도', '제주도': '제주특별자치도'};
const canonicalRegionName = name => regionIconAliases[name] || name || '';
const regionIconEntries = JSON.parse($('#regionIconData').textContent);
const canonicalIconCode = code => ({'51': '42', '52': '45'}[String(code)] || String(code || ''));
const provinceIconsByCode = new Map(regionIconEntries.filter(icon => icon.level === '시·도')
  .map(icon => [canonicalIconCode(icon.region_code), icon.url]));
const localIconsByCode = new Map(regionIconEntries.filter(icon => icon.parent)
  .map(icon => [`${canonicalIconCode(icon.region_code)}|${canonicalRegionName(icon.name)}`, icon.url]));
const regionIcons = new Map(regionIconEntries.map(icon =>
  [`${canonicalRegionName(icon.parent)}|${canonicalRegionName(icon.name)}`, icon.url]));
function regionImageUrl(feature) {
  const name = feature.properties.displayName;
  const parent = state.selectedRegion?.name || '';
  const isProvince = Boolean(feature.properties.CTP_KOR_NM);
  const code = canonicalIconCode(feature.properties.regionCode || feature.properties.CTPRVN_CD || state.selectedRegion?.code);
  const codedIcon = isProvince ? provinceIconsByCode.get(code)
    : localIconsByCode.get(`${code}|${canonicalRegionName(name)}`);
  if (codedIcon) return codedIcon;
  return regionIcons.get(`${isProvince ? '' : canonicalRegionName(parent)}|${canonicalRegionName(name)}`);
}
function regionLabel(feature) {
  const name = feature.properties.displayName;
  const url = regionImageUrl(feature);
  const label = document.createElement('span');
  label.className = 'region-map-label';
  if (url) {
    const image = document.createElement('img');
    image.src = url;
    image.alt = '';
    image.className = 'region-map-icon';
    image.decoding = 'async';
    image.addEventListener('error', () => image.remove(), {once: true});
    label.append(image);
  }
  const caption = document.createElement('span');
  caption.className = 'region-map-caption';
  caption.textContent = name;
  label.append(caption);
  return label;
}
function showHomeView() {
  const width = document.getElementById('map').clientWidth;
  map.setView([36.7, 128.3], width >= 1200 ? 7.5 : width >= 700 ? 7.25 : 6.75, {animate: false});
}
// Scattered, deterministic wavelets avoid an obvious repeating ocean tile.
function decorateOcean() {
  const ocean = $('.ocean-waves');
  if (!ocean) return;
  let seed = 731;
  const random = () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  const fragment = document.createDocumentFragment();
  for (let i = 0; i < 58; i++) {
    const wave = document.createElement('span');
    wave.className = 'ocean-wavelet';
    const values = {
      '--wave-x': `${random() * 100}%`, '--wave-y': `${random() * 100}%`,
      '--wave-width': `${22 + random() * 80}px`, '--wave-height': `${7 + random() * 15}px`,
      '--wave-opacity': (.15 + random() * .4).toFixed(2),
      '--wave-duration': `${22 + random() * 27}s`, '--wave-delay': `${-random() * 49}s`,
      '--wave-angle': `${-18 + random() * 30}deg`, '--wave-drift': `${15 + random() * 35}px`
    };
    Object.entries(values).forEach(([key, value]) => wave.style.setProperty(key, value));
    fragment.appendChild(wave);
  }
  ocean.appendChild(fragment);
}
decorateOcean();
const ISLAND_DISPLAYS = [
  {name: '제주도', center: [126.55, 33.38], scale: 1.55, contains: (x, y) => x > 125.8 && x < 127.2 && y > 32.8 && y < 33.9},
  {name: '울릉도', center: [130.9, 37.5], scale: 3, contains: (x, y) => x > 130.5 && x < 131.3 && y > 37 && y < 38},
  {name: '독도', center: [131.87, 37.24], scale: 9, contains: (x, y) => x > 131.5 && x < 132.2 && y > 37 && y < 37.7}
];
function displayCoordinate(coordinate) {
  const [x, y] = coordinate;
  const island = ISLAND_DISPLAYS.find(item => item.contains(x, y));
  return island ? [island.center[0] + (x - island.center[0]) * island.scale,
    island.center[1] + (y - island.center[1]) * island.scale] : [x, y];
}
function displayLatLng(lat, lng) {
  const [x, y] = displayCoordinate([lng, lat]);
  return [y, x];
}
const sharedProvinceVertices = new Set();
const coordinateKey = ([x, y]) => `${x.toFixed(7)},${y.toFixed(7)}`;
function indexProvinceBorders(features) {
  sharedProvinceVertices.clear();
  const owners = new Map();
  features.forEach((feature, index) => {
    asPolygons(feature.geometry).forEach(polygon => polygon.forEach(ring => {
      ring.forEach(point => {
        const key = coordinateKey(point);
        if (owners.has(key) && owners.get(key) !== index) sharedProvinceVertices.add(key);
        else owners.set(key, index);
      });
    }));
  });
}
// Cut coastal corners only; shared administrative vertices stay stationary.
// A bounded radius keeps small islands recognizable and avoids oversized curves.
function roundCoastline(points, radius, tolerance) {
  const simplify = run => {
    const reduced = L.LineUtil.simplify(run.map(([x, y]) => L.point(x, y)), tolerance);
    return reduced.map(point => [point.x, point.y]);
  };
  const anchors = points.map((point, i) => sharedProvinceVertices.has(coordinateKey(point)) ? i : -1)
    .filter(i => i >= 0);
  let rounded;
  if (!anchors.length) {
    const reduced = simplify([...points, points[0]]).slice(0, -1);
    rounded = reduced.length >= 3 ? reduced : points;
  } else {
    rounded = [];
    anchors.forEach((start, i) => {
      const end = anchors[(i + 1) % anchors.length];
      const run = [points[start]];
      let cursor = (start + 1) % points.length;
      while (cursor !== end) {
        run.push(points[cursor]);
        cursor = (cursor + 1) % points.length;
      }
      run.push(points[end]);
      rounded.push(...(run.length > 2 ? simplify(run) : run).slice(0, -1));
    });
  }
  if (rounded.length < 3) rounded = points;
  for (let pass = 0; pass < 5; pass++) {
    rounded = rounded.flatMap((point, i) => {
      if (sharedProvinceVertices.has(coordinateKey(point))) return [point];
      const previous = rounded[(i + rounded.length - 1) % rounded.length];
      const next = rounded[(i + 1) % rounded.length];
      const towards = neighbor => {
        const distance = Math.hypot(neighbor[0] - point[0], neighbor[1] - point[1]);
        const fraction = distance ? Math.min(.3, radius / distance) : 0;
        return point.map((value, axis) => value + (neighbor[axis] - value) * fraction);
      };
      return [towards(previous), towards(next)];
    });
  }
  return rounded;
}
function smoothDisplayFeature(feature, detailed = false) {
  const polygons = asPolygons(feature.geometry);
  // Detail must retain shared vertices exactly; independent simplification or
  // rounding opens gaps where two administrative polygons meet.
  if (detailed) return {...feature, geometry: {type: 'MultiPolygon',
    coordinates: polygons.map(polygon => polygon.map(ring => ring.map(displayCoordinate)))}};
  const area = ring => Math.abs(ring.reduce((sum, p, i) => {
    const q = ring[(i + 1) % ring.length];
    return sum + p[0] * q[1] - q[0] * p[1];
  }, 0));
  const largest = Math.max(...polygons.map(p => area(p[0])), 0);
  const isProvince = Boolean(feature.properties.CTP_KOR_NM);
  // Hide only small offshore fragments in the overview; retain district detail.
  const kept = polygons.filter(p => !isProvince || area(p[0]) >= largest * .002 ||
    ISLAND_DISPLAYS.some(island => island.contains(...p[0][0])));
  const coordinates = kept.map(polygon => polygon.map(ring => {
    const importantIsland = ISLAND_DISPLAYS.some(island => island.contains(...ring[0]));
    const tolerance = importantIsland ? .00015 : (isProvince ? .004 : .0005);
    const points = ring.slice(0, -1).map(([x, y]) => L.point(x, y));
    const simplified = L.LineUtil.simplify(points, tolerance);
    const outline = simplified.length >= 3 ? simplified.map(p => [p.x, p.y]) : ring.slice(0, -1);
    // Detail layers keep their existing geometry; only the overview gets rounded.
    const softened = isProvince ? roundCoastline(outline,
      importantIsland ? .025 : .18, importantIsland ? .0025 : .045) : outline;
    const displayed = softened.map(displayCoordinate);
    return [...displayed, [...displayed[0]]];
  }));
  return {...feature, geometry: {type: 'MultiPolygon', coordinates}};
}

// 전 세계 배경 타일(OpenStreetMap)을 사용하지 않습니다.
// 따라서 중국·일본 등 외국의 지형이나 도시가 보이지 않습니다.
const map = L.map('map', {
  zoomControl: false,
  zoomAnimation: false,
  markerZoomAnimation: false,
  fadeAnimation: false,
  preferCanvas: false,
  minZoom: 6,
  maxZoom: 18,
  zoomSnap: .25,
  maxBoundsViscosity: 1.0
}).setView([36.7, 128.3], 7.5);
L.control.zoom({position: 'bottomright'}).addTo(map);
map.createPane('countryRelief');
map.getPane('countryRelief').style.zIndex = '390';
map.getPane('countryRelief').style.pointerEvents = 'none';
map.createPane('selectedRelief');
map.getPane('selectedRelief').style.zIndex = '410';
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let clearRegionLift = () => {};
let liftedRegion = null;
map.on('zoomstart', () => map.getContainer().classList.add('map-zooming'));
map.on('zoomend', () => {
  map.getContainer().classList.remove('map-zooming');
});
let mapViewChanging = false;
map.on('movestart zoomstart', () => {
  mapViewChanging = true;
  clearRegionLift();
});
map.on('moveend zoomend', () => {
  mapViewChanging = false;
  clearRegionLift();
});
map.on('viewreset resize', () => clearRegionLift());

const state = {
  regions: [], provinceFeatures: [], districtFeatures: [],
  selectedRegion: null, selectedCity: null, selectedCategory: 'all',
  geoLayer: null, countryLayer: null, markerLayer: L.layerGroup().addTo(map),
  islandLabelLayer: L.layerGroup().addTo(map),
  cityFeatures: [], fetchToken: 0, landmarkData: null, placePage: 0
};

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  if (data.ok === false) throw new Error(data.error || '데이터 요청 오류');
  return data;
}

async function fetchGeo(filename) {
  let lastError;
  for (const base of GEO_BASES) {
    try {
      const data = await fetchJSON(base + filename);
      if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) {
        throw new Error('GeoJSON 형식이 올바르지 않습니다.');
      }
      return data.features;
    } catch (err) { lastError = err; }
  }
  throw lastError || new Error('지도 경계 데이터를 불러올 수 없습니다.');
}

function toast(message) {
  const el = $('#toast');
  el.textContent = message;
  el.classList.remove('hidden');
}
function hideToast() { $('#toast').classList.add('hidden'); }
let cityWatermark = null;
let geoRenderer = null;
let countryRenderer = null;
function clearMap() {
  // Finish any previous camera movement before replacing its SVG layers.
  map.stop();
  map.getContainer().classList.remove('map-zooming');
  map.closePopup();
  state.landmarkData = null;
  state.placePage = 0;
  state.focusedRanking = null;
  if (cityWatermark) { map.removeLayer(cityWatermark); cityWatermark = null; }
  rankingMarkers.clearLayers();
  rankingMarkersByPoi.clear();
  state.favoritesMode = false;
  $('#favoritesBtn').setAttribute('aria-pressed', 'false');
  clearRegionLift();
  if (state.geoLayer) map.removeLayer(state.geoLayer);
  state.geoLayer = null;
  // Remove the SVG itself, including decorative paths and cached filter output.
  if (geoRenderer) { map.removeLayer(geoRenderer); geoRenderer = null; }
  state.markerLayer.clearLayers();
}
function fit(layer, maxZoom = 10, padding = [28, 28]) {
  if (layer && layer.getBounds().isValid()) {
    map.fitBounds(layer.getBounds(), {padding, maxZoom, animate: true});
  }
}
function fitSelectedRegion(layer) {
  if (!layer || !layer.getBounds().isValid()) return;
  const size = map.getSize();
  const sidebarOpen = document.querySelector('.app-shell').classList.contains('sidebar-open');
  const sidebarWidth = sidebarOpen ? document.getElementById('travelSidebar').getBoundingClientRect().width : 0;
  const puzzleView = Boolean(state.selectedCity);
  const horizontal = puzzleView ? Math.max(14, size.x * .02) : Math.max(28, size.x * .06);
  const vertical = puzzleView ? Math.max(30, size.y * .06) : Math.max(45, size.y * .12);
  map.fitBounds(layer.getBounds(), {
    paddingTopLeft: [Math.min(sidebarWidth, size.x * .4) + horizontal, vertical],
    paddingBottomRight: [horizontal, vertical],
    maxZoom: puzzleView ? 18 : 16,
    animate: !puzzleView
  });
}
// 전국 17개 행정구역 윤곽을 배경으로 표시합니다.
// 클릭은 위에 별도로 올리는 선택 가능한 행정구역 레이어에서 처리합니다.
function drawKoreaBackground(detailed = false) {
  if (state.countryLayer) map.removeLayer(state.countryLayer);
  if (countryRenderer) map.removeLayer(countryRenderer);
  countryRenderer = L.svg({pane: 'countryRelief'});
  state.islandLabelLayer.clearLayers();
  document.getElementById('map').classList.toggle('map-detail', detailed);
  // Derive province backgrounds from the same district polygons as the active
  // layer. Province and district datasets can have different outer boundaries.
  const districtsByProvince = new Map();
  if (detailed) state.districtFeatures.forEach(feature => {
    const code = String(feature.properties.CTPRVN_CD);
    if (!districtsByProvince.has(code)) districtsByProvince.set(code, []);
    districtsByProvince.get(code).push(...asPolygons(feature.geometry));
  });
  const background = state.provinceFeatures.map(feature => {
    const polygons = districtsByProvince.get(String(feature.properties.CTPRVN_CD));
    return polygons?.length ? {...feature,
      geometry: {type: 'MultiPolygon', coordinates: polygons}} : feature;
  });
  state.countryLayer = L.geoJSON(background.map(feature => smoothDisplayFeature(feature, detailed)), {
    smoothFactor: 0,
    noClip: true,
    interactive: false,
    pane: 'countryRelief',
    renderer: countryRenderer,
    style: feature => ({
      color: '#827a8e', weight: detailed ? 0 : 1.4,
      fillColor: provinceColor(feature), fillOpacity: 1,
      className: 'country-relief'
    })
  }).addTo(map);
  ISLAND_DISPLAYS.filter(island => island.name !== '제주도').forEach(island => {
    const coordinates = state.provinceFeatures.flatMap(feature => asPolygons(feature.geometry))
      .filter(polygon => island.contains(...polygon[0][0]))
      .flatMap(polygon => polygon[0].map(displayCoordinate));
    if (!coordinates.length) return;
    const center = L.latLngBounds(coordinates.map(([x, y]) => [y, x])).getCenter();
    L.tooltip({permanent: true, direction: 'bottom', offset: [0, 8], className: 'place-tooltip island-tooltip'})
      .setLatLng(center).setContent(island.name).addTo(state.islandLabelLayer);
  });

  // 한국 주변에서만 이동할 수 있도록 지도 범위를 고정합니다.
  const bounds = state.countryLayer.getBounds();
  if (bounds.isValid()) {
    map.setMaxBounds(bounds.pad(0.14));
  }
}

// DB에 시·도가 빠져 있어도 GeoJSON의 전국 17개 지역을 모두 클릭할 수 있도록 보충합니다.
// 기존 DB에 등록된 지역 이름·유형은 우선 사용하고, 누락된 지역은 GeoJSON 이름을 사용합니다.
function buildAllRegions(dbRows, provinces) {
  const fromDB = new Map(dbRows.map(r => [String(r.code), r]));
  const seen = new Set();
  return provinces.map((feature, i) => {
    const code = String(feature.properties.CTPRVN_CD || '');
    if (!code || seen.has(code)) return null;
    seen.add(code);
    const saved = fromDB.get(code);
    return {
      code,
      name: saved?.name || feature.properties.CTP_KOR_NM || code,
      region_type: saved?.region_type || (METRO_CODES.has(code) ? 'metro' : 'province'),
      order: REGION_ORDER.indexOf(code) < 0 ? 100 + i : REGION_ORDER.indexOf(code)
    };
  }).filter(Boolean).sort((a, b) => a.order - b.order);
}

// Codes keep each province's color stable regardless of DB/GeoJSON ordering.
const PROVINCE_COLORS = {
  '11': '#f3acc4', '26': '#f6b6a0', '27': '#c4ade5', '28': '#9dd7cf',
  '29': '#ddaed1', '30': '#a9c5e8', '31': '#f3c888', '36': '#cdb7e5',
  '41': '#c7dca0', '42': '#a0d4bd', '43': '#f1c1a5', '44': '#a6d5de',
  '45': '#e8b7cb', '46': '#cbd9ac', '47': '#bebce7', '48': '#f1d79e',
  '50': '#94d6c4', '51': '#a0d4bd', '52': '#e8b7cb'
};
function colorFor(index) {
  const palette = Object.values(PROVINCE_COLORS).slice(0, 17);
  return palette[index % palette.length];
}
function provinceColor(feature) {
  return PROVINCE_COLORS[String(feature.properties.CTPRVN_CD)] || colorFor(feature.properties.colorIndex || 0);
}
function shapeStyle(feature) {
  return {color: '#8b8296', weight: 1.15, fillColor: provinceColor(feature),
    fillOpacity: 1, className: 'geo-shape'};
}
// Find an interior label position on the largest landmass, excluding holes.
// A bounding-box center can fall in the sea for provinces with many islands.
function regionLabelCenter(feature) {
  const polygons = asPolygons(feature.geometry).map(polygon => polygon.map(ring =>
    ring.map(([lng, lat]) => L.CRS.EPSG3857.project(L.latLng(lat, lng)))));
  const area = ring => Math.abs(ring.reduce((sum, p, i) => {
    const q = ring[(i + 1) % ring.length];
    return sum + p.x * q.y - q.x * p.y;
  }, 0));
  const polygon = polygons.filter(p => p[0]?.length >= 3)
    .sort((a, b) => area(b[0]) - area(a[0]))[0];
  if (!polygon) return L.geoJSON(feature).getBounds().getCenter();
  const inside = (point, ring) => {
    let result = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const a = ring[i], b = ring[j];
      if ((a.y > point.y) !== (b.y > point.y) &&
          point.x < (b.x - a.x) * (point.y - a.y) / (b.y - a.y) + a.x) result = !result;
    }
    return result;
  };
  const clearance = point => {
    if (!inside(point, polygon[0]) || polygon.slice(1).some(ring => inside(point, ring))) return -1;
    let distance = Infinity;
    polygon.forEach(ring => ring.forEach((a, i) => {
      const b = ring[(i + 1) % ring.length];
      const dx = b.x - a.x, dy = b.y - a.y;
      const t = Math.max(0, Math.min(1,
        ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy || 1)));
      distance = Math.min(distance, Math.hypot(point.x - a.x - t * dx, point.y - a.y - t * dy));
    }));
    return distance;
  };
  const bounds = L.bounds(polygon[0]);
  let best = polygon[0][0], score = -1;
  let left = bounds.min.x, bottom = bounds.min.y;
  let width = bounds.max.x - left, height = bounds.max.y - bottom;
  for (let pass = 0; pass < 4; pass++) {
    for (let x = 0; x < 18; x++) for (let y = 0; y < 18; y++) {
      const point = L.point(left + width * (x + .5) / 18, bottom + height * (y + .5) / 18);
      const value = clearance(point);
      if (value > score) { score = value; best = point; }
    }
    width /= 6; height /= 6;
    left = best.x - width / 2; bottom = best.y - height / 2;
  }
  return L.CRS.EPSG3857.unproject(best);
}
function decorativeRegionCopy(path) {
  const copy = path.cloneNode(false);
  copy.removeAttribute('tabindex');
  copy.removeAttribute('role');
  copy.removeAttribute('aria-label');
  copy.setAttribute('aria-hidden', 'true');
  copy.classList.remove('leaflet-interactive', 'region-hit-active');
  // Leaflet's own SVG selector can override ordinary CSS pointer-events rules.
  copy.style.pointerEvents = 'none';
  return copy;
}
function liftRegion(layer) {
  // A cloned SVG path does not follow Leaflet's later path reprojection.
  // The selected city is already highlighted and does not need a hover copy.
  if (state.selectedCity || mapViewChanging) {
    clearRegionLift();
    return;
  }
  if (liftedRegion === layer) return;
  clearRegionLift();
  const path = layer.getElement();
  if (!path) return;
  // Keep the original hit area stationary so the rising region never flickers.
  const raised = decorativeRegionCopy(path);
  raised.classList.add('region-hover');
  // Never reinsert the actual click target between pointer down and pointer up.
  // Only the decorative copy moves to the front; keyboard focus reuses it.
  path.parentNode.appendChild(raised);
  liftedRegion = layer;
  path.classList.add('region-hit-active');
  const tooltip = layer.getTooltip();
  tooltip.options.offset = L.point(0, -8);
  tooltip.update();
  clearRegionLift = () => {
    liftedRegion = null;
    raised.remove();
    path.classList.remove('region-hit-active');
    tooltip.options.offset = L.point(0, 0);
    tooltip.update();
    clearRegionLift = () => {};
  };
}
function bounceRegion(layer, feature, onClick) {
  clearRegionLift();
  const path = layer.getElement();
  if (path && !reducedMotion.matches) {
    const animated = decorativeRegionCopy(path);
    animated.classList.add('region-boing');
    path.parentNode.appendChild(animated);
    setTimeout(() => animated.remove(), 620);
  }
  // Navigation runs immediately; the decorative animation cannot block it.
  onClick(feature);
}
function addGeoLayer(features, onClick) {
  geoRenderer = L.svg({pane: state.selectedRegion ? 'selectedRelief' : 'overlayPane'});
  state.geoLayer = L.geoJSON(features.map(feature => smoothDisplayFeature(feature, Boolean(state.selectedRegion))), {
    smoothFactor: 0,
    noClip: true,
    pane: state.selectedRegion ? 'selectedRelief' : 'overlayPane',
    renderer: geoRenderer,
    style: shapeStyle,
    onEachFeature: (feature, layer) => {
      const name = feature.properties.displayName;
      const labelCenter = regionLabelCenter(feature);
      // Leaflet uses getCenter() for permanent center tooltips, including on zoom.
      layer.getCenter = () => labelCenter;
      layer.on({
        click: () => bounceRegion(layer, feature, onClick),
      });
      layer.on('add', () => {
        const path = layer.getElement();
        if (!path) return;
        path.setAttribute('tabindex', '0');
        path.setAttribute('role', 'button');
        path.setAttribute('aria-label', `${name} 선택`);
        path.addEventListener('mouseenter', () => liftRegion(layer));
        path.addEventListener('mouseleave', () => {
          if (liftedRegion === layer) clearRegionLift();
        });
        path.addEventListener('focus', () => liftRegion(layer));
        path.addEventListener('blur', () => {
          if (liftedRegion === layer) clearRegionLift();
        });
        path.addEventListener('keydown', event => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            bounceRegion(layer, feature, onClick);
          }
        });
      });
      layer.bindTooltip(regionLabel(feature), {permanent: true, direction: 'center',
        className: 'place-tooltip region-icon-tooltip', opacity: .98});
    }
  }).addTo(map);
  return state.geoLayer;
}

function updateStep(number, heading, detail) {
  $('#stepHeading') && ($('#stepHeading').textContent = heading);
  $('#stepDetail') && ($('#stepDetail').textContent = detail);
}
function updateBreadcrumb() {
  document.dispatchEvent(new CustomEvent('map-region-changed', {detail: {
    region: state.selectedRegion?.code || null,
    city: state.selectedCity?.properties.displayName || null
  }}));
  if ($('#crumbRegion')) $('#crumbRegion').textContent = state.selectedRegion?.name || '';
  if ($('#crumbCity')) $('#crumbCity').textContent = state.selectedCity?.properties.displayName || '';
  $('#backBtn').disabled = !state.selectedRegion && !state.favoritesMode;
}
function addRegionButton(container, label, onClick) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'region-button';
  const province = regionIconEntries.find(icon => !icon.parent && canonicalRegionName(icon.name) === canonicalRegionName(label));
  const local = regionIconEntries.find(icon => icon.parent && (
    `${icon.parent} ${icon.name}` === label ||
    (canonicalRegionName(icon.parent) === canonicalRegionName(state.selectedRegion?.name) && icon.name === label)
  ));
  const icon = province || local;
  if (icon) {
    const image = document.createElement('img');
    image.src = icon.url;
    image.alt = '';
    image.className = 'region-button-logo';
    image.loading = 'lazy';
    image.addEventListener('error', () => image.remove(), {once: true});
    btn.append(image);
    btn.style.setProperty('--region-accent', icon.accent || '#608a86');
  }
  const caption = document.createElement('span');
  caption.textContent = label;
  btn.append(caption);
  btn.addEventListener('click', onClick);
  container.appendChild(btn);
}

function goHome() {
  state.favoritesMode = false;
  $('#favoritesBtn').setAttribute('aria-pressed', 'false');
  if ($('#placesDrawer').parentElement === $('#favoritesListSlot')) $('#placesDrawer').classList.add('hidden');
  state.fetchToken++;
  state.selectedRegion = null;
  state.selectedCity = null;
  clearMap(); hideToast();
  drawKoreaBackground();
  $('#selectedCard').classList.add('hidden');
  $('#filters').classList.remove('hidden');
  updateStep('01', '지역을 선택하세요', `시·도 ${state.regions.length}개 지역`);
  updateBreadcrumb();
  $('#mapTip').textContent = '👆 지도에서 시·도를 선택하면 확대됩니다.';
  const list = $('#regionList'); list.replaceChildren();
  $('#regionExpand').classList.remove('hidden');
  renderHomeRegions(false);

  const codes = new Map(state.regions.map(r => [r.code, r]));
  const features = state.provinceFeatures
    .filter(f => codes.has(f.properties.CTPRVN_CD))
    .map((f, i) => ({...f, properties: {
      ...f.properties,
      displayName: codes.get(f.properties.CTPRVN_CD).name,
      colorIndex: i
    }}));
  if (features.length) {
    addGeoLayer(features, f => selectRegion(f.properties.CTPRVN_CD));
    showHomeView();
  }
  else toast('행정구역 지도 데이터를 받지 못했습니다. 인터넷 연결을 확인하세요.');
}

// '수원시 장안구' 같은 도 소속 자치구는 '수원시' 하나로 묶습니다.
// 광역시·특별시는 시 안의 개별 구·군을 그대로 보여 줍니다.
function cityGroupName(feature, metro) {
  const name = feature.properties.SIG_KOR_NM;
  if (metro) return name;
  const names = (feature.properties.FULL_NM || '').split(/\s+/);
  if (names.length >= 3 && names[1].endsWith('시') && names[2].endsWith('구')) return names[1];
  return name;
}
function asPolygons(geometry) {
  if (geometry.type === 'Polygon') return [geometry.coordinates];
  if (geometry.type === 'MultiPolygon') return geometry.coordinates;
  return [];
}
function groupCities(region) {
  const groups = new Map();
  const metro = region.region_type === 'metro';
  const raw = state.districtFeatures.filter(f => f.properties.CTPRVN_CD === region.code);
  raw.forEach(f => {
    const name = cityGroupName(f, metro);
    if (!name) return;
    if (!groups.has(name)) groups.set(name, {polygons: [], name});
    groups.get(name).polygons.push(...asPolygons(f.geometry));
  });
  return [...groups.values()].sort((a, b) => a.name.localeCompare(b.name, 'ko'))
    .map((group, i) => ({
      type: 'Feature',
      properties: {displayName: group.name, regionCode: region.code, colorIndex: i},
      geometry: {type: 'MultiPolygon', coordinates: group.polygons}
    }));
}

// 세종은 산하 시·군·구가 없으므로, 법정 읍·면·동 GeoJSON으로 하위 지역을 구성합니다.
function groupSejongEmd(features) {
  const groups = new Map();
  features.filter(f => String(f.properties.CTPRVN_CD) === '36').forEach(f => {
    const name = f.properties.EMD_KOR_NM;
    if (!name) return;
    if (!groups.has(name)) groups.set(name, []);
    groups.get(name).push(...asPolygons(f.geometry));
  });
  return [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0], 'ko'))
    .map(([name, polygons], i) => ({
      type: 'Feature',
      properties: {displayName: name, regionCode: '36', colorIndex: i},
      geometry: {type: 'MultiPolygon', coordinates: polygons}
    }));
}

async function getSejongCities() {
  if (!sejongEmdCache) {
    sejongEmdCache = fetchGeo('emd.geojson').catch(error => {
      sejongEmdCache = null; // 네트워크 실패 시 다시 시도할 수 있도록 캐시 초기화
      throw error;
    });
  }
  return groupSejongEmd(await sejongEmdCache);
}

function renderHomeRegions(expanded) {
  const list = $('#regionList');
  list.replaceChildren();
  const regions = expanded ? state.regions : [];
  regions.forEach(r => addRegionButton(list, r.name, () => selectRegion(r.code)));
  $('#regionExpand').setAttribute('aria-expanded', String(expanded));
  $('#regionExpand').textContent = expanded ? '전체 지역 접기 −' : `전체 ${state.regions.length}개 지역 펼치기 +`;
  updateStep('01', '지역 선택', '지역을 검색하거나 전체 지역을 펼쳐 선택하세요');
}

$('#regionExpand').addEventListener('click', () => {
  renderHomeRegions($('#regionExpand').getAttribute('aria-expanded') !== 'true');
});

const normalizeRegionSearch = value => value.replace(/\s+/g, '').replace(/특별자치도|특별자치시|특별시|광역시/g, '').replace(/전라북도/g, '전북').replace(/강원도/g, '강원');
let regionSearchVersion = 0;
$('#regionSearchForm').addEventListener('submit', async event => {
  event.preventDefault();
  const requestedCategory = state.selectedCategory;
  const version = ++regionSearchVersion;
  const query = normalizeRegionSearch($('#regionSearchInput').value.trim());
  const message = $('#regionSearchMessage');
  const results = $('#regionSearchResults');
  results.replaceChildren();
  if (!query) { message.textContent = '찾고 싶은 지역 이름을 입력해 주세요.'; return; }
  if (!state.regions.length) { message.textContent = '지도 자료를 불러온 뒤 다시 검색해 주세요.'; return; }
  const matches = [];
  state.regions.forEach(region => {
    const province = normalizeRegionSearch(region.name);
    if (province.includes(query)) matches.push({region, city: null, label: region.name, exact: province === query});
    groupCities(region).forEach(city => {
      const name = city.properties.displayName;
      const normalized = normalizeRegionSearch(name);
      if (normalized.includes(query) || (province + normalized).includes(query)) {
        matches.push({region, city: name, label: `${region.name} ${name}`, exact: normalized === query || province + normalized === query});
      }
    });
  });
  const exact = matches.filter(match => match.exact);
  const found = exact.length ? exact : matches;
  async function openMatch(match) {
    message.textContent = `${match.label}(으)로 이동하고 있어요…`;
    results.replaceChildren();
    await selectRegion(match.region.code);
    if (version !== regionSearchVersion || state.selectedRegion?.code !== match.region.code) return;
    if (match.city) await selectCity(match.city, requestedCategory);
    if (version === regionSearchVersion) message.textContent = `${match.label} 지도를 확대했습니다.`;
  }
  if (found.length === 1) {
    try { await openMatch(found[0]); }
    catch (error) { message.textContent = '지역을 불러오지 못했습니다. 다시 검색해 주세요.'; }
  } else if (found.length) {
    message.textContent = `${found.length}개 지역을 찾았습니다. 원하는 지역을 선택해 주세요.`;
    found.forEach(match => addRegionButton(results, match.label, () => {
      openMatch(match).catch(() => { message.textContent = '지역을 불러오지 못했습니다. 다시 검색해 주세요.'; });
    }));
  } else {
    message.textContent = '일치하는 지역이 없습니다. 시·도 또는 시·군·구 이름으로 검색해 주세요.';
  }
});

async function selectRegion(code) {
  if ($('#placesDrawer').parentElement === $('#favoritesListSlot')) $('#placesDrawer').classList.add('hidden');
  const region = state.regions.find(r => r.code === code);
  if (!region) return;
  $('#regionExpand').classList.add('hidden');
  const token = ++state.fetchToken;
  state.selectedRegion = region;
  state.selectedCity = null;
  clearMap(); hideToast();
  drawKoreaBackground(true);
  $('#selectedCard').classList.add('hidden');
  updateBreadcrumb();

  const isSejong = code === '36';
  const unit = isSejong ? '읍·면·동' : (region.region_type === 'metro' ? '구·군' : '시·군');
  const list = $('#regionList');
  list.replaceChildren();
  updateStep('02', `${unit}을(를) 선택하세요`, `${region.name} · 지역 불러오는 중`);
  $('#mapTip').textContent = `👆 ${region.name}의 ${unit}을(를) 클릭하세요.`;

  let cities = [];
  if (isSejong) {
    list.textContent = '세종특별자치시 읍·면·동 경계를 불러오는 중...';
    try {
      cities = await getSejongCities();
    } catch (error) {
      // 읍면동을 불러오지 못했을 때 시군구 레벨의 세종 전체 경계로 대체
      cities = groupCities(region);
      if (token === state.fetchToken) {
        toast('세종 읍·면·동 경계 로딩 실패. 전체 지역만 표시합니다.');
      }
    }
  } else {
    cities = groupCities(region);
  }
  if (token !== state.fetchToken) return; // 다른 지역을 선택한 중간에 응답이 오면 폐기

  // 하위 GeoJSON이 비어 있을 때도 시·도 자체 선택 화면으로 진입할 수 있게 합니다.
  if (!cities.length) {
    const province = state.provinceFeatures.find(
      f => String(f.properties.CTPRVN_CD) === region.code
    );
    if (province) {
      cities = [{
        type: 'Feature',
        properties: {displayName: `${region.name} 전체`, regionCode: region.code, colorIndex: 0},
        geometry: province.geometry
      }];
    }
  }

  state.cityFeatures = cities;
  updateStep('02', `${unit}을(를) 선택하세요`, `${region.name} · ${cities.length}개 지역`);
  list.replaceChildren();
  cities.forEach(city => addRegionButton(list, city.properties.displayName,
    () => selectCity(city.properties.displayName)));
  if (cities.length) fitSelectedRegion(addGeoLayer(cities, f => selectCity(f.properties.displayName)));
  else {
    toast('이 지역의 행정구역 경계가 없습니다. GeoJSON을 확인하세요.');
    list.textContent = '하위 행정구역 데이터가 없습니다.';
  }
}

async function selectCity(cityName, category = state.selectedCategory) {
  $('#selectedCard').insertBefore($('#placesDrawer'), $('#selectedCard .data-note'));
  $('#placesDrawer').classList.remove('hidden');
  $('#placesDrawer summary span').textContent = '발견한 장소';
  const city = state.cityFeatures.find(f => f.properties.displayName === cityName);
  if (!city) return;
  $('#placesDrawer').open = false;
  state.selectedCity = city;
  state.selectedCategory = category;
  clearMap(); hideToast();
  const one = addGeoLayer([city], () => {});
  fitSelectedRegion(one);
  const logoUrl = regionImageUrl(city);
  if (logoUrl) {
    if (!map.getPane('cityWatermark')) {
      map.createPane('cityWatermark');
      map.getPane('cityWatermark').style.zIndex = '420';
      map.getPane('cityWatermark').style.pointerEvents = 'none';
    }
    const bounds = one.getBounds();
    const nw = map.project(bounds.getNorthWest(), 0), se = map.project(bounds.getSouthEast(), 0);
    const rings = asPolygons(smoothDisplayFeature(city,true).geometry).map(p=>p.map(r=>r.map(([lng,lat])=>map.project([lat,lng],0))));
    function inRing(point,ring) {
      let inside=false;
      for(let i=0,j=ring.length-1;i<ring.length;j=i++) {
        const a=ring[i],b=ring[j];
        if((a.y>point.y)!==(b.y>point.y)&&point.x<(b.x-a.x)*(point.y-a.y)/(b.y-a.y)+a.x)inside=!inside;
      }
      return inside;
    }
    const contains=p=>rings.some(r=>inRing(p,r[0])&&!r.slice(1).some(h=>inRing(p,h)));
    const middle=nw.add(se).divideBy(2);
    let center=null,half;
    for(let scale=.30;scale>=.02&&!center;scale*=.82) {
      half=se.subtract(nw).multiplyBy(scale/2);
      let distance=Infinity;
      for(let y=0;y<=24;y++)for(let x=0;x<=24;x++) {
        const candidate=L.point(nw.x+(se.x-nw.x)*x/24,nw.y+(se.y-nw.y)*y/24);
        let fits=true;
        for(let k=0;k<=16&&fits;k++) {
          const f=k/16*2-1;
          for(const p of [L.point(candidate.x+half.x*f,candidate.y-half.y),L.point(candidate.x+half.x*f,candidate.y+half.y),L.point(candidate.x-half.x,candidate.y+half.y*f),L.point(candidate.x+half.x,candidate.y+half.y*f)])if(!contains(p)){fits=false;break;}
        }
        if(fits&&contains(candidate)&&candidate.distanceTo(middle)<distance){center=candidate;distance=candidate.distanceTo(middle);}
      }
    }
    if(center) {
      const top=center.subtract(half),bottom=center.add(half);
      const logoBottom=L.point(bottom.x,top.y+(bottom.y-top.y)*.76);
      const logoBounds=L.latLngBounds(map.unproject(top,0),map.unproject(logoBottom,0));
      const labelBounds=L.latLngBounds(map.unproject(L.point(top.x,logoBottom.y),0),map.unproject(bottom,0));
      const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg'),text=document.createElementNS(ns,'text');
      svg.setAttribute('viewBox','0 0 200 40');
      text.setAttribute('x','100');text.setAttribute('y','28');text.setAttribute('text-anchor','middle');text.setAttribute('font-size',Math.min(25,170/cityName.length));text.setAttribute('font-weight','700');text.setAttribute('fill','#476656');text.textContent=cityName;svg.append(text);
      cityWatermark=L.layerGroup([
        L.imageOverlay(logoUrl,logoBounds,{pane:'cityWatermark',opacity:.24,interactive:false,className:'city-logo-watermark'}),
        L.svgOverlay(svg,labelBounds,{pane:'cityWatermark',interactive:false,opacity:.55})
      ]).addTo(map);
    }
    one.eachLayer(layer => layer.unbindTooltip());
  }
  updateStep('03', '여행 장소를 탐색하세요', '아래 버튼으로 종류를 바꿀 수 있어요');
  updateBreadcrumb();
  $('#selectedName').textContent = `${state.selectedRegion.name} ${cityName}`;
  $('#selectedCard').classList.remove('hidden');
  $('#filters').classList.remove('hidden');
  $('#mapTip').textContent = `✨ ${cityName}의 여행 장소를 찾고 있어요.`;
  $('#regionList').replaceChildren();
  $('#filters').querySelectorAll('.filter').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.category === state.selectedCategory);
    btn.setAttribute('aria-pressed', String(btn.dataset.category === state.selectedCategory));
  });
  await loadLandmarks();
}

function popupContent(p) {
  const wrap = document.createElement('div');
  wrap.className = 'place-popup-content';
  wrap.append(window.TripTray.button(p));
  const title = document.createElement('p'); title.className = 'popup-title';
  title.textContent = `${CATEGORIES[p.category].emoji} ${p.title}`;
  wrap.append(title);
  if (/^https?:\/\//.test(p.location_url || '')) {
    const a = document.createElement('a');
    a.className = 'popup-link'; a.href = p.location_url; a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = p.latitude==null||p.longitude==null?'원문 정보 열기 ↗':'위치 지도 열기 ↗';
    wrap.appendChild(a);
  }
  if (p.id != null) {
    wrap.append(window.CityVisits.button(p));
    if (!p.datalab_place) wrap.append(window.CityFavorites.button(p));
  } else {
    const note = document.createElement('p');
    note.textContent = `데이터랩 맛집 ${p.area_rank}위 · 방문 기록 연결 전`;
    wrap.append(note);
  }
  return wrap;
}
function landmarkIcon(p, i = 0) {
  const cat = CATEGORIES[p.category];
  const safeType = p.category;
  return L.divIcon({
    html: `<span class="category-location-tag tag-${safeType}" style="--tag-delay:${Math.min(i*55,900)}ms" role="img" aria-label="${cat.label}"><span class="category-tag-emoji" aria-hidden="true">${cat.emoji}</span>${window.CityVisits.has(p) ? '<span class="category-tag-check" aria-label="방문 완료">✓</span>' : ''}</span>`,
    className: 'category-tag-marker', iconSize: [48, 48], iconAnchor: [24, 24]
  });
}
function displayedCityPolygons() {
  const polygons=[];
  if(state.selectedCity)state.geoLayer?.eachLayer(layer=>{
    if(layer.feature?.geometry)polygons.push(...asPolygons(layer.feature.geometry));
  });
  return polygons;
}

function scatterInCity(count) {
  if (!count || !state.selectedCity || map._animatingZoom) return [];
  const polygons=displayedCityPolygons();
  if(!polygons.length)return [];
  const points=polygons.flat(2),xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);
  const west=Math.min(...xs),east=Math.max(...xs),south=Math.min(...ys),north=Math.max(...ys);
  function contains(x,y,r) {
    let hit=false;
    for(let i=0,j=r.length-1;i<r.length;j=i++) {
      const a=r[i],b=r[j];
      if((a[1]>y)!==(b[1]>y)&&x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])hit=!hit;
    }
    return hit;
  }
  const candidates=[];
  const inside=(x,y)=>polygons.some(p=>contains(x,y,p[0])&&!p.slice(1).some(r=>contains(x,y,r)));
  const zoom=map.getZoom(),size=map.getSize();
  const sidebar=document.querySelector('.app-shell').classList.contains('sidebar-open')
    ? document.getElementById('travelSidebar').getBoundingClientRect().width : 0;
  const nw=map.containerPointToLatLng([sidebar+56,60]);
  const se=map.containerPointToLatLng([size.x-56,size.y-110]);
  const viewWest=Math.max(west,nw.lng),viewEast=Math.min(east,se.lng);
  const viewSouth=Math.max(south,se.lat),viewNorth=Math.min(north,nw.lat);
  if(viewEast<=viewWest||viewNorth<=viewSouth)return [];
  const footprint=[];
  for(let dx=-54;dx<=54;dx+=18)footprint.push([dx,-48],[dx,68]);
  for(let dy=-48;dy<=68;dy+=20)footprint.push([-54,dy],[54,dy]);
  const mapRect=map.getContainer().getBoundingClientRect();
  const paths=[];
  state.geoLayer.eachLayer(layer=>{
    const path=layer.getElement?.(),matrix=path?.getScreenCTM?.();
    if(matrix&&path.isPointInFill)paths.push({path,inverse:matrix.inverse()});
  });
  let seed=731;
  const random=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
  for(let n=0;n<4000&&candidates.length<Math.max(120,count*12);n++) {
    const x=viewWest+random()*(viewEast-viewWest),y=viewSouth+random()*(viewNorth-viewSouth);
    if(!inside(x,y))continue;
    const pixel=map.project(L.latLng(y,x),zoom);
    const screen=map.latLngToContainerPoint([y,x]);
    if(screen.x<sidebar+56||screen.x>size.x-56||screen.y<60||screen.y>size.y-110)continue;
    const fits=footprint.every(([dx,dy])=>{
      const p=map.unproject(pixel.add(L.point(dx,dy)),zoom);
      if(!inside(p.lng,p.lat))return false;
      const point=new DOMPoint(mapRect.left+screen.x+dx,mapRect.top+screen.y+dy);
      return !paths.length||paths.some(({path,inverse})=>path.isPointInFill(point.matrixTransform(inverse)));
    });
    if(fits)candidates.push({x,y,pixel,d:Infinity});
  }
  const result=[];
  while(result.length<count&&candidates.length) {
    let best=0;
    for(let i=1;i<candidates.length;i++)if(candidates[i].d>candidates[best].d)best=i;
    const p=candidates.splice(best,1)[0];result.push(L.latLng(p.y,p.x));
    for(let i=candidates.length-1;i>=0;i--) {
      const c=candidates[i],dx=c.pixel.x-p.pixel.x,dy=c.pixel.y-p.pixel.y;
      if(Math.abs(dx)<110&&Math.abs(dy)<120)candidates.splice(i,1);
      else c.d=Math.min(c.d,dx*dx+dy*dy);
    }
  }
  return result;
}

function markerBudget() {
  const size=map.getSize();
  let area=size.x*size.y*.6;
  if(state.selectedCity) {
    const polygons=displayedCityPolygons();
    const ringArea=ring=>{
      const points=ring.map(([lng,lat])=>map.latLngToContainerPoint([lat,lng]));
      return Math.abs(points.reduce((sum,p,i)=>{
        const q=points[(i+1)%points.length];return sum+p.x*q.y-q.x*p.y;
      },0))/2;
    };
    area=Math.min(area,polygons.reduce((sum,p)=>sum+ringArea(p[0])-p.slice(1).reduce((holes,r)=>holes+ringArea(r),0),0));
  }
  return Math.max(4,Math.min(state.selectedCity?28:40,Math.floor(area/18000)));
}

// Category quotas prevent a large restaurant dataset from hiding other places.
function sampleMapPlaces(places,rankings,budget,page=0) {
  if(budget<=0)return [];
  const groups={tourism:[],food:[],event:[]},weights={tourism:.5,food:.2,event:.3};
  const rankedIds=new Set(rankings.map(p=>p.landmark_id).filter(id=>id!=null));
  for(const p of places) {
    if(p.category==='food'&&rankedIds.has(p.id))continue;
    groups[p.category].push({place:p,ranking:false});
  }
  for(const p of rankings)groups.food.push({place:p,ranking:true});
  // Round-robin localities also keeps province/nationwide views balanced.
  for(const category of Object.keys(groups)) {
    const localities=new Map();
    for(const item of groups[category]) {
      const key=`${item.place.region_code||''}|${item.place.locality_name||''}`;
      if(!localities.has(key))localities.set(key,[]);
      localities.get(key).push(item);
    }
    const lists=[...localities.values()],ordered=[];
    for(let i=0;ordered.length<groups[category].length;i++) {
      for(const list of lists)if(i<list.length)ordered.push(list[i]);
    }
    groups[category]=ordered;
  }
  const used={tourism:0,food:0,event:0},categories=[];
  while(categories.length<budget) {
    const available=Object.keys(groups).filter(c=>used[c]<groups[c].length);
    if(!available.length)break;
    const category=available.reduce((best,c)=>used[c]/weights[c]<used[best]/weights[best]?c:best);
    categories.push(category);
    used[category]++;
  }
  const offsets={tourism:0,food:0,event:0};
  const selected=categories.map(category=>{
    const pool=groups[category];
    return pool[(page*used[category]+offsets[category]++)%pool.length];
  });
  if(state.focusedRanking) {
    const focused=rankings.find(p=>p.poi_id===state.focusedRanking);
    if(focused&&!selected.some(item=>item.ranking&&item.place.poi_id===focused.poi_id)) {
      if(selected.length===budget)selected.pop();
      selected.unshift({place:focused,ranking:true});
    }
  }
  return selected;
}

function cityMarkerBoundary() {
  if(!state.selectedCity)return ()=>true;
  const paths=[];
  state.geoLayer?.eachLayer(layer=>{
    const path=layer.getElement?.(),matrix=path?.getScreenCTM?.();
    if(matrix&&path.isPointInFill)paths.push({path,inverse:matrix.inverse()});
  });
  const inside=(x,y)=>paths.some(({path,inverse})=>
    path.isPointInFill(new DOMPoint(x,y).matrixTransform(inverse)));
  return marker=>{
    const icon=marker.getElement()?.querySelector('.category-location-tag');
    if(!icon||!paths.length)return false;
    const elements=[icon,marker.getTooltip()?.getElement()].filter(Boolean);
    return elements.every(element=>{
      const r=element.getBoundingClientRect();
      if(!r.width||!r.height)return false;
      const columns=Math.ceil(r.width/12),rows=Math.ceil(r.height/12);
      for(let x=0;x<=columns;x++)for(let y=0;y<=rows;y++) {
        if(!inside(r.left+r.width*x/columns,r.top+r.height*y/rows))return false;
      }
      return true;
    });
  };
}

function renderMapPlaces() {
  const data=state.landmarkData;
  if(!data||state.favoritesMode||map._animatingZoom)return;
  state.markerLayer.clearLayers();
  rankingMarkers.clearLayers();
  const budget=markerBudget();
  let selected=sampleMapPlaces(data.places,data.rankings,budget,state.placePage);
  if(state.selectedCity) {
    const positions=scatterInCity(selected.length);
    selected=sampleMapPlaces(data.places,data.rankings,positions.length,state.placePage);
    selected.forEach((item,i)=>{item.place._displayPosition=positions[i];});
  } else {
    const occupied=[];
    selected=sampleMapPlaces(data.places.filter(p=>{
      if(p.latitude==null||p.longitude==null)return false;
      const point=map.latLngToContainerPoint(displayLatLng(p.latitude,p.longitude));
      return point.x>=50&&point.y>=50&&point.x<=map.getSize().x-50&&point.y<=map.getSize().y-90;
    }),data.rankings,budget,state.placePage).filter(item=>{
      const p=item.place;
      if(p.latitude==null||p.longitude==null)return false;
      const point=map.latLngToContainerPoint(displayLatLng(p.latitude,p.longitude));
      if(occupied.some(q=>Math.abs(point.x-q.x)<108&&Math.abs(point.y-q.y)<108))return false;
      occupied.push(point);return true;
    });
  }
  let places=selected.filter(item=>!item.ranking).map(item=>item.place);
  let rankings=selected.filter(item=>item.ranking).map(item=>item.place);
  let markers=places.map((p,i)=>makeMarker(p,i));
  markers.forEach(marker=>state.markerLayer.addLayer(marker));
  renderRankingMarkers(rankings);
  const fits=cityMarkerBoundary();
  const visible=[];
  markers.forEach((marker,i)=>{
    if(fits(marker))visible.push({marker,place:places[i]});
    else state.markerLayer.removeLayer(marker);
  });
  places=visible.map(item=>item.place);
  markers=visible.map(item=>item.marker);
  rankings=rankings.filter(place=>{
    const marker=rankingMarkersByPoi.get(place.poi_id);
    if(marker&&fits(marker))return true;
    if(marker)rankingMarkers.removeLayer(marker);
    rankingMarkersByPoi.delete(place.poi_id);
    return false;
  });
  renderCards(places,markers,rankings);
  const shown=places.length+rankings.length;
  const total=data.places.length+data.rankings.length;
  $('#resultCount').textContent=`${shown} / ${total}`;
  if(total&&!shown)$('#landmarkList').textContent='지도를 확대하면 이 지역의 장소를 볼 수 있어요.';
  if(total>shown) {
    const more=document.createElement('button');
    more.type='button';more.className='ranking-map-button';more.textContent='다른 장소 보기';
    more.addEventListener('click',()=>{state.placePage++;state.focusedRanking=null;renderMapPlaces();});
    $('#landmarkList').append(more);
  }
  const area=state.selectedCity?.properties.displayName||state.selectedRegion?.name||'전국';
  $('#mapTip').textContent=`${area} · 전체 ${total}곳 중 ${shown}곳 표시 · 확대하면 더 볼 수 있어요${state.selectedCity?' · 실제 위치와 다른 지역 안내 태그입니다.':''}`;
}

let markerRefreshTimer;
let placePopupOpen=false;
map.on('popupopen',()=>{placePopupOpen=true;});
map.on('popupclose',()=>{placePopupOpen=false;});
map.on('zoomstart',()=>{
  if(!state.landmarkData||state.favoritesMode)return;
  map.closePopup();
  state.markerLayer.clearLayers();
  rankingMarkers.clearLayers();
});
map.on('moveend zoomend resize',()=>{
  clearTimeout(markerRefreshTimer);
  markerRefreshTimer=setTimeout(()=>{
    if(placePopupOpen||!state.landmarkData||state.favoritesMode)return;
    state.geoLayer?.eachLayer(layer=>layer.redraw?.());
    cityWatermark?.eachLayer(layer=>layer.setBounds(layer.getBounds()));
    renderMapPlaces();
  },180);
});
function shortPlaceLabel(title) {
  const letters = Array.from(title || '');
  const label = document.createElement('span');
  label.textContent = letters.length > 5 ? letters.slice(0, 5).join('') + '...' : letters.join('');
  label.title = title || '';
  return label;
}
function makeMarker(p, i) {
  const exact=p.latitude!=null&&p.longitude!=null;
  const position=state.selectedCity?p._displayPosition:exact?displayLatLng(p.latitude,p.longitude):null;
  if(!position)return null;
  const marker = L.marker(position, {icon: landmarkIcon(p, i),
    title: `${p.title}${window.CityVisits.has(p) ? ' · 방문 완료' : ''}`});
  marker.visitPlace = p;
  marker.bindTooltip(shortPlaceLabel(p.title),{permanent:true,direction:'bottom',offset:[0,24],className:'location-name-tag'});
  return marker.bindPopup(() => popupContent(p));
}
document.addEventListener('visits-updated', () => {
  if (state.selectedCity && !state.favoritesMode) loadLandmarks();
  state.markerLayer.eachLayer(marker => {
    if (!marker.visitPlace) return;
    marker.setIcon(landmarkIcon(marker.visitPlace));
    const element = marker.getElement();
    if (element) element.title = `${marker.visitPlace.title}${window.CityVisits.has(marker.visitPlace) ? ' · 방문 완료' : ''}`;
  });
});
function renderCards(places, markers, rankings = []) {
  const container = $('#landmarkList'); container.replaceChildren();
  $('#resultCount').textContent = String(places.length + rankings.length);
  if (!places.length && !rankings.length) {
    const empty = document.createElement('div'); empty.className = 'empty-message';
    empty.textContent = '등록된 장소가 없습니다. 다른 버튼을 누르거나 다른 지역을 선택해 보세요.';
    container.append(empty); return;
  }
  places.forEach((p, i) => {
    const card = document.createElement('article'); card.className = 'landmark-card';
    const title = document.createElement('div'); title.className = 'landmark-card-title';
    title.textContent = `${CATEGORIES[p.category].emoji} ${p.title}`;
    const desc = document.createElement('p'); desc.textContent = p.description || '';
    card.append(title, desc);
    const source = document.createElement('p');
    source.className = 'source-meta';
    source.textContent = `자료: ${p.source_name || '출처 정보 없음'}`;
    card.append(source);
    const favorite = window.CityFavorites.button(p);
    favorite.addEventListener('click', event => event.stopPropagation());
    card.append(favorite);
    if (/^https?:\/\//.test(p.location_url || '')) {
      const a = document.createElement('a'); a.textContent = '지도에서 위치 확인 ↗';
      if(p.latitude==null||p.longitude==null)a.textContent='원문 정보 보기 ↗';
      a.href = p.location_url; a.target = '_blank'; a.rel = 'noopener noreferrer';
      a.addEventListener('click', e => e.stopPropagation());
      card.append(a);
    }
    card.addEventListener('click', () => {
      if(!markers[i]) {
        toast('정확한 위치가 확인되지 않은 장소입니다. 원문 정보를 확인해 주세요.');
        return;
      }
      if (!state.favoritesMode && !state.selectedCity) map.flyTo(displayLatLng(p.latitude, p.longitude), Math.max(map.getZoom(), 12));
      markers[i].openPopup();
    });
    container.append(card);
  });
  if (rankings.length) {
    const heading = document.createElement('div');
    heading.className = 'ranking-results-heading';
    heading.textContent = '🍜 데이터랩 인기 맛집 · 전체 방문자 기준';
    container.prepend(heading);
    const cards = document.createDocumentFragment();
    rankings.forEach(place => {
      const card = document.createElement('article');
      card.className = 'landmark-card ranking-result-card';
      const title = document.createElement('div');
      title.className = 'landmark-card-title';
      title.textContent = `${place.area_rank}위 · ${place.title}`;
      const detail = document.createElement('p');
      detail.textContent = `${place.locality_name} · ${place.subtype} · ${place.period_start}~${place.period_end}`;
      const note = document.createElement('small');
      note.className = 'source-meta';
      note.textContent = '한국관광 데이터랩 · 좌표가 없으면 지역 안에 임의 표시합니다.';
      card.append(title, detail, note);
      const locate = document.createElement('button');
      locate.type = 'button'; locate.className = 'ranking-map-button'; locate.textContent = '지도에서 보기';
      locate.addEventListener('click', () => document.dispatchEvent(new CustomEvent('food-ranking-focus', {detail: place})));
      card.append(locate);
      cards.append(card);
    });
    heading.after(cards);
  }
}

async function loadLandmarks(nationwide = false) {
  if (!nationwide && (!state.selectedCity || !state.selectedRegion)) return;
  const token = ++state.fetchToken;
  state.markerLayer.clearLayers();
  state.landmarkData=null;
  state.placePage=0;
  state.focusedRanking=null;
  $('#landmarkList').textContent = '장소를 불러오는 중...';
  $('#resultCount').textContent = '…';
  const params = new URLSearchParams(nationwide ? {
    scope: 'all', category: state.selectedCategory
  } : {
    region: state.selectedRegion.code,
    locality: state.selectedCity.properties.displayName,
    category: state.selectedCategory
  });
  try {
    const [data] = await Promise.all([fetchJSON(`/api/landmarks?${params.toString()}`), window.CityVisits.ready, window.CityFavorites.ready]);
    if (token !== state.fetchToken) return;
    hideToast();
    state.landmarkData={places:data.landmarks,rankings:data.food_rankings||[]};
    renderMapPlaces();
  } catch (err) {
    if (token !== state.fetchToken) return;
    $('#resultCount').textContent = '0';
    $('#landmarkList').textContent = '';
    toast(`랜드마크 조회 실패: ${err.message}`);
  }
}

async function showFavorites() {
  const token = ++state.fetchToken;
  try {
    const [places] = await Promise.all([window.CityFavorites.refresh(), window.CityVisits.ready]);
    if (token !== state.fetchToken) return;
    clearMap(); hideToast();
    state.favoritesMode = true;
    state.selectedRegion = null;
    state.selectedCity = null;
    drawKoreaBackground();
    updateBreadcrumb();
    $('#backBtn').disabled = false;
    $('#favoritesBtn').setAttribute('aria-pressed', 'true');
    $('#regionList').replaceChildren();
    $('#selectedName').textContent = '나의 즐겨찾기 장소';
    $('#selectedCard').classList.add('hidden');
    $('#favoritesListSlot').append($('#placesDrawer'));
    $('#placesDrawer').classList.remove('hidden');
    $('#filters').classList.add('hidden');
    updateStep('★', '즐겨찾기 장소', `${places.length}곳의 여행지를 모았어요`);
    const markers = places.map((place, index) => makeMarker(place, index));
    markers.filter(Boolean).forEach(marker => state.markerLayer.addLayer(marker));
    renderCards(places, markers);
    $('#placesDrawer').open = false;
    $('#placesDrawer summary span').textContent = '저장한 즐겨찾기 펼쳐보기';
    const container = $('#landmarkList');
    const cards = [...container.children];
    if (places.length > 5) {
      container.replaceChildren(...cards.slice(0,5));
      const more = document.createElement('details');more.className='favorite-more';
      const heading = document.createElement('summary');heading.textContent=`나머지 ${places.length-5}곳 더 펼쳐보기`;
      more.append(heading,...cards.slice(5));container.append(more);
    }
    if (!places.length) {
      $('#landmarkList').textContent = '아직 즐겨찾기가 없습니다. 장소 정보에서 ☆ 즐겨찾기 등록을 눌러 주세요.';
    }
    $('#mapTip').textContent = `★ 즐겨찾기 ${places.length}곳 · 지도 표시 ${markers.filter(Boolean).length}곳`;
  } catch (error) {
    if (token === state.fetchToken) toast(error.message);
  }
}
$('#favoritesBtn').addEventListener('click', showFavorites);
document.addEventListener('favorites-updated', () => {
  if (state.favoritesMode) showFavorites();
});
const rankingMarkers = L.layerGroup().addTo(map);
const rankingMarkersByPoi = new Map();
function renderRankingMarkers(rows) {
  rankingMarkers.clearLayers();
  rankingMarkersByPoi.clear();
  if (state.favoritesMode || (state.selectedCity && !['all', 'food'].includes(state.selectedCategory))) return;
  for (const place of rows) {
    const exact = place.latitude != null && place.longitude != null && Number.isFinite(Number(place.latitude)) && Number.isFinite(Number(place.longitude));
    const position = state.selectedCity ? place._displayPosition : exact ? displayLatLng(Number(place.latitude), Number(place.longitude)) : null;
    if (!position) continue;
    const visitPlace = {...place,id:place.landmark_id,category:'food'};
    const marker = L.marker(position, {icon:landmarkIcon(visitPlace),title:place.title});
    const content = document.createElement('div');
    content.className = 'place-popup-content';
    content.append(window.TripTray.button(visitPlace));
    marker.bindTooltip(shortPlaceLabel(place.title),{permanent:true,direction:'bottom',offset:[0,24],className:'location-name-tag'});
    const title = document.createElement('strong'); title.textContent = `${place.area_rank}위 · ${place.title}`;
    const subtitle = document.createElement('p'); subtitle.textContent = `${place.locality_name} · ${place.subtype}`;
    const source = document.createElement('small'); source.textContent = '한국관광 데이터랩 · 기존 맛집 DB의 위치';
    if (place.road_address) { const address = document.createElement('p'); address.textContent = place.road_address; content.append(address); }
    content.append(title, subtitle, source);
    content.append(window.CityVisits.button(visitPlace));
    source.textContent = state.selectedCity ? '지역 안에 임의 배치한 태그이며 실제 위치가 아닙니다.' : exact ? '기존 맛집 DB의 위치입니다.' : '좌표가 확인되지 않은 장소입니다.';
    marker.bindPopup(content).addTo(rankingMarkers);
    rankingMarkersByPoi.set(place.poi_id, marker);
  }
}
document.addEventListener('food-ranking-markers', event => {
  if(state.landmarkData&&!state.favoritesMode) {
    state.landmarkData.rankings=['all','food'].includes(state.selectedCategory)?event.detail.rankings:[];
    renderMapPlaces();
  }
});
document.addEventListener('food-ranking-focus', event => {
  if(state.landmarkData&&!state.favoritesMode) {
    state.focusedRanking=event.detail.poi_id;
    renderMapPlaces();
  }
  const marker = rankingMarkersByPoi.get(event.detail.poi_id);
  if (!marker) return;
  map.panTo(marker.getLatLng());
  marker.openPopup();
});

$('#backBtn').addEventListener('click', () => {
  if (state.selectedCity) selectRegion(state.selectedRegion.code);
  else goHome();
});
$('#filters').addEventListener('click', e => {
  const btn = e.target.closest('[data-category]');
  if (!btn) return;
  state.selectedCategory = btn.dataset.category;
  $('#filters').querySelectorAll('.filter').forEach(el => {
    el.classList.toggle('active', el === btn);
    el.setAttribute('aria-pressed', String(el === btn));
  });
  const category = btn.dataset.category;
  if (state.selectedCity) {
    loadLandmarks();
    return;
  }
  if (state.selectedRegion) {
    const region = state.selectedRegion;
    const request = ++state.fetchToken;
    state.landmarkData=null;
    state.placePage=0;
    state.markerLayer.clearLayers();
    rankingMarkers.clearLayers();
    Promise.all([fetchJSON(`/api/landmarks?scope=all&category=${category}`), window.CityVisits.ready]).then(([data]) => {
      if (request !== state.fetchToken) return;
      const places = data.landmarks.filter(place => String(place.region_code) === String(region.code));
      state.landmarkData={places,rankings:[]};
      renderMapPlaces();
      $('#selectedName').textContent = `${region.name} ${category === 'all' ? '여행 장소' : CATEGORIES[category].label}`;
      $('#selectedCard').classList.remove('hidden');
      $('#placesDrawer').classList.remove('hidden');
    }).catch(error => toast(error.message));
    return;
  }
  goHome();
  state.selectedCategory = category;
  $('#selectedCard').insertBefore($('#placesDrawer'), $('#selectedCard .data-note'));
  $('#selectedName').textContent = category === 'all' ? '전국 여행 장소' : `전국 ${CATEGORIES[category].label}`;
  $('#placesDrawer summary span').textContent = '발견한 장소';
  $('#placesDrawer').classList.remove('hidden');
  $('#selectedCard').classList.remove('hidden');
  loadLandmarks(true);

});

(async function init() {
  try {
    const [regionData, provinces, districts] = await Promise.all([
      fetchJSON('/api/regions'), fetchGeo('ctprvn.geojson'), fetchGeo('sig.geojson')
    ]);
    state.provinceFeatures = provinces;
    indexProvinceBorders(provinces);
    state.districtFeatures = districts;
    state.regions = buildAllRegions(regionData.regions, provinces);
    goHome();
  } catch (error) {
    $('#regionList').textContent = '초기화 실패: ' + error.message;
    toast('MariaDB 연결과 인터넷(지도 경계 서버)을 확인하세요.');
  }
})();
