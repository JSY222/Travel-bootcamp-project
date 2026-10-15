'use strict';
(() => {
  const signedIn = document.querySelector('meta[name="signed-in"]')?.content === 'true';
  const categories = {tourism: '관광지', food: '맛집', event: '행사'};
  let records = [];
  let loaded = false;
  let loadError = '';
  const key = place => `${place.category}:${place.landmark_id ?? place.id}`;
  const find = place => records.find(visit => key(visit) === key(place));
  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  async function refresh() {
    if (!signedIn) return;
    const response = await fetch('/api/visits', {cache: 'no-store'});
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || '방문 기록을 불러올 수 없습니다.');
    records = data.visits;
    loaded = true;
    loadError = '';
    renderProfile(data.totals, data.regional_totals || []);
    document.dispatchEvent(new CustomEvent('visits-updated', {detail: {visits: records}}));
  }
  function renderProfile(totals, regionalTotals) {
    const root = document.getElementById('profileVisits');
    if (!root) return;
    root.replaceChildren();
    const regionKey = row => JSON.stringify([row.region_code || '', row.locality_name || '?? ???']);
    const regionLabel = row => [row.region_name, row.locality_name || '?? ???'].filter(Boolean).join(' ? ');
    const groups = new Map();
    records.forEach(visit => {
      const id = regionKey(visit);
      if (!groups.has(id)) groups.set(id, {label: regionLabel(visit), visits: []});
      groups.get(id).visits.push(visit);
    });
    const ordered = [...groups.entries()].sort((a, b) => a[1].label.localeCompare(b[1].label, 'ko'));
    if (!records.length) root.append(element('p', '?? ?? ?? ??? ????.', 'visit-empty'));
    for (const [, group] of ordered) {
      const section = element('details', '', 'visit-region');
      section.append(element('summary', `${group.label} ? ${group.visits.length}?`));
      for (const visit of group.visits) {
        const card = element('article', '', 'visit-card');
        const image = element('img');
        image.src = visit.photo_url;
        image.alt = `${visit.title} ?? ??`;
        image.loading = 'lazy';
        const content = element('div');
        content.append(element('h4', `? ${visit.title}`),
          element('small', categories[visit.category] || '?? ??'),
          element('p', visit.review, 'visit-review'));
        card.append(image, content);
        section.append(card);
      }
      root.append(section);
    }
    const summary = element('section', '', 'visit-summary');
    summary.append(element('h3', `? ?? ? ${records.length}?`));
    const total = Object.values(totals).reduce((sum, value) => sum + Number(value), 0);
    summary.append(element('p', `?? ?? ${total}? ? ${records.length}? ??`));
    const statistics = new Map(regionalTotals.map(row => [regionKey(row), {
      label: regionLabel(row), total: Number(row.total), visited: groups.get(regionKey(row))?.visits.length || 0
    }]));
    ordered.forEach(([id, group]) => {
      if (!statistics.has(id)) statistics.set(id, {label: group.label, total: null, visited: group.visits.length});
    });
    const statsList = [...statistics.values()].sort((a, b) => b.visited - a.visited || a.label.localeCompare(b.label, 'ko'));
    for (const row of statsList.filter(row => row.visited > 0)) {
      summary.append(element('p', `${row.label}: ${row.visited}? ??${row.total === null ? '' : ` / ${row.total}?`}`, 'visit-region-stat'));
    }
    const unvisited = statsList.filter(row => row.visited === 0);
    if (unvisited.length) {
      const more = element('details', '', 'visit-unvisited');
      more.append(element('summary', `?? ???? ?? ?? ${unvisited.length}? ???`));
      unvisited.forEach(row => more.append(element('p', `${row.label}: 0? ?? / ${row.total}?`)));
      summary.append(more);
    }
    summary.append(element('small', '?? ??? ??? ???? ?? ?? ?? ???? ????.'));
    root.append(summary);
  }
  const dialog = document.getElementById('visitDialog');
  const form = document.getElementById('visitForm');
  let current = null;
  let saving = false;
  const message = document.getElementById('visitMessage');
  if (dialog) {
    document.getElementById('visitClose').addEventListener('click', () => { if (!saving) dialog.close(); });
    dialog.addEventListener('cancel', event => { if (saving) event.preventDefault(); });
    dialog.addEventListener('close', () => { form.reset(); current = null; });
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (!current || saving) return;
      const data = new FormData(form);
      data.set('category', current.category);
      data.set('landmark_id', current.id);
      const button = form.querySelector('button[type="submit"]');
      saving = true;
      button.disabled = true;
      message.textContent = '저장 중입니다…';
      let saved = false;
      const earnsStamp = !find(current);
      try {
        const response = await fetch('/api/visits', {method: 'POST', body: data,
          headers: {'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content}});
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error(result.error || '저장하지 못했습니다.');
        saved = true;
        await refresh();
        if (earnsStamp) document.dispatchEvent(new CustomEvent('stamp-earned', {detail: {title: current.title}}));
        dialog.close();
      } catch (error) {
        message.textContent = saved ? '저장은 완료됐지만 지도 갱신에 실패했습니다. 새로고침해 주세요.' : error.message;
      } finally { saving = false; button.disabled = false; }
    });
  }
  window.CityVisits = {
    has: place => Boolean(find(place)),
    button(place) {
      if (!signedIn) return element('p', '로그인하면 사진과 리뷰로 방문 기록을 남길 수 있어요.', 'visit-login-hint');
      const button = element('button', find(place) ? '✓ 방문 기록 보기 / 수정' : '사진·리뷰로 방문 기록 남기기', 'auth-submit visit-open');
      button.type = 'button';
      button.addEventListener('click', async () => {
        try {
          if (!loaded) await refresh();
          const record = find(place);
          current = place;
          form.reset();
          document.getElementById('visitTitle').textContent = place.title;
          form.elements.review.value = record?.review || '';
          form.elements.photo.required = !record;
          const image = document.getElementById('visitExistingPhoto');
          image.hidden = !record;
          if (record) image.src = record.photo_url;
          else image.removeAttribute('src');
          message.textContent = record ? '새 사진을 선택하지 않으면 기존 사진을 유지합니다.' : '사진과 리뷰를 저장하면 방문한 장소로 표시됩니다.';
          dialog.showModal();
        } catch (error) { button.textContent = error.message; }
      });
      return button;
    }
  };
  window.CityVisits.ready = refresh().catch(error => {
    loadError = error.message;
    const root = document.getElementById('profileVisits');
    if (root) root.textContent = loadError;
    document.dispatchEvent(new CustomEvent('stamps-error', {detail: {message: loadError}}));
  });
})();
