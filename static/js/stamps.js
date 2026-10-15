'use strict';
(() => {
  const list = document.getElementById('stampList');
  if (!list) return;
  const message = document.getElementById('stampMessage');
  const categories = {tourism: '관광지', food: '맛집', event: '행사'};
  const icons = JSON.parse(document.getElementById('regionIconData').textContent);
  const canonical = value => ({'51': '42', '52': '45'}[String(value)] || String(value || ''));
  const node = (tag, text, className) => {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  let rankingVersion = 0;
  let rankingType = 'white';
  const typeLabels = {white:'흰색',silver:'은색',gold:'금색'};
  const rankMessages = {
    1:'여행의 주인공은 바로 당신! 가장 빛나는 발자취를 남겼어요.',
    2:'정상이 바로 눈앞이에요. 다음 여행의 주인공이 되어 볼까요?',
    3:'멋진 여행가의 반열에 올랐어요. 이제 선두를 향해 한 걸음 더!',
    4:'상위권 입성! 다음 스탬프로 앞선 여행가를 따라잡아 보세요.',
    5:'아슬아슬한 TOP 5! 짐은 챙겼나요? 다른 여행가는 벌써 출발했대요.'
  };
  function stampPicture(type) {
    const picture = node('span', '', `stamp-type-picture picture-${type}`);
    picture.setAttribute('aria-hidden', 'true');
    return picture;
  }
  document.querySelectorAll('[data-stamp-type]').forEach(button => button.prepend(stampPicture(button.dataset.stampType)));
  document.querySelectorAll('[data-stamp-type]').forEach(button => button.addEventListener('click', () => {
    rankingType = button.dataset.stampType;
    document.querySelectorAll('[data-stamp-type]').forEach(btn => btn.setAttribute('aria-pressed', String(btn.dataset.stampType === rankingType)));
    refreshRanking();
  }));
  async function refreshRanking() {
    const version = ++rankingVersion;
    const root = document.getElementById('stampRankingList');
    const mine = document.getElementById('stampMyRank');
    try {
      const response = await fetch(`/api/stamps/ranking?type=${rankingType}`, {cache: 'no-store'});
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || '순위를 불러오지 못했습니다.');
      if (version !== rankingVersion) return;
      root.replaceChildren();
      data.ranking.slice(0,5).forEach(row => {
        const item = node('li', '', row.is_me ? 'stamp-rank-me' : '');
        item.dataset.rank = row.rank;
        const rankBadge = node('span', `${row.rank}위`);
        rankBadge.className = 'ranking-position';
        if (row.rank <= 3) rankBadge.setAttribute('aria-label', `${row.rank}위 상위 랭커`);
        item.append(rankBadge, node('strong', row.name));
        const stats = node('div', '', 'ranking-user-stamps');
        ['white','silver','gold'].forEach(type => {
          const value = row.stamps[type];
          if (!value.earned) return;
          const badge = node('span', '', `ranking-user-stamp user-stamp-${type}`);
          badge.append(stampPicture(type), node('span', `${value.earned}`));
          badge.title = `${typeLabels[type]} 스탬프 ${value.earned}개 보유`;
          badge.setAttribute('aria-label',badge.title);
          stats.append(badge);
        });
        item.append(stats);
        root.append(item);
      });
      mine.textContent = data.my_rank ? `내 순위 ${data.my_rank.rank}위`
        : data.ranking.length ? '로그인하면 내 순위를 볼 수 있어요.' : '첫 여행 스탬프의 주인공이 되어 보세요.';
      const sidebar = document.getElementById('sidebarStampRankingList');
      sidebar.replaceChildren(...Array.from(root.children, child => child.cloneNode(true)));
      document.getElementById('sidebarStampMyRank').textContent = mine.textContent;
      const goal = document.getElementById('rankingNextGoal');
      const ahead = data.my_rank && data.ranking.filter(row => row.points > data.my_rank.points).pop();
      goal.textContent = data.my_rank
        ? data.my_rank.rank <= 5 ? rankMessages[data.my_rank.rank] : `현재 ${data.my_rank.rank}위! 새로운 여행으로 TOP 5에 도전하세요.`
        : '로그인하고 나만의 여행 순위에 도전해 보세요.';
      document.getElementById('sidebarStampProgress').replaceChildren();
    } catch (error) {
      if (version === rankingVersion) {
        mine.textContent = error.message;
        document.getElementById('sidebarStampMyRank').textContent = error.message;
      }
    }
  }
  refreshRanking();
  document.getElementById('rankingExplore').addEventListener('click', () => {
    const input = document.getElementById('regionSearchInput');
    input.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',block:'center'});
    input.focus({preventScroll:true});
  });
  if (document.querySelector('meta[name="signed-in"]').content !== 'true') {
    message.textContent = '로그인하고 사진과 리뷰로 나만의 스탬프를 모아 보세요.';
  } else message.textContent = '스탬프를 불러오는 중…';
  document.addEventListener('visits-updated', event => {
    refreshRanking();
    const visits = event.detail.visits.filter((visit, i, all) => all.findIndex(v => v.category === visit.category && v.landmark_id === visit.landmark_id) === i);
    list.replaceChildren();
    document.getElementById('stampCount').textContent = visits.length;
    message.textContent = visits.length ? '스탬프를 누르면 사진과 리뷰를 볼 수 있어요.' : '사진과 리뷰를 남기면 장소 스탬프가 생겨요.';
    visits.forEach(visit => {
      const button = node('button', '', `travel-stamp stamp-${visit.category}`);
      button.type = 'button';
      button.setAttribute('aria-label', `${visit.title} 스탬프, 사진과 리뷰 보기`);
      const seal = node('span', '', 'stamp-seal');
      const code = canonical(visit.region_code);
      const icon = code && (icons.find(item => item.parent && canonical(item.region_code) === code && item.name === visit.locality_name)
        || icons.find(item => !item.parent && canonical(item.region_code) === code));
      if (icon) {
        const image = node('img'); image.src = icon.url; image.alt = '';
        image.addEventListener('error', () => { image.remove(); seal.prepend(node('span', '✓')); }, {once: true});
        seal.append(image);
      } else seal.append(node('span', '✓'));
      button.append(seal, node('strong', visit.title), node('small', visit.locality_name));
      button.addEventListener('click', () => {
        document.getElementById('stampPlaceTitle').textContent = visit.title;
        document.getElementById('stampPlaceArea').textContent = [...[visit.region_name, visit.locality_name].filter(Boolean), `방문일: ${visit.visited_on || '미기록'}`].join(' · ');
        const photo = document.getElementById('stampPhoto');
        photo.src = visit.photo_url; photo.alt = `${visit.title} 방문 사진`;
        document.getElementById('stampReview').textContent = visit.review;
        document.getElementById('stampDialog').showModal();
      });
      list.append(button);
    });
  });
  const celebrationQueue = [];
  let celebrating = false;
  function showNextCelebration() {
    if (!celebrationQueue.length) { celebrating = false; return; }
    celebrating = true;
    const reward = celebrationQueue.shift();
    const popup = node('div', '', 'stamp-celebration');
    popup.setAttribute('role', 'status');
    popup.setAttribute('aria-live', 'polite');
    const image = node('img', '', 'stamp-celebration-image');
    image.src = `/static/images/stamps/${reward.type}.svg`;
    image.alt = '';
    popup.append(image, node('strong', `${typeLabels[reward.type]} 스탬프를 획득하였습니다!`),
      node('span', `+${Number(reward.points).toLocaleString('ko-KR')}P`));
    const close = node('button', '닫기');
    close.type = 'button';
    let timer;
    const dismiss = () => {
      clearTimeout(timer);
      popup.remove();
      showNextCelebration();
    };
    close.addEventListener('click', dismiss, {once: true});
    popup.append(close);
    document.body.append(popup);
    timer = setTimeout(dismiss, 2800);
  }
  document.addEventListener('stamp-earned', event => {
    celebrationQueue.push(...(event.detail.stamps || []).filter(reward => typeLabels[reward.type]));
    if (!celebrating) showNextCelebration();
    message.textContent = `${event.detail.title} 스탬프를 획득했어요!`;
    list.firstElementChild?.classList.add('stamp-new');
  });
  document.addEventListener('stamps-error', event => {
    message.textContent = event.detail.message;
    document.getElementById('stampCount').textContent = '—';
  });
  document.getElementById('stampClose').addEventListener('click', () => document.getElementById('stampDialog').close());
})();
