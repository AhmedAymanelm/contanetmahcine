const API_BASE = '/api';

function go(element) {
    document.querySelectorAll('nav a').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
    
    document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));
    const targetId = element.getAttribute('data-page');
    if (targetId) {
        const targetPage = document.getElementById(targetId);
        if (targetPage) {
            targetPage.classList.add('active');
        }
    }
}

function goId(pageId) {
    const link = document.querySelector(`nav a[data-page="${pageId}"]`);
    if (link) go(link);
}

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
                'LinkedIn': 'var(--violet)',
                'Facebook': 'var(--amber)',
                'X': 'var(--muted)',
                'TikTok': 'var(--teal)'
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

function openEditModal(id) {
    currentEditId = id;
    const currentEditData = window.reviewItemsData[id];
    const container = document.getElementById('edit-modal-content');
    container.innerHTML = '';

    if (typeof currentEditData !== 'object') {
        container.innerHTML = `<textarea id="edit-raw" class="input" style="width:100%; height:300px; background:var(--bg); border:1px solid var(--line); color:var(--text); padding:10px;">${currentEditData}</textarea>`;
    } else {
        for (const [key, val] of Object.entries(currentEditData)) {
            let label = document.createElement('label');
            label.innerText = key;
            label.style.display = 'block';
            label.style.marginBottom = '8px';
            label.style.color = 'var(--text)';
            label.style.fontWeight = 'bold';
            
            let input = document.createElement('textarea');
            input.className = 'input';
            input.style.width = '100%';
            input.style.minHeight = typeof val === 'string' ? '100px' : '200px';
            input.style.marginBottom = '20px';
            input.style.background = 'var(--bg)';
            input.style.border = '1px solid var(--line)';
            input.style.color = 'var(--text)';
            input.style.padding = '10px';
            
            if (typeof val === 'string') {
                input.value = val;
            } else {
                input.style.fontFamily = 'monospace';
                input.style.direction = 'ltr';
                input.value = JSON.stringify(val, null, 2);
                input.dataset.json = 'true';
            }
            input.dataset.key = key;
            
            container.appendChild(label);
            container.appendChild(input);
        }
    }

    document.getElementById('edit-modal').style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('edit-modal').style.display = 'none';
    currentEditId = null;
}

