// 장소 검색(OpenStreetMap Nominatim) + 지도 클릭/핀 드래그로 위도·경도를 hidden 입력에 채웁니다.
(() => {
  const mapEl = document.getElementById('picker-map');
  if (!mapEl || !window.L) return;
  const latIn = document.getElementById('lat');
  const lngIn = document.getElementById('lng');
  const out = document.getElementById('picker-coords');
  const q = document.getElementById('picker-q');
  const results = document.getElementById('picker-results');

  const has = latIn.value && lngIn.value;
  const map = L.map(mapEl).setView(has ? [+latIn.value, +lngIn.value] : [50.0875, 14.4213], has ? 16 : 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  let marker = null;
  function setPoint(lat, lng, zoom) {
    latIn.value = (+lat).toFixed(6);
    lngIn.value = (+lng).toFixed(6);
    if (marker) marker.setLatLng([lat, lng]);
    else {
      marker = L.marker([lat, lng], { draggable: true }).addTo(map);
      marker.on('dragend', () => { const p = marker.getLatLng(); setPoint(p.lat, p.lng); });
    }
    if (zoom) map.setView([lat, lng], zoom);
    out.textContent = `선택한 위치: ${latIn.value}, ${lngIn.value}`;
  }
  if (has) setPoint(latIn.value, lngIn.value);
  map.on('click', (e) => setPoint(e.latlng.lat, e.latlng.lng));

  async function search() {
    const term = q.value.trim();
    if (!term) return;
    results.hidden = false;
    results.innerHTML = '<li class="muted">검색 중…</li>';
    try {
      const url = 'https://nominatim.openstreetmap.org/search?format=json&limit=5&accept-language=ko&q=' + encodeURIComponent(term);
      const items = await (await fetch(url, { headers: { Accept: 'application/json' } })).json();
      results.innerHTML = '';
      if (!items.length) { results.innerHTML = '<li class="muted">검색 결과가 없어요. 다른 이름으로 찾거나 지도를 직접 눌러주세요.</li>'; return; }
      items.forEach((it) => {
        const li = document.createElement('li');
        const b = document.createElement('button');
        b.type = 'button';
        b.textContent = it.display_name;
        b.addEventListener('click', () => { setPoint(it.lat, it.lon, 17); results.hidden = true; });
        li.appendChild(b);
        results.appendChild(li);
      });
    } catch (e) {
      results.innerHTML = '<li class="muted">검색하지 못했어요. 잠시 후 다시 시도하거나 지도를 직접 눌러주세요.</li>';
    }
  }
  document.getElementById('picker-go').addEventListener('click', search);
  // Enter in the search box searches instead of submitting the surrounding form
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); search(); } });
})();
