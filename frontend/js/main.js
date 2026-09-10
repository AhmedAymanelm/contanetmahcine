const API_BASE = '/api';

// Route external images through backend proxy to bypass hotlink protection
function imgProxy(url) {
    if (!url) return '';
    // Static files served directly — no proxy needed
    if (url.startsWith('/static/') || url.startsWith(window.location.origin)) return url;
    return `${API_BASE}/img-proxy?url=${encodeURIComponent(url)}`;
}


// ════════════════════════════════════════════════
// DARK / LIGHT THEME
// ════════════════════════════════════════════════
(function initTheme() {
    const saved = localStorage.getItem('cm_theme') || 'dark';
    applyTheme(saved);
})();

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('cm_theme', theme);
    const icon  = document.getElementById('theme-icon');
    const label = document.getElementById('theme-label');
    if (icon)  icon.textContent  = theme === 'light' ? '☀️' : '🌙';
    if (label) label.textContent = theme === 'light' ? 'الوضع النهاري' : 'الوضع الليلي';
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    applyTheme(current === 'dark' ? 'light' : 'dark');
}

// Custom Toast Notification System
window.showToast = function(message, type = 'success') {
    const existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.innerHTML = message;
    
    document.body.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Auto remove
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
};

// ── Page map: which pages need auto-load on activation ──────────────────────
const PAGE_LOADERS = {
    'page-trends':    () => {},
    'page-analytics': () => { loadAnalytics(); loadEngagement(); },
    'page-recs':      () => loadRecs(),
};

// ── Navigate to a page ────────────────────────────────────────────────────
function go(element) {
    document.querySelectorAll('nav a').forEach(el => el.classList.remove('active'));
    element.classList.add('active');

    document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));
    const targetId = element.getAttribute('data-page');
    if (!targetId) return;

    const targetPage = document.getElementById(targetId);
    if (targetPage) {
        targetPage.classList.add('active');
        history.replaceState(null, '', '#' + targetId);
        if (PAGE_LOADERS[targetId]) PAGE_LOADERS[targetId]();
    }
    // Close sidebar on mobile after navigation
    closeSidebar();
}

// ── Mobile Sidebar Toggle ──────────────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.getElementById('main-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const isOpen  = sidebar.classList.toggle('open');
    overlay.classList.toggle('active', isOpen);
    document.body.style.overflow = isOpen ? 'hidden' : '';
    document.documentElement.style.overflow = isOpen ? 'hidden' : '';
}

function closeSidebar() {
    const sidebar = document.getElementById('main-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
}

function goId(pageId) {
    const link = document.querySelector(`nav a[data-page="${pageId}"]`);
    if (link) go(link);
}

// ── Restore page on refresh via hash ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const hash = window.location.hash.replace('#', '') || 'page-dashboard';
    const link = document.querySelector(`nav a[data-page="${hash}"]`);
    if (link) {
        go(link);
    } else {
        // fallback to dashboard
        const dash = document.querySelector('nav a[data-page="page-dashboard"]');
        if (dash) go(dash);
    }
});


// ---------------- API Fetching ----------------

