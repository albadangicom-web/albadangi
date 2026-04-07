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

// ── Determine effective type (상시모집 if no date or '상시' keyword) ──
function getEffectiveType(p) {
  const title = (p.title || '').toLowerCase();
  const raw = (p.raw_content || '').toLowerCase();
  
  // 1. 제목이나 본문에 '상시'가 명시적으로 있으면 상시모집
  if (title.includes('상시') || raw.includes('상시모집')) {
    return '상시모집';
  }
  
  // 2. 이미 유형이 명확히 추출되었다면(기타 제외) 해당 유형 유지
  if (p.type && p.type !== '기타') {
    return p.type;
  }
  
  // 3. 날짜 정보가 아예 없는 경우에만 상시모집으로 취급
  if (!p.date && !p.time) {
    return '상시모집';
  }
  
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
  
  let targetStr = "";
  if (p.target_age && p.target_gender) {
    targetStr = `${p.target_age} ${p.target_gender}`;
  } else if (p.target_age) {
    targetStr = p.target_age;
  } else if (p.target_gender) {
    targetStr = p.target_gender;
  }
  
  if (targetStr) {
    keyInfoItems.push(`<div class="posting-card__info-row"><span class="posting-card__info-label">&#128100; 대상</span><span class="posting-card__info-value">${escapeHtml(targetStr)}</span></div>`);
  }

  if (p.location) {
    keyInfoItems.push(`<div class="posting-card__info-row"><span class="posting-card__info-label">&#128205; 장소</span><span class="posting-card__info-value">${escapeHtml(p.location)}</span></div>`);
  }
  
  // Secondary meta (empty now since we moved them up)
  const metaItems = [];
  
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
        <p>현재 열려있는 공고가 없습니다.</p>
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
  if (postingCount) postingCount.textContent = `${postings.length} : 오늘 아침5시 새롭게 추가된 공고`;
  
  // Count unique sources
  const sources = new Set(postings.map(p => p.source));
  if (statSources) statSources.textContent = sources.size;
}

// ── Update date header ──
function updateDateHeader() {
  const dateEl = document.getElementById('current-date');
  if (!dateEl) return;
  
  const now = new Date();
  const days = ['일', '월', '화', '수', '목', '금', '토'];
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const dayName = days[now.getDay()];
  
  dateEl.textContent = `${year}.${month}.${day} (${dayName})`;
}

// ── Date parsing for urgent sort ──
function parseDateScore(dateStr) {
  if (!dateStr) return Number.MAX_SAFE_INTEGER;
  // Check for formats like "4월 8일" or "4/8"
  let match = dateStr.match(/(\d{1,2})월\s*(\d{1,2})일/);
  if (!match) {
    match = dateStr.match(/(\d{1,2})\/(\d{1,2})/);
  }
  if (!match) return Number.MAX_SAFE_INTEGER;
  
  const m = parseInt(match[1], 10);
  const d = parseInt(match[2], 10);
  return m * 100 + d;
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
      } else if (filterType === 'urgent') {
        const withDates = allPostings.filter(p => p.date && parseDateScore(p.date) !== Number.MAX_SAFE_INTEGER);
        withDates.sort((a, b) => parseDateScore(a.date) - parseDateScore(b.date));
        renderPostings(withDates);
      } else if (filterType === '상시모집') {
        const filtered = allPostings.filter(p => getEffectiveType(p) === '상시모집');
        renderPostings(filtered);
      } else {
        const filtered = allPostings.filter(p => p.type === filterType && getEffectiveType(p) !== '상시모집');
        filtered.sort((a, b) => parseDateScore(a.date) - parseDateScore(b.date));
        renderPostings(filtered);
      }
    });
  });
}

// ── Update filter button counts ──
function updateFilterCounts() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  
  filterBtns.forEach(btn => {
    const filterType = btn.dataset.filter;
    let count = 0;
    
    if (filterType === 'all') {
      count = allPostings.length;
    } else if (filterType === 'urgent') {
      count = allPostings.filter(p => p.date && parseDateScore(p.date) !== Number.MAX_SAFE_INTEGER).length;
    } else if (filterType === '상시모집') {
      count = allPostings.filter(p => getEffectiveType(p) === '상시모집').length;
    } else {
      count = allPostings.filter(p => p.type === filterType && getEffectiveType(p) !== '상시모집').length;
    }
    
    // Remove existing count badge
    const existing = btn.querySelector('.filter-count');
    if (existing) existing.remove();
    
    // Add new count badge
    const badge = document.createElement('span');
    badge.className = 'filter-count';
    badge.textContent = count;
    btn.appendChild(badge);
  });
}

