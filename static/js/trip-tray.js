'use strict';
(() => {
  let places = [];
  try { places = JSON.parse(sessionStorage.getItem('travel-trip-tray') || '[]'); } catch {}
  if (!Array.isArray(places)) places=[];
  const key=p=>`${p.category}:${p.id}`;
  const labels={tourism:'관광지',food:'맛집',event:'행사'};
  const message=document.getElementById('tripTrayMessage');
  const node=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};
  function render() {
    try {sessionStorage.setItem('travel-trip-tray',JSON.stringify(places));}catch{}
    const root=document.getElementById('tripTrayList');root.replaceChildren();
    document.getElementById('tripTrayCount').textContent=places.length;
    document.getElementById('tripTraySave').disabled=!places.length;
    places.forEach(place=>{
      const row=document.createElement('div');row.className='trip-tray-row';
      const caption=document.createElement('div');caption.append(node('strong',place.title),node('small',`${place.locality_name||''} · ${labels[place.category]}`));
      const remove=node('button','×');remove.type='button';remove.setAttribute('aria-label',`${place.title} 찜 해제`);
      remove.addEventListener('click',()=>{places=places.filter(p=>key(p)!==key(place));render();});
      row.append(caption,remove);root.append(row);
    });
    if(!places.length)root.append(node('p','장소 정보의 ♡ 찜 버튼으로 담아 보세요.'));
    document.querySelectorAll('[data-tray-key]').forEach(button=>{
      const active=places.some(p=>key(p)===button.dataset.trayKey);button.textContent=active?'♥ 찜 해제':'♡ 찜';button.setAttribute('aria-pressed',String(active));
    });
  }
  window.TripTray={button(place){
    const button=node('button',places.some(p=>key(p)===key(place))?'♥ 찜 해제':'♡ 찜');button.type='button';button.className='trip-tray-toggle';button.dataset.trayKey=key(place);
    button.addEventListener('click',event=>{event.stopPropagation();if(places.some(p=>key(p)===key(place)))places=places.filter(p=>key(p)!==key(place));else places.push({id:place.id,category:place.category,title:place.title,locality_name:place.locality_name});message.textContent='';render();});return button;
  }};
  document.getElementById('tripTraySave').addEventListener('click',async()=>{
    if(document.querySelector('meta[name="signed-in"]').content!=='true'){message.textContent='로그인 후 즐겨찾기에 저장해 주세요.';return;}
    const button=document.getElementById('tripTraySave');button.disabled=true;
    const snapshot=[...places];let success=0;
    try {
      for(const place of snapshot){
        const response=await fetch('/api/favorites',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify({category:place.category,landmark_id:Number(place.id),active:true})});
        const data=await response.json();if(!response.ok||!data.ok)throw new Error(data.error||'저장하지 못했습니다.');success++;
      }
      message.textContent=`${success}곳을 즐겨찾기에 추가했습니다.`;
    }catch(error){message.textContent=`${success}곳 저장 완료. ${error.message}`;}
    finally{await window.CityFavorites.refresh().catch(()=>{});document.dispatchEvent(new Event('favorites-updated'));button.disabled=!places.length;}
  });
  render();
})();
