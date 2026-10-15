'use strict';
(() => {
  const categories = {tourism: '관광지', food: '맛집', event: '행사'};
  const regionIcons = JSON.parse(document.getElementById('profileRegionIcons').textContent);
  const canonicalCode = code => ({'51': '42', '52': '45'}[String(code)] || String(code || ''));
  function cityLogo(visit) {
    const code = canonicalCode(visit.region_code);
    if (!code) return null;
    return regionIcons.find(icon => icon.parent && canonicalCode(icon.region_code) === code && icon.name === visit.locality_name)
      || regionIcons.find(icon => !icon.parent && canonicalCode(icon.region_code) === code);
  }
  const node = (tag, text, className) => {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  async function read(url) {
    const response = await fetch(url, {cache: 'no-store'});
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || '자료를 불러오지 못했습니다.');
    return data;
  }
  function renderVisits(visits) {
    const cities = document.getElementById('visitedCitiesList');
    const records = document.getElementById('travelRecordsList');
    const stamps = document.getElementById('profileStampsList');
    stamps.replaceChildren();
    const seenPlaces = new Set();
    document.getElementById('profileStampsCount').textContent = new Set(visits.map(v => `${v.category}:${v.landmark_id}`)).size;
    cities.replaceChildren();
    records.replaceChildren();
    const groups = new Map();
    visits.forEach(visit => {
      const key = JSON.stringify([visit.region_code, visit.locality_name]);
      if (!groups.has(key)) groups.set(key, {name: [visit.region_name, visit.locality_name || '지역 미확인'].filter(Boolean).join(' · '), count: 0, icon: cityLogo(visit)});
      groups.get(key).count++;
      const card = node('article', '', 'profile-record');
      const image = node('img');
      image.src = visit.photo_url;
      image.alt = `${visit.title} 방문 사진`;
      image.loading = 'lazy';
      card.append(image, node('h3', visit.title),
        node('small', [visit.locality_name, categories[visit.category]].filter(Boolean).join(' · ')),
        node('p', `방문일: ${visit.visited_on || '미기록'}`),
        node('p', visit.review, 'profile-record-review'));
      records.append(card);
      const placeKey = `${visit.category}:${visit.landmark_id}`;
      if (seenPlaces.has(placeKey)) return;
      seenPlaces.add(placeKey);
      const stamp = node('details', '', 'profile-stamp');
      const heading = node('summary');
      const seal = node('span', '', 'profile-stamp-seal');
      const logo = cityLogo(visit);
      if (logo) {
        const image = node('img');
        image.src = logo.url;
        image.alt = '';
        image.loading = 'lazy';
        seal.append(image);
      } else seal.append(node('span', '✓'));
      const label = node('div');
      label.append(node('strong', visit.title), node('small', [visit.locality_name, categories[visit.category]].filter(Boolean).join(' · ')));
      heading.append(seal, label);
      const photo = node('img', '', 'profile-stamp-photo');
      photo.src = visit.photo_url;
      photo.alt = `${visit.title} 방문 사진`;
      photo.loading = 'lazy';
      stamp.append(heading, photo, node('p', `방문일: ${visit.visited_on || '미기록'}`), node('p', visit.review, 'profile-record-review'));
      stamps.append(stamp);
    });
    [...groups.values()].sort((a, b) => a.name.localeCompare(b.name, 'ko')).forEach(city => {
      const row = node('div', '', 'profile-city-row');
      if (city.icon) {
        const image = node('img', '', 'profile-city-logo');
        image.src = city.icon.url;
        image.alt = `${city.icon.name} 로고`;
        image.loading = 'lazy';
        image.addEventListener('error', () => image.remove(), {once: true});
        row.append(image);
      }
      const caption = node('div', '', 'profile-city-caption');
      caption.append(node('strong', city.name), node('small', `${city.count}회 방문`));
      row.append(caption);
      cities.append(row);
    });
    document.getElementById('visitedCitiesCount').textContent = groups.size;
    document.getElementById('travelRecordsCount').textContent = visits.length;
    if (!visits.length) {
      cities.append(node('p', '아직 방문한 도시가 없습니다.', 'profile-empty'));
      records.append(node('p', '지도에서 장소를 선택해 사진과 리뷰를 남겨 보세요.', 'profile-empty'));
      stamps.append(node('p', '방문 사진과 리뷰를 남기면 장소 스탬프를 얻을 수 있어요.', 'profile-empty'));
    }
  }
  function renderFavorites(places) {
    const root = document.getElementById('favoritePlacesList');
    root.replaceChildren();
    document.getElementById('favoritePlacesCount').textContent = places.length;
    places.forEach(place => {
      const card = node('article', '', 'profile-favorite');
      card.append(node('h3', `★ ${place.title}`), node('small', [place.locality_name, categories[place.category]].filter(Boolean).join(' · ')));
      if (place.description) card.append(node('p', place.description));
      if (/^https?:\/\//i.test(place.location_url || '')) {
        const link = node('a', '장소 위치 보기 ↗');
        link.href = place.location_url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        card.append(link);
      }
      root.append(card);
    });
    if (!places.length) root.append(node('p', '지도에서 마음에 드는 장소에 별을 눌러 담아 보세요.', 'profile-empty'));
  }
  read('/api/visits').then(data => renderVisits(data.visits)).catch(error => {
    ['visitedCitiesList', 'travelRecordsList', 'profileStampsList'].forEach(id => { document.getElementById(id).textContent = error.message; });
    ['visitedCitiesCount', 'travelRecordsCount', 'profileStampsCount'].forEach(id => { document.getElementById(id).textContent = '—'; });
  });
  read('/api/favorites').then(data => renderFavorites(data.landmarks)).catch(error => {
    document.getElementById('favoritePlacesList').textContent = error.message;
    document.getElementById('favoritePlacesCount').textContent = '—';
  });
})();