if(document.getElementById('save-edit-btn')) {
    document.getElementById('save-edit-btn').addEventListener('click', async () => {
        if(!currentEditId) return;
        
        let newContent = {};
        const container = document.getElementById('edit-modal-content');
        
        if (document.getElementById('edit-raw')) {
            newContent = document.getElementById('edit-raw').value;
        } else {
            const inputs = container.querySelectorAll('textarea');
            inputs.forEach(input => {
                const key = input.dataset.key;
                if (input.dataset.json) {
                    try {
                        newContent[key] = JSON.parse(input.value);
                    } catch(e) {
                        newContent[key] = input.value;
                    }
                } else {
                    newContent[key] = input.value;
                }
            });
        }

        const btn = document.getElementById('save-edit-btn');
        const orig = btn.innerText;
        btn.innerText = "جاري الحفظ...";
        btn.disabled = true;

        try {
            const res = await fetch(`${API_BASE}/content/${currentEditId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ generated_content: newContent })
            });
            
            if (res.ok) {
                showToast("تم حفظ التعديلات بنجاح", "success");
                closeEditModal();
                fetchReviewContent();
            } else {
                showToast("حدث خطأ أثناء الحفظ", "error");
            }
        } catch(err) {
            showToast("خطأ في الاتصال بالخادم", "error");
        } finally {
            btn.innerText = orig;
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
        
        const rawList = document.getElementById('raw-articles-list');
        if(rawList) {
            rawList.innerHTML = '';
            data.forEach((art, idx) => {
                // Generate a random gradient for the image placeholder based on ID or index
                const hue = (idx * 137.5) % 360;
                const gradient = `linear-gradient(160deg, hsl(${hue}, 70%, 90%), hsl(${hue}, 40%, 80%))`;
                
                const thumbStyle = art.image_url ? `background-image:url('${art.image_url}'); background-size:cover; background-position:center;` : `background:${gradient};`;
                const thumbContent = art.image_url ? '' : (art.source ? art.source.name : 'مجهول');
                
                rawList.innerHTML += `
                    <div class="panel" style="display:flex; flex-direction:column; justify-content:space-between;">
                        <div>
                            <div class="thumb" style="width:100%; height:180px; margin-bottom:12px; border-radius:8px; ${thumbStyle} display:flex; align-items:center; justify-content:center; color:#fff; font-weight:bold; font-size:18px; text-shadow:0 2px 4px rgba(0,0,0,0.2);">${thumbContent}</div>
                            <div class="t" style="margin-bottom:8px; line-height:1.4;">${art.title || 'بدون عنوان'}</div>
                            <div class="snippet" style="font-size:13px; color:var(--muted); line-height:1.5; margin-bottom:12px; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">${art.content || 'لا يوجد محتوى نصي...'}</div>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--line); padding-top:10px; margin-top:10px;">
                            <div class="m" style="font-family:var(--mono); font-size:11px">${new Date(art.created_at).toLocaleTimeString('ar-EG')}</div>
                            <div style="display:flex; gap:6px;">
                                <button class="btn ghost" style="padding:4px 10px; font-size:11px;" onclick='openArticleModal(${JSON.stringify(art.title || "بدون عنوان")}, ${JSON.stringify(art.content || "")}, ${JSON.stringify(art.url)}, ${JSON.stringify(art.image_url || "")})'>قراءة</button>
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

async function approveArticle(id, btn) {
    const orig = btn.innerText;
    btn.innerText = "جاري الصياغة...";
    btn.disabled = true;
    try {
        const res = await fetch(`${API_BASE}/raw-articles/${id}/generate`, { method: "POST" });
        if (res.ok) {
            btn.parentElement.parentElement.parentElement.style.opacity = '0.4';
            showToast("تم تحويل الخبر للصياغة عبر Claude بنجاح", "success");
            setTimeout(fetchRawArticles, 2000);
            fetchDashboardStats();
        } else {
            showToast("حدث خطأ أثناء الصياغة", "error");
            btn.innerText = orig;
            btn.disabled = false;
        }
    } catch (err) {
        console.error(err);
        showToast("خطأ في الاتصال بالخادم", "error");
        btn.innerText = orig;
        btn.disabled = false;
    }
}

function openArticleModal(title, content, url, imageUrl) {
    document.getElementById('modal-title').innerText = title;
    
    const imgEl = document.getElementById('modal-image');
    if (imageUrl) {
        imgEl.style.backgroundImage = `url('${imageUrl}')`;
        imgEl.style.display = 'block';
    } else {
        imgEl.style.display = 'none';
    }
    
    document.getElementById('modal-content').innerText = content;
    document.getElementById('modal-url').href = url;
    document.getElementById('article-modal').style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
}

function closeArticleModal() {
    document.getElementById('article-modal').style.display = 'none';
    document.body.style.overflow = ''; // Restore background scrolling
}

// ---------------- CUSTOM CONFIRM MODAL ----------------
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
                if (item.generated_content) {
                    try {
                        let gen = typeof item.generated_content === 'string' ? JSON.parse(item.generated_content) : item.generated_content;
                        title = gen.title || gen.hook || title;
                    } catch(e) {}
                }
                if (title === 'بدون عنوان' && item.raw_article) title = item.raw_article.title;

                const d = new Date(item.created_at);
                const dateStr = d.toLocaleDateString('ar-EG') + ' ' + d.toLocaleTimeString('ar-EG', {hour: '2-digit', minute:'2-digit'});

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
            // Prevent rebuilding the DOM if the data hasn't changed to avoid interrupting clicks
            const currentHash = JSON.stringify({data, generatingData});
            if (window.lastReviewDataHash === currentHash) {
                if (generatingData.length > 0) {
                    setTimeout(fetchReviewContent, 3000);
                }
                return;
            }
            window.lastReviewDataHash = currentHash;
            
            reviewList.innerHTML = '';
            
            if (data.length === 0 && generatingData.length === 0) {
                reviewList.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--muted); padding: 40px;">لا يوجد محتوى بانتظار المراجعة.</div>`;
                return;
            }

            generatingData.forEach(art => {
                reviewList.innerHTML += `
                    <div class="panel" style="display:flex; flex-direction:column; height:100%; opacity:0.6; border: 1px dashed var(--teal);">
                        <div class="thumb" style="width:100%; height:120px; margin-bottom:12px; font-size:12px; background:linear-gradient(160deg,#202428,#15181a); color:#fff; display:flex; align-items:center; justify-content:center; text-align:center; padding:10px;">
                            ${art.title || "بدون عنوان"}
                        </div>
                        <div class="review-body" style="display:flex; flex-direction:column; flex:1; text-align:center; align-items:center; justify-content:center;">
                            <div style="width: 30px; height: 30px; border: 3px solid var(--line); border-top: 3px solid var(--teal); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 15px;"></div>
                            <div style="color:var(--teal); font-weight:bold;">جاري الصياغة بالذكاء الاصطناعي...</div>
                            <div style="font-size:12px; color:var(--muted); margin-top:5px;">هذا يستغرق بضع ثوانٍ</div>
                        </div>
                    </div>
                `;
            });
            
            window.reviewItemsData = window.reviewItemsData || {};
            window.reviewItemsDataRaw = window.reviewItemsDataRaw || {};
            
            data.forEach(item => {
                let generated = typeof item.generated_content === 'string' ? JSON.parse(item.generated_content) : item.generated_content;
                window.reviewItemsData[item.id] = generated;
                window.reviewItemsDataRaw[item.id] = item;
                
                let title = item.raw_article ? item.raw_article.title : 'بدون عنوان';
                let sourceName = item.raw_article && item.raw_article.source ? item.raw_article.source.name : 'AI';
                let typeText = item.content_type;
                let snippetHtml = '';
                
                if (item.content_type === 'POST') {
                    snippetHtml = `<b>X:</b> ${generated.x_tweet || ''}<br><br><b>LinkedIn:</b> ${generated.linkedin_post || ''}`;
                } else if (item.content_type === 'CAROUSEL') {
                    snippetHtml = `<b>العنوان:</b> ${generated.title || ''}<br><br><b>الشريحة 1:</b> ${generated.slides && generated.slides[0] ? generated.slides[0].heading : ''}`;
                } else if (item.content_type === 'VIDEO_SCRIPT') {
                    snippetHtml = `<b>Hook:</b> ${generated.hook || ''}<br><br><b>Body:</b> ${generated.body || ''}`;
                }
                
                let platforms = item.platform ? item.platform : (Array.isArray(item.platforms) ? item.platforms.join(', ') : item.platforms);
                if (!platforms) platforms = '';
                
                reviewList.innerHTML += `
                    <div class="panel" style="display:flex; flex-direction:column; height:100%;" id="review-card-${item.id}">
                        <div class="thumb" style="width:100%; height:120px; margin-bottom:12px; font-size:12px; background:linear-gradient(160deg,#202428,#15181a); color:#fff; display:flex; align-items:center; justify-content:center; text-align:center; padding:10px;">${title}</div>
                        <div class="review-body" style="display:flex; flex-direction:column; flex:1;">
                            <div class="t">${typeText} — ${sourceName}</div>
                            <div class="m" style="margin-top:4px;">المنصات: ${platforms}</div>
                            <div class="snippet" style="margin-top:10px; font-size:13px; line-height:1.5; color:var(--text); flex-grow:1; max-height:100px; overflow-y:auto; padding-right:5px;">
                                ${snippetHtml}
                            </div>
                            ${item.content_type === 'CAROUSEL' ? (() => {
                                let hasUrls = generated.carousel_urls && generated.carousel_urls.length > 0;
                                let html = `
                                <div style="margin-top:10px; display:flex; gap:6px;">
                                    <button class="btn" style="background:linear-gradient(135deg,#7c3aed,#a855f7); color:#fff; border:none; padding:10px 15px; font-size:14px; border-radius:10px; cursor:pointer; width:100%; display:flex; justify-content:center; gap:8px;" onclick="openTemplatePickerModal(${item.id})">
                                        <span>✨</span> ${hasUrls ? 'إعادة توليد الكاروسيل' : 'توليد الكاروسيل بالصور'}
                                    </button>
                                </div>`;
                                
                                if (hasUrls) {
                                    const slidesJson = JSON.stringify(generated.carousel_urls).replace(/"/g, '&quot;');
                                    html += `
                                    <div id="carousel-slides-${item.id}" style="margin-top:10px; display:flex; gap:6px; width:100%; align-items:stretch;">
                                        <button class="btn" style="flex:1; background:linear-gradient(135deg,#3b82f6,#2563eb); color:#fff; border:none; padding:8px 12px; font-size:13px; border-radius:8px; cursor:pointer;" onclick="openSwiperModal(${slidesJson})">
                                            👀 معاينة
                                        </button>
                                        <button class="btn" style="background:rgba(239, 68, 68, 0.15); color:#ef4444; border:1px solid rgba(239, 68, 68, 0.3); padding:8px; border-radius:8px; cursor:pointer; width:45px; display:flex; align-items:center; justify-content:center; transition:all 0.2s;" onmouseover="this.style.background='rgba(239, 68, 68, 0.25)'" onmouseout="this.style.background='rgba(239, 68, 68, 0.15)'" onclick="deleteCarouselSlides(${item.id})" title="حذف الصور">
                                            🗑️
                                        </button>
                                    </div>`;
                                } else {
                                    html += `<div id="carousel-slides-${item.id}" style="display:none; margin-top:10px; display:flex; gap:6px;"></div>`;
                                }
                                return html;
                            })() : ''}
                            <div class="review-actions" style="margin-top:auto; border-top:1px solid var(--line); padding-top:10px; display:flex; gap:8px;">
                                <button class="btn ghost" style="color:var(--red); padding:6px 12px;" onclick="rejectContentItem(${item.id}, this)">رفض</button>
                                <button class="btn ghost" style="padding:6px 12px;" onclick="openEditModal(${item.id})">تعديل</button>
                                <button class="btn" style="background:var(--teal); color:#000; padding:6px 12px; flex-grow:1;" onclick="approveContentItem(${item.id}, this)">موافقة واعتماد</button>
                            </div>
                        </div>
                    </div>
                `;
            });

            if (generatingData.length > 0) {
                setTimeout(fetchReviewContent, 3000);
            }
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
        let url = `${API_BASE}/content/${id}/render-carousel?template_id=${templateId}`;
        if (textColor) url += `&custom_text_color=${encodeURIComponent(textColor)}`;
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
                        <button class="btn" style="flex:1; background:linear-gradient(135deg,#3b82f6,#2563eb); color:#fff; border:none; padding:8px 12px; font-size:13px; border-radius:8px; cursor:pointer;" onclick="openSwiperModal(${slidesJson})">
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
        html += `
            <div onclick="selectTemplateForContent(${contentId}, ${tpl.id})" style="cursor:pointer; background:var(--panel-2); border:1px solid rgba(255,255,255,0.05); border-radius:16px; overflow:hidden; transition:transform 0.2s; display:flex; flex-direction:column;" onmouseover="this.style.transform='translateY(-5px)'; this.style.borderColor='var(--teal)'" onmouseout="this.style.transform='translateY(0)'; this.style.borderColor='rgba(255,255,255,0.05)'">
                <div style="height:170px; background-image:url(${tpl.cover_bg_path.startsWith('http') ? tpl.cover_bg_path : tpl.cover_bg_path}); background-size:cover; background-position:center;"></div>
                <div style="padding:15px; text-align:center; flex-grow:1; display:flex; align-items:center; justify-content:center;">
                    <h4 style="margin:0; color:var(--text); font-size:16px; font-weight:700;">${tpl.name}</h4>
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

let currentApproveId = null;
let currentApproveBtn = null;

async function approveContentItem(id, btn) {
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
            { id: 'LI', name: 'LinkedIn' },
            { id: 'X', name: 'X (تويتر)' },
            { id: 'TT', name: 'TikTok' },
            { id: 'TH', name: 'Threads' }
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
            showToast("حدث خطأ", "error");
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
        const res = await fetch(`${API_BASE}/content/${id}/schedule`, { 
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scheduled_at: scheduledAt })
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

async function runIngestion() {
    const btn = document.getElementById('btn-run-ingestion');
    const originalText = btn.innerText;
    btn.innerHTML = `<span style="display:inline-block; width:12px; height:12px; border:2px solid rgba(255,255,255,0.3); border-radius:50%; border-top-color:#fff; animation:spin 1s linear infinite; margin-left:8px; vertical-align:middle;"></span> جاري السحب...`;
    btn.style.opacity = '0.8';
    btn.style.cursor = 'wait';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/sources/run-ingestion`, { method: 'POST' });
        const data = await res.json();
        if(res.ok) {
            showToast(data.detail || "تم السحب بنجاح", "success");
        } else {
            showToast("حدث خطأ أثناء السحب", "error");
        }
        
        // Refresh everything
        fetchDashboardStats();
        fetchSources();
        fetchRawArticles();
        fetchAllContent();
        fetchReviewContent();
    } catch(err) {
        console.error(err);
        showToast("حدث خطأ أثناء تشغيل السحب", "error");
    } finally {
        btn.innerText = originalText;
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

function openSwiperModal(slidesUrls) {
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
        'LinkedIn': { name: 'LinkedIn', desc: 'يتطلب تفعيل صلاحية النشر', status: 'غير مربوط', isConnected: false },
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

    let html = `
        <div class="src-item"><div><div class="n">Instagram</div><div class="u" style="font-size:11px">${instaDesc}</div></div><span class="badge ${instaConnected ? 'approved' : 'draft'}">${instaConnected ? 'متصل' : 'غير مربوط'}</span></div>
        <div class="src-item"><div><div class="n">Facebook</div><div class="u" style="font-size:11px">${fbDesc}</div></div><span class="badge ${fbConnected ? 'approved' : 'draft'}">${fbConnected ? 'متصل' : 'غير مربوط'}</span></div>
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
