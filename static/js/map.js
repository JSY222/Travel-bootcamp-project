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
  tourism: {emoji: '🏞️', label: '관광지'},
  food: {emoji: '🍜', label: '맛집'},
  event: {emoji: '🎉', label: '행사'}
};
const $ = (selector) => document.querySelector(selector);
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
function smoothDisplayFeature(feature) {
  const polygons = asPolygons(feature.geometry);
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
  preferCanvas: false,
  minZoom: 6,
  maxZoom: 18,
  zoomSnap: .25,
  maxBoundsViscosity: 1.0
}).setView([36.4, 127.9], 7);
L.control.zoom({position: 'bottomright'}).addTo(map);
map.createPane('countryRelief');
map.getPane('countryRelief').style.zIndex = '390';
map.getPane('countryRelief').style.pointerEvents = 'none';
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let clearRegionLift = () => {};
let liftedRegion = null;
map.on('zoomstart', () => clearRegionLift());

const state = {
  regions: [], provinceFeatures: [], districtFeatures: [],
  selectedRegion: null, selectedCity: null, selectedCategory: 'all',
  geoLayer: null, countryLayer: null, markerLayer: L.layerGroup().addTo(map),
  islandLabelLayer: L.layerGroup().addTo(map),
  cityFeatures: [], fetchToken: 0
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
function clearMap() {
  clearRegionLift();
  if (state.geoLayer) map.removeLayer(state.geoLayer);
  state.geoLayer = null;
  state.markerLayer.clearLayers();
}
function fit(layer, maxZoom = 10, padding = [28, 28]) {
  if (layer && layer.getBounds().isValid()) {
    map.fitBounds(layer.getBounds(), {padding, maxZoom, animate: true});
  }
}
// 전국 17개 행정구역 윤곽을 배경으로 표시합니다.
// 클릭은 위에 별도로 올리는 선택 가능한 행정구역 레이어에서 처리합니다.
function drawKoreaBackground() {
  if (state.countryLayer) map.removeLayer(state.countryLayer);
  state.islandLabelLayer.clearLayers();
  state.countryLayer = L.geoJSON(state.provinceFeatures.map(smoothDisplayFeature), {
    smoothFactor: 0,
    interactive: false,
    pane: 'countryRelief',
    style: feature => ({
      color: '#827a8e', weight: 1.4,
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
  state.geoLayer = L.geoJSON(features.map(smoothDisplayFeature), {
    smoothFactor: 0,
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
      layer.bindTooltip(name, {permanent: true, direction: 'center', className: 'place-tooltip', opacity: .94});
    }
  }).addTo(map);
  return state.geoLayer;
}

function updateStep(number, heading, detail) {
  $('#stepNum').textContent = number;
  $('#stepHeading').textContent = heading;
  $('#stepDetail').textContent = detail;
}
function updateBreadcrumb() {
  $('#crumbRegion').textContent = state.selectedRegion?.name || '';
  $('#crumbCity').textContent = state.selectedCity?.properties.displayName || '';
  $('#backBtn').classList.toggle('hidden', !state.selectedRegion);
}
function addRegionButton(container, label, onClick) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'region-button';
  btn.textContent = label;
  btn.addEventListener('click', onClick);
  container.appendChild(btn);
}

function goHome() {
  state.fetchToken++;
  state.selectedRegion = null;
  state.selectedCity = null;
  clearMap(); hideToast();
  $('#selectedCard').classList.add('hidden');
  $('#nationwideControls').classList.remove('hidden');
  $('#filters').classList.remove('hidden');
  $('#nationwideFilters').querySelectorAll('.filter').forEach(btn => {
    btn.classList.remove('active');
    btn.setAttribute('aria-pressed', 'false');
  });
  updateStep('01', '지역을 선택하세요', `시·도 ${state.regions.length}개 지역`);
  updateBreadcrumb();
  $('#mapTip').textContent = '👆 지도에서 시·도를 선택하면 확대됩니다.';
  const list = $('#regionList'); list.replaceChildren();
  state.regions.forEach(r => addRegionButton(list, r.name, () => selectRegion(r.code)));

  const codes = new Map(state.regions.map(r => [r.code, r]));
  const features = state.provinceFeatures
    .filter(f => codes.has(f.properties.CTPRVN_CD))
    .map((f, i) => ({...f, properties: {
      ...f.properties,
      displayName: codes.get(f.properties.CTPRVN_CD).name,
      colorIndex: i
    }}));
  if (features.length) fit(addGeoLayer(features, f => selectRegion(f.properties.CTPRVN_CD)), 8.5, [44, 60]);
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

async function selectRegion(code) {
  const region = state.regions.find(r => r.code === code);
  if (!region) return;
  const token = ++state.fetchToken;
  state.selectedRegion = region;
  state.selectedCity = null;
  clearMap(); hideToast();
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
  if (cities.length) fit(addGeoLayer(cities, f => selectCity(f.properties.displayName)), 10);
  else {
    toast('이 지역의 행정구역 경계가 없습니다. GeoJSON을 확인하세요.');
    list.textContent = '하위 행정구역 데이터가 없습니다.';
  }
}

async function selectCity(cityName) {
  const city = state.cityFeatures.find(f => f.properties.displayName === cityName);
  if (!city) return;
  state.selectedCity = city;
  state.selectedCategory = 'all';
  clearMap(); hideToast();
  const one = addGeoLayer([city], () => {});
  fit(one, 12);
  updateStep('03', '여행 장소를 탐색하세요', '아래 버튼으로 종류를 바꿀 수 있어요');
  updateBreadcrumb();
  $('#selectedName').textContent = `${state.selectedRegion.name} ${cityName}`;
  $('#selectedCard').classList.remove('hidden');
  $('#filters').classList.remove('hidden');
  $('#mapTip').textContent = `✨ ${cityName}의 여행 장소를 찾고 있어요.`;
  $('#regionList').replaceChildren();
  $('#filters').querySelectorAll('.filter').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.category === 'all');
  });
  await loadLandmarks();
}

function popupContent(p) {
  const wrap = document.createElement('div');
  const title = document.createElement('p'); title.className = 'popup-title';
  title.textContent = `${CATEGORIES[p.category].emoji} ${p.title}`;
  const desc = document.createElement('p'); desc.className = 'popup-desc';
  desc.textContent = p.description || '자세한 사항은 방문 전에 확인하세요.';
  wrap.append(title, desc);
  const source = document.createElement('p');
  source.className = 'source-meta';
  source.textContent = `자료: ${p.source_name || '출처 정보 없음'}`;
  wrap.append(source);
  if (/^https?:\/\//.test(p.location_url || '')) {
    const a = document.createElement('a');
    a.className = 'popup-link'; a.href = p.location_url; a.target = '_blank';
    a.rel = 'noopener noreferrer'; a.textContent = '위치 지도 열기 ↗';
    wrap.appendChild(a);
  }
  return wrap;
}
function makeMarker(p, i) {
  const cat = CATEGORIES[p.category];
  const safeType = p.category;
  const icon = L.divIcon({
    html: `<div class="landmark-pin" style="animation-delay:${Math.min(i * 65, 700)}ms"><div class="pin-bubble pin-${safeType}"><span>${cat.emoji}</span></div></div>`,
    className: '', iconSize: [36, 40], iconAnchor: [18, 38]
  });
  return L.marker(displayLatLng(p.latitude, p.longitude), {icon}).bindPopup(popupContent(p));
}
function renderCards(places, markers) {
  const container = $('#landmarkList'); container.replaceChildren();
  $('#resultCount').textContent = String(places.length);
  if (!places.length) {
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
    if (/^https?:\/\//.test(p.location_url || '')) {
      const a = document.createElement('a'); a.textContent = '지도에서 위치 확인 ↗';
      a.href = p.location_url; a.target = '_blank'; a.rel = 'noopener noreferrer';
      a.addEventListener('click', e => e.stopPropagation());
      card.append(a);
    }
    card.addEventListener('click', () => {
      map.flyTo(displayLatLng(p.latitude, p.longitude), Math.max(map.getZoom(), 12));
      markers[i].openPopup();
    });
    container.append(card);
  });
}

