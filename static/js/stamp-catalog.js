'use strict';
(() => {
  const dialog = document.getElementById('stampCatalogDialog');
  const root = document.getElementById('stampCatalogContent');
  const message = document.getElementById('stampCatalogMessage');
  const labels = {tourism: '관광지', food: '맛집', event: '행사'};
  const node = (tag, text, cls) => {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  };
  let version = 0;
  async function load() {
    const request = ++version;
    message.textContent = '모은 스탬프를 불러오는 중…';
    root.replaceChildren();
    try {
      const response = await fetch('/api/stamps/catalog', {cache: 'no-store'});
      const data = await response.json();
      if (request !== version) return;
      if (!response.ok || !data.ok) throw new Error(data.error || '도감을 불러오지 못했습니다.');
      const provinces = new Map();
      data.places.forEach(place => {
        if (!provinces.has(place.region_code)) provinces.set(place.region_code, {name: place.region_name || place.region_code, cities: new Map()});
        const province = provinces.get(place.region_code);
        if (!province.cities.has(place.locality_name)) province.cities.set(place.locality_name, []);
        province.cities.get(place.locality_name).push(place);
      });
      message.textContent = data.places.length ? '지역을 펼쳐 모은 스탬프와 다음 여행지를 확인해 보세요.' : '아직 지도에 등록된 장소가 없습니다.';
      provinces.forEach(province => {
        if (![...province.cities.values()].some(places => places.some(p=>p.visit_id))) return;
        const section = node('details', '', 'catalog-region');
        const cities = [...province.cities.entries()];
        const visitedCities = cities.filter(([, places]) => places.some(p => p.visit_id)).length;
        const total = cities.reduce((sum, [, places]) => sum + places.length, 0);
        const earned = cities.reduce((sum, [, places]) => sum + places.filter(p => p.visit_id).length, 0);
        const tourism = cities.flatMap(([, places]) => places);
        const gold = tourism.length > 0 && tourism.every(p => p.visit_id);
        const summary = node('summary', `${province.name} · ${earned}/${total}개 · ${Math.round(earned / total * 100)}%`);
        section.append(summary, node('p', `방문 지역 ${visitedCities}/${cities.length}개`, 'catalog-meta'));
        section.append(node('div', gold ? '★ 금색 관광지 완성 스탬프 획득' : '☆ 금색 관광지 완성 스탬프 미획득', `catalog-medal medal-gold ${gold ? '' : 'medal-locked'}`));
        cities.forEach(([city, places]) => {
          const count = places.filter(p => p.visit_id).length;
          if (!count) return;
          const percent = Math.round(count / places.length * 100);
          const cityTourism = places;
          const silver = cityTourism.length > 0 && cityTourism.every(p => p.visit_id);
          const citySection = node('details', '', 'catalog-city');
          citySection.append(node('summary', `${city} · ${count}/${places.length}개 · ${percent}%`));
          const progress = node('progress');
          progress.max = places.length; progress.value = count;
          progress.setAttribute('aria-label', `${city} 스탬프 진행률 ${percent}%`);
          citySection.append(progress);
          const medals = node('div', '', 'catalog-medals');
          medals.append(node('span', `흰색 ${count}개`, `catalog-medal medal-white ${count ? '' : 'medal-locked'}`),
            node('span', silver ? '은색 획득' : '은색 미획득', `catalog-medal medal-silver ${silver ? '' : 'medal-locked'}`));
          citySection.append(medals);
          const grid = node('div', '', 'catalog-stamps');
          places.forEach(place => {
            if (!place.visit_id) return;
            const stamp = node('div', '', `catalog-place stamp-${place.category} ${place.visit_id ? 'is-earned' : 'is-locked'}`);
            stamp.append(node('span', place.visit_id ? '✓ 획득' : '○ 미획득'), node('strong', place.title), node('small', labels[place.category]));
            grid.append(stamp);
          });
          citySection.append(grid); section.append(citySection);
        });
        root.append(section);
      });
      message.textContent = root.childElementCount ? '지역을 펼쳐 내가 모은 스탬프를 확인해 보세요.' : '아직 모은 스탬프가 없습니다. 사진과 리뷰로 첫 스탬프를 모아 보세요.';
    } catch (error) { if (request === version) message.textContent = error.message; }
  }
  document.getElementById('stampCatalogOpen').addEventListener('click', () => { dialog.showModal(); load(); });
  document.getElementById('stampCatalogClose').addEventListener('click', () => dialog.close());
  const help = document.getElementById('stampHelpDialog');
  document.querySelectorAll('[data-stamp-help]').forEach(button=>button.addEventListener('click',()=>help.showModal()));
  document.getElementById('stampHelpClose').addEventListener('click',()=>help.close());
  document.addEventListener('visits-updated', () => { if (dialog.open) load(); });
})();
