// api_settings.js

const platformsMeta = {
    anthropic: { title: "Claude AI", icon: "🧠", type: "ai" },
    facebook: { title: "Facebook", icon: "📘", type: "social" },
    instagram: { title: "Instagram", icon: "📸", type: "social" },
    twitter: { title: "X (Twitter)", icon: "🐦", type: "social" },
    linkedin: { title: "LinkedIn", icon: "💼", type: "social" },
    threads: { title: "Threads", icon: "🧵", type: "social" },
    tiktok: { title: "TikTok", icon: "🎵", type: "social" },
    snapchat: { title: "Snapchat", icon: "👻", type: "social" },
};

async function loadApiSettings() {
    try {
        const token = localStorage.getItem('cm_token');
        const res = await fetch('/api/settings/platforms', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        renderApiCards('api-ai-grid', data.ai);
        renderApiCards('api-social-grid', data.social);
    } catch (e) {
        console.error("Failed to load settings:", e);
    }
}

function renderApiCards(containerId, platformsData) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    let html = '';
    for (const [key, data] of Object.entries(platformsData)) {
        const meta = platformsMeta[key] || { title: key, icon: "🔗" };
        
        let statusBadge = '';
        let statusColor = '';
        let borderColor = '';
        
        if (data.connected && !data.paused) {
            statusBadge = '🟢 نشط';
            statusColor = '#10b981';
            borderColor = 'rgba(16,185,129,0.3)';
        } else if (data.connected && data.paused) {
            statusBadge = '🟡 متوقف مؤقتاً';
            statusColor = '#f59e0b';
            borderColor = 'rgba(245,158,11,0.3)';
        } else {
            statusBadge = '🔴 غير مربوط';
            statusColor = '#ef4444';
            borderColor = 'rgba(239,68,68,0.3)';
        }
        
        html += `
        <div style="background:var(--panel); border:1px solid ${borderColor}; border-radius:12px; padding:20px; transition:0.2s;" class="api-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px;">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="font-size:2rem; background:rgba(255,255,255,0.05); width:50px; height:50px; display:flex; align-items:center; justify-content:center; border-radius:12px;">${meta.icon}</div>
                    <div>
                        <h3 style="margin:0; font-size:1.1rem; color:var(--text);">${meta.title}</h3>
                        <div style="font-size:0.75rem; color:${statusColor}; font-weight:700; margin-top:4px; display:flex; align-items:center; gap:4px;">
                            ${statusBadge} 
                            ${data.has_token ? '<span style="color:#818cf8; background:rgba(99,102,241,0.15); padding:2px 6px; border-radius:4px; font-size:0.65rem;">OAuth مسجل</span>' : ''}
                        </div>
                    </div>
                </div>
            </div>
            
            <div style="display:flex; gap:10px; margin-top:20px;">
                <button onclick="openApiModal('${key}', '${encodeURIComponent(JSON.stringify(data.keys))}')" style="flex:1; background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.3); color:#818cf8; padding:8px; border-radius:8px; cursor:pointer; font-weight:600; font-family:inherit;">⚙️ الإعدادات</button>
                
                ${data.connected ? `
                <button onclick="togglePlatformPause('${key}', ${!data.paused})" style="flex:1; background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); color:#fbbf24; padding:8px; border-radius:8px; cursor:pointer; font-weight:600; font-family:inherit;">
                    ${data.paused ? '▶️ تفعيل' : '⏸️ إيقاف'}
                </button>
                ` : ''}
            </div>
        </div>`;
    }
    
    container.innerHTML = html;
}

// ── Modals ──────────────────────────────────────────────────────────────────

