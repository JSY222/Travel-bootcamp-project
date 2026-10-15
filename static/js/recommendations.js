'use strict';
(() => {
  const root=document.getElementById('personalityPlaces'),summary=document.getElementById('personalitySummary');
  const labels={tourism:'📷 관광지',food:'🍜 맛집',event:'🎉 행사'};
  const node=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};
  async function load(){
    try{
      const response=await fetch('/api/recommendations',{cache:'no-store'}),data=await response.json();
      if(!response.ok||!data.ok)throw new Error(data.error||'추천을 불러오지 못했습니다.');
      summary.textContent='';
      root.replaceChildren();
      const details=document.createElement('details');details.className='recommendations-list';details.append(node('summary',`추천 장소 ${data.places.length}곳 펼치기`));
      data.places.forEach(place=>{
        const card=document.createElement('article');card.className='recommendation-card';
        card.append(node('small',`${labels[place.category]} · ${place.region_name} ${place.locality_name}`),node('h3',place.title),node('p',place.reason));
        card.append(window.TripTray.button(place),window.CityFavorites.button(place));
        details.append(card);
      });
      if(data.places.length)root.append(details);else root.append(node('p','현재 자료에서 성향에 맞는 키워드를 찾지 못했습니다. 지역 검색으로 다른 장소를 둘러보세요.'));
    }catch(error){summary.textContent=error.message;}
  }
  load();
})();