// ── Subscribe form ──
const WEB_APP_URL = "https://script.google.com/macros/s/AKfycbznThqYqKC9Ld6lN7R1uFtjTuuwe-CDfddqKJjKihVLFMrskUFF-5StdeYeHN5X2OVJ4A/exec";

function initSubscribeForm() {
  const forms = document.querySelectorAll('.subscribe-form');
  forms.forEach(form => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const emailInput = form.querySelector('input[type="email"]');
      if (!emailInput) return;
      const email = emailInput.value.trim();
      
      if (!email) return;
      
      const submitBtn = form.querySelector('button[type="submit"]');
      const originalText = submitBtn ? submitBtn.textContent : '';
      if (submitBtn) {
        submitBtn.textContent = '처리중...';
        submitBtn.disabled = true;
      }
      
      fetch(WEB_APP_URL, {
        method: 'POST',
        // Text/plain avoids CORS preflight OPTIONS request for simple cross-origin
        headers: { 'Content-Type': 'text/plain;charset=utf-8' },
        body: JSON.stringify({ email: email })
      })
      .then(response => {
        emailInput.value = '';
        alert('구독 신청이 완료되었습니다! 매일 아침 최신 알바 정보를 보내드릴게요.');
        if (submitBtn) {
          submitBtn.textContent = originalText;
          submitBtn.disabled = false;
        }
      })
      .catch(err => {
        // Apps Script sometimes triggers fake CORS errors on success, so we fallback
        emailInput.value = '';
        alert('구독 신청이 완료되었습니다! 매일 아침 최신 알바 정보를 보내드릴게요.');
        if (submitBtn) {
          submitBtn.textContent = originalText;
          submitBtn.disabled = false;
        }
      });
    });
  });

  // Handle header unsubscribe
  const headerUnsubBtns = document.querySelectorAll('.nav-unsubscribe-btn');
  headerUnsubBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const form = btn.closest('form');
      const emailInput = form.querySelector('input[type="email"]');
      if (!emailInput) return;
      
      const email = emailInput.value.trim();
      if (!email) {
        alert('구독 취소할 이메일 주소를 입력해주세요.');
        emailInput.focus();
        return;
      }
      
      let subscribers = JSON.parse(localStorage.getItem('mr_subscribers') || '[]');
      if (subscribers.includes(email)) {
        subscribers = subscribers.filter(sub => sub !== email);
        localStorage.setItem('mr_subscribers', JSON.stringify(subscribers));
        alert('구독이 성공적으로 취소되었습니다.');
      } else {
        alert('등록되지 않은 이메일입니다.');
      }
      emailInput.value = '';
    });
  });

  // Handle footer unsubscribe
  const footerUnsubBtns = document.querySelectorAll('.footer-unsubscribe-btn');
  footerUnsubBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const email = prompt('구독 취소할 이메일 주소를 입력해주세요:');
      if (!email) return;
      
      const trimmedEmail = email.trim();
      if (!trimmedEmail) return;
      
      let subscribers = JSON.parse(localStorage.getItem('mr_subscribers') || '[]');
      if (subscribers.includes(trimmedEmail)) {
        subscribers = subscribers.filter(sub => sub !== trimmedEmail);
        localStorage.setItem('mr_subscribers', JSON.stringify(subscribers));
        alert('구독이 성공적으로 취소되었습니다.');
      } else {
        alert('등록되지 않은 이메일입니다.');
      }
    });
  });
}

// ── Load data ──
async function loadPostings() {
  try {
    // Check if data is provided via data.js loaded in HTML
    if (window.postingsData) {
      allPostings = window.postingsData.postings || window.postingsData;
      
      // Default to urgent filter if available
      const urgentBtn = document.querySelector('[data-filter="urgent"]');
      if (urgentBtn) {
        urgentBtn.click();
      } else {
        renderPostings(allPostings);
      }
      
      updateStats(allPostings);
      updateFilterCounts();
    } else {
      // Fallback if data.json is used on an actual server
      const resp = await fetch('data.json');
      if (resp.ok) {
        const data = await resp.json();
        allPostings = data.postings || data;
        renderPostings(allPostings);
        updateStats(allPostings);
      updateFilterCounts();
      }
    }
  } catch (err) {
    console.log('No data found, using embedded data if available');
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
