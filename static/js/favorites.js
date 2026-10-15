'use strict';
(() => {
  const signedIn = document.querySelector('meta[name="signed-in"]')?.content === 'true';
  const key = place => `${place.category}:${place.id}`;
  let saved = new Set();
  function paintButton(button) {
    const active = saved.has(button.dataset.favoriteKey);
    button.textContent = active ? '★ 즐겨찾기 해제' : '☆ 즐겨찾기 등록';
    button.setAttribute('aria-pressed', String(active));
  }
  async function refresh() {
    if (!signedIn) throw new Error('로그인 후 즐겨찾기를 이용해 주세요.');
    const response = await fetch('/api/favorites', {cache: 'no-store'});
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || '즐겨찾기를 불러올 수 없습니다.');
    const places = [...new Map(data.landmarks.map(place => [key(place), place])).values()];
    saved = new Set(places.map(key));
    document.querySelectorAll('.favorite-toggle').forEach(paintButton);
    return places;
  }
  let loaded = false;
  const ready = signedIn ? refresh().then(() => { loaded = true; }).catch(() => {}) : Promise.resolve();
  window.CityFavorites = {
    ready, refresh,
    button(place) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'favorite-toggle';
      button.dataset.favoriteKey = key(place);
      function paint() {
        paintButton(button);
      }
      paint();
      button.addEventListener('click', async () => {
        button.disabled = true;
        try {
          if (!signedIn) throw new Error('로그인 후 즐겨찾기를 이용해 주세요.');
          if (!loaded) { await refresh(); loaded = true; }
          const active = !saved.has(key(place));
          const response = await fetch('/api/favorites', {method: 'POST', headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content
          }, body: JSON.stringify({category: place.category, landmark_id: Number(place.id), active})});
          const data = await response.json();
          if (!response.ok || !data.ok) throw new Error(data.error || '저장하지 못했습니다.');
          if (active) saved.add(key(place)); else saved.delete(key(place));
          paint();
          document.querySelectorAll('.favorite-toggle').forEach(paintButton);
          document.dispatchEvent(new Event('favorites-updated'));
        } catch (error) { button.textContent = error.message; }
        finally { button.disabled = false; }
      });
      return button;
    }
  };
})();
