'use strict';
(() => {
  const root=document.getElementById('personalityPlaces'),summary=document.getElementById('personalitySummary');
  const labels={tourism:'📷 관광지',food:'🍜 맛집',event:'🎉 행사'};
  const node=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};
  async function load(){
    try{
      const response=await fetch('/api/recommendations',{cache:'no-store'}),data=await response.json();
      if(!response.ok||!data.ok)throw new Error(data.error||'추천을 불러오지 못했습니다.');
      summary.textContent=`${data.mbti} · ${data.travel_styles.join(', ') || '여행스타일 미선택'} 기준`;
      root.replaceChildren();
      const help=document.createElement('details');help.className='recommendations-list';
      help.append(node('summary','추천 기준 보기'),node('p','장소 이름·설명의 키워드로 점수를 계산합니다. 선택한 여행스타일은 서로 다른 키워드 1개당 20점, 최대 60점입니다. MBTI는 네 글자별 키워드 1개당 5점, 각 최대 10점으로 총 40점입니다. 합계가 높은 순으로 최대 15곳을 표시합니다. MBTI는 탐색용 분류 기준이며 실제 성격 적합성을 보장하지 않습니다. 일치 키워드가 부족한 장소는 탐색 추천으로 구분합니다.'));
      root.append(help);
      const details=document.createElement('details');details.className='recommendations-list';details.append(node('summary',`추천 장소 ${data.places.length}곳 펼치기`));
      data.places.forEach(place=>{
        const card=document.createElement('article');card.className='recommendation-card';
        card.append(node('small',`${labels[place.category]} · ${place.region_name} ${place.locality_name}`),node('h3',place.title),node('p',place.reason));
        card.insertBefore(node('p',`${place.match_level} · ${place.score}점 (스타일 ${place.style_score}/60 · MBTI ${place.mbti_score}/40)`),card.lastChild);
        card.append(window.TripTray.button(place),window.CityFavorites.button(place));
        details.append(card);
      });
      if(data.places.length)root.append(details);else root.append(node('p','현재 자료에서 성향에 맞는 키워드를 찾지 못했습니다. 지역 검색으로 다른 장소를 둘러보세요.'));
    }catch(error){summary.textContent=error.message;}
  }
  load();
})();