async function loadLandmarks(nationwide = false) {
  if (!nationwide && (!state.selectedCity || !state.selectedRegion)) return;
  const token = ++state.fetchToken;
  state.markerLayer.clearLayers();
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
    const data = await fetchJSON(`/api/landmarks?${params.toString()}`);
    if (token !== state.fetchToken) return;
    hideToast();
    const places = data.landmarks;
    const markers = places.map((p, i) => makeMarker(p, i));
    markers.forEach(m => state.markerLayer.addLayer(m));
    renderCards(places, markers);
    const area = nationwide ? '전국' : state.selectedCity.properties.displayName;
    $('#mapTip').textContent = `✨ ${area} · ${places.length}개 장소 표시 중`;
  } catch (err) {
    if (token !== state.fetchToken) return;
    $('#resultCount').textContent = '0';
    $('#landmarkList').textContent = '';
    toast(`랜드마크 조회 실패: ${err.message}`);
  }
}

$('#homeBtn').addEventListener('click', goHome);
$('#nationwideFilters').addEventListener('click', e => {
  const btn = e.target.closest('[data-category]');
  if (!btn) return;
  const category = btn.dataset.category;
  goHome();
  state.selectedCategory = category;
  $('#nationwideFilters').querySelectorAll('.filter').forEach(el => {
    const active = el.dataset.category === category;
    el.classList.toggle('active', active);
    el.setAttribute('aria-pressed', String(active));
  });
  $('#selectedName').textContent = category === 'all' ? '전국의 여행 장소' : `전국 ${CATEGORIES[category].label}`;
  $('#selectedCard').classList.remove('hidden');
  $('#filters').classList.add('hidden');
  loadLandmarks(true);
});
$('#backBtn').addEventListener('click', () => {
  if (state.selectedCity) selectRegion(state.selectedRegion.code);
  else goHome();
});
$('#filters').addEventListener('click', e => {
  const btn = e.target.closest('[data-category]');
  if (!btn || !state.selectedCity) return;
  state.selectedCategory = btn.dataset.category;
  $('#filters').querySelectorAll('.filter').forEach(el => {
    el.classList.toggle('active', el === btn);
  });
  loadLandmarks();
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
    drawKoreaBackground();
    goHome();
  } catch (error) {
    $('#regionList').textContent = '초기화 실패: ' + error.message;
    toast('MariaDB 연결과 인터넷(지도 경계 서버)을 확인하세요.');
  }
})();
