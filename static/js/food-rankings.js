'use strict';
(() => {
  const locality = document.getElementById('rankingLocality');
  const period = document.getElementById('rankingPeriod');
  const audience = document.getElementById('rankingAudience');
  const message = document.getElementById('rankingMessage');
  const list = document.getElementById('foodRankingList');
  let options = [];
  let requestId = 0;
  let currentRegion = null;
  const regionCode = code => ({'51': '42', '52': '45'}[code] || code);
  async function json(url) {
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || '자료를 불러오지 못했습니다.');
    return data;
  }
  async function load() {
    const id = ++requestId;
    list.replaceChildren();
    document.dispatchEvent(new CustomEvent('food-ranking-markers', {detail: {rankings: []}}));
    if (!locality.value || !period.value) return;
    message.textContent = '맛집 순위를 불러오는 중…';
    const [start, end] = period.value.split('-');
    try {
      const data = await json('/api/food-rankings?' + new URLSearchParams({sigungu: locality.value, audience: audience.value, start, end}));
      if (id !== requestId) return;
      for (const row of data.rankings) {
        const item = document.createElement('li');
        const rank = document.createElement('span'); rank.className = 'food-rank-number'; rank.textContent = row.area_rank;
        const info = document.createElement('div');
        const title = document.createElement('strong'); title.textContent = row.title;
        const type = document.createElement('small'); type.textContent = row.subtype;
        info.append(title, type); item.append(rank, info); list.append(item);
        {
          const button = document.createElement('button');
          button.type = 'button'; button.className = 'ranking-map-button';
          button.textContent = '지도에서 보기';
          button.addEventListener('click', () => document.dispatchEvent(new CustomEvent('food-ranking-focus', {detail: row})));
          info.append(button);
        }
      }
      document.dispatchEvent(new CustomEvent('food-ranking-markers', {detail: data}));
      message.textContent = data.rankings.length
        ? `${data.rankings.length}개 맛집 · 지도 표시 ${data.mapped_count}곳 · 위치 미확인 ${data.missing_coordinates}곳`
        : '해당 조건의 맛집 순위가 없습니다.';
    } catch (error) { if (id === requestId) message.textContent = error.message; }
  }
  function choosePeriod() {
    period.replaceChildren();
    options.filter(row => row.sigungu_code === locality.value).forEach(row => {
      const value = `${row.period_start}-${row.period_end}`;
      if (![...period.options].some(option => option.value === value)) {
        const option = document.createElement('option'); option.value = value;
        option.textContent = `${row.period_start.slice(0, 4)}.${row.period_start.slice(4)} ~ ${row.period_end.slice(0, 4)}.${row.period_end.slice(4)}`;
        period.append(option);
      }
    });
    load();
  }
  function populate(region = null) {
    const previous = locality.value;
    locality.replaceChildren();
    const seen = new Set();
    options.filter(row => !region || regionCode(row.region_code) === regionCode(region)).forEach(row => {
      if (seen.has(row.sigungu_code)) return;
      seen.add(row.sigungu_code);
      const option = document.createElement('option'); option.value = row.sigungu_code;
      option.textContent = `${row.province_name} ${row.locality_name}`; locality.append(option);
    });
    if (seen.has(previous)) locality.value = previous;
    locality.disabled = !seen.size; period.disabled = !seen.size;
    if (!seen.size) { ++requestId; list.replaceChildren(); period.replaceChildren(); document.dispatchEvent(new CustomEvent('food-ranking-markers', {detail: {rankings: []}})); message.textContent = '선택한 지역의 데이터랩 맛집 자료가 아직 없습니다.'; }
    else choosePeriod();
  }
  function syncRegion(detail) {
    currentRegion = detail;
    if (!options.length) return;
    populate(currentRegion.region);
    if (currentRegion.city) {
      const match = options.find(row => regionCode(row.region_code) === regionCode(currentRegion.region) &&
        (row.locality_name === currentRegion.city || row.locality_name.startsWith(currentRegion.city + ' ')));
      if (match) { locality.value = match.sigungu_code; choosePeriod(); }
    }
  }
  document.addEventListener('map-region-changed', event => syncRegion(event.detail));
  locality.addEventListener('change', choosePeriod);
  period.addEventListener('change', load);
  audience.addEventListener('change', load);
  json('/api/food-rankings/options').then(data => {
    options = data.options;
    if (currentRegion) syncRegion(currentRegion); else populate();
  }).catch(error => { locality.replaceChildren(); message.textContent = error.message; });
})();
