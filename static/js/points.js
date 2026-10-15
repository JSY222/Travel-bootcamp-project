'use strict';
(() => {
  const region = document.getElementById('pointRegion');
  const locality = document.getElementById('pointLocality');
  const options = JSON.parse(document.getElementById('pointLocalityOptions').textContent);
  const update = () => {
    locality.replaceChildren(new Option('전체 시군구', ''));
    (options[region.value] || []).forEach(name => locality.add(new Option(name, name)));
    locality.disabled = !region.value;
  };
  region.addEventListener('change', update);
  locality.disabled = !region.value;
})();
