// 여행일지 페이지 동작. GALLERY 는 templates/journal.html 에서 주입됩니다.
function openGallery(key, title){
  const grid = document.getElementById('lbGrid');
  grid.innerHTML = '';
  (GALLERY[key] || []).forEach(src => {
    const img = document.createElement('img');
    img.src = src;
    grid.appendChild(img);
  });
  document.getElementById('lbTitle').textContent = title + ' (' + (GALLERY[key]||[]).length + '장)';
  document.getElementById('lightbox').classList.add('open');
}
function closeGallery(){
  document.getElementById('lightbox').classList.remove('open');
}
document.getElementById('lightbox').addEventListener('click', (e)=>{
  if(e.target.id === 'lightbox') closeGallery();
});

document.querySelectorAll('.album-tab').forEach(btn=>{
  btn.addEventListener('click', ()=>{
    document.querySelectorAll('.album-tab').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const p = btn.dataset.p;
    document.querySelectorAll('#albumGrid .polaroid').forEach(card=>{
      if(p === 'all' || card.dataset.person === p){ card.classList.remove('hidden'); }
      else { card.classList.add('hidden'); }
    });
  });
});

// 화면에 보일 때만 짧은 영상이 자동재생되도록 처리
const scrollVideos = document.querySelectorAll('video.scroll-video');
if ('IntersectionObserver' in window) {
  const videoObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      const video = entry.target;
      if (entry.isIntersecting) {
        video.play().catch(() => {});
      } else {
        video.pause();
      }
    });
  }, { threshold: 0.5 });
  scrollVideos.forEach(v => videoObserver.observe(v));
} else {
  // IntersectionObserver 미지원 브라우저는 기존처럼 바로 재생
  scrollVideos.forEach(v => v.play().catch(() => {}));
}

// 날짜 선택 바를 헤더 바로 아래에 고정
const topHeader = document.querySelector('.site-header');
const dayPills = document.getElementById('dayPills');
function positionDayPills(){
  if (topHeader && dayPills) {
    dayPills.style.top = topHeader.offsetHeight + 'px';
  }
}
positionDayPills();
window.addEventListener('resize', positionDayPills);
window.addEventListener('load', positionDayPills);

// 스크롤 위치에 따라 현재 날짜 탭 활성화 (스크롤 스파이)
const spySections = document.querySelectorAll('section.day[id]');
const pillLinks = Array.from(document.querySelectorAll('.pill[href^="#day"]'));
function scrollPillIntoView(pill){
  if (!dayPills || !pill) return;
  const stripRect = dayPills.getBoundingClientRect();
  const pillRect = pill.getBoundingClientRect();
  const offset = (pillRect.left - stripRect.left) - 24; // 앞쪽에 약간 여백을 두고 보이도록
  dayPills.scrollTo({ left: dayPills.scrollLeft + offset, behavior: 'smooth' });
}
if ('IntersectionObserver' in window && spySections.length && pillLinks.length) {
  const spyObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        pillLinks.forEach(p => {
          const isActive = p.getAttribute('href') === '#' + id;
          p.classList.toggle('active', isActive);
          if (isActive) scrollPillIntoView(p);
        });
      }
    });
  }, { rootMargin: '-45% 0px -50% 0px', threshold: 0 });
  spySections.forEach(sec => spyObserver.observe(sec));
}

// 대표 사진 버튼 → 관련 사진 갤러리
document.querySelectorAll('.landmark-frame[data-gallery]').forEach(btn => {
  btn.addEventListener('click', () => openGallery(btn.dataset.gallery, btn.dataset.title));
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeGallery(); });
