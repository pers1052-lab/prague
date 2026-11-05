// 교통정보 > 트램 노선: trams.json(PID GTFS에서 매주 생성)을 읽어
// 주간/야간 탭, 노선 버튼, 방향 탭, 정류장 목록(체코어 + 한글), Leaflet 지도 위 경로 선을 그립니다.
(() => {
  const panel = document.getElementById('trams');
  if (!panel) return;
  const $ = (id) => document.getElementById(id);
  const picker = $('tram-picker');
  const detail = $('tram-detail');
  const tabs = panel.querySelector('.tram-tabs');
  let routes = [], kind = 'day', map, layer, current, dirIndex = 0;

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const withKo = (name, ko) => (ko && ko !== name ? `${name} (${ko})` : name);
  const kindOf = (r) => (r.night ? 'night' : 'day');

  fetch(panel.dataset.src || '/static/data/trams.json')
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((data) => {
      routes = data.routes;
      ['day', 'night'].forEach((k) => {
        panel.querySelector(`[data-count="${k}"]`).textContent = `${routes.filter((r) => kindOf(r) === k).length}개`;
      });
      tabs.hidden = false;
      tabs.addEventListener('click', (e) => { const t = e.target.closest('.tram-tab'); if (t) showKind(t.dataset.kind); });
      picker.addEventListener('click', (e) => { const b = e.target.closest('.tram-chip'); if (b) select(b.dataset.id, true); });
      $('tram-source').textContent = `출처: 프라하 교통공사(PID) 공개 시간표 · ${data.valid_from} 기준 · 매주 자동 갱신 · 한글은 체코어 발음을 옮긴 참고 표기예요`;
      const fromHash = location.hash.match(/^#tram-(.+)$/);
      const start = fromHash && routes.find((r) => r.name === decodeURIComponent(fromHash[1]));
      showKind(start ? kindOf(start) : 'day');
      if (start) select(start.id, false);
    })
    .catch(() => { picker.innerHTML = '<p class="muted">트램 노선 정보를 아직 준비 중이에요. 잠시 후 다시 확인해주세요.</p>'; });

  function showKind(k) {
    kind = k;
    tabs.querySelectorAll('.tram-tab').forEach((t) => t.setAttribute('aria-selected', String(t.dataset.kind === k)));
    picker.innerHTML = `<div class="tram-chips">${routes.filter((r) => kindOf(r) === k).map((r) =>
      `<button type="button" class="tram-chip${r.night ? ' night' : ''}" data-id="${esc(r.id)}" style="--tram:${esc(r.color)}"
        aria-pressed="${current && current.id === r.id}">${esc(r.name)}</button>`).join('')}</div>`;
  }

  function select(id, scroll) {
    current = routes.find((r) => r.id === id);
    if (!current) return;
    dirIndex = 0;
    picker.querySelectorAll('.tram-chip').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.id === id)));
    history.replaceState(null, '', '#tram-' + encodeURIComponent(current.name));
    detail.hidden = false;
    detail.style.setProperty('--tram', current.color);
    $('tram-badge').textContent = current.name;
    $('tram-title').textContent = `${current.name}번 ${current.night ? '야간 ' : ''}트램`;
    const ends = current.directions.map((d) => withKo(d.headsign, d.headsign_ko));
    $('tram-sub').textContent = ends.length > 1 ? `${ends[1]} ↔ ${ends[0]}` : `${ends[0]} 방면`;
    $('tram-dirs').innerHTML = current.directions.map((d, i) =>
      `<button type="button" role="tab" class="tram-dir" data-i="${i}" aria-selected="${i === 0}">${esc(withKo(d.headsign, d.headsign_ko))} 방면</button>`).join('');
    $('tram-dirs').onclick = (e) => { const b = e.target.closest('.tram-dir'); if (b) { dirIndex = +b.dataset.i; draw(); } };
    draw();
    if (scroll) detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function draw() {
    const d = current.directions[dirIndex];
    $('tram-dirs').querySelectorAll('.tram-dir').forEach((b) => b.setAttribute('aria-selected', String(+b.dataset.i === dirIndex)));

    // The stop list never depends on the map, so it shows even if the map library fails to load
    const list = $('tram-stops');
    list.innerHTML = d.stops.map((s, i) => `<li><button type="button" data-i="${i}">
      <span class="stop-cz">${esc(s.name)}</span>${s.ko && s.ko !== s.name ? `<span class="stop-ko">(${esc(s.ko)})</span>` : ''}</button></li>`).join('');

    const mapEl = $('tram-map');
    if (!window.L) {
      mapEl.hidden = true;
      $('tram-map-error').hidden = false;
      list.onclick = null;
      return;
    }
    if (!map) {
      map = L.map(mapEl, { scrollWheelZoom: false });
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
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
      }).bindTooltip(`${i + 1}. ${esc(withKo(s.name, s.ko))}`).addTo(layer);
    });
    // The detail block was hidden until now; size the map after layout settles
    requestAnimationFrame(() => { map.invalidateSize(); map.fitBounds(line.getBounds(), { padding: [24, 24] }); });

    list.onclick = (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      const m = markers[+b.dataset.i];
      map.setView(m.getLatLng(), 16);
      m.openTooltip();
      mapEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    };
  }
})();
