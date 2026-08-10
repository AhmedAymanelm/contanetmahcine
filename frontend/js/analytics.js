// ── Analytics State ────────────────────────────────────────────────────────
let _anCharts = {};
let _anFilters = { days: 7, platform: '', type: '', source_id: '' };
let _anAutoRefreshTimer = null;
let _anGoalTodayPublished = 0;

function destroyAnCharts() {
  Object.values(_anCharts).forEach(c => { try { c.destroy(); } catch(e){} });
  _anCharts = {};
}

const PLATFORM_COLORS = {
  'Instagram':'#e1306c','Facebook':'#1877f2','LinkedIn':'#0a66c2',
  'X (Twitter)':'#1da1f2','TikTok':'#69c9d0','Threads':'#a855f7','Snapchat':'#fffc00',
};
const PLATFORM_ICONS = {
  'Instagram':'📸','Facebook':'👤','LinkedIn':'💼',
  'X (Twitter)':'🐦','TikTok':'🎵','Threads':'🧵','Snapchat':'👻',
};
const TYPE_LABELS = { POST:'بوست', CAROUSEL:'كاروسيل', VIDEO_SCRIPT:'سكريبت فيديو' };

function anColor(i, alpha=0.85) {
  const p=[
    `rgba(99,102,241,${alpha})`,`rgba(16,185,129,${alpha})`,
    `rgba(245,158,11,${alpha})`,`rgba(239,68,68,${alpha})`,
    `rgba(6,182,212,${alpha})`,`rgba(168,85,247,${alpha})`,
    `rgba(251,146,60,${alpha})`,`rgba(20,184,166,${alpha})`,
  ];
  return p[i%p.length];
}

const chartDefaults = {
  responsive:true, maintainAspectRatio:true,
  plugins:{ legend:{ labels:{ color:'#94a3b8', font:{ family:'Inter', size:12 }, boxWidth:14 } } },
  scales:{
    x:{ ticks:{ color:'#64748b', font:{ family:'Inter', size:11 } }, grid:{ color:'rgba(255,255,255,0.04)' } },
    y:{ ticks:{ color:'#64748b', font:{ family:'Inter', size:11 } }, grid:{ color:'rgba(255,255,255,0.04)' }, beginAtZero:true }
  }
};