async function fetchDashboardStats() {
    try {
        const res = await fetch(`${API_BASE}/stats/`);
        if (!res.ok) throw new Error('Failed to fetch stats');
        const data = await res.json();
        
        // Update stats blocks
        document.getElementById('stat-articles').innerText = data.stats.articles_today;
        document.getElementById('stat-pending').innerText = data.stats.pending_reviews;
        document.getElementById('stat-approved').innerText = data.stats.approval_rate;
        document.getElementById('stat-scheduled').innerText = data.stats.scheduled;

        document.getElementById('stat-articles-sub').innerText = 'تم التحديث للتو';
        document.getElementById('stat-pending-sub').innerText = data.stats.pending_reviews > 0 ? 'يتطلب إجراء' : 'لا يوجد مهام';
        document.getElementById('stat-approved-sub').innerText = 'معدل الموافقة الكلي';
        document.getElementById('stat-scheduled-sub').innerText = 'جاهز للنشر';

        // Update Sidebar Counts
        document.getElementById('sidebar-count-sources').innerText = data.sidebar_counts.sources;
        document.getElementById('sidebar-count-raw').innerText = data.sidebar_counts.raw_articles;
        document.getElementById('sidebar-count-content').innerText = data.sidebar_counts.content;
        document.getElementById('sidebar-count-review').innerText = data.sidebar_counts.review;

        // Update Last Ingestion Time
        const timeEl = document.getElementById('last-ingestion-time');
        if (timeEl) {
            const todayStr = new Date().toLocaleDateString('ar-AE', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', timeZone: 'Asia/Dubai' });
            let ingestStr = 'لم يتم السحب بعد';
            if (data.stats.last_ingestion_time) {
                const ingestDate = new Date(data.stats.last_ingestion_time);
                ingestStr = ingestDate.toLocaleTimeString('ar-AE', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Dubai' });
            }
            timeEl.innerText = `${todayStr} — آخر عملية سحب أخبار: ${ingestStr}`;
        }

        // Update Pipeline Counts

        document.getElementById('pipeline-count-raw').innerText = data.pipeline_counts.raw;
        document.getElementById('pipeline-count-draft').innerText = data.pipeline_counts.draft;
        document.getElementById('pipeline-count-review').innerText = data.pipeline_counts.review;
        document.getElementById('pipeline-count-scheduled').innerText = data.pipeline_counts.scheduled;
        document.getElementById('pipeline-count-published').innerText = data.pipeline_counts.published;

        // Update Platform Performance
        const perfList = document.getElementById('platform-performance-list');
        if (perfList && data.platform_performance) {
            const perf = data.platform_performance;
            let maxCount = Math.max(...Object.values(perf));
            if (maxCount === 0) maxCount = 1; // prevent division by zero
            
            const pColors = {
                'Instagram': 'var(--red)',
                'Facebook': 'var(--amber)',
                'X': 'var(--muted)',
                'TikTok': 'var(--teal)',
                'Snapchat': 'var(--yellow)',
                'Threads': 'var(--foreground)'
            };
            
            let html = '';
            for (const [platform, count] of Object.entries(perf)) {
                const width = (count / maxCount) * 100;
                const color = pColors[platform] || 'var(--teal)';
                html += `<div class="bar-row"><div class="l">${platform}</div><div class="bar-track"><div class="bar-fill" style="width:${width}%; background:${color}"></div></div><div class="v">${count}</div></div>`;
            }
            perfList.innerHTML = html;
        }

        // Update Recent Content
        const recentList = document.getElementById('recent-content-list');
        if(recentList) {
            recentList.innerHTML = '';
            data.recent_content.forEach(item => {
                let s = item.status.toLowerCase();
                let badgeClass = 'draft';
                let statusAr = item.status;
                if (s === 'approved') { badgeClass = 'approved'; statusAr = 'معتمد'; }
                else if (s === 'pending_review') { badgeClass = 'review'; statusAr = 'قيد المراجعة'; }
                else if (s === 'scheduled') { badgeClass = 'scheduled'; statusAr = 'مجدول'; }
                else if (s === 'published') { badgeClass = 'published'; statusAr = 'منشور'; }
                else if (s === 'expired') { badgeClass = 'draft'; statusAr = 'منتهي الصلاحية'; }

                let cType = item.content_type || 'POST';
                let cTypeAr = 'بوست';
                if (cType.toUpperCase() === 'CAROUSEL') cTypeAr = 'كاروسيل';
                else if (cType.toUpperCase() === 'VIDEO' || cType.toUpperCase() === 'VIDEO_SCRIPT') cTypeAr = 'فيديو';

                let platformsArr = item.platforms || [];
                let platforms = platformsArr.map(p => `<span>${p}</span>`).join('');
                recentList.innerHTML += `
                    <tr>
                        <td><div class="src"><span class="dot" style="background:var(--amber)"></span>${item.source_name}</div></td>
                        <td class="title-cell"><span class="t">${item.title || 'بدون عنوان'}</span><span class="m cal-slot-type type-${cType.toLowerCase()}" style="display:inline-block; margin-top:4px">${cTypeAr}</span></td>
                        <td><span class="badge ${badgeClass}">${statusAr}</span></td>
                        <td><div class="plats">${platforms}</div></td>
                    </tr>
                `;
            });
        }

        // Update Pending Reviews
        const pendingList = document.getElementById('pending-reviews-list');
        if(pendingList) {
            pendingList.innerHTML = '';
            data.pending_content.forEach(item => {
                pendingList.innerHTML += `
                    <div class="review-item">
                        <div class="thumb" style="font-size:10px">${item.source_name}</div>
                        <div class="review-body">
                            <div class="t">${item.title}</div>
                            <div class="m">${item.content_type}</div>
                            <div class="review-actions">
                                <button class="reject">رفض</button>
                                <button>تعديل</button>
                                <button class="approve">موافقة</button>
                            </div>
                        </div>
                    </div>
                `;
            });
        }

    } catch (err) {
        console.error(err);
    }
}

async function fetchSources() {
    try {
        const res = await fetch(`${API_BASE}/sources/`);
        const data = await res.json();
        
        // Update Dashboard Sources
        const dashSources = document.getElementById('dashboard-sources-list');
        if(dashSources) {
            dashSources.innerHTML = '';
            data.slice(0, 5).forEach(src => {
                const activeClass = src.is_active ? '' : 'off';
                dashSources.innerHTML += `
                    <div class="src-item">
                        <div>
                            <div class="n">${src.name}</div>
                            <div class="u">${src.url}</div>
                        </div>
                        <div class="toggle ${activeClass}" onclick="toggleSource(${src.id}, this)"></div>
                    </div>
                `;
            });
        }

        // Update Sources Page Table
        const sourcesPageList = document.getElementById('sources-page-list');
        if(sourcesPageList) {
            sourcesPageList.innerHTML = '';
            data.forEach(src => {
                const activeClass = src.is_active ? '' : 'off';
                sourcesPageList.innerHTML += `
                    <tr>
                        <td><div class="src"><span class="dot" style="background:var(--teal)"></span>${src.name}</div></td>
                        <td class="m" style="font-family:var(--mono); font-size:11px; color:var(--muted)">${src.url}</td>
                        <td>${src.scraping_type}</td>
                        <td>${src.interval_mins} د</td>
                        <td class="m" style="font-family:var(--mono)">${src.health_status || 'ok'}</td>
                        <td><div class="toggle ${activeClass}" onclick="toggleSource(${src.id}, this)"></div></td>
                        <td><button class="reject" onclick="deleteSource(${src.id})" style="padding:5px 10px; border:1px solid var(--line); background:var(--panel-2); border-radius:6px; cursor:pointer">حذف</button></td>
                    </tr>
                `;
            });
        }
    } catch (err) {
        console.error(err);
    }
}

async function toggleSource(id, element) {
    try {
        const res = await fetch(`${API_BASE}/sources/${id}/toggle`, { method: 'PUT' });
        if(res.ok) {
            element.classList.toggle('off');
        }
    } catch(err) {
        console.error(err);
    }
}

async function deleteSource(id) {
    showConfirmModal(
        "حذف المصدر", 
        "هل أنت متأكد من حذف هذا المصدر نهائياً؟ ستتوقف عملية السحب التلقائي منه ولن يمكن التراجع عن هذا الإجراء.",
        async () => {
            try {
                const res = await fetch(`${API_BASE}/sources/${id}`, { method: 'DELETE' });
                if(res.ok) {
                    showToast("تم الحذف بنجاح", "success");
                    fetchSources();
                } else {
                    showToast("حدث خطأ في الحذف", "error");
                }
            } catch(err) {
                console.error(err);
                showToast("خطأ اتصال", "error");
            }
        }
    );
}

async function addNewSource() {
    const name = document.getElementById('source-name').value;
    const url = document.getElementById('source-url').value;
    const type = document.getElementById('source-type').value;
    const interval = document.getElementById('source-interval').value;
    const statusDiv = document.getElementById('add-source-status');

    if(!name || !url) {
        statusDiv.innerText = "يرجى ملء جميع الحقول";
        statusDiv.style.color = "red";
        return;
    }

    statusDiv.innerText = "جاري الإضافة...";
    statusDiv.style.color = "var(--text)";

    try {
        const res = await fetch(`${API_BASE}/sources/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                url: url,
                scraping_type: type,
                interval_mins: parseInt(interval)
            })
        });

        if(res.ok) {
            statusDiv.innerText = "تم إضافة المصدر بنجاح!";
            statusDiv.style.color = "green";
            document.getElementById('source-name').value = '';
            document.getElementById('source-url').value = '';
            fetchSources(); // Refresh list
        } else {
            statusDiv.innerText = "حدث خطأ أثناء الإضافة";
            statusDiv.style.color = "red";
        }
    } catch(err) {
        console.error(err);
        statusDiv.innerText = "حدث خطأ في الاتصال";
        statusDiv.style.color = "red";
    }
}

let currentEditId = null;
let currentEditData = null;
let activeEditTab = null;
let saveController = null;
const SAVE_BTN_ORIG_HTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M20 6 9 17l-5-5"/></svg> حفظ التعديلات`;

function openEditModal(id) {
    currentEditId = id;
    currentEditData = JSON.parse(JSON.stringify(window.reviewItemsData[id])); // deep copy
    // Always reset save button when opening fresh
    const saveBtn = document.getElementById('save-edit-btn');
    if (saveBtn) { saveBtn.innerHTML = SAVE_BTN_ORIG_HTML; saveBtn.disabled = false; }
    const tabs = document.getElementById('edit-modal-tabs');
    const content = document.getElementById('edit-modal-content');
    const subtitle = document.getElementById('edit-modal-subtitle');
    tabs.innerHTML = '';
    content.innerHTML = '';

    // Subtitle from the content
    if (currentEditData && currentEditData.title) {
        subtitle.innerText = currentEditData.title;
    } else if (currentEditData && currentEditData.unified_post) {
        subtitle.innerText = (currentEditData.unified_post || '').substring(0, 60) + '...';
    } else {
        subtitle.innerText = '';
    }

    if (typeof currentEditData !== 'object' || currentEditData === null) {
        // Raw string fallback
        tabs.innerHTML = '';
        content.innerHTML = `<div class="edit-panel"><div class="edit-field"><textarea id="edit-raw" style="width:100%;height:300px;background:var(--panel);border:1px solid var(--line);color:var(--text);padding:10px;border-radius:11px;font-family:inherit;">${currentEditData}</textarea></div></div>`;
    } else {
        // Detect content type by keys present
        const keys = Object.keys(currentEditData);
        const isPost = keys.includes('unified_post') || keys.includes('linkedin_post');
        const isCarousel = keys.includes('slides') || keys.includes('title');
        const isReel = keys.includes('hook') || keys.includes('body') || keys.includes('visual_cues');

        const tabDefs = [];
        if (isPost) tabDefs.push({ id: 'post', icon: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>', label: 'منشور موحّد', badge: '2 حقل' });
        if (isCarousel) tabDefs.push({ id: 'slides', icon: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>', label: 'شرائح', badge: 'كاروسيل' });
        if (isReel) tabDefs.push({ id: 'reel', icon: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>', label: 'سكريبت ريلز', badge: '4 حقول' });

        // If no type detected, show raw JSON
        if (tabDefs.length === 0) {
            content.innerHTML = `<div class="edit-panel"><div class="edit-field"><textarea id="edit-raw" class="mono" style="width:100%;height:350px;background:var(--panel);border:1px solid var(--line);color:var(--text);padding:12px;border-radius:11px;font-family:monospace;direction:ltr;">${JSON.stringify(currentEditData, null, 2)}</textarea></div></div>`;
        } else {
            // Build tabs
            tabDefs.forEach((t, i) => {
                const btn = document.createElement('button');
                btn.className = 'edit-tab' + (i === 0 ? ' active' : '');
                btn.innerHTML = t.icon + ' ' + t.label + ` <span class="etab-badge">${t.badge}</span>`;
                btn.onclick = () => {
                    document.querySelectorAll('.edit-tab').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    document.querySelectorAll('.edit-panel-section').forEach(p => p.style.display = 'none');
                    const panel = document.getElementById('em-panel-' + t.id);
                    if (panel) panel.style.display = 'block';
                };
                tabs.appendChild(btn);
            });

            // Build panels
            const wrap = document.createElement('div');
            if (isPost) wrap.appendChild(buildPostPanel(currentEditData));
            if (isCarousel) wrap.appendChild(buildCarouselPanel(currentEditData));
            if (isReel) wrap.appendChild(buildReelPanel(currentEditData));
            content.appendChild(wrap);

            // Show first
            document.querySelectorAll('.edit-panel-section').forEach((p, i) => p.style.display = i === 0 ? 'block' : 'none');
        }
    }

    document.getElementById('edit-modal').style.display = 'flex';
}

function buildPostPanel(data) {
    const div = document.createElement('div');
    div.id = 'em-panel-post';
    div.className = 'edit-panel-section edit-panel';
    div.innerHTML = `
        <div class="edit-field">
            <div class="edit-field-label">
                <span class="ename"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg> المنشور الموحّد <code>unified_post</code></span>
            </div>
            <textarea data-key="unified_post" rows="6">${data.unified_post || ''}</textarea>
        </div>
        ${data.linkedin_post !== undefined ? `
        <div class="edit-field">
            <div class="edit-field-label">
                <span class="ename"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/><path d="M10 9h4v12h-4zM10 13a4 4 0 0 1 8 0v8h-4v-8a2 2 0 0 0-2-2h-2"/></svg> منشور لينكدإن <code>linkedin_post</code></span>
            </div>
            <textarea data-key="linkedin_post" rows="5" style="direction:ltr;text-align:left;">${data.linkedin_post || ''}</textarea>
        </div>
        ` : ''}
    `;
    return div;
}

function buildCarouselPanel(data) {
    const div = document.createElement('div');
    div.id = 'em-panel-slides';
    div.className = 'edit-panel-section edit-panel';

    const titleHtml = `
        <div class="edit-field">
            <div class="edit-field-label">
                <span class="ename"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7V4h16v3M9 20h6M12 4v16"/></svg> العنوان <code>title</code></span>
            </div>
            <textarea data-key="title" rows="2">${data.title || ''}</textarea>
        </div>
    `;

    let slidesHtml = '<div id="em-slides-container">';
    const slides = Array.isArray(data.slides) ? data.slides : [];
    slides.forEach((slide, idx) => slidesHtml += buildSlideCard(slide, idx));
    slidesHtml += '</div>';
    slidesHtml += `<button class="add-slide-em" onclick="emAddSlide()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg> إضافة شريحة جديدة</button>`;

    div.innerHTML = titleHtml + slidesHtml;
    return div;
}

function buildSlideCard(slide, idx) {
    const heading = slide.heading || '';
    const body = slide.body || '';
    const tips = Array.isArray(slide.tips_list) ? slide.tips_list : [];
    const tipsHtml = tips.length > 0 ? `
        <div>
            <div class="mini-label-em"><code>tips_list</code> نقاط إضافية</div>
            <div class="em-tips-list" data-slide="${idx}">
                ${tips.map((t, ti) => `
                <div class="em-tip-row" style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                    <span style="color:#e0b563;">●</span>
                    <input type="text" class="mini-ta" value="${t.replace(/"/g, '&quot;')}" data-slide="${idx}" data-tip="${ti}" style="flex:1;min-height:unset;resize:none;padding:8px 12px;">
                    <button class="em-del-btn" onclick="emRemoveTip(${idx},${ti})"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg></button>
                </div>`).join('')}
            </div>
            <button class="add-slide-em" style="padding:8px;margin-top:0;border-radius:9px;font-size:12px;" onclick="emAddTip(${idx})"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M12 5v14M5 12h14"/></svg> إضافة نقطة</button>
        </div>
    ` : '';

    return `
    <div class="slide-card-em" data-slide-idx="${idx}">
        <div class="slide-card-em-head">
            <div style="display:flex;align-items:center;gap:9px;font-size:12.5px;color:var(--muted);font-weight:500;">
                <span class="slide-num-em">${String(idx+1).padStart(2,'0')}</span> الشريحة ${idx === 0 ? 'الأولى' : idx === 1 ? 'الثانية' : idx + 1}
            </div>
            <button class="em-del-btn" onclick="emRemoveSlide(${idx})" title="حذف الشريحة"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6"/></svg></button>
        </div>
        <div class="slide-body-em">
            <div>
                <div class="mini-label-em"><code>heading</code> العنوان</div>
                <textarea class="mini-ta" rows="1" data-slide="${idx}" data-field="heading">${heading}</textarea>
            </div>
            <div>
                <div class="mini-label-em"><code>body</code> النص</div>
                <textarea class="mini-ta" rows="3" data-slide="${idx}" data-field="body">${body}</textarea>
            </div>
            ${tipsHtml}
        </div>
    </div>`;
}

function emRemoveSlide(idx) {
    const container = document.getElementById('em-slides-container');
    const cards = container.querySelectorAll('.slide-card-em');
    if (cards.length <= 1) return;
    cards[idx].remove();
    // Re-number
    container.querySelectorAll('.slide-card-em').forEach((c, i) => {
        c.dataset.slideIdx = i;
        const num = c.querySelector('.slide-num-em');
        if (num) num.textContent = String(i+1).padStart(2,'0');
    });
}

function emAddSlide() {
    const container = document.getElementById('em-slides-container');
    const idx = container.querySelectorAll('.slide-card-em').length;
    container.insertAdjacentHTML('beforeend', buildSlideCard({ heading:'', body:'' }, idx));
}

function emAddTip(slideIdx) {
    const container = document.getElementById('em-slides-container');
    const card = container.querySelector(`.slide-card-em[data-slide-idx="${slideIdx}"]`);
    if (!card) return;
    const tipsList = card.querySelector('.em-tips-list');
    if (!tipsList) return;
    const tipCount = tipsList.querySelectorAll('.em-tip-row').length;
    tipsList.insertAdjacentHTML('beforeend', `
        <div class="em-tip-row" style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="color:#e0b563;">●</span>
            <input type="text" class="mini-ta" value="" data-slide="${slideIdx}" data-tip="${tipCount}" style="flex:1;min-height:unset;resize:none;padding:8px 12px;">
            <button class="em-del-btn" onclick="this.parentElement.remove()"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg></button>
        </div>
    `);
}

function emRemoveTip(slideIdx, tipIdx) {
    const container = document.getElementById('em-slides-container');
    const card = container.querySelector(`.slide-card-em[data-slide-idx="${slideIdx}"]`);
    if (!card) return;
    const tips = card.querySelectorAll('.em-tip-row');
    if (tips[tipIdx]) tips[tipIdx].remove();
}

function buildReelPanel(data) {
    const div = document.createElement('div');
    div.id = 'em-panel-reel';
    div.className = 'edit-panel-section edit-panel';
    div.innerHTML = `
        <div class="edit-field">
            <div class="edit-field-label"><span class="ename" style="color:#e0745f;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2 3 14h9l-1 8 10-12h-9z"/></svg> الجملة الافتتاحية <code>hook</code></span></div>
            <textarea data-key="hook" rows="2">${data.hook || ''}</textarea>
        </div>
        <div class="edit-field">
            <div class="edit-field-label"><span class="ename"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg> المحتوى <code>body</code></span></div>
            <textarea data-key="body" rows="5">${data.body || ''}</textarea>
        </div>
        <div class="edit-field">
            <div class="edit-field-label"><span class="ename" style="color:#e0b563;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"/></svg> دعوة للتفاعل <code>call_to_action</code></span></div>
            <textarea data-key="call_to_action" rows="3">${data.call_to_action || ''}</textarea>
        </div>
        <div class="edit-field">
            <div class="edit-field-label"><span class="ename"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L7 21"/></svg> إرشادات بصرية <code>visual_cues</code></span></div>
            <textarea data-key="visual_cues" rows="4">${data.visual_cues || ''}</textarea>
        </div>
    `;
    return div;
}

function closeEditModal() {
    // Abort any pending save request
    if (saveController) { saveController.abort(); saveController = null; }
    // Reset button state
    const saveBtn = document.getElementById('save-edit-btn');
    if (saveBtn) { saveBtn.innerHTML = SAVE_BTN_ORIG_HTML; saveBtn.disabled = false; }
    document.getElementById('edit-modal').style.display = 'none';
    currentEditId = null;
    currentEditData = null;
}

if(document.getElementById('save-edit-btn')) {
    document.getElementById('save-edit-btn').addEventListener('click', async () => {
        if(!currentEditId) return;
        
        let newContent = {};
        const container = document.getElementById('edit-modal-content');

        if (document.getElementById('edit-raw')) {
            try { newContent = JSON.parse(document.getElementById('edit-raw').value); }
            catch(e) { newContent = document.getElementById('edit-raw').value; }
        } else {
            // Copy original data
            newContent = JSON.parse(JSON.stringify(currentEditData));

            // Collect simple key fields (post & reel)
            container.querySelectorAll('textarea[data-key]').forEach(ta => {
                newContent[ta.dataset.key] = ta.value;
            });

            // Collect carousel title
            const titleTA = container.querySelector('textarea[data-key="title"]');
            if (titleTA) newContent.title = titleTA.value;

            // Collect slides
            const slidesContainer = document.getElementById('em-slides-container');
            if (slidesContainer) {
                const slides = [];
                slidesContainer.querySelectorAll('.slide-card-em').forEach(card => {
                    const slide = {};
                    const headingTA = card.querySelector('textarea[data-field="heading"]');
                    const bodyTA = card.querySelector('textarea[data-field="body"]');
                    if (headingTA) slide.heading = headingTA.value;
                    if (bodyTA) slide.body = bodyTA.value;
                    const tipInputs = card.querySelectorAll('input[data-tip]');
                    if (tipInputs.length > 0) {
                        slide.tips_list = Array.from(tipInputs).map(i => i.value).filter(v => v.trim());
                    }
                    slides.push(slide);
                });
                newContent.slides = slides;
            }
        }

        const btn = document.getElementById('save-edit-btn');
        const origHTML = btn.innerHTML;
        btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg> جاري الحفظ...';
        btn.disabled = true;

        try {
            const token = localStorage.getItem('cm_token');
            saveController = new AbortController();
            const timeoutId = setTimeout(() => saveController.abort(), 15000);
            const res = await fetch(`${API_BASE}/content/${currentEditId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ generated_content: newContent }),
                signal: saveController.signal
            });
            clearTimeout(timeoutId);
            saveController = null;
            
            if (res.ok) {
                showToast("تم حفظ التعديلات بنجاح ✅", "success");
                closeEditModal();
                fetchReviewContent();
            } else {
                showToast("حدث خطأ أثناء الحفظ", "error");
            }
        } catch(err) {
            if (err.name !== 'AbortError') {
                showToast("خطأ في الاتصال بالخادم", "error");
            }
        } finally {
            btn.innerHTML = SAVE_BTN_ORIG_HTML;
            btn.disabled = false;
        }
    });
}

// ---------------- RAW ARTICLES ----------------
async function fetchRawArticles() {
    try {
        const res = await fetch(`${API_BASE}/raw-articles/`);
        if(!res.ok) return;
        const data = await res.json();
        // Store all articles in a map for safe access
        window._rawArticlesMap = {};
        data.forEach(a => { window._rawArticlesMap[a.id] = a; });
        
        const rawList = document.getElementById('raw-articles-list');
        if(rawList) {
            rawList.innerHTML = '';
            
            if (data.length === 0) {
                rawList.innerHTML = `
                    <div style="grid-column: 1 / -1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding: 60px 20px; text-align:center; background:var(--panel); border-radius:12px; border:1px dashed var(--line);">
                        <div style="font-size:48px; margin-bottom:16px;">📰</div>
                        <h3 style="margin-bottom:8px; font-weight:600; color:#fff;">لا توجد أخبار جديدة اليوم</h3>
                        <p style="color:var(--muted); font-size:14px; max-width:300px; line-height:1.5;">جميع الأخبار تم سحبها مسبقاً أو لم تنشر المصادر أي أخبار جديدة بعد. انتظر حتى يتم سحب أخبار جديدة.</p>
                    </div>
                `;
                return;
            }
            
            data.forEach((art, idx) => {
                // Generate a random gradient for the image placeholder based on ID or index
                const hue = (idx * 137.5) % 360;
                const gradient = `linear-gradient(160deg, hsl(${hue}, 70%, 90%), hsl(${hue}, 40%, 80%))`;
                
                const _tmpDiv = document.createElement('div');
                _tmpDiv.innerHTML = art.content || '';
                const cleanSnippet = _tmpDiv.textContent || _tmpDiv.innerText || 'لا يوجد محتوى نصي...';
                const thumbStyle = art.image_url ? `background-image:url('${imgProxy(art.image_url)}'); background-size:cover; background-position:center;` : `background:${gradient};`;
                const thumbContent = art.image_url ? '' : (art.source ? art.source.name : 'مجهول');
                
                rawList.innerHTML += `
                    <div class="panel" style="display:flex; flex-direction:column; justify-content:space-between;">
                        <div>
                            <div class="thumb" style="width:100%; height:180px; margin-bottom:12px; border-radius:8px; ${thumbStyle} display:flex; align-items:center; justify-content:center; color:#fff; font-weight:bold; font-size:18px; text-shadow:0 2px 4px rgba(0,0,0,0.2);">${thumbContent}</div>
                            <div class="t" style="margin-bottom:8px; line-height:1.4;">${art.title || 'بدون عنوان'}</div>
                            <div class="snippet" style="font-size:13px; color:var(--muted); line-height:1.5; margin-bottom:12px; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">${cleanSnippet}</div>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--line); padding-top:10px; margin-top:10px;">
                            <div class="m" style="font-family:var(--mono); font-size:11px">${new Date(art.created_at).toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'})}</div>
                            <div style="display:flex; gap:6px;">
                                <button class="btn ghost" style="padding:4px 10px; font-size:11px; color:var(--red); border-color:rgba(255,80,80,0.2);" onclick="deleteRawArticle(${art.id}, this)" title="حذف الخبر">🗑️</button>
                                <button class="btn ghost" style="padding:4px 10px; font-size:11px;" onclick="openArticleById(${art.id})">قراءة</button>
                                <button class="btn" style="padding:4px 10px; font-size:11px; background:var(--teal); color:#0a0a0a; border:none;" onclick='approveArticle(${art.id}, this)'>موافقة ⚡</button>
                            </div>
                        </div>
                    </div>
                `;
            });
        }
    } catch(err) {
        console.error(err);
    }
}

async function deleteRawArticle(id, btn) {
    const card = btn.closest('.panel');
    
    // Show custom delete confirmation modal
    let modal = document.getElementById('delete-article-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'delete-article-modal';
        modal.style.cssText = 'display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:10001; align-items:center; justify-content:center; backdrop-filter:blur(6px);';
        modal.innerHTML = `
            <div style="background:linear-gradient(145deg,#1e1a1a,#1a1010); width:92%; max-width:360px; border-radius:20px; border:1px solid rgba(255,80,80,0.2); padding:0; overflow:hidden; box-shadow:0 30px 60px rgba(0,0,0,0.7); animation:genFadeUp 0.3s ease forwards;">
                <div style="padding:28px 28px 20px; text-align:center; background:linear-gradient(135deg,rgba(255,80,80,0.08),transparent);">
                    <div style="width:52px; height:52px; background:linear-gradient(135deg,#ff4444,#cc2222); border-radius:16px; display:flex; align-items:center; justify-content:center; font-size:24px; margin:0 auto 16px; box-shadow:0 8px 24px rgba(255,68,68,0.35);">🗑️</div>
                    <h3 style="margin:0 0 8px; font-size:18px; color:#fff; font-weight:800;">حذف الخبر</h3>
                    <p style="color:rgba(255,255,255,0.5); font-size:13.5px; margin:0; line-height:1.6;">هل أنت متأكد من حذف هذا الخبر نهائياً؟<br>لا يمكن التراجع عن هذا الإجراء.</p>
                </div>
                <div style="padding:0 20px 20px; display:flex; gap:10px;">
                    <button id="delete-article-cancel" style="flex:1; background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.6); border:1.5px solid rgba(255,255,255,0.08); padding:13px; font-size:14px; font-weight:600; border-radius:12px; cursor:pointer; transition:all 0.2s;"
                        onmouseover="this.style.background='rgba(255,255,255,0.1)'; this.style.color='#fff'"
                        onmouseout="this.style.background='rgba(255,255,255,0.05)'; this.style.color='rgba(255,255,255,0.6)'">إلغاء</button>
                    <button id="delete-article-confirm" style="flex:1.2; background:linear-gradient(135deg,#ff4444,#cc2222); color:#fff; border:none; padding:13px; font-size:14px; font-weight:800; border-radius:12px; cursor:pointer; transition:all 0.2s; box-shadow:0 6px 20px rgba(255,68,68,0.35);"
                        onmouseover="this.style.transform='translateY(-2px)'"
                        onmouseout="this.style.transform='translateY(0)'">🗑️ نعم، احذفه</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        document.getElementById('delete-article-cancel').onclick = () => {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        };
    }
    
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    
    document.getElementById('delete-article-confirm').onclick = async () => {
        modal.style.display = 'none';
        document.body.style.overflow = '';
        try {
            const token = localStorage.getItem('cm_token');
            const res = await fetch(`${API_BASE}/raw-articles/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                if (card) { card.style.opacity = '0'; card.style.transition = 'opacity 0.3s'; setTimeout(() => card.remove(), 300); }
                showToast('✅ تم حذف الخبر', 'success');
                fetchDashboardStats();
            } else {
                showToast('❌ فشل الحذف', 'error');
            }
        } catch(e) {
            showToast('❌ خطأ في الاتصال', 'error');
        }
    };
}

async function approveArticle(id, btn) {
    showCustomConfirm(`ما هي صيغ المحتوى التي تود توليدها لهذا الخبر؟`, async (formats, carouselPlatforms) => {
        const orig = btn.innerText;
        btn.innerText = "جاري الصياغة...";
        btn.disabled = true;
        try {
            const token = localStorage.getItem('cm_token');
            const res = await fetch(`${API_BASE}/raw-articles/${id}/generate`, { 
                method: "POST",
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ formats: formats, carousel_platforms: carouselPlatforms || ['IG', 'Li'] })
            });
            if (res.ok) {
                btn.parentElement.parentElement.parentElement.style.opacity = '0.4';
                showToast("✅ تم إرسال الخبر لكلود... سيظهر في المراجعة خلال ثوانٍ", "success");
                setTimeout(fetchRawArticles, 2000);
                fetchDashboardStats();
                let polls = 0;
                const pollInterval = setInterval(() => {
                    polls++;
                    fetchDashboardStats();
                    if (polls >= 12) clearInterval(pollInterval);
                }, 5000);
            } else {
                const err = await res.json().catch(() => ({}));
                showToast(`❌ خطأ: ${err.detail || err.error || 'حدث خطأ أثناء الصياغة'}`, "error");
                btn.innerText = orig;
                btn.disabled = false;
            }
        } catch (err) {
            console.error(err);
            showToast("❌ خطأ في الاتصال بالخادم", "error");
            btn.innerText = orig;
            btn.disabled = false;
        }
    });
}


function openArticleById(id) {
    const art = (window._rawArticlesMap || {})[id];
    if (!art) return;
    openArticleModal(art.title || 'بدون عنوان', art.content || '', art.url || '#', imgProxy(art.image_url || ''));
}

function openArticleModal(title, content, url, imageUrl) {
    document.getElementById('modal-title').innerText = title;
    
    const imgEl = document.getElementById('modal-image');
    if (imageUrl) {
        imgEl.src = imageUrl;
        imgEl.style.display = 'block';
    } else {
        imgEl.src = '';
        imgEl.style.display = 'none';
    }
    
    // Strip any HTML tags from content before displaying
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = content;
    const cleanContent = tempDiv.textContent || tempDiv.innerText || content;
    document.getElementById('modal-content').innerText = cleanContent;
    document.getElementById('modal-url').href = url;
    document.getElementById('article-modal').style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
}

function closeArticleModal() {
    document.getElementById('article-modal').style.display = 'none';
    document.body.style.overflow = ''; // Restore background scrolling
    // Reset translation state
    window._articleOriginalContent = null;
    const btn = document.getElementById('modal-translate-btn');
    if (btn) { btn.innerText = '🌍 ترجمة للإنجليزية'; btn.disabled = false; }
}

// ---------------- ARTICLE TRANSLATION ----------------
window._articleOriginalContent = null;

async function translateModalContent() {
    const contentEl = document.getElementById('modal-content');
    const btn = document.getElementById('modal-translate-btn');
    
    // Toggle: if already translated, revert to original
    if (window._articleOriginalContent) {
        contentEl.innerText = window._articleOriginalContent;
        window._articleOriginalContent = null;
        btn.innerHTML = '🌍 ترجمة للإنجليزية';
        btn.disabled = false;
        contentEl.style.direction = 'rtl';
        return;
    }

    const text = contentEl.innerText.trim();
    if (!text || text.length < 5) return;
    
    btn.innerHTML = '⏳ جاري الترجمة...';
    btn.disabled = true;

    try {
        // Split into chunks of 500 chars (MyMemory limit per call)
        const chunks = [];
        for (let i = 0; i < text.length; i += 450) {
            chunks.push(text.slice(i, i + 450));
        }
        
        const translated = [];
        for (const chunk of chunks) {
            const url = `https://api.mymemory.translated.net/get?q=${encodeURIComponent(chunk)}&langpair=ar|en`;
            const res = await fetch(url);
            const data = await res.json();
            translated.push(data.responseData?.translatedText || chunk);
        }
        
        window._articleOriginalContent = text;
        contentEl.innerText = translated.join(' ');
        contentEl.style.direction = 'ltr';
        btn.innerHTML = '↩️ عرض النص الأصلي';
        btn.disabled = false;
    } catch (err) {
        console.error('Translation error:', err);
        showToast('❌ فشل الترجمة، حاول مرة أخرى', 'error');
        btn.innerHTML = '🌍 ترجمة للإنجليزية';
        btn.disabled = false;
    }
}


function showConfirmModal(title, message, onConfirmCallback) {
    const modal = document.getElementById('confirm-modal');
    const box = document.getElementById('confirm-box');
    
    document.getElementById('confirm-title').innerText = title;
    document.getElementById('confirm-message').innerText = message;
    
    modal.style.display = 'flex';
    // Trigger animation
    requestAnimationFrame(() => {
        modal.style.opacity = '1';
        box.style.transform = 'scale(1)';
    });
    
    const btnCancel = document.getElementById('confirm-cancel-btn');
    const btnOk = document.getElementById('confirm-ok-btn');
    
    // Clear old listeners
    const newBtnCancel = btnCancel.cloneNode(true);
    btnCancel.parentNode.replaceChild(newBtnCancel, btnCancel);
    
    const newBtnOk = btnOk.cloneNode(true);
    btnOk.parentNode.replaceChild(newBtnOk, btnOk);
    
    const close = () => {
        modal.style.opacity = '0';
        document.getElementById('confirm-box').style.transform = 'scale(0.95)';
        setTimeout(() => modal.style.display = 'none', 200);
    };
    
    newBtnCancel.onclick = close;
    
    newBtnOk.onclick = () => {
        close();
        if (onConfirmCallback) onConfirmCallback();
    };
}

// ---------------- TOAST NOTIFICATION ----------------
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    const bgColor = type === 'success' ? 'var(--teal)' : 'var(--red)';
    toast.style.cssText = `
        background: ${bgColor};
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        font-family: var(--font);
        font-weight: 600;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        max-width: 400px;
        word-break: break-word;
        line-height: 1.5;
    `;
    toast.innerText = message;
    
    container.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 10);
    
    // Animate out and remove
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

async function fetchAllContent() {
    try {
        const res = await fetch(`${API_BASE}/content/?_t=${Date.now()}`);
        if(!res.ok) return;
        const data = await res.json();
        
        const allContentList = document.getElementById('all-content-list');
        if(allContentList) {
            const currentHash = JSON.stringify(data);
            if (window.lastAllContentHash === currentHash) {
                return;
            }
            window.lastAllContentHash = currentHash;
            
            
            window.allContentData = data;
            renderContentList();
        }
    } catch(err) {
        console.error(err);
    }
}

function renderContentList() {
    const data = window.allContentData || [];
    const filterEl = document.querySelector('#content-filters .chip.active');
    const activeFilter = filterEl ? filterEl.getAttribute('data-filter') : 'all';
    
    let filteredData = data;
    if (activeFilter.startsWith('type-')) {
        const t = activeFilter.split('-')[1].toUpperCase();
        filteredData = data.filter(item => {
            const ct = (item.content_type || '').toUpperCase();
            if (t === 'VIDEO') return ct.includes('VIDEO');
            return ct === t;
        });
    } else if (activeFilter.startsWith('status-')) {
        const s = activeFilter.split('-')[1];
        filteredData = data.filter(item => (item.status || '').toLowerCase() === s);
    } else if (activeFilter.startsWith('date-')) {
        const d = activeFilter.split('-')[1];
        const now = new Date();
        now.setHours(0,0,0,0);
        
        filteredData = data.filter(item => {
            if (!item.created_at) return false;
            const created = new Date(item.created_at);
            created.setHours(0,0,0,0);
            
            if (d === 'today') return now.getTime() === created.getTime();
            if (d === 'yesterday') {
                const yesterday = new Date(now);
                yesterday.setDate(yesterday.getDate() - 1);
                return created.getTime() === yesterday.getTime();
            }
            if (d === 'last7') {
                const diffTime = Math.abs(now - created);
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                return diffDays <= 7;
            }
            return true;
        });
    }

    // Update counts
    const counts = {
        'all': data.length,
        'type-post': data.filter(i => (i.content_type||'').toUpperCase() === 'POST').length,
        'type-carousel': data.filter(i => (i.content_type||'').toUpperCase() === 'CAROUSEL').length,
        'type-video': data.filter(i => (i.content_type||'').toUpperCase().includes('VIDEO')).length,
        'status-draft': data.filter(i => (i.status||'').toLowerCase() === 'draft').length,
        'status-pending_review': data.filter(i => (i.status||'').toLowerCase() === 'pending_review').length,
        'status-approved': data.filter(i => (i.status||'').toLowerCase() === 'approved').length,
        'status-scheduled': data.filter(i => (i.status||'').toLowerCase() === 'scheduled').length,
        'status-published': data.filter(i => (i.status||'').toLowerCase() === 'published').length,
        'date-today': data.filter(i => { if(!i.created_at)return false; let d=new Date(i.created_at); d.setHours(0,0,0,0); let n=new Date(); n.setHours(0,0,0,0); return d.getTime()===n.getTime(); }).length,
        'date-yesterday': data.filter(i => { if(!i.created_at)return false; let d=new Date(i.created_at); d.setHours(0,0,0,0); let n=new Date(); n.setHours(0,0,0,0); n.setDate(n.getDate()-1); return d.getTime()===n.getTime(); }).length,
        'date-last7': data.filter(i => { if(!i.created_at)return false; let d=new Date(i.created_at); d.setHours(0,0,0,0); let n=new Date(); n.setHours(0,0,0,0); return Math.ceil(Math.abs(n-d)/(1000*60*60*24)) <= 7; }).length
    };

    document.querySelectorAll('#content-filters .chip').forEach(chip => {
        const f = chip.getAttribute('data-filter');
        const countSpan = chip.querySelector('.c');
        if (countSpan) countSpan.innerText = `(${counts[f] || 0})`;
    });

    const allContentList = document.getElementById('all-content-list');
    if (!allContentList) return;
    
    allContentList.innerHTML = '';
    
    if (filteredData.length === 0) {
        allContentList.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 40px; color: var(--muted);">لا توجد عناصر مطابقة للفلتر المحدد.</td></tr>`;
        return;
    }

    filteredData.forEach(item => {
                let s = item.status.toLowerCase();
                let badgeClass = 'draft';
                let statusAr = item.status;
                if (s === 'approved') { badgeClass = 'approved'; statusAr = 'معتمد'; }
                else if (s === 'pending_review') { badgeClass = 'review'; statusAr = 'قيد المراجعة'; }
                else if (s === 'scheduled') { badgeClass = 'scheduled'; statusAr = 'مجدول'; }
                else if (s === 'published') { badgeClass = 'published'; statusAr = 'منشور'; }
                else if (s === 'expired') { badgeClass = 'draft'; statusAr = 'منتهي الصلاحية'; }
                
                let platformsArr = [];
                if (Array.isArray(item.platforms)) platformsArr = item.platforms;
                else if (typeof item.platforms === 'string') platformsArr = item.platforms.split(',');
                else if (Array.isArray(item.platform)) platformsArr = item.platform;
                else if (typeof item.platform === 'string') platformsArr = item.platform.split(',');
                
                let platforms = platformsArr.filter(p => p.trim() !== '').map(p => `<span>${p.trim()}</span>`).join('');
                
                let cType = item.content_type || 'POST';
                let cTypeAr = 'بوست';
                if (cType.toUpperCase() === 'CAROUSEL') cTypeAr = 'كاروسيل';
                else if (cType.toUpperCase() === 'VIDEO' || cType.toUpperCase() === 'VIDEO_SCRIPT') cTypeAr = 'فيديو';
                
                let title = 'بدون عنوان';
                let gen = null;
                if (item.generated_content) {
                    try {
                        gen = typeof item.generated_content === 'string' ? JSON.parse(item.generated_content) : item.generated_content;
                        title = gen.title || gen.hook || title;
                    } catch(e) {}
                }
                if (title === 'بدون عنوان' && item.raw_article) title = item.raw_article.title;
                if (gen && gen.trend_title) title = `🔥 ترند: ${gen.trend_title}`;

                const d = new Date(item.created_at);
                const dateStr = d.toLocaleDateString('en-GB') + ' ' + d.toLocaleTimeString('en-GB', {hour: '2-digit', minute:'2-digit'});

                allContentList.innerHTML += `
                    <tr>
                        <td><div class="src"><span class="dot" style="background:var(--amber)"></span>${item.raw_article ? item.raw_article.source.name : 'مجهول'}</div></td>
                        <td class="title-cell"><span class="t">${title}</span><span class="m cal-slot-type type-${cType.toLowerCase()}" style="display:inline-block; margin-top:4px">${cTypeAr}</span></td>
                        <td class="m" style="font-family:var(--mono); font-size:11px; direction:ltr; text-align:right;">${dateStr}</td>
                        <td><span class="badge ${badgeClass}">${statusAr}</span></td>
                        <td><div class="plats">${platforms}</div></td>
                    </tr>
                `;
    });
}

// ---------------- REVIEW & APPROVE ----------------
async function fetchReviewContent() {
    try {
        const [res, resGen] = await Promise.all([
            fetch(`${API_BASE}/content/review?_t=${Date.now()}`),
            fetch(`${API_BASE}/raw-articles/generating?_t=${Date.now()}`)
        ]);
        if(!res.ok) return;
        const data = await res.json();
        const generatingData = resGen.ok ? await resGen.json() : [];
        
        const reviewList = document.getElementById('review-articles-list');
        const reviewCount = document.getElementById('sidebar-count-review');
        if (reviewCount) reviewCount.innerText = data.length || '-';
        
        if(reviewList) {
            const currentHash = JSON.stringify({data, generatingData});
            if (window.lastReviewDataHash === currentHash) {
                if (generatingData.length > 0) setTimeout(fetchReviewContent, 3000);
                return;
            }
            window.lastReviewDataHash = currentHash;
            reviewList.innerHTML = '';

            if (data.length === 0 && generatingData.length === 0) {
                reviewList.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--muted); padding: 40px;">لا يوجد محتوى بانتظار المراجعة.</div>`;
                return;
            }

            window.reviewItemsData    = window.reviewItemsData    || {};
            window.reviewItemsDataRaw = window.reviewItemsDataRaw || {};

            // ── Group content items by raw_article_id ──────────────────────────
            const groups = {}; // key = raw_article_id (or "noarticle_<id>")
            const groupOrder = [];

            data.forEach(item => {
                let generated = typeof item.generated_content === 'string'
                    ? JSON.parse(item.generated_content)
                    : item.generated_content;
                window.reviewItemsData[item.id]    = generated;
                window.reviewItemsDataRaw[item.id] = item;

                const gKey = item.raw_article_id != null ? String(item.raw_article_id) : `solo_${item.id}`;
                if (!groups[gKey]) {
                    groups[gKey] = { article: item.raw_article || null, items: [] };
                    groupOrder.push(gKey);
                }
                groups[gKey].items.push({ item, generated });
            });

            // ── Render "generating" placeholders (one per generating article) ──
            generatingData.forEach(art => {
                // Calculate time stuck
                const createdAt = art.created_at ? new Date(art.created_at) : null;
                const minutesStuck = createdAt ? Math.floor((Date.now() - createdAt.getTime()) / 60000) : 0;
                const isLikelyStuck = minutesStuck > 10;

                reviewList.innerHTML += `
                <div style="grid-column: 1 / -1;">
                  <div style="border:1.5px dashed ${isLikelyStuck ? '#ef4444' : 'var(--teal)'}; border-radius:16px; background:var(--panel); padding:0; overflow:hidden; opacity:${isLikelyStuck ? '0.9' : '0.65'}; margin-bottom:0;">
                    <!-- Article header -->
                    <div style="display:flex; align-items:center; gap:12px; padding:14px 18px; border-bottom:1px solid var(--line); background:linear-gradient(90deg,rgba(${isLikelyStuck ? '239,68,68' : '53,211,153'},0.06),transparent);">
                      ${art.image_url ? `<img src="${imgProxy(art.image_url)}" style="width:46px;height:46px;object-fit:cover;border-radius:10px;flex-shrink:0;" onerror="this.style.display='none'">` : ''}
                      <div style="flex:1; min-width:0;">
                        <div style="font-size:13.5px;font-weight:600;color:var(--text);line-height:1.4;">${art.title || 'بدون عنوان'}</div>
                        <div style="font-size:11px;color:var(--muted);margin-top:2px;">📡 ${art.source_name || ''} ${isLikelyStuck ? `<span style="color:#ef4444;margin-right:6px;">⚠️ متوقف منذ ${minutesStuck} دقيقة</span>` : ''}</div>
                      </div>
                      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px;min-width:160px;">
                        ${isLikelyStuck ? `
                        <div style="display:flex;gap:6px;">
                          <button onclick="retryStuckArticle(${art.id})" style="background:rgba(53,211,153,0.15);border:1px solid rgba(53,211,153,0.3);color:var(--teal);padding:5px 12px;border-radius:8px;font-size:12px;cursor:pointer;font-weight:700;">🔄 إعادة محاولة</button>
                          <button onclick="cancelStuckArticle(${art.id})" style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.25);color:#ef4444;padding:5px 10px;border-radius:8px;font-size:12px;cursor:pointer;">✕</button>
                        </div>` : `
                        <div style="display:flex;align-items:center;gap:8px;color:var(--teal);font-size:12px;white-space:nowrap;">
                          <div style="width:14px;height:14px;border:2px solid rgba(53,211,153,0.3);border-top:2px solid var(--teal);border-radius:50%;animation:spin 1s linear infinite;"></div>
                          جاري الصياغة...
                        </div>
                        <div style="width:100%;height:4px;background:rgba(53,211,153,0.15);border-radius:2px;overflow:hidden;">
                          <div style="height:100%;background:var(--teal);border-radius:2px;animation:simulatedProgress 25s cubic-bezier(0.1, 0.7, 0.1, 1) forwards;"></div>
                        </div>`}
                      </div>
                    </div>
                  </div>
                </div>`;
            });

            // ── Render grouped article boxes ────────────────────────────────────
            groupOrder.forEach(gKey => {
                const { article, items: groupItems } = groups[gKey];

                const articleTitle  = article ? (article.title || 'بدون عنوان') : 'محتوى مستقل';
                const articleSource = article && article.source ? article.source.name : 'AI';
                const articleImage  = article ? article.image_url : null;
                const articleDate   = article && article.published_at
                    ? new Date(article.published_at).toLocaleDateString('ar-SA', {day:'numeric', month:'short'})
                    : '';

                // Type badge colours
                const typeMeta = {
                    'POST':         { label:'منشور',    bg:'rgba(53,211,153,0.12)',  color:'var(--teal)' },
                    'CAROUSEL':     { label:'كاروسيل',  bg:'rgba(139,92,246,0.12)',  color:'#a78bfa' },
                    'VIDEO_SCRIPT': { label:'سكريبت',   bg:'rgba(251,146,60,0.12)',  color:'#fb923c' },
                };

                // Build sub-cards HTML for each item in this group
                let subCardsHtml = '';
                groupItems.forEach(({ item, generated }) => {
                    const tm  = typeMeta[item.content_type] || { label: item.content_type, bg:'rgba(255,255,255,0.06)', color:'var(--muted)' };
                    let platforms = Array.isArray(item.platforms)
                        ? item.platforms.join(' · ')
                        : (item.platforms || item.platform || '');

                    // Snippet preview
                    let snippetHtml = '';
                    if (item.content_type === 'POST') {
                        const txt = generated && (generated.unified_post || generated.post_text || '');
                        snippetHtml = `<div style="font-size:12.5px;line-height:1.7;color:var(--text);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">${txt}</div>`;
                    } else if (item.content_type === 'CAROUSEL') {
                        snippetHtml = `<div style="font-size:12.5px;line-height:1.6;color:var(--text);">
                            <b style="color:var(--muted);font-size:11px;">العنوان</b><br>${generated && generated.title || ''}
                            ${generated && generated.slides && generated.slides[0] ? `<br><b style="color:var(--muted);font-size:11px;margin-top:6px;display:block;">الشريحة الأولى</b><br>${generated.slides[0].heading || ''}` : ''}
                        </div>`;
                    } else if (item.content_type === 'VIDEO_SCRIPT') {
                        snippetHtml = `<div style="font-size:12.5px;line-height:1.6;color:var(--text);">
                            <b style="color:#fb923c;font-size:11px;">Hook</b><br>${generated && generated.hook || ''}
                            ${generated && generated.body ? `<br><b style="color:var(--muted);font-size:11px;margin-top:6px;display:block;">Body</b><br><span style="display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">${generated.body}</span>` : ''}
                        </div>`;
                    }

                    // Carousel image generation controls
                    let carouselControls = '';
                    if (item.content_type === 'CAROUSEL') {
                        const hasUrls = generated && generated.carousel_urls && generated.carousel_urls.length > 0;
                        carouselControls = `<div style="margin-bottom:10px;display:flex;gap:6px;">
                            <button class="btn" style="background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff;border:none;padding:8px 14px;font-size:12.5px;border-radius:9px;cursor:pointer;flex:1;display:flex;justify-content:center;gap:6px;" onclick="openTemplatePickerModal(${item.id})">
                                ✨ ${hasUrls ? 'إعادة توليد الكاروسيل' : 'توليد الكاروسيل بالصور'}
                            </button>
                            ${hasUrls ? `
                            <button class="btn" style="background:rgba(59,130,246,0.15);color:#60a5fa;border:1px solid rgba(59,130,246,0.3);padding:8px 12px;border-radius:9px;cursor:pointer;font-size:12.5px;" onclick="openSwiperModal(${JSON.stringify(generated.carousel_urls).replace(/"/g,'&quot;')}, ${JSON.stringify(articleTitle).replace(/"/g,'&quot;')})">👀</button>
                            <button class="btn" style="background:rgba(239,68,68,0.12);color:#ef4444;border:1px solid rgba(239,68,68,0.25);padding:8px 10px;border-radius:9px;cursor:pointer;font-size:12.5px;" onclick="deleteCarouselSlides(${item.id})">🗑️</button>` : ''}
                        </div>`;
                    }

                    subCardsHtml += `
                    <div id="review-card-${item.id}" style="background:var(--bg);border:1px solid var(--line);border-radius:13px;padding:14px;display:flex;flex-direction:column;gap:10px;transition:border-color .15s;" onmouseover="this.style.borderColor='rgba(53,211,153,0.3)'" onmouseout="this.style.borderColor='var(--line)'">
                        <!-- Type badge + platforms -->
                        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;">
                            <span style="font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;background:${tm.bg};color:${tm.color};">${tm.label}</span>
                            <span style="font-size:11px;color:var(--muted);">${platforms}</span>
                        </div>
                        <!-- Snippet -->
                        <div style="flex:1;">${snippetHtml}</div>
                        <!-- Carousel controls -->
                        ${carouselControls}
                        <!-- Actions -->
                        <div style="display:flex;gap:7px;padding-top:8px;border-top:1px solid var(--line);">
                            <button class="btn ghost" style="color:var(--red);padding:6px 10px;font-size:12.5px;" onclick="rejectContentItem(${item.id}, this)">رفض</button>
                            <button class="btn ghost" style="padding:6px 10px;font-size:12.5px;" onclick="openEditModal(${item.id})">تعديل</button>
                            <button class="btn" style="background:var(--teal);color:#000;padding:6px 12px;flex-grow:1;font-size:12.5px;" onclick="openPreviewModal(${item.id}, this)">عرض</button>
                        </div>
                    </div>`;
                });

                reviewList.innerHTML += `
                <div style="grid-column: 1 / -1;">
                  <div style="border:1px solid rgba(255,255,255,0.07); border-radius:20px; background:var(--panel); overflow:hidden; margin-bottom:6px; box-shadow:0 4px 24px rgba(0,0,0,0.3);">
                    <!-- Article header row - Premium Design -->
                    <div style="display:flex;align-items:center;gap:16px;padding:18px 22px;border-bottom:1px solid rgba(255,255,255,0.06);background:linear-gradient(135deg,rgba(53,211,153,0.06) 0%,rgba(100,80,255,0.04) 50%,transparent 100%); position:relative; overflow:hidden;">
                        <!-- Decorative glow -->
                        <div style="position:absolute;top:-30px;right:-30px;width:120px;height:120px;background:radial-gradient(circle,rgba(53,211,153,0.12),transparent 70%);pointer-events:none;"></div>
                        
                        <!-- Image -->
                        ${articleImage 
                            ? `<img src="${articleImage}" style="width:64px;height:64px;object-fit:cover;border-radius:14px;flex-shrink:0;box-shadow:0 6px 20px rgba(0,0,0,0.4);border:2px solid rgba(255,255,255,0.08);" onerror="this.style.display='none'">`
                            : `<div style="width:64px;height:64px;border-radius:14px;background:linear-gradient(135deg,rgba(53,211,153,0.15),rgba(100,80,255,0.1));border:1px solid rgba(255,255,255,0.08);flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:26px;box-shadow:0 6px 20px rgba(0,0,0,0.3);">📰</div>`}
                        
                        <!-- Text content -->
                        <div style="flex:1;min-width:0;">
                            <div style="font-size:16px;font-weight:800;color:#fff;line-height:1.4;margin-bottom:8px;letter-spacing:-0.2px;">${articleTitle}</div>
                            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                                <span style="display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;background:rgba(255,255,255,0.07);color:rgba(255,255,255,0.5);border:1px solid rgba(255,255,255,0.07);">📡 ${articleSource}</span>
                                ${articleDate ? `<span style="display:inline-flex;align-items:center;gap:4px;font-size:11px;padding:3px 10px;border-radius:20px;background:rgba(255,255,255,0.04);color:rgba(255,255,255,0.35);">🗓️ ${articleDate}</span>` : ''}
                                <span style="display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:700;padding:3px 12px;border-radius:20px;background:rgba(53,211,153,0.12);color:var(--teal);border:1px solid rgba(53,211,153,0.2);">✨ ${groupItems.length} ${groupItems.length === 1 ? 'صيغة' : 'صيغ'} مُولَّدة</span>
                            </div>
                        </div>
                    </div>
                    <!-- Sub-cards grid -->
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px;padding:16px 18px;">
                        ${subCardsHtml}
                    </div>
                  </div>
                </div>`;
            });

            if (generatingData.length > 0) setTimeout(fetchReviewContent, 3000);
        }
    } catch(err) {
        console.error(err);
    }
}


window.currentWeekOffset = 0;

function changeWeek(offset) {
    window.currentWeekOffset += offset;
    fetchScheduledContent();
}

function getWeekRange(offset) {
    const now = new Date();
    const dayOfWeek = now.getDay();
    const diffToSat = dayOfWeek === 6 ? 0 : dayOfWeek + 1;
    
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - diffToSat + (offset * 7));
    startOfWeek.setHours(0,0,0,0);
    
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    endOfWeek.setHours(23,59,59,999);
    
    return { startOfWeek, endOfWeek };
}

async function fetchScheduledContent() {
    try {
        const res = await fetch(`${API_BASE}/content/scheduled?_t=${Date.now()}`);
        if (!res.ok) return;
        const data = await res.json();
        
        // Clear all days
        for(let i=0; i<=6; i++) {
            const el = document.querySelector(`#cal-day-${i} .cal-content`);
            if (el) el.innerHTML = '';
        }
        
        const { startOfWeek, endOfWeek } = getWeekRange(window.currentWeekOffset);
        
        // Update Week Display
        const weekDisplay = document.getElementById('current-week-display');
        if (weekDisplay) {
            if (window.currentWeekOffset === 0) weekDisplay.innerText = "الأسبوع الحالي";
            else if (window.currentWeekOffset === 1) weekDisplay.innerText = "الأسبوع القادم";
            else if (window.currentWeekOffset === -1) weekDisplay.innerText = "الأسبوع السابق";
            else weekDisplay.innerText = `${startOfWeek.toLocaleDateString('en-GB')} - ${endOfWeek.toLocaleDateString('en-GB')}`;
        }
        
        // Update column headers with exact dates
        for (let i = 0; i <= 6; i++) {
            const calDayMapping = { 6: 0, 0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6 }; 
            const d = new Date(startOfWeek);
            d.setDate(startOfWeek.getDate() + calDayMapping[i]);
            
            const titleSpan = document.querySelector(`#cal-day-${i} h4 .d`);
            if (titleSpan) {
                titleSpan.innerText = `${d.getDate()}/${d.getMonth()+1}`;
                titleSpan.style.color = 'var(--teal)';
                titleSpan.style.fontSize = '10px';
                titleSpan.style.marginRight = '8px';
                
                // Highlight today
                const today = new Date();
                if (d.getDate() === today.getDate() && d.getMonth() === today.getMonth() && d.getFullYear() === today.getFullYear()) {
                    document.querySelector(`#cal-day-${i}`).style.borderColor = 'var(--teal)';
                    document.querySelector(`#cal-day-${i}`).style.background = 'rgba(20, 184, 166, 0.05)';
                } else {
                    document.querySelector(`#cal-day-${i}`).style.borderColor = 'var(--line)';
                    document.querySelector(`#cal-day-${i}`).style.background = 'var(--panel-2)';
                }
            }
        }
        
        data.forEach(item => {
            if (!item.scheduled_at) return;
            const date = new Date(item.scheduled_at);
            
            // Check if it belongs to current week view
            if (date < startOfWeek || date > endOfWeek) return;

            const dayOfWeek = date.getDay(); // 0 = Sunday, 6 = Saturday
            const container = document.querySelector(`#cal-day-${dayOfWeek} .cal-content`);
            
            if (container) {
                let generated = typeof item.generated_content === 'string' ? JSON.parse(item.generated_content) : (item.generated_content || {});
                let title = item.raw_article ? item.raw_article.title : 'بدون عنوان';
                if (generated && generated.trend_title) {
                    title = `🔥 ترند: ${generated.trend_title}`;
                }
                if (item.content_type === 'CAROUSEL' && generated.title) {
                    title = generated.title;
                }
                
                // Format Date and Time
                let hours = date.getHours();
                let minutes = date.getMinutes();
                const ampm = hours >= 12 ? 'م' : 'ص';
                hours = hours % 12;
                hours = hours ? hours : 12;
                minutes = minutes < 10 ? '0' + minutes : minutes;
                const timeStr = `${hours}:${minutes}${ampm}`;
                const dateStr = `${date.getDate()}/${date.getMonth() + 1}`;
                
                // Platform badge
                let platforms = item.platform || item.platforms || '';
                if (Array.isArray(platforms)) platforms = platforms.join(',');
                platforms = platforms.toLowerCase();
                let platClass = '';
                let platShort = '';
                
                if (platforms.includes('instagram') || platforms.includes('ig')) { platClass = 'ig'; platShort = 'IG'; }
                else if (platforms.includes('tiktok') || platforms.includes('tt')) { platClass = 'tt'; platShort = 'TT'; }
                else if (platforms.includes('facebook') || platforms.includes('fb')) { platClass = 'fb'; platShort = 'FB'; }
                else if (platforms.includes('linkedin') || platforms.includes('li')) { platClass = 'li'; platShort = 'LI'; }
                else if (platforms.includes('x') || platforms.includes('twitter')) { platClass = 'x'; platShort = 'X'; }
                else if (platforms.includes('th') || platforms.includes('threads')) { platClass = 'th'; platShort = 'TH'; }
                else { platClass = 'fb'; platShort = platforms.substring(0,2).toUpperCase(); }
                
                // Content type badge
                let cType = item.content_type || 'POST';
                let cTypeAr = 'بوست';
                if (cType.toUpperCase() === 'CAROUSEL') cTypeAr = 'كاروسيل';
                else if (cType.toUpperCase() === 'VIDEO') cTypeAr = 'فيديو';
                
                container.innerHTML += `
                    <div class="cal-slot plat-${platClass}">
                        <div class="cal-slot-top">
                            <div class="cal-slot-time">${timeStr}</div>
                            <div class="cal-slot-plat ${platClass}">${platShort}</div>
                        </div>
                        <div class="cal-slot-title" title="${title}">${title}</div>
                        <div class="cal-slot-bottom">
                            <div class="cal-slot-date">${dateStr}</div>
                            <div class="cal-slot-type type-${cType.toLowerCase()}">${cTypeAr}</div>
                        </div>
                    </div>
                `;
            }
        });
        
    } catch(err) {
        console.error("Error fetching scheduled content:", err);
    }
}

async function renderCarouselImages(id, templateId, textColor = null, accentColor = null, btnElement = null) {
    let btn = btnElement;
    if (!btn) {
        // Fallback to finding the generate button if triggered from modal
        btn = document.querySelector(`button[onclick="openTemplatePickerModal(${id})"]`);
    }
    
    if (btn) {
        btn.innerHTML = '⌛ جاري توليد الصور...';
        btn.disabled = true;
    }

    try {
        let url = `${API_BASE}/content/${id}/render-carousel`;
        if (templateId) url += `?template_id=${templateId}`;
        if (textColor) url += `${templateId ? '&' : '?'}custom_text_color=${encodeURIComponent(textColor)}`;
        if (accentColor) url += `&custom_accent_color=${encodeURIComponent(accentColor)}`;

        const res = await fetch(url, { method: 'POST' });
        if (!res.ok) { showToast('حدث خطأ في التوليد', 'error'); return; }

        showToast('جاري توليد الصور... ستظهر خلال ثواني', 'success');
        if (btn) btn.innerHTML = '⏳ جاري المعالجة...';

        // Poll until ready
        let attempts = 0;
        const poll = async () => {
            attempts++;
            const r2 = await fetch(`${API_BASE}/content/${id}/carousel-slides`);
            const slides = await r2.json();
            if (slides.ready) {
                if (slides.error) {
                    btn.innerHTML = '❌ خطأ في المعالجة';
                    btn.style.background = '#b91c1c';
                    let errorMsg = slides.error;
                    const errMatch = errorMsg.match(/\[err\]\s*(.*?)(?=\n|$)/);
                    if (errMatch) {
                        errorMsg = errMatch[1].trim();
                    } else if (errorMsg.length > 200) {
                        errorMsg = errorMsg.substring(0, 200) + '...';
                    }
                    showToast(`فشل توليد الصور: ${errorMsg}`, 'error');
                    return;
                }
                if (window.reviewItemsData && window.reviewItemsData[id]) {
                    window.reviewItemsData[id].carousel_urls = slides.slides;
                }
                if (window.reviewItemsDataRaw && window.reviewItemsDataRaw[id]) {
                    let gen = window.reviewItemsDataRaw[id].generated_content || {};
                    if (typeof gen === 'string') {
                        try { gen = JSON.parse(gen); } catch(e){}
                    }
                    gen.carousel_urls = slides.slides;
                    window.reviewItemsDataRaw[id].generated_content = gen;
                }
                
                const container = document.getElementById(`carousel-slides-${id}`);
                if (container) {
                    container.style.display = 'flex';
                    container.style.flexDirection = 'row';
                    container.style.flexWrap = 'nowrap';
                    container.style.alignItems = 'stretch';
                    container.style.width = '100%';
                    // Pass slides directly as a JSON string to avoid global variable conflicts
                    const slidesJson = JSON.stringify(slides.slides).replace(/"/g, '&quot;');
                    container.innerHTML = `
                        <button class="btn" style="flex:1; background:linear-gradient(135deg,#3b82f6,#2563eb); color:#fff; border:none; padding:8px 12px; font-size:13px; border-radius:8px; cursor:pointer;" onclick="openSwiperModal(${slidesJson}, ${JSON.stringify(articleTitle || '').replace(/"/g,'&quot;')})">
                            👀 معاينة
                        </button>
                        <button class="btn" style="background:rgba(239, 68, 68, 0.15); color:#ef4444; border:1px solid rgba(239, 68, 68, 0.3); padding:8px; border-radius:8px; cursor:pointer; width:45px; display:flex; align-items:center; justify-content:center; transition:all 0.2s;" onmouseover="this.style.background='rgba(239, 68, 68, 0.25)'" onmouseout="this.style.background='rgba(239, 68, 68, 0.15)'" onclick="deleteCarouselSlides(${id})" title="حذف الصور">
                            🗑️
                        </button>
                    `;
                }
                btn.innerHTML = `✅ تم توليد ${slides.count} صورة`;
                btn.style.background = '#166534';
                showToast(`تم توليد ${slides.count} صور بنجاح! اضغط على "معاينة الكاروسيل"`, 'success');
            } else if (attempts < 90) {
                setTimeout(poll, 2000);
            } else {
                btn.innerHTML = orig;
                btn.disabled = false;
                showToast('انتهت المدة المحددة, حاول مرة تانية', 'error');
            }
        };
        setTimeout(poll, 3000);

    } catch(err) {
        console.error(err);
        btn.innerHTML = orig;
        btn.disabled = false;
        showToast('خطأ في الاتصال بالخادم', 'error');
    }
}
function showConfirm(title, message, onConfirm) {
    const modal = document.getElementById('custom-confirm-modal');
    const content = document.getElementById('custom-confirm-content');
    document.getElementById('custom-confirm-title').innerText = title;
    document.getElementById('custom-confirm-message').innerText = message;
    
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.style.opacity = '1';
        content.style.transform = 'scale(1)';
    }, 10);
    
    document.getElementById('custom-confirm-cancel').onclick = () => {
        modal.style.opacity = '0';
        content.style.transform = 'scale(0.95)';
        setTimeout(() => modal.style.display = 'none', 200);
    };
    
    document.getElementById('custom-confirm-ok').onclick = function() {
        if (this.disabled) return;
        this.disabled = true;
        
        modal.style.opacity = '0';
        content.style.transform = 'scale(0.95)';
        setTimeout(() => {
            modal.style.display = 'none';
            this.disabled = false;
        }, 200);
        
        onConfirm();
    };
}

async function deleteCarouselSlides(id) {
    showConfirm(
        'تأكيد حذف صور الكاروسيل', 
        'هل أنت متأكد من رغبتك في حذف جميع الصور الخاصة بهذا الكاروسيل؟', 
        async () => {
            try {
                const res = await fetch(`${API_BASE}/content/${id}/carousel-slides`, { method: 'DELETE' });
                if (!res.ok) { showToast('حدث خطأ أثناء الحذف', 'error'); return; }
                
                showToast('تم حذف الصور بنجاح', 'success');
                // Refresh the UI to reflect deletion
                fetchReviewContent();
                fetchAllContent();
            } catch (e) {
                console.error(e);
                showToast('حدث خطأ أثناء الحذف', 'error');
            }
        }
    );
}

// ---------------- TEMPLATE PICKER MODAL ----------------
// ── Color swatch helpers for template picker ──
function setTplColor(type, hex) {
    if (type === 'text') {
        const el = document.getElementById('modal-text-color');
        const preview = document.getElementById('modal-text-color-preview');
        if (el) el.value = hex;
        if (preview) preview.style.background = hex;
    } else {
        const el = document.getElementById('modal-accent-color');
        const preview = document.getElementById('modal-accent-color-preview');
        if (el) el.value = hex;
        if (preview) preview.style.background = hex;
    }
    // Highlight selected swatch
    document.querySelectorAll('.clr-swatch').forEach(s => s.style.boxShadow = '');
    event.target.style.boxShadow = '0 0 0 3px rgba(255,255,255,0.7)';
}

function resetTplColors() {
    const textEl = document.getElementById('modal-text-color');
    const accentEl = document.getElementById('modal-accent-color');
    const textPrev = document.getElementById('modal-text-color-preview');
    const accentPrev = document.getElementById('modal-accent-color-preview');
    if (textEl) { textEl.value = '#ffffff'; if (textPrev) textPrev.style.background = '#ffffff'; }
    if (accentEl) { accentEl.value = '#facc15'; if (accentPrev) accentPrev.style.background = '#facc15'; }
    document.querySelectorAll('.clr-swatch').forEach(s => s.style.boxShadow = '');
}

function openTemplatePickerModal(contentId) {
    const modal = document.getElementById('template-picker-modal');
    const grid = document.getElementById('template-picker-grid');
    const content = document.getElementById('template-picker-content');
    
    // Build Grid
    grid.style.display = 'grid';
    grid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(200px, 1fr))';
    grid.style.gap = '20px';
    
    let html = `
        <div onclick="selectTemplateForContent(${contentId}, '')" style="cursor:pointer; background:var(--panel-2); border:1px solid rgba(255,255,255,0.05); border-radius:16px; overflow:hidden; transition:transform 0.2s; display:flex; flex-direction:column; justify-content:center; align-items:center; height:250px;" onmouseover="this.style.transform='translateY(-5px)'; this.style.borderColor='var(--teal)'" onmouseout="this.style.transform='translateY(0)'; this.style.borderColor='rgba(255,255,255,0.05)'">
            <span style="font-size:40px; margin-bottom:15px;">🌟</span>
            <h4 style="margin:0; color:var(--text); font-size:16px;">القالب الافتراضي</h4>
        </div>
    `;
    
    const templates = window._availableTemplates || [];
    templates.forEach(tpl => {
        const bgUrl = tpl.cover_bg_path && tpl.cover_bg_path.startsWith('http')
            ? tpl.cover_bg_path
            : '/' + tpl.cover_bg_path;
        const textClr  = tpl.text_color  || '#ffffff';
        const accentClr = tpl.accent_color || '#facc15';

        html += `
            <div onclick="selectTemplateForContent(${contentId}, ${tpl.id})"
                 style="cursor:pointer; background:var(--panel-2); border:2px solid rgba(255,255,255,0.06); border-radius:16px; overflow:hidden; transition:all 0.2s; display:flex; flex-direction:column; position:relative;"
                 onmouseover="this.style.transform='translateY(-5px)'; this.style.borderColor=accentClr||'var(--teal)'; this.style.boxShadow='0 12px 30px rgba(0,0,0,0.4)'"
                 onmouseout="this.style.transform='translateY(0)'; this.style.borderColor='rgba(255,255,255,0.06)'; this.style.boxShadow='none'">

                <!-- Background + Text Preview -->
                <div style="height:185px; position:relative; background-image:url('${bgUrl}'); background-size:cover; background-position:center; overflow:hidden;">

                    <!-- Dark gradient overlay so text is readable -->
                    <div style="position:absolute; inset:0; background:linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.2) 50%, transparent 100%);"></div>

                    <!-- Accent top bar -->
                    <div style="position:absolute; top:0; right:0; left:0; height:4px; background:${accentClr};"></div>

                    <!-- Sample text overlay -->
                    <div style="position:absolute; bottom:0; right:0; left:0; padding:14px 14px 12px; text-align:right; direction:rtl;">
                        <div style="font-size:11px; font-weight:800; color:${accentClr}; letter-spacing:0.5px; margin-bottom:5px; text-transform:uppercase;">تقنية</div>
                        <div style="font-size:13px; font-weight:700; color:${textClr}; line-height:1.4; text-shadow:0 1px 4px rgba(0,0,0,0.8);">الذكاء الاصطناعي يغير مستقبل التقنية</div>
                    </div>
                </div>

                <!-- Name label -->
                <div style="padding:10px 14px; text-align:center; background:var(--panel-2); border-top:1px solid rgba(255,255,255,0.05);">
                    <h4 style="margin:0; color:var(--text); font-size:14px; font-weight:700;">${tpl.name}</h4>
                </div>
            </div>
        `;
    });
    
    grid.innerHTML = html;
    
    // Prevent background scrolling
    document.body.style.overflow = 'hidden';
    
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.style.opacity = '1';
        content.style.transform = 'scale(1)';
    }, 10);
}

function closeTemplatePickerModal() {
    const modal = document.getElementById('template-picker-modal');
    const content = document.getElementById('template-picker-content');
    
    modal.style.opacity = '0';
    content.style.transform = 'scale(0.95)';
    
    // Restore background scrolling
    document.body.style.overflow = '';
    
    setTimeout(() => {
        modal.style.display = 'none';
    }, 300);
}

function selectTemplateForContent(contentId, templateId) {
    const overrideCheckbox = document.getElementById('modal-override-colors');
    let textColor = null;
    let accentColor = null;
    
    if (overrideCheckbox && overrideCheckbox.checked) {
        textColor = document.getElementById('modal-text-color').value;
        accentColor = document.getElementById('modal-accent-color').value;
    }

    closeTemplatePickerModal();
    renderCarouselImages(contentId, templateId, textColor, accentColor);
}

// ────────────────────────────────────────────────────
// CONTENT PREVIEW MODAL
// ────────────────────────────────────────────────────
let currentApproveId = null;
let currentApproveBtn = null;
let previewScheduleMode = false;

const PLATFORM_INFO = {
    'FB':  { name:'Facebook',  icon:'🔵', color:'#1877f2', textColor:'#fff', bg:'#1877f2' },
    'IG':  { name:'Instagram', icon:'🟣', color:'#e1306c', textColor:'#fff', bg:'linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888)' },
    'X':   { name:'X (تويتر)', icon:'⚫', color:'#000',    textColor:'#fff', bg:'#000' },
    'Li':  { name:'LinkedIn',  icon:'🔷', color:'#0077b5', textColor:'#fff', bg:'#0077b5' },
    'TT':  { name:'TikTok',    icon:'🖤', color:'#010101', textColor:'#fff', bg:'#010101' },
    'Th':  { name:'Threads',   icon:'⚫', color:'#101010', textColor:'#fff', bg:'#101010' },
    'SC':  { name:'Snapchat',  icon:'🟡', color:'#fffc00', textColor:'#000', bg:'#fffc00' },
};

function openPreviewModal(id, btn) {
    currentApproveId = id;
    currentApproveBtn = btn;

    const item = window.reviewItemsDataRaw ? window.reviewItemsDataRaw[id] : null;
    if (!item) { openApproveOptionsModal(id, btn); return; }

    let gen = item.generated_content || {};
    if (typeof gen === 'string') { try { gen = JSON.parse(gen); } catch(e) {} }

    // Figure out platforms
    let platforms = [];
    if (Array.isArray(item.platforms)) platforms = item.platforms;
    else if (typeof item.platforms === 'string') platforms = item.platforms.split(',');

    // Build tabs
    const tabsEl = document.getElementById('preview-tabs');
    tabsEl.innerHTML = '';

    const activePlatforms = platforms.filter(p => PLATFORM_INFO[p]);
    if (activePlatforms.length === 0) {
        // no known platforms, skip preview
        openApproveOptionsModal(id, btn);
        return;
    }

    activePlatforms.forEach((pId, i) => {
        const p = PLATFORM_INFO[pId];
        const btn2 = document.createElement('button');
        btn2.style.cssText = `display:flex;align-items:center;gap:6px;padding:10px 14px;border-radius:10px 10px 0 0;font-size:12.5px;color:var(--muted);cursor:pointer;border:1px solid transparent;border-bottom:none;background:transparent;transition:all .15s;position:relative;top:1px;font-family:inherit;white-space:nowrap;`;
        btn2.innerHTML = `${p.icon} ${p.name}`;
        if (i === 0) {
            btn2.style.color = 'var(--text)';
            btn2.style.background = 'var(--bg)';
            btn2.style.borderColor = 'var(--line)';
            btn2.style.borderBottom = '1px solid var(--bg)';
        }
        btn2.onclick = () => {
            tabsEl.querySelectorAll('button').forEach(b => {
                b.style.color = 'var(--muted)'; b.style.background = 'transparent'; b.style.borderColor = 'transparent'; b.style.borderBottom = 'none';
            });
            btn2.style.color = 'var(--text)'; btn2.style.background = 'var(--bg)'; btn2.style.borderColor = 'var(--line)'; btn2.style.borderBottom = '1px solid var(--bg)';
            renderPreview(pId, gen, item);
        };
        tabsEl.appendChild(btn2);
    });

    // Show first tab
    renderPreview(activePlatforms[0], gen, item);

    // Show modal
    const modal = document.getElementById('preview-modal');
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.style.opacity = '1';
        document.getElementById('preview-modal-content').style.transform = 'scale(1)';
    }, 10);
}

function renderPreview(platformId, gen, item) {
    const area = document.getElementById('preview-area');
    const p = PLATFORM_INFO[platformId] || { name: platformId, color:'#333', textColor:'#fff' };
    const type = item.content_type;

    let postText = '';
    if (type === 'POST') {
        if (platformId === 'Li' && gen.linkedin_post) postText = gen.linkedin_post;
        else postText = gen.unified_post || gen.post_text || JSON.stringify(gen);
    } else if (type === 'VIDEO_SCRIPT') {
        postText = (gen.hook ? gen.hook + '\n\n' : '') + (gen.body || '') + (gen.call_to_action ? '\n\n' + gen.call_to_action : '');
    } else if (type === 'CAROUSEL') {
        postText = gen.title || '';
    }

    const escHtml = (s) => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ar-SA', { hour:'2-digit', minute:'2-digit' });

    // Resolve the image to show in the preview
    const previewImg = (type === 'POST')
        ? (gen.image_url || (item.raw_article && item.raw_article.image_url) || null)
        : null;

    const imgBlock = (height = '220px') => previewImg
        ? `<img src="${previewImg}" style="width:100%;height:${height};object-fit:cover;display:block;" onerror="this.style.display='none'">`
        : `<div style="width:100%;height:${height};background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);display:flex;align-items:center;justify-content:center;"><span style="font-size:48px;">📸</span></div>`;

    let mockupHtml = '';

    if (platformId === 'FB' || platformId === 'Li') {
        const headerColor = platformId === 'Li' ? '#0077b5' : '#1877f2';
        const platformName = platformId === 'Li' ? 'LinkedIn' : 'Facebook';
        mockupHtml = `
        <div style="background:#fff; border-radius:14px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.3); font-family:'Segoe UI',sans-serif; direction:ltr;">
            <div style="background:${headerColor}; padding:12px 16px; display:flex; align-items:center; gap:10px;">
                <div style="width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,0.25);display:flex;align-items:center;justify-content:center;font-size:18px;">👤</div>
                <div><div style="color:#fff;font-weight:700;font-size:14px;">غرفة المحتوى</div><div style="color:rgba(255,255,255,0.7);font-size:11px;">${timeStr} · 🌐 ${platformName}</div></div>
            </div>
            <div style="padding:14px 16px; color:#1c1e21; font-size:14px; line-height:1.75; text-align:right; direction:rtl;">${escHtml(postText)}</div>
            ${imgBlock('220px')}
            <div style="padding:10px 16px 12px; border-top:1px solid #e4e6eb; display:flex; gap:22px; color:#65676b; font-size:13px;">
                <span>👍 إعجاب</span><span>💬 تعليق</span><span>↗️ مشاركة</span>
            </div>
        </div>`;
    } else if (platformId === 'IG') {
        mockupHtml = `
        <div style="background:#fff; border-radius:14px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.3); font-family:-apple-system,sans-serif; direction:ltr;">
            <div style="padding:10px 12px; display:flex; align-items:center; gap:10px; border-bottom:1px solid #efefef;">
                <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366);padding:2px;"><div style="width:100%;height:100%;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;">📸</div></div>
                <div style="font-weight:600;font-size:13px;color:#000;">content_machine</div>
                <div style="margin-right:auto;color:#0095f6;font-size:12px;font-weight:600;">متابعة</div>
            </div>
            ${imgBlock('260px')}
            <div style="padding:10px 12px;">
                <div style="display:flex;gap:14px;margin-bottom:8px;font-size:22px;">❤️ 💬 ✈️</div>
                <div style="font-size:13px;color:#000;line-height:1.5;text-align:right;direction:rtl;"><b>content_machine</b> ${escHtml(postText.substring(0,200))}${postText.length>200?'...':''}</div>
                <div style="color:#8e8e8e;font-size:11px;margin-top:6px;">${timeStr}</div>
            </div>
        </div>`;
    } else if (platformId === 'X') {
        mockupHtml = `
        <div style="background:#000; border-radius:14px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.5); font-family:-apple-system,sans-serif; color:#fff; padding:16px; direction:ltr;">
            <div style="display:flex; gap:12px;">
                <div style="width:40px;height:40px;border-radius:50%;background:#333;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:18px;">👤</div>
                <div style="flex:1;">
                    <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                        <span style="font-weight:700;font-size:14px;">غرفة المحتوى</span>
                        <span style="color:#71767b;font-size:13px;">@content_machine · ${timeStr}</span>
                    </div>
                    <div style="font-size:14px;line-height:1.7;text-align:right;direction:rtl;">${escHtml(postText.substring(0,280))}${postText.length>280?'...':''}</div>
                    ${previewImg ? `<img src="${previewImg}" style="width:100%;border-radius:12px;margin-top:10px;max-height:200px;object-fit:cover;" onerror="this.style.display='none'">` : ''}
                    <div style="display:flex;gap:20px;margin-top:12px;color:#71767b;font-size:13px;">
                        <span>💬 رد</span><span>🔁 إعادة تغريد</span><span>❤️ إعجاب</span>
                    </div>
                </div>
            </div>
        </div>`;
    } else if (platformId === 'TT' || platformId === 'Th') {
        const bgColor = platformId === 'TT' ? '#010101' : '#101010';
        mockupHtml = `
        <div style="background:${bgColor}; border-radius:14px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.5); color:#fff; font-family:-apple-system,sans-serif; direction:ltr;">
            ${imgBlock('180px')}
            <div style="padding:14px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                    <div style="width:32px;height:32px;border-radius:50%;background:#333;display:flex;align-items:center;justify-content:center;">${platformId === 'TT' ? '🎬' : '🧵'}</div>
                    <span style="font-weight:700;font-size:13px;">content_machine</span>
                </div>
                <div style="font-size:13px;line-height:1.6;text-align:right;direction:rtl;">${escHtml(postText.substring(0,250))}${postText.length>250?'...':''}</div>
                <div style="display:flex;gap:16px;margin-top:12px;color:#aaa;font-size:12px;">
                    <span>❤️ إعجاب</span><span>💬 تعليق</span><span>↗️ مشاركة</span>
                </div>
            </div>
        </div>`;
    } else {
        mockupHtml = `<div style="background:var(--panel);border-radius:14px;padding:20px;border:1px solid var(--line);"><div style="font-size:14px;line-height:1.8;text-align:right;direction:rtl;color:var(--text);">${escHtml(postText)}</div></div>`;
    }


    // Carousel extra info
    let extraHtml = '';
    if (type === 'CAROUSEL' && gen.slides && gen.slides.length > 0) {
        extraHtml = `<div style="margin-top:14px;padding:14px;background:var(--panel);border-radius:12px;border:1px solid var(--line);">
            <div style="font-size:12px;color:var(--muted);margin-bottom:10px;">🖼️ شرائح الكاروسيل (${gen.slides.length} شريحة)</div>
            ${gen.slides.slice(0,3).map((s,i) => `<div style="padding:10px;background:var(--bg);border-radius:8px;margin-bottom:8px;"><div style="font-weight:700;font-size:13px;color:var(--text);margin-bottom:4px;">${i+1}. ${escHtml(s.heading||'')}</div><div style="font-size:12px;color:var(--muted);line-height:1.6;">${escHtml((s.body||'').substring(0,100))}${(s.body||'').length>100?'...':''}</div></div>`).join('')}
            ${gen.slides.length > 3 ? `<div style="color:var(--muted);font-size:12px;text-align:center;">+ ${gen.slides.length - 3} شرائح أخرى</div>` : ''}
        </div>`;
    }
    if (type === 'VIDEO_SCRIPT' && gen.visual_cues) {
        extraHtml = `<div style="margin-top:14px;padding:12px;background:rgba(224,181,99,0.08);border-radius:12px;border:1px solid rgba(224,181,99,0.2);">
            <div style="font-size:12px;color:#e0b563;margin-bottom:6px;">🎬 إرشادات بصرية</div>
            <div style="font-size:12px;color:var(--muted);line-height:1.6;text-align:right;direction:rtl;">${escHtml(gen.visual_cues)}</div>
        </div>`;
    }

    area.innerHTML = `<div style="max-width:460px;margin:0 auto;">${mockupHtml}${extraHtml}</div>`;
}

function closePreviewModal() {
    const modal = document.getElementById('preview-modal');
    modal.style.opacity = '0';
    setTimeout(() => modal.style.display = 'none', 220);
}

function confirmFromPreview(scheduleMode) {
    previewScheduleMode = scheduleMode;
    closePreviewModal();
    setTimeout(() => openApproveOptionsModal(currentApproveId, currentApproveBtn, scheduleMode), 250);
}

function openApproveOptionsModal(id, btn, autoSchedule = false) {

    const item = window.reviewItemsDataRaw ? window.reviewItemsDataRaw[id] : null;
    if (item && item.content_type === 'CAROUSEL') {
        let generated = item.generated_content || {};
        if (typeof generated === 'string') {
            try { generated = JSON.parse(generated); } catch(e) {}
        }
        const hasUrls = generated.carousel_urls && generated.carousel_urls.length > 0;
        if (!hasUrls) {
            showToast("يجب توليد صور الكاروسيل أولاً قبل الاعتماد", "error");
            return;
        }
    }

    currentApproveId = id;
    currentApproveBtn = btn;
    
    document.getElementById('schedule-picker-container').style.display = 'none';
    document.getElementById('schedule-submit-container').style.display = 'none';
    document.getElementById('approve-buttons-container').style.display = 'flex';
    document.getElementById('schedule-date-input').value = '';
    document.getElementById('schedule-time-input').value = '';
    
    // Setup Platform Checkboxes
    const platformContainer = document.getElementById('approve-platform-checkboxes');
    if (platformContainer) {
        let currentPlatforms = [];
        if (Array.isArray(item.platforms)) currentPlatforms = item.platforms;
        else if (typeof item.platforms === 'string') currentPlatforms = item.platforms.split(',');
        
        currentPlatforms = currentPlatforms.map(p => p.toUpperCase().trim());
        const allPlatforms = [
            { id: 'IG', name: 'Instagram' },
            { id: 'FB', name: 'Facebook' },
            { id: 'X', name: 'X (تويتر)' },
            { id: 'TT', name: 'TikTok' },
            { id: 'TH', name: 'Threads' },
            { id: 'LI', name: 'LinkedIn' },
            { id: 'SC', name: 'Snapchat' }
        ];
        
        const activeStyle = "padding:8px 18px; border-radius:30px; background:var(--teal); border:1px solid var(--teal); color:#000; font-size:14px; font-weight:700; transition:all 0.2s; box-shadow:0 4px 12px rgba(20,184,166,0.3); display:inline-flex; align-items:center; gap:6px;";
        const inactiveStyle = "padding:8px 18px; border-radius:30px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); color:var(--muted); font-size:14px; font-weight:600; transition:all 0.2s; display:inline-flex; align-items:center; gap:6px;";

        platformContainer.innerHTML = allPlatforms.map(p => {
            const isChecked = currentPlatforms.includes(p.id);
            const styleStr = isChecked ? activeStyle : inactiveStyle;
            const icon = isChecked ? '✓' : '+';
            return `
            <label style="cursor:pointer; user-select:none;" onmouseover="if(!this.querySelector('input').checked) this.children[1].style.background='rgba(255,255,255,0.1)'" onmouseout="if(!this.querySelector('input').checked) this.children[1].style.background='rgba(255,255,255,0.05)'">
                <input type="checkbox" value="${p.id}" class="approve-platform-cb" style="display:none;" 
                    onchange="this.nextElementSibling.style.cssText = this.checked ? '${activeStyle}' : '${inactiveStyle}'; this.nextElementSibling.firstElementChild.innerText = this.checked ? '✓' : '+';" 
                    ${isChecked ? 'checked' : ''}>
                <div style="${styleStr}">
                    <span style="font-size:12px; font-weight:bold;">${icon}</span> ${p.name}
                </div>
            </label>
            `;
        }).join('');
    }
    
    const modal = document.getElementById('approve-options-modal');
    const content = document.getElementById('approve-options-content');
    modal.style.display = 'flex';
    setTimeout(() => {
        modal.style.opacity = '1';
        content.style.transform = 'scale(1)';
    }, 10);
}

function closeApproveModal() {
    const modal = document.getElementById('approve-options-modal');
    const content = document.getElementById('approve-options-content');
    modal.style.opacity = '0';
    content.style.transform = 'scale(0.95)';
    setTimeout(() => modal.style.display = 'none', 200);
}

document.getElementById('btn-approve-cancel').onclick = closeApproveModal;

document.getElementById('btn-approve-direct').onclick = async function() {
    if (!currentApproveId || !currentApproveBtn) return;
    const btn = currentApproveBtn;
    const id = currentApproveId;
    closeApproveModal();
    
    const orig = btn.innerText;
    btn.innerText = 'جاري الاعتماد...';
    btn.disabled = true;
    try {
        const selectedPlatforms = Array.from(document.querySelectorAll('.approve-platform-cb:checked')).map(cb => cb.value);
        
        const res = await fetch(`${API_BASE}/content/${id}/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ platforms: selectedPlatforms })
        });
        if (res.ok) {
            btn.closest('.panel').style.opacity = '0.4';
            closeApproveModal();
            showToast("تم اعتماد المحتوى بنجاح", "success");
            fetchScheduledContent();
            setTimeout(fetchReviewContent, 1000);
            fetchDashboardStats();
            fetchAllContent();
        } else {
            const errData = await res.json().catch(() => ({}));
            const errMsg = errData.detail || "حدث خطأ أثناء الاعتماد";
            showToast(errMsg, "error");
            btn.innerText = orig;
            btn.disabled = false;
        }
    } catch (err) {
        showToast("خطأ اتصال", "error");
        btn.innerText = orig;
        btn.disabled = false;
    }
};

document.getElementById('btn-approve-schedule-show').onclick = function() {
    document.getElementById('approve-buttons-container').style.display = 'none';
    document.getElementById('schedule-picker-container').style.display = 'block';
    document.getElementById('schedule-submit-container').style.display = 'flex';
};

document.getElementById('btn-schedule-cancel').onclick = function() {
    document.getElementById('schedule-picker-container').style.display = 'none';
    document.getElementById('schedule-submit-container').style.display = 'none';
    document.getElementById('approve-buttons-container').style.display = 'flex';
};

document.getElementById('btn-schedule-confirm').onclick = async function() {
    if (!currentApproveId || !currentApproveBtn) return;
    const dateVal = document.getElementById('schedule-date-input').value;
    const timeVal = document.getElementById('schedule-time-input').value;
    if (!dateVal || !timeVal) {
        showToast("يرجى اختيار تاريخ ووقت النشر بشكل كامل", "error");
        return;
    }
    
    // Send local time directly to avoid UTC timezone shifts when saving/fetching
    const scheduledAt = `${dateVal}T${timeVal}:00`;
    
    const btn = currentApproveBtn;
    const id = currentApproveId;
    
    const orig = this.innerText;
    this.innerText = 'جاري الجدولة...';
    this.disabled = true;
    
    try {
        const selectedPlatforms = Array.from(document.querySelectorAll('.approve-platform-cb:checked')).map(cb => cb.value);
        const res = await fetch(`${API_BASE}/content/${id}/schedule`, { 
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scheduled_at: scheduledAt, platforms: selectedPlatforms })
        });
        if (res.ok) {
            closeApproveModal();
            showToast("تم جدولة المحتوى بنجاح", "success");
            fetchScheduledContent(); // Refresh the schedule board immediately
            setTimeout(fetchReviewContent, 1000);
            fetchDashboardStats();
            fetchAllContent();
            
            // Navigate to schedule page automatically
            const scheduleBtn = document.querySelector('.sidebar-menu a[onclick*="page-schedule"]');
            if(scheduleBtn) go(scheduleBtn);
        } else {
            showToast("حدث خطأ أثناء الجدولة", "error");
        }
    } catch (err) {
        showToast("خطأ اتصال", "error");
    } finally {
        this.innerText = orig;
        this.disabled = false;
    }
};

// ── Stuck Article Helpers ──
async function retryStuckArticle(articleId) {
    try {
        showToast('⏳ جاري إعادة تشغيل التوليد...', 'success');
        const res = await fetch(`${API_BASE}/raw-articles/${articleId}/retry`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
            body: JSON.stringify({ formats: ['POST','CAROUSEL','VIDEO_SCRIPT'], carousel_platforms: ['IG','Li'] })
        });
        if (res.ok) {
            showToast('✅ بدأ التوليد من جديد', 'success');
            setTimeout(fetchReviewContent, 2000);
        } else {
            showToast('❌ فشلت إعادة المحاولة', 'error');
        }
    } catch(e) {
        showToast('❌ خطأ في الاتصال', 'error');
    }
}

async function cancelStuckArticle(articleId) {
    try {
        const res = await fetch(`${API_BASE}/raw-articles/reset-stuck`, {
            method: 'POST',
            headers: { ...authHeaders() }
        });
        if (res.ok) {
            showToast('✅ تم إلغاء التوليد وإعادة المقال للقائمة', 'success');
            setTimeout(fetchReviewContent, 1500);
        } else {
            showToast('❌ فشل الإلغاء', 'error');
        }
    } catch(e) {
        showToast('❌ خطأ في الاتصال', 'error');
    }
}

async function rejectContentItem(id, btn) {

    const orig = btn.innerText;
    btn.innerText = 'جاري...';
    btn.disabled = true;
    try {
        const res = await fetch(`${API_BASE}/content/${id}/reject`, { method: "POST" });
        if (res.ok) {
            btn.closest('.panel').style.opacity = '0.4';
            showToast("تم رفض المحتوى وإلغاؤه", "error"); // Red toast
            setTimeout(fetchReviewContent, 1000);
            fetchDashboardStats();
            fetchAllContent();
        } else {
            showToast("حدث خطأ", "error");
            btn.innerText = orig;
            btn.disabled = false;
        }
    } catch (err) {
        showToast("خطأ اتصال", "error");
        btn.innerText = orig;
        btn.disabled = false;
    }
}

async function deleteAllArticles() {
    const confirmed = await new Promise(resolve => {
        const overlay = document.createElement('div');
        overlay.style.cssText = `position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);`;
        overlay.innerHTML = `
            <div style="background:#1a1d2e;border:1px solid rgba(251,146,60,0.4);border-radius:16px;padding:32px;max-width:400px;width:90%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
                <div style="font-size:48px;margin-bottom:16px;">⚠️</div>
                <h3 style="color:#f1f5f9;font-size:18px;margin-bottom:10px;">مسح كل الأخبار</h3>
                <p style="color:#94a3b8;font-size:14px;margin-bottom:24px;line-height:1.6;">سيتم حذف <strong style="color:#fb923c;">جميع الأخبار المسحوبة</strong> بغض النظر عن تاريخها (باستثناء المرتبطة بمنشور مجدول أو منشور). لا يمكن التراجع عن هذا الإجراء.</p>
                <div style="display:flex;gap:12px;justify-content:center;">
                    <button id="del-cancel" style="flex:1;padding:10px 20px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);background:transparent;color:#94a3b8;cursor:pointer;font-size:14px;">إلغاء</button>
                    <button id="del-confirm" style="flex:1;padding:10px 20px;border-radius:10px;border:none;background:linear-gradient(135deg,#fb923c,#f97316);color:#fff;cursor:pointer;font-size:14px;font-weight:600;">نعم، امسح الكل</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);
        overlay.querySelector('#del-cancel').onclick = () => { overlay.remove(); resolve(false); };
        overlay.querySelector('#del-confirm').onclick = () => { overlay.remove(); resolve(true); };
    });
    if (!confirmed) return;

    const btn = event.target;
    const orig = btn.innerHTML;
    btn.innerHTML = '⏳ جاري المسح...';
    btn.disabled = true;
    try {
        const token = localStorage.getItem('cm_token');
        const res = await fetch(`${API_BASE}/sources/delete-all`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        showToast(data.detail || '✅ تم مسح كل الأخبار', 'success');
        fetchRawArticles();
        fetchDashboardStats();
    } catch(e) {
        showToast('❌ حدث خطأ أثناء المسح', 'error');
    } finally {
        btn.innerHTML = orig;
        btn.disabled = false;
    }
}

async function manualCleanup() {
    // Custom styled confirm modal
    const confirmed = await new Promise(resolve => {
        const overlay = document.createElement('div');
        overlay.style.cssText = `position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);`;
        overlay.innerHTML = `
            <div style="background:#1a1d2e;border:1px solid rgba(248,113,113,0.3);border-radius:16px;padding:32px;max-width:400px;width:90%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
                <div style="font-size:48px;margin-bottom:16px;">🗑️</div>
                <h3 style="color:#f1f5f9;font-size:18px;margin-bottom:10px;">مسح الأخبار القديمة</h3>
                <p style="color:#94a3b8;font-size:14px;margin-bottom:24px;line-height:1.6;">سيتم حذف كل الأخبار التي مضى عليها أكثر من 24 ساعة نهائياً. هذا الإجراء لا يمكن التراجع عنه.</p>
                <div style="display:flex;gap:12px;justify-content:center;">
                    <button id="cleanup-cancel" style="flex:1;padding:10px 20px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);background:transparent;color:#94a3b8;cursor:pointer;font-size:14px;">إلغاء</button>
                    <button id="cleanup-confirm" style="flex:1;padding:10px 20px;border-radius:10px;border:none;background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff;cursor:pointer;font-size:14px;font-weight:600;">نعم، امسح</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);
        overlay.querySelector('#cleanup-cancel').onclick = () => { overlay.remove(); resolve(false); };
        overlay.querySelector('#cleanup-confirm').onclick = () => { overlay.remove(); resolve(true); };
    });
    if (!confirmed) return;

    const btn = event.target;
    const orig = btn.innerHTML;
    btn.innerHTML = '⏳ جاري المسح...';
    btn.disabled = true;
    try {
        const token = localStorage.getItem('cm_token');
        const res = await fetch(`${API_BASE}/sources/cleanup-now`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        showToast(data.detail || '✅ تم مسح الأخبار القديمة', 'success');
        fetchRawArticles();
        fetchDashboardStats();
    } catch(e) {
        showToast('❌ حدث خطأ أثناء المسح', 'error');
    } finally {
        btn.innerHTML = orig;
        btn.disabled = false;
    }
}

async function runIngestion() {
    const btn = document.getElementById('btn-run-ingestion');
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.style.cursor = 'wait';

    // Create animated overlay
    const overlay = document.createElement('div');
    overlay.id = 'ingestion-overlay';
    overlay.style.cssText = `
        position:fixed; top:0; left:0; width:100%; height:100%; 
        background:rgba(0,0,0,0.6); backdrop-filter:blur(6px);
        z-index:99999; display:flex; align-items:center; justify-content:center;
    `;
    overlay.innerHTML = `
        <div style="background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:32px 40px; min-width:340px; text-align:center; box-shadow:0 20px 60px rgba(0,0,0,0.5);">
            <h3 style="margin:0 0 8px; color:var(--text); font-size:18px;">جاري سحب الأخبار...</h3>
            <p id="ingestion-step" style="color:var(--muted); font-size:13px; margin-bottom:20px;">جاري الاتصال بالمصادر...</p>
            <div style="background:var(--bg); border-radius:100px; height:6px; overflow:hidden;">
                <div id="ingestion-bar" style="background:var(--teal); height:100%; width:0%; border-radius:100px; transition:width 0.5s ease;"></div>
            </div>
            <p style="color:var(--muted); font-size:11px; margin-top:12px; opacity:0.6;">يستغرق عادةً 30-60 ثانية</p>
        </div>
    `;
    document.body.appendChild(overlay);

    // Animated steps
    const steps = [
        { text: " جاري الاتصال بالمصادر...", pct: 10 },
        { text: " جاري سحب RSS وأخبار الشبكة...", pct: 35 },
        { text: " جاري استخراج المحتوى...", pct: 60 },
        { text: " جاري حفظ الأخبار الجديدة...", pct: 80 },
        { text: " تقريباً خلص...", pct: 95 },
    ];
    let stepIdx = 0;
    const stepEl = document.getElementById('ingestion-step');
    const barEl = document.getElementById('ingestion-bar');
    const stepTimer = setInterval(() => {
        if (stepIdx < steps.length) {
            stepEl.textContent = steps[stepIdx].text;
            barEl.style.width = steps[stepIdx].pct + '%';
            stepIdx++;
        }
    }, 2000);

    try {
        const res = await fetch(`${API_BASE}/sources/run-ingestion`, { method: 'POST' });
        const data = await res.json();
        clearInterval(stepTimer);
        barEl.style.width = '100%';
        stepEl.textContent = '✅ اكتمل السحب بنجاح!';
        
        setTimeout(() => {
            overlay.remove();
            if(res.ok) {
                showToast(data.detail || `تم السحب! 🎉`, "success");
            } else {
                showToast("حدث خطأ أثناء السحب", "error");
            }
            fetchDashboardStats();
            fetchSources();
            fetchRawArticles();
            fetchAllContent();
            fetchReviewContent();
        }, 1000);

    } catch(err) {
        clearInterval(stepTimer);
        overlay.remove();
        console.error(err);
        showToast("حدث خطأ أثناء تشغيل السحب", "error");
    } finally {
        btn.innerHTML = originalHTML;
        btn.style.opacity = '1';
        btn.style.cursor = 'pointer';
        btn.disabled = false;
    }
}

// Load data on start
document.addEventListener('DOMContentLoaded', async () => {
    // Set current date
    const dateDisplay = document.getElementById('current-date-display');
    if (dateDisplay) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        dateDisplay.innerText = "اليوم: " + new Date().toLocaleDateString('ar-EG', options);
    }

    // Setup Content Filters
    document.querySelectorAll('#content-filters .chip').forEach(chip => {
        chip.addEventListener('click', function() {
            document.querySelectorAll('#content-filters .chip').forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            renderContentList();
        });
    });

    loadTemplates(); // Load async without blocking
    fetchDashboardStats();
    fetchSources();
    fetchRawArticles();
    fetchAllContent();
    fetchReviewContent();
    fetchScheduledContent();
    fetchPlatformStatus();

    // Refresh data every 30 seconds
    setInterval(() => {
        fetchDashboardStats();
        fetchRawArticles();
        fetchReviewContent();
        fetchScheduledContent();
        fetchPlatformStatus();
    }, 30000);
});

let swiperInstance = null;

let _currentSwiperSlides = [];
let _currentSwiperTitle = 'carousel';

function openSwiperModal(slidesUrls, title = '') {
    _currentSwiperSlides = slidesUrls;
    _currentSwiperTitle = (title || 'carousel').substring(0, 60).replace(/[^\w\u0600-\u06FF\s-]/g, '').trim() || 'carousel';
    const modal = document.getElementById('swiper-modal');
    const containerWrapper = document.getElementById('swiper-container-wrapper');
    
    // Destroy old instance BEFORE modifying DOM to prevent memory leaks and CSS bugs
    if (swiperInstance) {
        swiperInstance.destroy(true, true);
        swiperInstance = null;
    }
    
    // Completely rebuild Swiper DOM to guarantee zero cached RTL translations
    containerWrapper.innerHTML = `
          <div class="swiper mySwiper" style="width: 100%; padding-top: 50px; padding-bottom: 50px;">
              <div class="swiper-wrapper" id="swiper-wrapper-content">
                  ${slidesUrls.map((url, idx) => `
                      <div class="swiper-slide" style="display:flex; justify-content:center; align-items:center; width: 450px; transition: transform 0.3s;">
                          <a href="${url.startsWith('http') ? url : url}" download="slide_${idx+1}.png" target="_blank" title="اضغط لتحميل الشريحة" style="display:block; width:100%;">
                              <img src="${url.startsWith('http') ? url : url}" style="width:100%; height:auto; object-fit:contain; border-radius:12px; box-shadow:0 20px 50px rgba(0,0,0,0.5); background:#fff;">
                          </a>
                      </div>
                  `).join('')}
              </div>
              <div class="swiper-pagination"></div>
              <div class="swiper-button-next" style="color:#fff;"></div>
              <div class="swiper-button-prev" style="color:#fff;"></div>
          </div>
    `;
    
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    
    // We must wait a tick for display:flex to render before initializing swiper
    setTimeout(() => {
        swiperInstance = new Swiper('.mySwiper', {
            effect: 'slide',
            grabCursor: true,
            centeredSlides: true,
            slidesPerView: 'auto',
            spaceBetween: 40,
            initialSlide: 0,
            observer: true,
            observeParents: true,
            pagination: {
                el: '.swiper-pagination',
                clickable: true,
            },
            navigation: {
                nextEl: '.swiper-button-next',
                prevEl: '.swiper-button-prev',
            },
            keyboard: {
                enabled: true,
                onlyInViewport: false,
            }
        });
        
        // Force layout recalculation to fix RTL centeredSlides offset bugs
        setTimeout(() => {
            if(swiperInstance) {
                swiperInstance.update();
                window.dispatchEvent(new Event('resize'));
            }
        }, 50);
    }, 100);
}

function closeSwiperModal() {
    document.getElementById('swiper-modal').style.display = 'none';
    document.body.style.overflow = '';
}

// ── Carousel Download Functions ──
async function downloadCarouselZip() {
    if (!_currentSwiperSlides || !_currentSwiperSlides.length) { showToast('لا توجد صور للتحميل', 'error'); return; }
    
    const zipName = _currentSwiperTitle || 'carousel';
    showToast('⏳ جاري تجهيز ملف ZIP...', 'success');
    
    try {
        const zip = new JSZip();
        const folder = zip.folder(zipName);
        
        for (let i = 0; i < _currentSwiperSlides.length; i++) {
            const url = _currentSwiperSlides[i];
            try {
                const resp = await fetch(url);
                const blob = await resp.blob();
                folder.file(`slide_${String(i+1).padStart(2,'0')}.png`, blob);
            } catch(e) {
                console.warn('Failed to fetch slide', i, e);
            }
        }
        
        const content = await zip.generateAsync({ type: 'blob' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(content);
        a.download = `${zipName}.zip`;
        a.click();
        showToast(`✅ تم تحميل ${_currentSwiperSlides.length} صور في ملف ZIP`, 'success');
    } catch(err) {
        console.error(err);
        showToast('❌ فشل إنشاء ZIP', 'error');
    }
}

async function downloadCarouselPDF() {
    if (!_currentSwiperSlides || !_currentSwiperSlides.length) { showToast('لا توجد صور للتحميل', 'error'); return; }
    
    const pdfName = _currentSwiperTitle || 'carousel';
    showToast('⏳ جاري إنشاء PDF...', 'success');
    
    // Build printable HTML - page-break ONLY between slides (not after last)
    const imgs = _currentSwiperSlides.map((url, i) => {
        const breakStyle = i < _currentSwiperSlides.length - 1 ? 'page-break-after:always;' : '';
        return `<div style="${breakStyle} display:flex; justify-content:center; align-items:center; height:100vh; width:100vw;">
            <img src="${url}" style="max-width:100%; max-height:100%; object-fit:contain;" crossorigin="anonymous">
        </div>`;
    }).join('');
    
    const win = window.open('', '_blank');
    win.document.write(`<!DOCTYPE html><html><head>
        <meta charset="utf-8">
        <title>${pdfName}</title>
        <style>
            @page { margin: 0; size: auto; }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { background: #fff; }
            @media print {
                html, body { width: 100%; height: 100%; }
                img { display: block; max-width: 100%; max-height: 100%; }
            }
        </style>
    </head><body>
        ${imgs}
        <script>window.onload = function(){ window.print(); }<\/script>
    </body></html>`);
    win.document.close();
    showToast('✅ اختر "حفظ كـ PDF" في نافذة الطباعة', 'success');
}

// ---------------- TEMPLATES MANAGEMENT ----------------

async function loadTemplates() {
    try {
        const res = await fetch(`${API_BASE}/templates/`);
        const templates = await res.json();
        
        // Update Templates Page Grid
        const grid = document.getElementById('templates-grid');
        if (grid) {
            grid.innerHTML = '';
            templates.forEach(tpl => {
                grid.innerHTML += `
                    <div style="background:var(--panel-2); border:1px solid rgba(255,255,255,0.05); border-radius:16px; overflow:hidden; box-shadow:0 8px 24px rgba(0,0,0,0.15); transition:transform 0.3s, box-shadow 0.3s; position:relative;" onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 12px 30px rgba(0,0,0,0.3)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 8px 24px rgba(0,0,0,0.15)'">
                        <button onclick="deleteTemplate(${tpl.id})" style="position:absolute; top:10px; left:10px; background:rgba(239, 68, 68, 0.9); color:#fff; border:none; width:36px; height:36px; border-radius:50%; font-size:16px; cursor:pointer; z-index:10; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 10px rgba(0,0,0,0.3); transition:background 0.2s;" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='rgba(239, 68, 68, 0.9)'" title="حذف القالب">
                            🗑️
                        </button>
                        <div style="height:220px; background-image:url(${tpl.cover_bg_path.startsWith('http') ? tpl.cover_bg_path : tpl.cover_bg_path}); background-size:cover; background-position:center; position:relative;">
                            <div style="position:absolute; bottom:0; left:0; width:100%; height:50%; background:linear-gradient(to top, var(--panel-2), transparent);"></div>
                        </div>
                        <div style="padding:20px; position:relative; z-index:5;">
                            <h4 style="margin:0 0 15px; color:var(--text); font-size:18px; font-weight:700;">${tpl.name}</h4>
                            <div style="display:flex; gap:15px;">
                                <div style="display:flex; align-items:center; gap:8px; font-size:13px; color:var(--muted); background:rgba(255,255,255,0.03); padding:5px 10px; border-radius:20px;">
                                    <div style="width:14px; height:14px; border-radius:50%; background:${tpl.text_color}; border:2px solid var(--panel); box-shadow:0 0 0 1px rgba(255,255,255,0.1);"></div> نص
                                </div>
                                <div style="display:flex; align-items:center; gap:8px; font-size:13px; color:var(--muted); background:rgba(255,255,255,0.03); padding:5px 10px; border-radius:20px;">
                                    <div style="width:14px; height:14px; border-radius:50%; background:${tpl.accent_color}; border:2px solid var(--panel); box-shadow:0 0 0 1px rgba(255,255,255,0.1);"></div> تمييز
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
        }

        // Store templates globally for dropdowns
        window._availableTemplates = templates;
        
    } catch (e) {
        console.error("Failed to load templates", e);
    }
}

async function fetchPlatformStatus() {
    const list = document.getElementById('platform-status-list');
    if (!list) return;

    // Default states for platforms we haven't implemented APIs for yet
    const platforms = {
        'X': { name: 'X (تويتر)', desc: 'يتطلب تفعيل صلاحية النشر', status: 'غير مربوط', isConnected: false },
        'TikTok': { name: 'TikTok', desc: 'يتطلب تفعيل صلاحية النشر', status: 'غير مربوط', isConnected: false }
    };

    let instaConnected = false;
    let instaDesc = 'غير مربوط';
    try {
        const res = await fetch(`${API_BASE}/social/instagram/status`);
        if (res.ok) {
            const data = await res.json();
            instaConnected = data.connected;
            instaDesc = instaConnected ? `حساب أعمال مربوط (@${data.username || data.instagram_account_id})` : 'فشل الاتصال';
        }
    } catch (e) {
        console.error("Failed to fetch Instagram status", e);
    }

    let fbConnected = false;
    let fbDesc = 'غير مربوط';
    try {
        const res = await fetch(`${API_BASE}/social/facebook/status`);
        if (res.ok) {
            const data = await res.json();
            fbConnected = data.connected;
            fbDesc = fbConnected ? `صفحة مربوطة (${data.name || data.facebook_page_id})` : 'فشل الاتصال';
        }
    } catch (e) {
        console.error("Failed to fetch Facebook status", e);
    }

    let thConnected = false;
    let thDesc = 'غير مربوط';
    try {
        const token = localStorage.getItem('cm_token');
        const res = await fetch(`${API_BASE}/threads/status`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            thConnected = data.connected;
            if (thConnected) {
                const uid = data.username || data.account_id || '';
                thDesc = uid ? `حساب مربوط (${uid})` : 'حساب مربوط';
            } else {
                thDesc = data.configured === false ? 'غير مفعّل' : 'غير مربوط';
            }
        }
    } catch (e) {
        console.error("Failed to fetch Threads status", e);
    }

    let liConnected = false;
    let liDesc = 'غير مربوط';
    try {
        const token = localStorage.getItem('cm_token');
        const res = await fetch(`${API_BASE}/social/linkedin/status`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            liConnected = data.connected;
            if (liConnected) {
                const uid = data.username || data.account_id || '';
                liDesc = uid ? `حساب مربوط (${uid})` : 'حساب مربوط';
            } else {
                liDesc = data.configured === false ? 'غير مفعّل' : 'غير مربوط';
            }
        }
    } catch (e) {
        console.error("Failed to fetch LinkedIn status", e);
    }

    let scConnected = false;
    let scDesc = 'غير مربوط';
    try {
        const res = await fetch(`${API_BASE}/social/snapchat/status`);
        if (res.ok) {
            const data = await res.json();
            scConnected = data.connected;
            scDesc = scConnected ? 'حساب مربوط' : 'فشل الاتصال';
        }
    } catch (e) {
        console.error("Failed to fetch Snapchat status", e);
    }

    let html = `
        <div class="src-item"><div><div class="n">Instagram</div><div class="u" style="font-size:11px">${instaDesc}</div></div><span class="badge ${instaConnected ? 'approved' : 'draft'}">${instaConnected ? 'متصل' : 'غير مربوط'}</span></div>
        <div class="src-item"><div><div class="n">Facebook</div><div class="u" style="font-size:11px">${fbDesc}</div></div><span class="badge ${fbConnected ? 'approved' : 'draft'}">${fbConnected ? 'متصل' : 'غير مربوط'}</span></div>
        <div class="src-item"><div><div class="n">Threads</div><div class="u" style="font-size:11px">${thDesc}</div></div><span class="badge ${thConnected ? 'approved' : 'draft'}">${thConnected ? 'متصل' : 'غير مربوط'}</span></div>
        <div class="src-item"><div><div class="n">LinkedIn</div><div class="u" style="font-size:11px">${liDesc}</div></div><span class="badge ${liConnected ? 'approved' : 'draft'}">${liConnected ? 'متصل' : 'غير مربوط'}</span></div>
        <div class="src-item"><div><div class="n">Snapchat</div><div class="u" style="font-size:11px">${scDesc}</div></div><span class="badge ${scConnected ? 'approved' : 'draft'}">${scConnected ? 'متصل' : 'غير مربوط'}</span></div>
    `;

    Object.values(platforms).forEach(p => {
        html += `<div class="src-item"><div><div class="n">${p.name}</div><div class="u" style="font-size:11px">${p.desc}</div></div><span class="badge ${p.isConnected ? 'approved' : 'draft'}">${p.status}</span></div>`;
    });

    list.innerHTML = html;
}



function deleteTemplate(id) {
    showConfirmModal('حذف القالب', 'هل أنت متأكد من حذف هذا القالب؟ سيتم حذف جميع صوره من الخادم ولن تتمكن من التراجع.', async () => {
        try {
            const res = await fetch(`${API_BASE}/templates/${id}`, { method: 'DELETE' });
            if (res.ok) {
                showToast('تم حذف القالب بنجاح', 'success');
                loadTemplates();
            } else {
                showToast('حدث خطأ أثناء الحذف', 'error');
            }
        } catch (e) {
            showToast('حدث خطأ أثناء الحذف', 'error');
        }
    });
}

// Upload Template Form UI Listeners
document.getElementById('tpl-text-color')?.addEventListener('input', (e) => {
    const hexLabel = document.getElementById('tpl-text-hex');
    if(hexLabel) hexLabel.textContent = e.target.value;
});
document.getElementById('tpl-accent-color')?.addEventListener('input', (e) => {
    const hexLabel = document.getElementById('tpl-accent-hex');
    if(hexLabel) hexLabel.textContent = e.target.value;
});
document.getElementById('tpl-file')?.addEventListener('change', (e) => {
    const el = document.getElementById('tpl-filename');
    if (e.target.files[0]) {
        el.textContent = e.target.files[0].name;
        el.style.display = 'block';
    } else {
        el.style.display = 'none';
    }
});

// Upload Template Form
const tplForm = document.getElementById('template-upload-form');
if (tplForm) {
    tplForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const name = document.getElementById('tpl-name').value;
        const styleMode = document.getElementById('tpl-style-mode').value;
        const fileInput = document.getElementById('tpl-file');
        const file = fileInput.files[0];
        
        if (!file) {
            showToast('الرجاء اختيار ملف PDF أو صورة', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('name', name);
        formData.append('style_mode', styleMode);
        formData.append('file', file);

        const statusDiv = document.getElementById('tpl-upload-status');
        statusDiv.style.display = 'block';
        statusDiv.innerText = 'جاري معالجة الملف واستخراج الصور...';
        
        try {
            const res = await fetch(`${API_BASE}/templates/upload`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (res.ok) {
                showToast('تم رفع القالب بنجاح!', 'success');
                tplForm.reset();
                loadTemplates();
            } else {
                showToast('خطأ: ' + (data.detail || 'حدث خطأ'), 'error');
            }
        } catch (err) {
            showToast('حدث خطأ في الاتصال بالخادم', 'error');
        } finally {
            statusDiv.style.display = 'none';
        }
    });
}

// Initialize flatpickr for the schedule inputs
if (typeof flatpickr !== 'undefined') {
    flatpickr("#schedule-date-input", {
        dateFormat: "Y-m-d",
        disableMobile: "true",
        placeholder: "اختر التاريخ",
        locale: {
            firstDayOfWeek: 6 // Saturday as first day of week for Arabic region
        }
    });

    flatpickr("#schedule-time-input", {
        enableTime: true,
        noCalendar: true,
        dateFormat: "H:i",
        time_24hr: false,
        disableMobile: "true",
        placeholder: "اختر الوقت"
    });
}

// ---------------- Geo Pill Selector ----------------
function selectGeo(btn, geo) {
    // Update pills active state
    document.querySelectorAll('.geo-pill').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    // Sync hidden select
    const sel = document.getElementById('trend-geo-select');
    if (sel) sel.value = geo;
}



function showCustomConfirm(msg, onConfirm) {
    let modal = document.getElementById('generation-confirm-modal');
    
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'generation-confirm-modal';
        modal.style.cssText = 'display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.75); z-index:10000; align-items:center; justify-content:center; backdrop-filter:blur(8px);';
        modal.innerHTML = `
            <div id="gen-modal-box" style="background:linear-gradient(145deg,#1a1f2e,#141820); width:92%; max-width:460px; border-radius:24px; border:1px solid rgba(255,255,255,0.1); display:flex; flex-direction:column; padding:0; box-shadow:0 40px 80px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.05); overflow:hidden; animation:genFadeUp 0.35s cubic-bezier(0.34,1.56,0.64,1) forwards;">
                
                <!-- Header -->
                <div style="padding:28px 28px 20px; background:linear-gradient(135deg,rgba(0,200,150,0.08),rgba(100,80,255,0.08)); border-bottom:1px solid rgba(255,255,255,0.06); text-align:center; position:relative;">
                    <div style="width:52px; height:52px; background:linear-gradient(135deg,#00c896,#6450ff); border-radius:16px; display:flex; align-items:center; justify-content:center; font-size:24px; margin:0 auto 14px; box-shadow:0 8px 24px rgba(0,200,150,0.3);">✨</div>
                    <h3 style="margin:0 0 6px; font-size:20px; color:#fff; font-weight:800; letter-spacing:-0.3px;">صناعة المحتوى</h3>
                    <p id="generation-confirm-msg" style="color:rgba(255,255,255,0.5); font-size:13.5px; margin:0; line-height:1.6;"></p>
                </div>

                <!-- Content Type Selectors -->
                <div style="padding:22px 24px;">
                    <div style="font-size:12px; color:rgba(255,255,255,0.35); font-weight:700; letter-spacing:1.2px; text-transform:uppercase; margin-bottom:14px; text-align:right;">اختر صيغ المحتوى</div>
                    
                    <div style="display:flex; flex-direction:column; gap:10px;">

                        <label id="card-carousel" style="display:flex; align-items:center; gap:14px; padding:14px 16px; background:rgba(255,255,255,0.04); border:1.5px solid rgba(255,255,255,0.08); border-radius:14px; cursor:pointer; transition:all 0.2s;" 
                            onmouseover="this.style.background='rgba(255,255,255,0.07)'"
                            onmouseout="this.style.background='rgba(255,255,255,0.04)'">
                            <input type="checkbox" id="chk-format-carousel" value="CAROUSEL" checked style="display:none;">
                            <div id="chk-carousel-dot" style="width:22px; height:22px; min-width:22px; border-radius:7px; background:linear-gradient(135deg,#e040fb,#9c27b0); display:flex; align-items:center; justify-content:center; font-size:13px; transition:all 0.2s; box-shadow:0 4px 12px rgba(224,64,251,0.4);">✓</div>
                            <div style="flex:1; text-align:right;">
                                <div style="display:flex; align-items:center; gap:6px; justify-content:flex-end; margin-bottom:3px;">
                                    <span style="font-size:14px; font-weight:700; color:#fff;">كاروسيل</span>
                                    <span style="font-size:18px;">📱</span>
                                </div>
                                <div style="font-size:12px; color:rgba(255,255,255,0.4); line-height:1.4;">عربي لـ Instagram • إنجليزي لـ LinkedIn</div>
                            </div>
                        </label>

                        <label id="card-post" style="display:flex; align-items:center; gap:14px; padding:14px 16px; background:rgba(255,255,255,0.04); border:1.5px solid rgba(255,255,255,0.08); border-radius:14px; cursor:pointer; transition:all 0.2s;"
                            onmouseover="this.style.background='rgba(255,255,255,0.07)'"
                            onmouseout="this.style.background='rgba(255,255,255,0.04)'">
                            <input type="checkbox" id="chk-format-post" value="POST" checked style="display:none;">
                            <div id="chk-post-dot" style="width:22px; height:22px; min-width:22px; border-radius:7px; background:linear-gradient(135deg,#00c896,#00b4d8); display:flex; align-items:center; justify-content:center; font-size:13px; transition:all 0.2s; box-shadow:0 4px 12px rgba(0,200,150,0.4);">✓</div>
                            <div style="flex:1; text-align:right;">
                                <div style="display:flex; align-items:center; gap:6px; justify-content:flex-end; margin-bottom:3px;">
                                    <span style="font-size:14px; font-weight:700; color:#fff;">منشور (بوست)</span>
                                    <span style="font-size:18px;">📝</span>
                                </div>
                                <div style="font-size:12px; color:rgba(255,255,255,0.4); line-height:1.4;">Facebook • X • LinkedIn</div>
                            </div>
                        </label>

                        <label id="card-video" style="display:flex; align-items:center; gap:14px; padding:14px 16px; background:rgba(255,255,255,0.04); border:1.5px solid rgba(255,255,255,0.08); border-radius:14px; cursor:pointer; transition:all 0.2s;"
                            onmouseover="this.style.background='rgba(255,255,255,0.07)'"
                            onmouseout="this.style.background='rgba(255,255,255,0.04)'">
                            <input type="checkbox" id="chk-format-video" value="VIDEO_SCRIPT" checked style="display:none;">
                            <div id="chk-video-dot" style="width:22px; height:22px; min-width:22px; border-radius:7px; background:linear-gradient(135deg,#ff6b35,#f7c59f); display:flex; align-items:center; justify-content:center; font-size:13px; transition:all 0.2s; box-shadow:0 4px 12px rgba(255,107,53,0.4);">✓</div>
                            <div style="flex:1; text-align:right;">
                                <div style="display:flex; align-items:center; gap:6px; justify-content:flex-end; margin-bottom:3px;">
                                    <span style="font-size:14px; font-weight:700; color:#fff;">سكريبت فيديو</span>
                                    <span style="font-size:18px;">🎬</span>
                                </div>
                                <div style="font-size:12px; color:rgba(255,255,255,0.4); line-height:1.4;">TikTok • Reels • YouTube Shorts</div>
                            </div>
                        </label>

                    </div>
                </div>
                
                <!-- Buttons -->
                <div style="padding:0 24px 24px; display:flex; gap:10px;">
                    <button id="generation-confirm-yes" style="flex:2; background:linear-gradient(135deg,#00c896,#00b4d8); color:#0a0f1e; border:none; padding:15px; font-size:15px; font-weight:800; border-radius:14px; cursor:pointer; transition:all 0.25s; letter-spacing:0.2px; box-shadow:0 8px 24px rgba(0,200,150,0.3);"
                        onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 12px 32px rgba(0,200,150,0.45)'"
                        onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 8px 24px rgba(0,200,150,0.3)'">
                        ✨ ابدأ الصياغة
                    </button>
                    <button id="generation-confirm-no" style="flex:1; background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.6); border:1.5px solid rgba(255,255,255,0.08); padding:15px; font-size:14px; font-weight:600; border-radius:14px; cursor:pointer; transition:all 0.2s;"
                        onmouseover="this.style.background='rgba(255,255,255,0.1)'; this.style.color='#fff'"
                        onmouseout="this.style.background='rgba(255,255,255,0.05)'; this.style.color='rgba(255,255,255,0.6)'">
                        إلغاء
                    </button>
                </div>
            </div>
            <style>
                @keyframes genFadeUp {
                    from { opacity:0; transform:translateY(20px) scale(0.95); }
                    to { opacity:1; transform:translateY(0) scale(1); }
                }
            </style>
        `;
        document.body.appendChild(modal);
        
        document.getElementById('generation-confirm-no').onclick = () => {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        };

        // Toggle checkbox visual state
        ['carousel','post','video'].forEach(key => {
            const card = document.getElementById(`card-${key}`);
            const chk = document.getElementById(`chk-format-${key === 'post' ? 'post' : key === 'video' ? 'video' : 'carousel'}`);
            const dot = document.getElementById(`chk-${key}-dot`);
            if (!card || !chk || !dot) return;
            const uncheckedBg = { carousel:'rgba(255,255,255,0.06)', post:'rgba(255,255,255,0.06)', video:'rgba(255,255,255,0.06)' };
            const checkedGradients = {
                carousel: 'linear-gradient(135deg,#e040fb,#9c27b0)',
                post: 'linear-gradient(135deg,#00c896,#00b4d8)',
                video: 'linear-gradient(135deg,#ff6b35,#f7c59f)'
            };
            card.addEventListener('click', () => {
                chk.checked = !chk.checked;
                dot.style.background = chk.checked ? checkedGradients[key] : 'rgba(255,255,255,0.1)';
                dot.style.boxShadow = chk.checked ? dot.style.boxShadow : 'none';
                dot.innerText = chk.checked ? '✓' : '';
                card.style.border = chk.checked ? `1.5px solid rgba(255,255,255,0.15)` : '1.5px solid rgba(255,255,255,0.06)';
            });
        });
    }
    
    document.getElementById('generation-confirm-msg').innerText = msg;
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    
    document.getElementById('generation-confirm-yes').onclick = () => {
        const formats = [];
        const chkCar = document.getElementById('chk-format-carousel');
        const chkPost = document.getElementById('chk-format-post');
        const chkVid = document.getElementById('chk-format-video');
        
        if (chkCar && chkPost && chkVid) {
            if(chkCar.checked) formats.push('CAROUSEL');
            if(chkPost.checked) formats.push('POST');
            if(chkVid.checked) formats.push('VIDEO_SCRIPT');
        } else {
            formats.push('CAROUSEL', 'POST', 'VIDEO_SCRIPT');
        }
        
        if (formats.length === 0) {
            showToast('يجب اختيار صيغة واحدة على الأقل', 'error');
            return;
        }
        
        modal.style.display = 'none';
        document.body.style.overflow = '';
        if (onConfirm) onConfirm(formats, ['IG', 'Li']);
    };
}


async function generateTrendContent(title, snippet, btn) {
    showCustomConfirm(`هل أنت متأكد أنك تريد توليد محتوى أوتوماتيكي بناءً على ترند:\n"${title}"؟`, async (formats) => {
        const origText = btn ? btn.innerHTML : "";
        if (btn) {
            btn.innerHTML = `<span class="ic">⏳</span> جاري الصياغة...`;
            btn.disabled = true;
            btn.style.opacity = '0.7';
        }
        showToast(`بدأ توليد المحتوى لترند: ${title}`);
    try {
        const token = localStorage.getItem('cm_token');
        const res = await fetch(`${API_BASE}/trends/generate`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ title, snippet, formats })
        });
        if (res.ok) {
            showToast(`تم إرسال الطلب لـ Claude بنجاح! سيظهر قريباً في المراجعة`, 'success');
        } else {
            showToast('حدث خطأ أثناء إرسال الطلب', 'error');
        }
        } catch (err) {
            console.error(err);
            showToast('خطأ في الاتصال بالسيرفر', 'error');
        }
    });
}

