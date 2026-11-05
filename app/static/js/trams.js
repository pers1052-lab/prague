// 교통정보 > 트램 노선: /static/data/trams.json(PID GTFS에서 매주 생성)을 읽어
// 노선 버튼, 방향 탭, 정류장 목록, Leaflet 지도 위 경로 선을 그립니다.
(() => {
  const picker = document.getElementById('tram-picker');
  if (!picker) return;
  const $ = (id) => document.getElementById(id);
  const detail = $('tram-detail');
  let routes = [], map, layer, current, dirIndex = 0;

  const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  fetch('/static/data/trams.json')
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((data) => {
      routes = data.routes;
      const group = (title, list) => list.length ? `<div class="tram-group"><div class="tram-group-title">${title}</div>
        <div class="tram-chips">${list.map((r) => `<button type="button" class="tram-chip" data-id="${esc(r.id)}"
          style="--tram:${esc(r.color)}" aria-pressed="false">${esc(r.name)}</button>`).join('')}</div></div>` : '';
      picker.innerHTML = group('주간 트램', routes.filter((r) => !r.night)) + group('야간 트램 (자정~새벽)', routes.filter((r) => r.night));
      $('tram-source').textContent = `출처: 프라하 교통공사(PID) 공개 시간표 · ${data.valid_from} 기준 · 매주 자동 갱신`;
      picker.addEventListener('click', (e) => {
        const b = e.target.closest('.tram-chip');
        if (b) select(b.dataset.id, 0, true);
      });
      const fromHash = location.hash.match(/^#tram-(.+)$/);
      const start = fromHash && routes.find((r) => r.name === decodeURIComponent(fromHash[1]));
      if (start) select(start.id, 0, false);
    })
    .catch(() => { picker.innerHTML = '<p class="muted">트램 노선 정보를 아직 준비 중이에요. 잠시 후 다시 확인해주세요.</p>'; });

  function select(id, dir, scroll) {
    current = routes.find((r) => r.id === id);
    if (!current) return;
    dirIndex = dir;
    picker.querySelectorAll('.tram-chip').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.id === id)));
    history.replaceState(null, '', '#tram-' + encodeURIComponent(current.name));
    detail.hidden = false;
    detail.style.setProperty('--tram', current.color);
    $('tram-badge').textContent = current.name;
    $('tram-title').textContent = `${current.name}번 트램${current.night ? ' (야간)' : ''}`;
    const ends = current.directions.map((d) => d.headsign);
    $('tram-sub').textContent = ends.length > 1 ? `${ends[1]} ↔ ${ends[0]}` : `${ends[0]} 방면`;
    $('tram-dirs').innerHTML = current.directions.map((d, i) =>
      `<button type="button" role="tab" class="tram-dir" data-i="${i}" aria-selected="${i === dirIndex}">${esc(d.headsign)} 방면</button>`).join('');
    $('tram-dirs').onclick = (e) => { const b = e.target.closest('.tram-dir'); if (b) { dirIndex = +b.dataset.i; draw(); } };
    draw();
    if (scroll) detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function draw() {
    const d = current.directions[dirIndex];
    $('tram-dirs').querySelectorAll('.tram-dir').forEach((b) => b.setAttribute('aria-selected', String(+b.dataset.i === dirIndex)));
    if (!window.L) return;
    if (!map) {
      map = L.map('tram-map', { scrollWheelZoom: false });
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(map);
    }
    if (layer) layer.remove();
    layer = L.layerGroup().addTo(map);
    L.polyline(d.path, { color: '#fff', weight: 9, opacity: 0.9 }).addTo(layer);
    const line = L.polyline(d.path, { color: current.color, weight: 5 }).addTo(layer);
    const markers = d.stops.map((s, i) => {
      const end = i === 0 || i === d.stops.length - 1;
      return L.circleMarker([s.lat, s.lng], {
        radius: end ? 7 : 5, color: current.color, weight: 2, fillColor: end ? current.color : '#fff', fillOpacity: 1,
      }).bindTooltip(`${i + 1}. ${s.name}`).addTo(layer);
    });
    map.invalidateSize();
    map.fitBounds(line.getBounds(), { padding: [24, 24] });

    const list = $('tram-stops');
    list.innerHTML = d.stops.map((s, i) => `<li><button type="button" data-i="${i}">${esc(s.name)}</button></li>`).join('');
    list.onclick = (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      const m = markers[+b.dataset.i];
      map.setView(m.getLatLng(), 16);
      m.openTooltip();
      document.getElementById('tram-map').scrollIntoView({ behavior: 'smooth', block: 'center' });
    };
  }
})();