// ── Filter helpers ─────────────────────────────────────────────────────────
function setAnFilter(key, val, btn) {
  _anFilters[key] = val;
  if (btn) {
    btn.closest('div').querySelectorAll('.an-filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }
  loadAnalytics();
}

function getAnFilterParams() {
  const p = new URLSearchParams();
  p.set('days', _anFilters.days);
  const platform = document.getElementById('an-filter-platform')?.value;
  const type     = document.getElementById('an-filter-type')?.value;
  const sourceId = document.getElementById('an-filter-source')?.value;
  if (platform) p.set('platform', platform);
  if (type)     p.set('content_type', type);
  if (sourceId) p.set('source_id', sourceId);
  return p.toString();
}

// ── Load sources for dropdown ──────────────────────────────────────────────
async function loadSourcesDropdown() {
  try {
    const token = localStorage.getItem('cm_token');
    const res = await fetch('/api/analytics/sources-list', {
      headers:{ 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) return;
    const sources = await res.json();
    const sel = document.getElementById('an-filter-source');
    if (!sel) return;
    sel.innerHTML = '<option value="">📡 كل المصادر</option>' +
      sources.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
  } catch(e) {}
}

// ── Main load ──────────────────────────────────────────────────────────────
async function loadAnalytics() {
  destroyAnCharts();
  const loadEl = document.getElementById('an-loading-state');
  const contentEl = document.getElementById('an-content');
  loadEl.style.display = 'flex';
  loadEl.innerHTML = '<span class="an-spin">⚙️</span><span>جاري تحميل البيانات...</span>';
  contentEl.style.display = 'none';

  try {
    const token = localStorage.getItem('cm_token');
    const res = await fetch(`/api/analytics/overview?${getAnFilterParams()}`, {
      headers:{ 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderAnalytics(data);
    loadEl.style.display = 'none';
    contentEl.style.display = 'block';
    setupAutoRefresh();
  } catch(e) {
    loadEl.innerHTML = `<span style="font-size:2rem;">😞</span><span style="color:#ef4444;">خطأ: ${e.message}</span>`;
  }
}

// ── Auto-refresh every 5 min ───────────────────────────────────────────────
function setupAutoRefresh() {
  if (_anAutoRefreshTimer) clearInterval(_anAutoRefreshTimer);
  _anAutoRefreshTimer = setInterval(() => {
    if (document.getElementById('page-analytics')?.classList.contains('active')) {
      loadAnalytics();
    }
  }, 5 * 60 * 1000);
}

// ── Export CSV ────────────────────────────────────────────────────────────
async function exportAnalyticsCSV() {
  const token = localStorage.getItem('cm_token');
  const days  = _anFilters.days;
  const a = document.createElement('a');
  a.href = `/api/analytics/export-csv?days=${days}`;
  // Add auth token as cookie-style isn't possible for <a> downloads easily,
  // so we fetch the blob manually
  const res = await fetch(`/api/analytics/export-csv?days=${days}`, {
    headers:{ 'Authorization': `Bearer ${token}` }
  });
  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  a.href = url;
  a.download = `content_machine_${days}d.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Goal Tracker ──────────────────────────────────────────────────────────
function updateGoalTracker() {
  const goal = parseInt(document.getElementById('an-goal-input')?.value || '5');
  const today = _anGoalTodayPublished;
  const pct   = Math.min(Math.round(today / goal * 100), 100);
  const bar   = document.getElementById('an-goal-bar');
  const label = document.getElementById('an-goal-pct-label');
  const detail= document.getElementById('an-goal-detail');
  if (bar)    bar.style.width = pct + '%';
  if (label)  label.textContent = pct + '%';
  if (detail) {
    if (pct >= 100) detail.textContent = `🎉 حققت هدفك! ${today}/${goal} منشور`;
    else            detail.textContent = `${today} من ${goal} منشور مطلوب اليوم`;
  }
}

// ── Render All ────────────────────────────────────────────────────────────
function renderAnalytics(data) {
  const { scraping, pipeline, platforms, content_types, trends,
          top_sources, top_content, top_performer, funnel,
          peak_hours, peak_days } = data;

  // ── Top Performer ──────────────────────────────────────────────────────
  const tpName  = document.getElementById('an-tp-name');
  const tpCount = document.getElementById('an-tp-count');
  if (top_performer && top_performer.name) {
    if (tpName)  tpName.textContent  = top_performer.name;
    if (tpCount) tpCount.textContent = `${top_performer.count} محتوى منشور`;
  } else {
    if (tpName)  tpName.textContent  = '—';
    if (tpCount) tpCount.textContent = 'لا يوجد بيانات';
  }

  // ── Week Comparison ────────────────────────────────────────────────────
  const cur  = pipeline.published;
  const prev = pipeline.prev_published || 0;
  const curEl   = document.getElementById('an-cur-pub');
  const prevEl  = document.getElementById('an-prev-pub');
  const arrowEl = document.getElementById('an-trend-arrow');
  const trendLbl= document.getElementById('an-trend-label');
  if (curEl)  curEl.textContent  = cur;
  if (prevEl) prevEl.textContent = prev;
  if (arrowEl) {
    if (cur > prev) { arrowEl.textContent='📈'; arrowEl.style.color='#34d399'; }
    else if (cur < prev) { arrowEl.textContent='📉'; arrowEl.style.color='#ef4444'; }
    else { arrowEl.textContent='→'; arrowEl.style.color='#94a3b8'; }
  }
  if (trendLbl) {
    const diff = cur - prev;
    trendLbl.textContent = diff === 0 ? 'نفس الأداء' :
      (diff > 0 ? `⬆️ +${diff} أكثر من الفترة السابقة` : `⬇️ ${diff} أقل من الفترة السابقة`);
    trendLbl.style.color = diff >= 0 ? '#34d399' : '#ef4444';
  }

  // ── Goal Tracker (today's published) ─────────────────────────────────
  _anGoalTodayPublished = cur;
  updateGoalTracker();

  // ── KPI Cards ─────────────────────────────────────────────────────────
  const kpis = [
    { icon:'📰', val:scraping.total_scraped,  label:'أخبار مسحوبة',   sub:`${scraping.scraped_7d} آخر 7 أيام`, color:'#6366f1' },
    { icon:'📡', val:scraping.active_sources, label:'مصادر نشطة',     sub:`من ${scraping.total_sources}`,       color:'#06b6d4' },
    { icon:'✅', val:pipeline.published,       label:'منشور',           sub:`من ${pipeline.total_content} محتوى`, color:'#10b981' },
    { icon:'📅', val:pipeline.scheduled,       label:'مجدول',           sub:'في انتظار النشر',                    color:'#8b5cf6' },
    { icon:'⏳', val:pipeline.pending_review,  label:'قيد المراجعة',   sub:'',                                   color:'#f59e0b' },
    { icon:'💯', val:`${pipeline.approval_rate}%`, label:'معدل الاعتماد',sub:'',                                color:'#ec4899' },
    { icon:'🚫', val:pipeline.rejected,        label:'مرفوض',           sub:'',                                   color:'#ef4444' },
    { icon:'📝', val:pipeline.draft,           label:'مسودة',           sub:'',                                   color:'#64748b' },
  ];
  document.getElementById('an-kpis').innerHTML = kpis.map(k => `
    <div class="an-kpi" style="--kpi-color:${k.color}">
      <span class="kpi-icon">${k.icon}</span>
      <div class="kpi-val">${k.val}</div>
      <div class="kpi-label">${k.label}</div>
      ${k.sub ? `<div class="kpi-sub">${k.sub}</div>` : ''}
    </div>`).join('');

  // ── Scrape Trend ───────────────────────────────────────────────────────
  _anCharts.scrape = new Chart(document.getElementById('chart-scrape-trend'), {
    type:'line',
    data:{ labels:trends.daily_scrape.map(d=>d.date), datasets:[{
      label:'أخبار مسحوبة', data:trends.daily_scrape.map(d=>d.articles),
      borderColor:'#6366f1', backgroundColor:'rgba(99,102,241,0.12)',
      tension:0.4, fill:true, pointRadius:4, pointBackgroundColor:'#6366f1',
    }]},
    options:{...chartDefaults}
  });

  // ── Content Trend ──────────────────────────────────────────────────────
  _anCharts.contentTrend = new Chart(document.getElementById('chart-content-trend'), {
    type:'line',
    data:{ labels:trends.daily_content.map(d=>d.date), datasets:[{
      label:'محتوى مُنشأ', data:trends.daily_content.map(d=>d.content),
      borderColor:'#10b981', backgroundColor:'rgba(16,185,129,0.12)',
      tension:0.4, fill:true, pointRadius:4, pointBackgroundColor:'#10b981',
    }]},
    options:{...chartDefaults}
  });

  // ── Platform Bar ───────────────────────────────────────────────────────
  const pubPlat = platforms.published_per_platform;
  const platL   = Object.keys(pubPlat);
  const platV   = Object.values(pubPlat);
  _anCharts.platforms = new Chart(document.getElementById('chart-platforms'), {
    type:'bar',
    data:{ labels:platL.map(l=>`${PLATFORM_ICONS[l]||'🌐'} ${l}`), datasets:[{
      label:'بوستات منشورة', data:platV,
      backgroundColor:platL.map(l=>PLATFORM_COLORS[l]||'#6366f1'),
      borderRadius:8, borderSkipped:false,
    }]},
    options:{...chartDefaults, plugins:{...chartDefaults.plugins, legend:{display:false}},
             indexAxis: platV.length > 4 ? 'y' : 'x'}
  });

  // ── Content Type Doughnut ─────────────────────────────────────────────
  const typeL = content_types.map(d=>d.type);
  const typeV = content_types.map(d=>d.count);
  _anCharts.types = new Chart(document.getElementById('chart-types'), {
    type:'doughnut',
    data:{ labels:typeL, datasets:[{
      data:typeV, backgroundColor:typeL.map((_,i)=>anColor(i)),
      borderWidth:2, borderColor:'#0d0f1a'
    }]},
    options:{ responsive:true, maintainAspectRatio:true, cutout:'65%',
      plugins:{ legend:{ position:'bottom', labels:{ color:'#94a3b8', font:{size:12}, boxWidth:14 } } } }
  });

  // ── Pipeline Doughnut ─────────────────────────────────────────────────
  const pipeKeys   = ['published','scheduled','pending_review','approved','draft','rejected'];
  const pipeLabelM = {published:'منشور',scheduled:'مجدول',pending_review:'قيد المراجعة',approved:'معتمد',draft:'مسودة',rejected:'مرفوض'};
  const pipeColorM = ['#10b981','#8b5cf6','#f59e0b','#06b6d4','#64748b','#ef4444'];
  const pipeV = pipeKeys.map((k,i)=>({v:pipeline[k]||0,l:pipeLabelM[k],c:pipeColorM[i]})).filter(x=>x.v>0);
  _anCharts.pipeline = new Chart(document.getElementById('chart-pipeline'), {
    type:'doughnut',
    data:{ labels:pipeV.map(x=>x.l), datasets:[{
      data:pipeV.map(x=>x.v), backgroundColor:pipeV.map(x=>x.c),
      borderWidth:2, borderColor:'#0d0f1a'
    }]},
    options:{ responsive:true, maintainAspectRatio:true, cutout:'65%',
      plugins:{ legend:{ position:'bottom', labels:{ color:'#94a3b8', font:{size:12}, boxWidth:14 } } } }
  });

  // ── Approval Funnel (visual bars) ──────────────────────────────────────
  const funnelEl = document.getElementById('an-funnel');
  const maxV = Math.max(...(funnel||[]).map(f=>f.value), 1);
  if (funnelEl && funnel) {
    const fColors = ['#6366f1','#06b6d4','#f59e0b','#10b981','#34d399'];
    funnelEl.innerHTML = funnel.map((f, i) => {
      const pct = Math.round(f.value / maxV * 100);
      return `
        <div style="margin-bottom:10px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span style="font-size:0.82rem; color:#94a3b8;">${f.label}</span>
            <span style="font-size:0.82rem; font-weight:700; color:${fColors[i]};">${f.value.toLocaleString()}</span>
          </div>
          <div style="background:rgba(255,255,255,0.06); border-radius:999px; height:8px; overflow:hidden;">
            <div style="height:100%; width:${pct}%; background:${fColors[i]}; border-radius:999px; transition:width 1s ease;"></div>
          </div>
        </div>`;
    }).join('');
  }

  // ── Peak Hours Bar ────────────────────────────────────────────────────
  const hourLabels = peak_hours.map(h => h.hour + ':00');
  const hourVals   = peak_hours.map(h => h.count);
  _anCharts.peakHours = new Chart(document.getElementById('chart-peak-hours'), {
    type:'bar',
    data:{ labels:hourLabels, datasets:[{
      label:'منشورات', data:hourVals,
      backgroundColor: hourVals.map(v =>
        v === Math.max(...hourVals) ? 'rgba(245,158,11,0.9)' : 'rgba(99,102,241,0.5)'
      ),
      borderRadius:4, borderSkipped:false,
    }]},
    options:{...chartDefaults, plugins:{...chartDefaults.plugins, legend:{display:false}}}
  });

  // ── Top Sources Bar ────────────────────────────────────────────────────
  _anCharts.sources = new Chart(document.getElementById('chart-sources'), {
    type:'bar',
    data:{ labels:top_sources.map(s=>s.source), datasets:[{
      label:'أخبار', data:top_sources.map(s=>s.articles),
      backgroundColor:top_sources.map((_,i)=>anColor(i,0.75)),
      borderRadius:6, borderSkipped:false,
    }]},
    options:{...chartDefaults, indexAxis:'y',
             plugins:{...chartDefaults.plugins, legend:{display:false}}}
  });

  // ── Top Content Table ──────────────────────────────────────────────────
  const tbody = document.getElementById('an-top-tbody');
  if (!top_content.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#64748b; padding:30px;">لا يوجد محتوى منشور في هذه الفترة</td></tr>';
  } else {
    tbody.innerHTML = top_content.map((item, idx) => {
      const tc       = (item.type||'').toUpperCase().replace(' ','_');
      const typeLbl  = TYPE_LABELS[tc] || item.type || '-';
      const platBadges = (item.platforms||[]).map(p =>
        `<span class="an-platform-pill">${PLATFORM_ICONS[p]||'🌐'} ${p}</span>`
      ).join('');
      const date = item.published_at ? new Date(item.published_at).toLocaleDateString('ar-EG') : '-';
      return `<tr>
        <td style="color:#64748b; font-size:.8rem;">${idx+1}</td>
        <td style="max-width:220px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${item.title}</td>
        <td style="color:#94a3b8; font-size:.8rem; white-space:nowrap;">${item.source||'—'}</td>
        <td><span class="an-badge ${tc}">${typeLbl}</span></td>
        <td>${platBadges}</td>
        <td style="color:#64748b; font-size:.82rem; white-space:nowrap;">${date}</td>
      </tr>`;
    }).join('');
  }
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadSourcesDropdown();

  // Add filter-btn styles
  const style = document.createElement('style');
  style.textContent = `
    .an-filter-btn {
      background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1);
      color:#94a3b8; padding:6px 14px; border-radius:8px; font-size:0.82rem;
      cursor:pointer; transition:.2s; font-family:inherit;
    }
    .an-filter-btn:hover { background:rgba(255,255,255,0.1); color:#e2e8f0; }
    .an-filter-btn.active { background:rgba(99,102,241,.25); border-color:rgba(99,102,241,.5); color:#818cf8; font-weight:700; }
    @media(max-width:800px){ #an-hero-row{ grid-template-columns:1fr 1fr !important; } }
    @media(max-width:580px){ #an-hero-row{ grid-template-columns:1fr !important; } }
  `;
  document.head.appendChild(style);
});

// ── Engagement Leaderboard ─────────────────────────────────────────────────
async function loadEngagement() {
  const loadEl  = document.getElementById('an-engagement-loading');
  const listEl  = document.getElementById('an-engagement-list');
  const emptyEl = document.getElementById('an-engagement-empty');
  const winCard = document.getElementById('an-winner-card');

  if (loadEl)  { loadEl.style.display = 'block'; }
  if (listEl)  { listEl.style.display = 'none'; }
  if (emptyEl) { emptyEl.style.display = 'none'; }
  if (winCard) { winCard.style.display = 'none'; }

  try {
    const token = localStorage.getItem('cm_token');
    const res = await fetch('/api/analytics/top-engagement', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (loadEl) loadEl.style.display = 'none';

    const { top_post, all_posts, platform_summary } = data;

    if (!all_posts || all_posts.length === 0) {
      if (emptyEl) emptyEl.style.display = 'block';
      return;
    }

    // ── Winner card ────────────────────────────────────────────────────────
    if (top_post && winCard) {
      winCard.style.display = 'block';

      // Thumbnail
      const thumbWrap = document.getElementById('an-winner-thumb-wrap');
      if (thumbWrap) {
        thumbWrap.innerHTML = top_post.thumbnail
          ? `<img src="${top_post.thumbnail}" alt="صورة البوست"
               style="width:90px; height:90px; object-fit:cover; border-radius:12px; border:2px solid rgba(245,158,11,.4);"
               onerror="this.style.display='none'">`
          : `<div style="width:90px; height:90px; border-radius:12px; background:rgba(245,158,11,.1); display:flex; align-items:center; justify-content:center; font-size:2rem; border:2px solid rgba(245,158,11,.2);">
               ${PLATFORM_ICONS[top_post.platform] || '📄'}
             </div>`;
      }

      // Platform + date
      const plEl = document.getElementById('an-winner-platform');
      if (plEl) plEl.innerHTML = `<span class="an-platform-pill">${PLATFORM_ICONS[top_post.platform]||'🌐'} ${top_post.platform}</span>`;

      const dateEl = document.getElementById('an-winner-date');
      if (dateEl && top_post.timestamp) {
        dateEl.textContent = new Date(top_post.timestamp).toLocaleDateString('ar-EG', { year:'numeric', month:'long', day:'numeric' });
      }

      // Caption
      const capEl = document.getElementById('an-winner-caption');
      if (capEl) capEl.textContent = top_post.caption || '(بدون نص)';

      // Stats
      document.getElementById('an-winner-likes').textContent    = `❤️ ${top_post.likes.toLocaleString()} لايك`;
      document.getElementById('an-winner-comments').textContent = `💬 ${top_post.comments.toLocaleString()} تعليق`;
      document.getElementById('an-winner-total').textContent    = `⚡ ${top_post.total.toLocaleString()} إجمالي`;

      const linkEl = document.getElementById('an-winner-link');
      if (linkEl) {
        if (top_post.permalink) { linkEl.href = top_post.permalink; linkEl.style.display = ''; }
        else { linkEl.style.display = 'none'; }
      }
    }

    // ── Platform summary pills ────────────────────────────────────────────
    const pillsEl = document.getElementById('an-platform-pills');
    if (pillsEl && platform_summary) {
      pillsEl.innerHTML = Object.entries(platform_summary).map(([pl, s]) => `
        <div style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:12px; padding:10px 16px; min-width:140px;">
          <div style="font-size:0.78rem; color:#94a3b8; margin-bottom:6px;">${PLATFORM_ICONS[pl]||'🌐'} ${pl}</div>
          <div style="font-size:0.82rem; color:#e2e8f0;">${s.posts} بوست</div>
          <div style="display:flex; gap:10px; margin-top:4px;">
            <span style="font-size:0.8rem; color:#f87171;">❤️ ${s.total_likes.toLocaleString()}</span>
            <span style="font-size:0.8rem; color:#60a5fa;">💬 ${s.total_comments.toLocaleString()}</span>
          </div>
        </div>`).join('');
    }

    // ── Ranked post list ───────────────────────────────────────────────────
    const postsEl = document.getElementById('an-posts-list');
    const maxTotal = all_posts[0]?.total || 1;
    if (postsEl) {
      postsEl.innerHTML = all_posts.map((p, idx) => {
        const barW  = Math.round(p.total / maxTotal * 100);
        const medal = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `#${idx+1}`;
        const platColor = {
          Instagram:'rgba(225,48,108,.2)', Facebook:'rgba(24,119,242,.2)',
          LinkedIn:'rgba(10,102,194,.2)',  'X (Twitter)':'rgba(29,161,242,.2)',
          TikTok:'rgba(105,201,208,.2)',
        }[p.platform] || 'rgba(255,255,255,0.05)';

        return `
          <div style="background:${platColor}; border:1px solid rgba(255,255,255,0.07); border-radius:12px; padding:14px 16px; transition:.2s;"
               onmouseover="this.style.transform='translateX(-2px)'" onmouseout="this.style.transform=''">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
              <span style="font-size:1rem; min-width:28px; text-align:center;">${medal}</span>
              <span class="an-platform-pill">${PLATFORM_ICONS[p.platform]||'🌐'} ${p.platform}</span>
              <span style="flex:1; font-size:0.87rem; color:#e2e8f0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${p.caption || '(بدون نص)'}</span>
              <div style="display:flex; gap:12px; flex-shrink:0;">
                <span style="font-size:0.85rem; color:#f87171; font-weight:700;">❤️ ${p.likes.toLocaleString()}</span>
                <span style="font-size:0.85rem; color:#60a5fa; font-weight:700;">💬 ${p.comments.toLocaleString()}</span>
                ${p.permalink ? `<a href="${p.permalink}" target="_blank" style="font-size:0.8rem; color:#818cf8; text-decoration:none;">🔗</a>` : ''}
              </div>
            </div>
            <div style="background:rgba(255,255,255,0.06); border-radius:999px; height:5px; overflow:hidden;">
              <div style="height:100%; width:${barW}%; background:linear-gradient(90deg,#f59e0b,#ef4444); border-radius:999px; transition:width 1s ease;"></div>
            </div>
          </div>`;
      }).join('');
    }

    if (listEl) listEl.style.display = 'block';

  } catch(e) {
    if (loadEl) loadEl.innerHTML = `<span style="color:#ef4444;">❌ خطأ: ${e.message}</span>`;
  }
}