async function openNewsModal(url, title, safeTitle, safeSnippet) {
    document.getElementById('news-modal-title').innerText = title;
    
        // reset UI
    document.getElementById('news-modal-loading').style.display = 'block';
    document.getElementById('news-modal-content').style.display = 'none';
    document.getElementById('news-modal-img').style.display = 'none';
    document.getElementById('news-modal-img').style.backgroundImage = '';
    document.getElementById('news-modal-h1').innerText = '';
    document.getElementById('news-modal-text').innerHTML = '';
    
    document.getElementById('news-modal').style.display = 'flex';
    document.getElementById('news-modal-generate').onclick = () => {
        closeNewsModal();
        generateTrendContent(safeTitle, safeSnippet, document.getElementById('news-modal-generate'));
    };

    try {
        const token = localStorage.getItem('cm_token');
        const res = await fetch(`${API_BASE}/trends/read`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ url: url })
        });
        
        if (!res.ok) throw new Error('Failed to load article');
        
        const data = await res.json();
        document.getElementById('news-modal-loading').style.display = 'none';
        document.getElementById('news-modal-content').style.display = 'block';
        
        if (data.image) {
            document.getElementById('news-modal-img').style.backgroundImage = `url('${data.image}')`;
            document.getElementById('news-modal-img').style.display = 'block';
        }
        
        // Use backend title if trafilatura found a better one, else use the RSS title
        document.getElementById('news-modal-h1').innerText = data.title || title;
        
        // Convert text to paragraphs
        let contentText = data.content;
        if (!contentText || contentText.trim() === '') {
             contentText = 'عذراً، لم نتمكن من قراءة النص كاملاً من المصدر. قد يكون الموقع يمنع النسخ الآلي.';
        }
        const contentHtml = contentText.split('\\n').map(p => p.trim()).filter(p => p.length > 0).map(p => `<p style="margin-bottom:15px;">${p}</p>`).join('');
        document.getElementById('news-modal-text').innerHTML = contentHtml;
        
    } catch (err) {
        console.error(err);
        document.getElementById('news-modal-loading').style.display = 'none';
        document.getElementById('news-modal-content').style.display = 'block';
        document.getElementById('news-modal-text').innerHTML = '<div style="color:red; text-align:center; padding:40px;">حدث خطأ أثناء الاتصال بالخادم لجلب تفاصيل الخبر. ربما المصدر يمنع الوصول.</div>';
    }
}

function closeNewsModal() {
    document.getElementById('news-modal').style.display = 'none';
}