function openApiModal(platformKey, keysJsonEncoded) {
    const keys = JSON.parse(decodeURIComponent(keysJsonEncoded));
    const meta = platformsMeta[platformKey];
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('api-keys-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'api-keys-modal';
        modal.style.cssText = 'display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); backdrop-filter:blur(5px); z-index:9999; align-items:center; justify-content:center; opacity:0; transition:opacity 0.2s;';
        document.body.appendChild(modal);
    }
    
    let inputsHtml = '';
    for (const [k, v] of Object.entries(keys)) {
        inputsHtml += `
        <div style="margin-bottom:15px;">
            <label style="display:block; font-size:0.8rem; color:var(--muted); margin-bottom:6px; font-family:monospace;">${k}</label>
            <input type="text" id="input_${k}" placeholder="${v ? v : 'أدخل المفتاح هنا...'}" style="width:100%; padding:10px 14px; background:rgba(0,0,0,0.2); border:1px solid var(--line); border-radius:8px; color:var(--text); font-family:monospace; font-size:0.85rem;" autocomplete="off">
        </div>`;
    }
    
    modal.innerHTML = `
    <div style="background:var(--panel); width:90%; max-width:500px; border-radius:16px; border:1px solid var(--line); padding:24px; box-shadow:0 20px 40px rgba(0,0,0,0.4); transform:scale(0.95); transition:transform 0.2s;" id="api-modal-content">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h3 style="margin:0; display:flex; align-items:center; gap:8px;">${meta.icon} إعدادات ${meta.title}</h3>
            <button onclick="closeApiModal()" style="background:none; border:none; color:var(--muted); font-size:1.5rem; cursor:pointer;">×</button>
        </div>
        
        <div style="margin-bottom:24px;">
            ${inputsHtml}
            <p style="font-size:0.75rem; color:var(--muted); margin-top:8px;">ملاحظة: لترك المفتاح القديم كما هو، اترك الخانة فارغة.</p>
        </div>
        
        <div style="display:flex; gap:12px; justify-content:flex-end;">
            <button onclick="deletePlatformKeys('${platformKey}')" style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); color:#f87171; padding:8px 16px; border-radius:8px; cursor:pointer; font-weight:600; font-family:inherit;">🗑️ حذف الربط</button>
            <button onclick="savePlatformKeys('${platformKey}', '${encodeURIComponent(JSON.stringify(Object.keys(keys)))}')" style="background:#6366f1; border:none; color:#fff; padding:8px 24px; border-radius:8px; cursor:pointer; font-weight:600; font-family:inherit;">💾 حفظ التغييرات</button>
        </div>
    </div>`;
    
    modal.style.display = 'flex';
    // Trigger reflow
    void modal.offsetWidth;
    modal.style.opacity = '1';
    document.getElementById('api-modal-content').style.transform = 'scale(1)';
}

function closeApiModal() {
    const modal = document.getElementById('api-keys-modal');
    if (modal) {
        modal.style.opacity = '0';
        document.getElementById('api-modal-content').style.transform = 'scale(0.95)';
        setTimeout(() => modal.style.display = 'none', 200);
    }
}

// ── API Actions ─────────────────────────────────────────────────────────────

async function savePlatformKeys(platform, keysListEncoded) {
    const keysList = JSON.parse(decodeURIComponent(keysListEncoded));
    const payload = {};
    
    for (const k of keysList) {
        const val = document.getElementById(`input_${k}`).value.trim();
        if (val) {
            payload[k] = val;
        }
    }
    
    if (Object.keys(payload).length === 0) {
        closeApiModal();
        return; // Nothing changed
    }
    
    try {
        const token = localStorage.getItem('cm_token');
        await fetch(`/api/settings/platforms/${platform}`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        closeApiModal();
        loadApiSettings(); // Refresh
        alert("✅ تم حفظ المفاتيح وتحديث النظام بنجاح");
    } catch (e) {
        alert("❌ حدث خطأ أثناء الحفظ");
    }
}

async function deletePlatformKeys(platform) {
    if (!confirm(`هل أنت متأكد من مسح مفاتيح وإلغاء ربط ${platform} بالكامل؟`)) return;
    
    try {
        const token = localStorage.getItem('cm_token');
        await fetch(`/api/settings/platforms/${platform}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        closeApiModal();
        loadApiSettings(); // Refresh
        alert("✅ تم إزالة الربط ومسح المفاتيح بنجاح");
    } catch (e) {
        alert("❌ حدث خطأ أثناء مسح المفاتيح");
    }
}

async function togglePlatformPause(platform, paused) {
    try {
        const token = localStorage.getItem('cm_token');
        await fetch(`/api/settings/platforms/${platform}/toggle`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ paused: paused })
        });
        
        loadApiSettings(); // Refresh
    } catch (e) {
        alert("❌ حدث خطأ أثناء تغيير الحالة");
    }
}

// Ensure loadApiSettings is called when opening the page
const originalGo = window.go;
window.go = function(el) {
    originalGo(el);
    if (el.getAttribute('data-page') === 'page-api') {
        loadApiSettings();
    }
};
