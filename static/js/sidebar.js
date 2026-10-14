'use strict';

(() => {
  const shell = document.querySelector('.app-shell');
  const sidebar = document.getElementById('travelSidebar');
  const handle = document.getElementById('sidebarHandle');
  let open = false;
  let drag = null;
  let suppressClick = false;

  function setOpen(next) {
    open = next;
    shell.classList.toggle('sidebar-open', open);
    shell.classList.remove('sidebar-dragging');
    shell.style.removeProperty('--sidebar-offset');
    sidebar.inert = !open;
    sidebar.setAttribute('aria-hidden', String(!open));
    handle.setAttribute('aria-expanded', String(open));
    handle.setAttribute('aria-label', open ? '여행 패널 닫기' : '여행 패널 열기');
    handle.title = open ? '왼쪽으로 끌거나 클릭해서 닫기' : '오른쪽으로 끌거나 클릭해서 열기';
  }

  handle.addEventListener('pointerdown', event => {
    if (!event.isPrimary || event.button !== 0) return;
    const width = sidebar.getBoundingClientRect().width;
    drag = {id: event.pointerId, startX: event.clientX, width,
      startOffset: open ? width : 0, offset: open ? width : 0, moved: false};
    suppressClick = false;
    handle.setPointerCapture(event.pointerId);
  });

  handle.addEventListener('pointermove', event => {
    if (!drag || event.pointerId !== drag.id) return;
    const distance = event.clientX - drag.startX;
    if (Math.abs(distance) > 5) drag.moved = true;
    if (!drag.moved) return;
    drag.offset = Math.max(0, Math.min(drag.width, drag.startOffset + distance));
    shell.classList.add('sidebar-dragging');
    shell.style.setProperty('--sidebar-offset', `${drag.offset}px`);
  });

  function finishDrag(event, cancelled = false) {
    if (!drag || event.pointerId !== drag.id) return;
    const current = drag;
    drag = null;
    suppressClick = current.moved;
    if (cancelled) setOpen(open);
    else if (current.moved) {
      const distance = current.offset - current.startOffset;
      // A short deliberate swipe also opens or closes the drawer.
      setOpen(Math.abs(distance) > 40 ? distance > 0 : current.offset > current.width / 2);
    }
    if (handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);
  }

  handle.addEventListener('pointerup', event => finishDrag(event));
  handle.addEventListener('pointercancel', event => finishDrag(event, true));
  handle.addEventListener('lostpointercapture', event => finishDrag(event, true));
  handle.addEventListener('click', event => {
    if (suppressClick && event.detail !== 0) {
      suppressClick = false;
      return;
    }
    setOpen(!open);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && open) {
      drag = null;
      setOpen(false);
      handle.focus();
    }
  });
  setOpen(false);
})();
