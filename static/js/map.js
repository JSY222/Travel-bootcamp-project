'use strict';

// 지도는 Leaflet, 경계선은 공개 GeoJSON, 장소는 Flask API에서 불러옵니다.
const GEO_BASES = [
  '/static/geo/',
  'https://cdn.jsdelivr.net/gh/KnellBalm/kr-admin-geojson@main/',
  'https://raw.githubusercontent.com/KnellBalm/kr-admin-geojson/main/'
];
const CATEGORIES = {
  tourism: {emoji: '🏞️', label: '관광지'},
  food: {emoji: '🍜', label: '맛집'},
  event: {emoji: '🎉', label: '행사'}
};
const $ = (selector) => document.querySelector(selector);

const map = L.map('map', {zoomControl: false, preferCanvas: true})
  .setView([36.4, 127.9], 7);
L.control.zoom({position: 'bottomright'}).addTo(map);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const state = {
  regions: [], provinceFeatures: [], districtFeatures: [],
  selectedRegion: null, selectedCity: null, selectedCategory: 'all',
  geoLayer: null, markerLayer: L.layerGroup().addTo(map),
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
  if (state.geoLayer) map.removeLayer(state.geoLayer);
  state.geoLayer = null;
  state.markerLayer.clearLayers();
}
function fit(layer, maxZoom = 10) {
  if (layer && layer.getBounds().isValid()) {
    map.fitBounds(layer.getBounds(), {padding: [28, 28], maxZoom, animate: true});
  }
}
function colorFor(index) {
  return ['#abd8b2','#b8dfc5','#c9e8b6','#afddcb','#d5e9bc','#bbe2d7'][index % 6];
}
function addGeoLayer(features, onClick) {
  state.geoLayer = L.geoJSON(features, {
    style: () => ({color: '#ffffff', weight: 2.1, fillColor: colorFor(2), fillOpacity: .65, className: 'geo-shape'}),
    onEachFeature: (feature, layer) => {
      const name = feature.properties.displayName;
      layer.setStyle({fillColor: colorFor(feature.properties.colorIndex || 0)});
      layer.on({
        click: () => onClick(feature),
        mouseover: () => layer.setStyle({fillColor: '#79c8a0', weight: 3, fillOpacity: .9}),
        mouseout: () => state.geoLayer && state.geoLayer.resetStyle(layer)
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
  updateStep('01', '지역을 선택하세요', '시·도 15개 지역');
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
  if (features.length) fit(addGeoLayer(features, f => selectRegion(f.properties.CTPRVN_CD)), 8);
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

function selectRegion(code) {
  const region = state.regions.find(r => r.code === code);
  if (!region) return;
  state.fetchToken++;
  state.selectedRegion = region; state.selectedCity = null;
  clearMap(); hideToast();
  $('#selectedCard').classList.add('hidden');
  const cities = groupCities(region);
  state.cityFeatures = cities;
  const unit = region.region_type === 'metro' ? '구·군' : '시·군';
  updateStep('02', `${unit}를 선택하세요`, `${region.name} · ${cities.length}개 지역`);
  updateBreadcrumb();
  $('#mapTip').textContent = `👆 ${region.name}의 ${unit}를 클릭하세요.`;
  const list = $('#regionList'); list.replaceChildren();
  cities.forEach(city => addRegionButton(list, city.properties.displayName,
    () => selectCity(city.properties.displayName)));
  if (cities.length) fit(addGeoLayer(cities, f => selectCity(f.properties.displayName)), 10);
  else {
    toast('이 지역의 시·군·구 경계가 없습니다. 행정구역 GeoJSON을 확인하세요.');
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
  return L.marker([p.latitude, p.longitude], {icon}).bindPopup(popupContent(p));
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
      map.flyTo([p.latitude, p.longitude], Math.max(map.getZoom(), 12));
      markers[i].openPopup();
    });
    container.append(card);
  });
}

async function loadLandmarks() {
  if (!state.selectedCity || !state.selectedRegion) return;
  const token = ++state.fetchToken;
  state.markerLayer.clearLayers();
  $('#landmarkList').textContent = '장소를 불러오는 중...';
  $('#resultCount').textContent = '…';
  const params = new URLSearchParams({
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
    $('#mapTip').textContent = `✨ ${state.selectedCity.properties.displayName} · ${places.length}개 장소 표시 중`;
  } catch (err) {
    if (token !== state.fetchToken) return;
    $('#resultCount').textContent = '0';
    $('#landmarkList').textContent = '';
    toast(`랜드마크 조회 실패: ${err.message}`);
  }
}

$('#homeBtn').addEventListener('click', goHome);
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
    state.regions = regionData.regions;
    state.provinceFeatures = provinces;
    state.districtFeatures = districts;
    goHome();
  } catch (error) {
    $('#regionList').textContent = '초기화 실패: ' + error.message;
    toast('MariaDB 연결과 인터넷(지도 경계 서버)을 확인하세요.');
  }
})();
