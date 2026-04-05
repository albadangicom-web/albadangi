/* ===================================================
   MR Newsletter — Frontend Logic
   =================================================== */

// Type → badge CSS class mapping
const TYPE_CLASS_MAP = {
  '좌담회': 'posting-card__type--fgd',
  '설문조사': 'posting-card__type--online',
  '온라인': 'posting-card__type--online',
  '맛테스트': 'posting-card__type--taste',
  '인터뷰': 'posting-card__type--interview',
  '유치조사': 'posting-card__type--other',
  '패널모집': 'posting-card__type--other',
  '기타': 'posting-card__type--other',
  '상시모집': 'posting-card__type--always',
};

// Type → icon mapping
const TYPE_ICON_MAP = {
  '좌담회': '&#128172;',
  '온라인': '&#128187;',
  '설문조사': '&#128187;',
  '맛테스트': '&#127860;',
  '인터뷰': '&#127908;',
  '유치조사': '&#128230;',
  '패널모집': '&#128101;',
  '기타': '&#128196;',
  '상시모집': '&#128260;',
};

let allPostings = [];

// ── Determine effective type (상시모집 if no date) ──
function getEffectiveType(p) {
  if (!p.date && !p.time) return '상시모집';
  return p.type || '기타';
}

// ── Render a single posting card ──
function renderPostingCard(p, index) {
  const effectiveType = getEffectiveType(p);
  const typeClass = TYPE_CLASS_MAP[effectiveType] || 'posting-card__type--other';
  const typeIcon = TYPE_ICON_MAP[effectiveType] || '&#128196;';
  
  // Key info rows (일정, 소요시간, 사례비) — prominent display
  const keyInfoItems = [];
  if (p.date) {
    keyInfoItems.push(`<div class="posting-card__info-row"><span class="posting-card__info-label">&#128197; 일정</span><span class="posting-card__info-value">${escapeHtml(p.date)}</span></div>`);
  }
  if (p.duration) {
    keyInfoItems.push(`<div class="posting-card__info-row"><span class="posting-card__info-label">&#9202; 소요시간</span><span class="posting-card__info-value">${escapeHtml(p.duration)}</span></div>`);
  }
  if (p.reward) {
    keyInfoItems.push(`<div class="posting-card__info-row"><span class="posting-card__info-label">&#128176; 사례비</span><span class="posting-card__info-value posting-card__info-value--reward">${escapeHtml(p.reward)}</span></div>`);
  }
  
  // Secondary meta (location, target info)
  const metaItems = [];
  if (p.location) metaItems.push(`<span class="posting-card__meta-item"><span class="icon">&#128205;</span> ${escapeHtml(p.location)}</span>`);
  if (p.target_age) metaItems.push(`<span class="posting-card__meta-item"><span class="icon">&#128100;</span> ${escapeHtml(p.target_age)}</span>`);
  if (p.target_gender) metaItems.push(`<span class="posting-card__meta-item"><span class="icon">&#128101;</span> ${escapeHtml(p.target_gender)}</span>`);
  
  return `
    <a href="${p.source_url}" target="_blank" rel="noopener noreferrer" 
       class="posting-card" data-type="${effectiveType}" 
       style="animation-delay: ${index * 0.05}s" id="posting-${p.id || index}">
      <div class="posting-card__header">
        <span class="posting-card__title">${escapeHtml(p.title)}</span>
        <span class="posting-card__type ${typeClass}">${typeIcon} ${effectiveType}</span>
      </div>
      ${keyInfoItems.length > 0 ? `<div class="posting-card__key-info">${keyInfoItems.join('')}</div>` : ''}
      ${metaItems.length > 0 ? `<div class="posting-card__meta">${metaItems.join('')}</div>` : ''}
      <span class="posting-card__link-hint">Click to apply &rarr;</span>
    </a>
  `;
}

// ── HTML escape ──
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ── Render all postings ──
function renderPostings(postings) {
  const list = document.getElementById('postings-list');
  if (!list) return;

  if (!postings || postings.length === 0) {
    list.innerHTML = `
      <div class="no-results" id="no-results">
        <div class="no-results__icon">&#128269;</div>
        <p>No postings available</p>
      </div>
    `;
    return;
  }

  list.innerHTML = postings.map((p, i) => renderPostingCard(p, i)).join('');
}

// ── Update stats ──
function updateStats(postings) {
  const statToday = document.getElementById('stat-today');
  const statTotal = document.getElementById('stat-total');
  const statSources = document.getElementById('stat-sources');
  const postingCount = document.getElementById('posting-count');
  
  if (statToday) statToday.textContent = postings.length;
  if (statTotal) statTotal.textContent = postings.length;
  if (postingCount) postingCount.textContent = `${postings.length} postings`;
  
  // Count unique sources
  const sources = new Set(postings.map(p => p.source));
  if (statSources) statSources.textContent = sources.size;
}

// ── Update date header ──
function updateDateHeader() {
  const dateEl = document.getElementById('current-date');
  if (!dateEl) return;
  
  const now = new Date();
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const dayName = days[now.getDay()];
  
  dateEl.textContent = `${year}.${month}.${day} (${dayName})`;
}

// ── Filter logic ──
function initFilters() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      // Update active state
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      const filterType = btn.dataset.filter;
      
      if (filterType === 'all') {
        renderPostings(allPostings);
      } else if (filterType === '상시모집') {
        const filtered = allPostings.filter(p => getEffectiveType(p) === '상시모집');
        renderPostings(filtered);
      } else {
        const filtered = allPostings.filter(p => p.type === filterType && getEffectiveType(p) !== '상시모집');
        renderPostings(filtered);
      }
    });
  });
}

// ── Subscribe form ──
function initSubscribeForm() {
  const form = document.getElementById('subscribe-form');
  if (!form) return;
  
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const emailInput = document.getElementById('subscribe-email');
    const email = emailInput.value.trim();
    
    if (!email) return;
    
    // For now, store locally and show confirmation
    const subscribers = JSON.parse(localStorage.getItem('mr_subscribers') || '[]');
    if (!subscribers.includes(email)) {
      subscribers.push(email);
      localStorage.setItem('mr_subscribers', JSON.stringify(subscribers));
    }
    
    emailInput.value = '';
    alert('Thank you for subscribing! We will send you daily updates.');
  });
}

// ── Load data ──
async function loadPostings() {
  try {
    // Try loading from data.json (generated by newsletter_builder.py)
    const resp = await fetch('data.json');
    if (resp.ok) {
      const data = await resp.json();
      allPostings = data.postings || data;
      renderPostings(allPostings);
      updateStats(allPostings);
    }
  } catch (err) {
    console.log('No data.json found, using embedded data if available');
    // Check if postings are embedded in the page
    if (window.__POSTINGS_DATA__) {
      allPostings = window.__POSTINGS_DATA__;
      renderPostings(allPostings);
      updateStats(allPostings);
    }
  }
}

// ── Theme Toggle ──
function initThemeToggle() {
  const toggle = document.getElementById('theme-toggle');
  if (!toggle) return;
  
  function setTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('mr_theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('mr_theme', 'light');
    }
  }
  
  toggle.addEventListener('click', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    setTheme(isDark ? 'light' : 'dark');
  });
  
  toggle.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggle.click();
    }
  });
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  updateDateHeader();
  initFilters();
  initSubscribeForm();
  initThemeToggle();
  loadPostings();
});
