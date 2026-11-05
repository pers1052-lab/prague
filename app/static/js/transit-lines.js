// 교통정보 > 트램·지하철 노선: trams.json(PID GTFS에서 매주 생성)을 읽어 패널마다
// 노선 버튼(트램은 주간/야간 탭), 방향 탭, 정류장 목록(체코어 + 한글), Leaflet 지도 위 경로 선을 그립니다.
// 패널 설정: data-src(JSON), data-set(JSON 안의 목록 이름), data-hash(#tram-22, #metro-A), data-unit(제목 뒤 말).
(() => {
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const withKo = (name, ko) => (ko && ko !== name ? `${name} (${ko})` : name);
  const kindOf = (r) => (r.night ? 'night' : 'day');
  // Dark text on light line colours (metro B is yellow)
  const ink = (hex) => {
    const n = parseInt(hex.slice(1), 16);
    return (0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) > 170 ? '#1D2A33' : '#fff';
  };
  // Search results open a line through this: TransitLines.open('metro', 'L991', 0, 'Můstek')
  const controllers = {};
  window.TransitLines = { open: (set, routeId, dir, stopName) => controllers[set] && controllers[set](routeId, dir, stopName) };
  const cache = {};
  const load = (src) => (cache[src] = cache[src] || fetch(src).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }));

  document.querySelectorAll('.line-panel').forEach((panel) => {
    const q = (sel) => panel.querySelector(sel);
    const picker = q('.line-picker'), detail = q('.line-detail'), tabs = q('.line-tabs');
    const { set, hash, unit } = panel.dataset;
    let routes = [], map, layer, current, dirIndex = 0, markers = [];

    const ready = load(panel.dataset.src);
    controllers[set] = (routeId, dir, stopName) => ready.then(() => {
      const r = routes.find((x) => x.id === routeId);
      if (!r) return;
      if (tabs) showKind(kindOf(r));
      select(routeId, false);
      if (dir && dir < r.directions.length) { dirIndex = dir; draw(); }
      highlight(stopName);
    });
    ready
      .then((data) => {
        routes = data[set] || [];
        if (!routes.length) throw new Error('empty');
        q('.line-source').textContent = `출처: 프라하 교통공사(PID) 공개 시간표 · ${data.valid_from} 기준 · 매주 자동 갱신 · 한글은 체코어 발음을 옮긴 참고 표기예요`;
        picker.addEventListener('click', (e) => { const b = e.target.closest('.line-chip'); if (b) select(b.dataset.id, true); });
        if (tabs) {
          ['day', 'night'].forEach((k) => { q(`[data-count="${k}"]`).textContent = `${routes.filter((r) => kindOf(r) === k).length}개`; });
          tabs.hidden = false;
          tabs.addEventListener('click', (e) => { const t = e.target.closest('.line-tab'); if (t) showKind(t.dataset.kind); });
        }
        const m = location.hash.match(new RegExp(`^#${hash}-(.+)$`));
        const start = m && routes.find((r) => r.name === decodeURIComponent(m[1]));
        showKind(start ? kindOf(start) : 'day');
        if (start) { select(start.id, false); panel.scrollIntoView({ block: 'start' }); }
      })
      .catch(() => { picker.innerHTML = '<p class="muted">노선 정보를 아직 준비 중이에요. 잠시 후 다시 확인해주세요.</p>'; });

    function showKind(k) {
      if (tabs) tabs.querySelectorAll('.line-tab').forEach((t) => t.setAttribute('aria-selected', String(t.dataset.kind === k)));
      const list = tabs ? routes.filter((r) => kindOf(r) === k) : routes;
      picker.innerHTML = `<div class="line-chips">${list.map((r) =>
        `<button type="button" class="line-chip${r.night ? ' night' : ''}${tabs ? '' : ' solid'}" data-id="${esc(r.id)}" style="--route:${esc(r.color)};--route-ink:${ink(r.color)}"
          aria-pressed="${!!current && current.id === r.id}">${esc(r.name)}</button>`).join('')}</div>`;
    }

    function select(id, scroll) {
      current = routes.find((r) => r.id === id);
      if (!current) return;
      dirIndex = 0;
      picker.querySelectorAll('.line-chip').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.id === id)));
      history.replaceState(null, '', `#${hash}-${encodeURIComponent(current.name)}`);
      detail.hidden = false;
      detail.style.setProperty('--route', current.color);
      detail.style.setProperty('--route-ink', ink(current.color));
      q('.line-badge').textContent = current.name;
      q('.line-title').textContent = `${current.name}${current.night ? '번 야간 트램' : unit}`;
      const ends = current.directions.map((d) => withKo(d.headsign, d.headsign_ko));
      q('.line-sub').textContent = ends.length > 1 ? `${ends[1]} ↔ ${ends[0]}` : `${ends[0]} 방면`;
      const dirs = q('.line-dirs');
      dirs.innerHTML = current.directions.map((d, i) =>
        `<button type="button" role="tab" class="line-dir" data-i="${i}" aria-selected="${i === 0}">${esc(withKo(d.headsign, d.headsign_ko))} 방면</button>`).join('');
      dirs.onclick = (e) => { const b = e.target.closest('.line-dir'); if (b) { dirIndex = +b.dataset.i; draw(); } };
      draw();
      if (scroll) detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Mark a stop in the list and on the map (used when arriving from the stop search)
    function highlight(stopName) {
      const i = current.directions[dirIndex].stops.findIndex((s) => s.name === stopName);
      const items = q('.line-stops').children;
      [...items].forEach((li) => li.classList.remove('is-hit'));
      detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
      if (i < 0) return;
      items[i].classList.add('is-hit');
      const list = q('.line-stops');
      list.scrollTop = items[i].offsetTop - list.clientHeight / 2;
      if (map && markers[i]) {
        requestAnimationFrame(() => { map.invalidateSize(); map.setView(markers[i].getLatLng(), 15); markers[i].openTooltip(); });
      }
    }

    function draw() {
      const d = current.directions[dirIndex];
      q('.line-dirs').querySelectorAll('.line-dir').forEach((b) => b.setAttribute('aria-selected', String(+b.dataset.i === dirIndex)));

      // The stop list never depends on the map, so it shows even if the map library fails to load
      const list = q('.line-stops');
      list.innerHTML = d.stops.map((s, i) => `<li><button type="button" data-i="${i}">
        <span class="stop-cz">${esc(s.name)}</span>${s.ko && s.ko !== s.name ? `<span class="stop-ko">(${esc(s.ko)})</span>` : ''}</button></li>`).join('');

      const mapEl = q('.line-map');
      if (!window.L) {
        mapEl.hidden = true;
        q('.line-map-error').hidden = false;
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
      const stroke = ink(current.color) === '#fff' ? current.color : '#1D2A33';  // keep yellow markers visible
      markers = d.stops.map((s, i) => {
        const end = i === 0 || i === d.stops.length - 1;
        return L.circleMarker([s.lat, s.lng], {
          radius: end ? 7 : 5, color: stroke, weight: 2, fillColor: end ? current.color : '#fff', fillOpacity: 1,
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
  });
})();
