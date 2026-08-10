// ═══════════════════════════ RECOMMENDATIONS ═══════════════════════════════
let _recsCharts = {};

function destroyRecsCharts() {
  Object.values(_recsCharts).forEach(c => { try { c.destroy(); } catch(e){} });
  _recsCharts = {};
}

async function loadRecs() {
  destroyRecsCharts();
  const loadEl    = document.getElementById('recs-loading');
  const contentEl = document.getElementById('recs-content');
  loadEl.style.display   = 'flex';
  loadEl.innerHTML = '<span class="an-spin">💡</span><span>جاري تحليل البيانات...</span>';
  contentEl.style.display = 'none';

  try {
    const token = localStorage.getItem('cm_token');
    const res = await fetch('/api/recommendations/overview', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    renderRecs(data);
    loadEl.style.display   = 'none';
    contentEl.style.display = 'block';
  } catch(e) {
    loadEl.innerHTML = `<span style="font-size:2rem;">😞</span><span style="color:#ef4444;">خطأ: ${e.message}</span>`;
  }
}

function renderRecs(data) {
  const { alerts, platform_strategy, best_posting_time, hours_dist, days_dist, source_scores, suggested_articles } = data;

  // ── Smart Alerts ──────────────────────────────────────────────────────
  const alertColors = { warning:'rgba(245,158,11,.12)', danger:'rgba(239,68,68,.12)', info:'rgba(99,102,241,.1)' };
  const alertBorder = { warning:'rgba(245,158,11,.35)', danger:'rgba(239,68,68,.35)', info:'rgba(99,102,241,.3)' };
  const alertText   = { warning:'#fbbf24', danger:'#f87171', info:'#818cf8' };
  const alertsEl = document.getElementById('recs-alerts');
  if (alertsEl) {
    if (!alerts.length) {
      alertsEl.innerHTML = `<div style="background:rgba(16,185,129,.1); border:1px solid rgba(16,185,129,.3); border-radius:12px; padding:14px 18px; color:#34d399; font-size:0.9rem;">✅ كل شيء يعمل بشكل ممتاز — لا توجد تنبيهات حالياً!</div>`;
    } else {
      alertsEl.innerHTML = alerts.map(a => `
        <div style="background:${alertColors[a.type]||alertColors.info}; border:1px solid ${alertBorder[a.type]||alertBorder.info}; border-radius:12px; padding:14px 18px; margin-bottom:10px; display:flex; gap:12px; align-items:flex-start;">
          <span style="font-size:1.4rem; flex-shrink:0;">${a.icon}</span>
          <div>
            <div style="font-weight:700; color:${alertText[a.type]||alertText.info}; margin-bottom:4px;">${a.title}</div>
            <div style="font-size:0.85rem; color:#94a3b8;">${a.body}</div>
          </div>
        </div>`).join('');
    }
  }

  // ── Platform Strategy ──────────────────────────────────────────────────
  const platEl = document.getElementById('recs-platform-list');
  if (platEl && platform_strategy.length) {
    const maxEng = Math.max(...platform_strategy.map(p => p.eng_per_post), 1);
    platEl.innerHTML = platform_strategy.map(p => {
      const barW = Math.round(p.eng_per_post / maxEng * 100);
      const clr  = PLATFORM_COLORS[p.platform] || '#6366f1';
      return `
        <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:12px; padding:16px;">
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px; flex-wrap:wrap;">
            <span class="an-platform-pill">${PLATFORM_ICONS[p.platform]||'🌐'} ${p.platform}</span>
            <span style="font-size:0.85rem; color:#e2e8f0;">${p.posts} بوست</span>
            <span style="font-size:0.85rem; color:#94a3b8;">•</span>
            <span style="font-size:0.85rem; color:${clr};">⚡ ${p.eng_per_post} تفاعل/بوست</span>
            <span style="font-size:0.82rem; color:#94a3b8; margin-right:auto;">${p.strategy}</span>
          </div>
          <div style="background:rgba(255,255,255,0.06); border-radius:999px; height:6px; overflow:hidden;">
            <div style="height:100%; width:${barW}%; background:${clr}; border-radius:999px; transition:width 1s;"></div>
          </div>
        </div>`;
    }).join('');
  } else if (platEl) {
    platEl.innerHTML = '<div style="color:#64748b; padding:20px; text-align:center;">لا توجد بيانات منصات بعد</div>';
  }

  // ── Days Chart ──────────────────────────────────────────────────────────
  if (days_dist && days_dist.length) {
    const maxDay = Math.max(...days_dist.map(d => d.count), 1);
    _recsCharts.days = new Chart(document.getElementById('recs-days-chart'), {
      type: 'bar',
      data: {
        labels: days_dist.map(d => d.day),
        datasets: [{
          label: 'بوستات',
          data: days_dist.map(d => d.count),
          backgroundColor: days_dist.map(d =>
            d.count === maxDay ? 'rgba(16,185,129,0.85)' : 'rgba(99,102,241,0.45)'
          ),
          borderRadius: 6, borderSkipped: false,
        }]
      },
      options: { ...chartDefaults, plugins: { ...chartDefaults.plugins, legend: { display: false } } }
    });
    const bestDayEl = document.getElementById('recs-best-day');
    if (bestDayEl && best_posting_time) {
      bestDayEl.innerHTML = `<span style="color:#34d399; font-weight:700;">📅 أفضل يوم: ${best_posting_time.day}</span> — ${best_posting_time.posts_at_peak} بوستات`;
    }
  }

  // ── Hours Chart ─────────────────────────────────────────────────────────
  if (hours_dist && hours_dist.length) {
    const maxHour = Math.max(...hours_dist.map(h => h.count), 1);
    _recsCharts.hours = new Chart(document.getElementById('recs-hours-chart'), {
      type: 'bar',
      data: {
        labels: hours_dist.map(h => h.hour + ':00'),
        datasets: [{
          label: 'بوستات',
          data: hours_dist.map(h => h.count),
          backgroundColor: hours_dist.map(h =>
            h.count === maxHour ? 'rgba(245,158,11,0.9)' : 'rgba(99,102,241,0.4)'
          ),
          borderRadius: 4, borderSkipped: false,
        }]
      },
      options: { ...chartDefaults, plugins: { ...chartDefaults.plugins, legend: { display: false } } }
    });
    const bestHourEl = document.getElementById('recs-best-hour');
    if (bestHourEl && best_posting_time) {
      bestHourEl.innerHTML = `<span style="color:#fbbf24; font-weight:700;">⏰ أفضل وقت: ${best_posting_time.hour}:00</span>`;
    }
  }

  // ── Source Scores ──────────────────────────────────────────────────────
  const srcEl = document.getElementById('recs-source-list');
  if (srcEl && source_scores.length) {
    srcEl.innerHTML = source_scores.map((s, idx) => {
      const scoreColor = s.score >= 70 ? '#10b981' : s.score >= 40 ? '#f59e0b' : '#ef4444';
      const scoreLabel = s.score >= 70 ? '🟢 ممتاز' : s.score >= 40 ? '🟡 جيد' : '🔴 ضعيف';
      const medal = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `#${idx+1}`;
      return `
        <div style="background:rgba(255,255,255,0.03); border:1px solid ${s.is_silent ? 'rgba(239,68,68,.35)' : 'rgba(255,255,255,0.07)'}; border-radius:12px; padding:14px 16px;">
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px; flex-wrap:wrap;">
            <span style="font-size:1rem; min-width:24px;">${medal}</span>
            <span style="font-size:0.9rem; font-weight:700; color:#e2e8f0; flex:1;">${s.name}</span>
            ${s.is_silent ? '<span style="font-size:0.72rem; background:rgba(239,68,68,.15); color:#f87171; padding:2px 8px; border-radius:999px;">📡 صامت</span>' : ''}
            ${!s.is_active ? '<span style="font-size:0.72rem; background:rgba(100,116,139,.15); color:#64748b; padding:2px 8px; border-radius:999px;">موقوف</span>' : ''}
            <span style="font-size:0.72rem; color:${scoreColor}; font-weight:700;">${scoreLabel}</span>
            <span style="font-size:1.1rem; font-weight:900; color:${scoreColor};">${s.score}</span>
          </div>
          <div style="display:flex; gap:16px; font-size:0.78rem; color:#64748b; margin-bottom:8px; flex-wrap:wrap;">
            <span>📰 ${s.total_scraped} خبر</span>
            <span>📝 ${s.total_content} محتوى</span>
            <span>✅ ${s.published_content} منشور</span>
            <span>📊 نسبة نشر ${s.publish_rate}%</span>
          </div>
          <div style="background:rgba(255,255,255,0.06); border-radius:999px; height:5px; overflow:hidden;">
            <div style="height:100%; width:${s.score}%; background:${scoreColor}; border-radius:999px; transition:width 1s;"></div>
          </div>
        </div>`;
    }).join('');
  } else if (srcEl) {
    srcEl.innerHTML = '<div style="color:#64748b; padding:20px; text-align:center;">لا توجد مصادر</div>';
  }

  // ── Suggested Articles ──────────────────────────────────────────────────
  const sugEl = document.getElementById('recs-suggested');
  if (sugEl && suggested_articles.length) {
    sugEl.innerHTML = suggested_articles.map((art, idx) => `
      <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:12px; padding:14px 16px; display:flex; align-items:flex-start; gap:12px; transition:.2s;"
           onmouseover="this.style.borderColor='rgba(16,185,129,.3)'" onmouseout="this.style.borderColor='rgba(255,255,255,0.07)'">
        <span style="font-size:1.1rem; flex-shrink:0; color:#64748b;">${idx+1}</span>
        <div style="flex:1; min-width:0;">
          <div style="font-size:0.88rem; color:#e2e8f0; margin-bottom:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${art.title}</div>
          <div style="display:flex; gap:10px; align-items:center; font-size:0.75rem; color:#64748b;">
            <span>📡 ${art.source}</span>
            <span>•</span>
            <span>${art.scraped_at ? new Date(art.scraped_at).toLocaleDateString('ar-EG') : '-'}</span>
            ${art.url ? `<a href="${art.url}" target="_blank" style="color:#818cf8; text-decoration:none; margin-right:auto;">🔗 قراءة</a>` : ''}
          </div>
        </div>
      </div>`).join('');
  } else if (sugEl) {
    sugEl.innerHTML = '<div style="color:#64748b; padding:20px; text-align:center;">لا توجد أخبار جديدة مقترحة</div>';
  }
}

// ── AI Summary ──────────────────────────────────────────────────────────────
async function loadAISummary() {
  const btn  = document.getElementById('btn-ai-summary');
  const body = document.getElementById('ai-summary-body');
  if (!body) return;
  if (btn) { btn.disabled = true; btn.textContent = '⏳ جاري التحليل...'; }
  body.innerHTML = '<div style="color:#64748b; animation:pulse 1s infinite;">🤖 Claude يحلل أداءك الأسبوعي...</div>';
  try {
    const token = localStorage.getItem('cm_token');
    const res = await fetch('/api/recommendations/ai-summary', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    body.innerHTML = `<div style="color:#e2e8f0; white-space:pre-wrap; font-size:0.88rem; line-height:1.8;">${data.summary}</div>
      <div style="font-size:0.72rem; color:#64748b; margin-top:10px;">🕐 ${new Date(data.generated_at).toLocaleString('ar-EG')}</div>`;
  } catch(e) {
    body.innerHTML = `<span style="color:#ef4444;">❌ ${e.message}</span>`;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '✨ اطلب التحليل'; }
  }
}

// ── Content Ideas ────────────────────────────────────────────────────────────
async function loadContentIdeas() {
  const btn  = document.getElementById('btn-content-ideas');
  const body = document.getElementById('content-ideas-body');
  if (!body) return;
  if (btn) { btn.disabled = true; btn.textContent = '⏳ جاري التوليد...'; }
  body.innerHTML = '<div style="color:#64748b; animation:pulse 1s infinite;">💡 Claude يولّد أفكار بناءً على أحدث الأخبار...</div>';
  try {
    const token = localStorage.getItem('cm_token');
    const res = await fetch('/api/recommendations/content-ideas', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    body.innerHTML = `<div style="color:#e2e8f0; white-space:pre-wrap; font-size:0.88rem; line-height:1.8;">${data.ideas}</div>
      <div style="font-size:0.72rem; color:#64748b; margin-top:10px;">🕐 ${new Date(data.generated_at).toLocaleString('ar-EG')}</div>`;
  } catch(e) {
    body.innerHTML = `<span style="color:#ef4444;">❌ ${e.message}</span>`;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '✨ ولّد أفكار'; }
  }
}