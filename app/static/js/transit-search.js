// 교통정보 > 정류장 검색: /api/transit/stops?q= 로 DB에서 정류장을 찾고,
// 결과의 노선 버튼을 누르면 아래 트램·지하철 패널에서 그 노선을 열어 정류장을 표시합니다.
(() => {
  const input = document.getElementById('stop-q');
  if (!input) return;
  const box = document.getElementById('stop-search');
  const list = box.querySelector('.stop-results');
  const status = box.querySelector('.stop-search-status');
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const ink = (hex) => {
    const n = parseInt(hex.slice(1), 16);
    return (0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) > 170 ? '#1D2A33' : '#fff';
  };
  let timer, controller;

  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(search, 250);
  });

  function search() {
    const q = input.value.trim();
    if (controller) controller.abort();
    if (!q) { list.innerHTML = ''; status.textContent = ''; return; }
    controller = new AbortController();
    status.textContent = '찾는 중…';
    fetch('/api/transit/stops?q=' + encodeURIComponent(q), { signal: controller.signal })
      .then((r) => r.json())
      .then((data) => {
        status.textContent = !data.stops.length ? `"${q}"에 맞는 정류장이 없어요.`
          : data.stops.length >= 20 ? '20곳 이상 찾았어요. 이름을 조금 더 입력하면 좁혀져요. 노선을 누르면 지도에서 보여드려요.'
          : `${data.stops.length}곳을 찾았어요. 노선을 누르면 지도에서 보여드려요.`;
        list.innerHTML = data.stops.map((s) => `<li class="stop-result">
          <div class="stop-result-name"><strong>${esc(s.name)}</strong>${s.ko && s.ko !== s.name ? ` <span class="muted">(${esc(s.ko)})</span>` : ''}</div>
          <div class="stop-result-lines">${s.lines.map((l) => `<button type="button" class="line-chip small${l.mode === 'metro' ? ' solid' : ''}${l.night ? ' night' : ''}"
              style="--route:${esc(l.color)};--route-ink:${ink(l.color)}" data-mode="${l.mode}" data-id="${esc(l.id)}" data-dir="${l.direction}" data-stop="${esc(s.name)}"
              title="${l.mode === 'metro' ? `${esc(l.name)}선 지하철` : `${esc(l.name)}번 ${l.night ? '야간 ' : ''}트램`}">${l.mode === 'metro' ? 'Ⓜ ' : ''}${esc(l.name)}</button>`).join('')}</div>
        </li>`).join('');
      })
      .catch((e) => { if (e.name !== 'AbortError') status.textContent = '검색하지 못했어요. 잠시 후 다시 시도해주세요.'; });
  }

  list.addEventListener('click', (e) => {
    const b = e.target.closest('.line-chip');
    if (!b || !window.TransitLines) return;
    window.TransitLines.open(b.dataset.mode === 'metro' ? 'metro' : 'routes', b.dataset.id, +b.dataset.dir, b.dataset.stop);
  });
})();
