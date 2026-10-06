// <div class="osm-map" data-lat data-lng data-zoom> 를 핀 하나가 찍힌 Leaflet 지도로 바꿉니다.
// 화면에 가까워질 때 그려서 지도가 많은 여행일지에서도 타일을 한꺼번에 받지 않습니다.
(() => {
  if (!window.L) return;
  const draw = (el) => {
    const pos = [+el.dataset.lat, +el.dataset.lng];
    const map = L.map(el, { scrollWheelZoom: false }).setView(pos, +el.dataset.zoom || 16);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
    L.marker(pos).addTo(map);
  };
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) { io.unobserve(e.target); draw(e.target); }
  }), { rootMargin: '300px' });
  document.querySelectorAll('.osm-map').forEach((el) => io.observe(el));
})();
