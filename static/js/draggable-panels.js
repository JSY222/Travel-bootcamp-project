'use strict';
(() => {
  const area = document.querySelector('.map-area');
  const panels = [document.querySelector('.login-card'), document.querySelector('.stamp-shelf'),document.getElementById('tripTray')];
  const clamp = (value, max) => Math.max(0, Math.min(value, Math.max(0, max)));
  function place(panel, x, y) {
    if (panel.parentElement !== area) area.append(panel);
    panel.classList.add('panel-positioned');
    panel.style.left = `${clamp(x, area.clientWidth - panel.offsetWidth)}px`;
    panel.style.top = `${clamp(y, area.clientHeight - panel.offsetHeight)}px`;
  }
  panels.forEach(panel => {
    const handle = panel;
    panel.setAttribute('tabindex', '0');
    let drag = null;
    handle.addEventListener('pointerdown', event => {
      if (!event.isPrimary || event.button !== 0) return;
      if (event.target.closest('input,button,a,select,textarea,summary,[role="button"]')) return;
      const rect = panel.getBoundingClientRect(), bounds = area.getBoundingClientRect();
      place(panel, rect.left-bounds.left, rect.top-bounds.top);
      drag = {id:event.pointerId,x:event.clientX,y:event.clientY,left:parseFloat(panel.style.left),top:parseFloat(panel.style.top)};
      handle.setPointerCapture(event.pointerId);
      event.preventDefault();
    });
    handle.addEventListener('pointermove', event => {
      if (!drag || drag.id !== event.pointerId) return;
      place(panel,drag.left+event.clientX-drag.x,drag.top+event.clientY-drag.y);
    });
    ['pointerup','pointercancel','lostpointercapture'].forEach(type => handle.addEventListener(type, () => { drag=null; }));
    handle.addEventListener('keydown', event => {
      if (event.target !== panel) return;
      const moves = {ArrowLeft:[-20,0],ArrowRight:[20,0],ArrowUp:[0,-20],ArrowDown:[0,20]};
      if (!moves[event.key]) return;
      event.preventDefault();
      const rect=panel.getBoundingClientRect(),bounds=area.getBoundingClientRect();
      place(panel,rect.left-bounds.left+moves[event.key][0],rect.top-bounds.top+moves[event.key][1]);
    });
    new ResizeObserver(() => {
      if (panel.classList.contains('panel-positioned')) place(panel,parseFloat(panel.style.left),parseFloat(panel.style.top));
    }).observe(panel);
  });
  window.addEventListener('resize', () => panels.forEach(panel => {
    if (panel.classList.contains('panel-positioned')) place(panel,parseFloat(panel.style.left),parseFloat(panel.style.top));
  }));
  const back = document.getElementById('mapCornerBack');
  const original = document.getElementById('backBtn');
  const sync = () => { back.disabled=original.disabled; };
  new MutationObserver(sync).observe(original,{attributes:true,attributeFilter:['disabled']});
  back.addEventListener('click', () => original.click());
  sync();
})();
