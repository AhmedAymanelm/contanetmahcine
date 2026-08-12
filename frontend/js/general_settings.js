// general_settings.js

async function loadGeneralSettings() {
    // Load current username
    try {
        const token = localStorage.getItem('cm_token');
        const res = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            const el = document.getElementById('current-username-display');
            if (el) el.textContent = data.username || '—';
        }
    } catch (e) { console.error(e); }

    // Check server status and get system info
    try {
        const res = await fetch('/api/health');
        const el = document.getElementById('settings-server-status');
        const vEl = document.getElementById('settings-app-version');
        const mEl = document.getElementById('settings-ai-model');
        
        if (res.ok) {
            const data = await res.json();
            if (el) { el.textContent = 'يعمل بكفاءة'; el.style.color = '#34d399'; }
            if (vEl && data.version) vEl.textContent = data.version;
            if (mEl && data.model) mEl.textContent = data.model;
        } else {
            if (el) { el.textContent = 'مشكلة'; el.style.color = '#f87171'; }
            if (vEl) vEl.textContent = '—';
            if (mEl) mEl.textContent = '—';
        }
    } catch (e) {
        const el = document.getElementById('settings-server-status');
        const vEl = document.getElementById('settings-app-version');
        const mEl = document.getElementById('settings-ai-model');
        if (el) { el.textContent = 'غير متاح'; el.style.color = '#f87171'; }
        if (vEl) vEl.textContent = '—';
        if (mEl) mEl.textContent = '—';
    }

    // Load saved app identity
    const savedName = localStorage.getItem('app_name');
    const savedTagline = localStorage.getItem('app_tagline');
    const savedLogo = localStorage.getItem('app_logo_url');

    if (savedName) {
        const el = document.getElementById('setting-app-name');
        if (el) el.value = savedName;
    }
    if (savedTagline) {
        const el = document.getElementById('setting-app-tagline');
        if (el) el.value = savedTagline;
    }
    if (savedLogo) {
        applyLogoToSidebar(savedLogo, null);
    }
}

// ── Logo Preview ─────────────────────────────────────────────────────────────

function previewLogo(input) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        const url = e.target.result;
        const preview = document.getElementById('logo-preview');
        if (preview) {
            preview.innerHTML = `<img src="${url}" style="width:100%; height:100%; object-fit:cover; border-radius:12px;">`;
        }
        // Store for saving
        input.dataset.logoUrl = url;
    };
    reader.readAsDataURL(file);
}

function applyLogoToSidebar(logoUrl, appName) {
    // Update sidebar logo (.mark)
    const sidebarMark = document.querySelector('.mark');
    if (sidebarMark && logoUrl) {
        sidebarMark.innerHTML = `<img src="${logoUrl}" style="width:100%; height:100%; object-fit:cover; border-radius:8px; display:block;">`;
        sidebarMark.style.padding = '0';
        sidebarMark.style.background = 'transparent';
    }
    // Update sidebar app name (.name)
    if (appName) {
        const nameEl = document.querySelector('.name');
        if (nameEl) nameEl.textContent = appName;
        document.title = appName;
    }
}

// ── Save App Identity ─────────────────────────────────────────────────────────

function saveAppIdentity() {
    const name = document.getElementById('setting-app-name')?.value.trim();
    const tagline = document.getElementById('setting-app-tagline')?.value.trim();
    const logoInput = document.getElementById('logo-upload');
    const logoUrl = logoInput?.dataset.logoUrl || localStorage.getItem('app_logo_url');

    if (name) {
        localStorage.setItem('app_name', name);
        const nameEl = document.querySelector('.name');
        if (nameEl) nameEl.textContent = name;
        document.title = name;
    }
    if (tagline) {
        localStorage.setItem('app_tagline', tagline);
        const tagEl = document.querySelector('.sub');
        if (tagEl) tagEl.textContent = tagline;
    }
    if (logoInput?.dataset.logoUrl) {
        localStorage.setItem('app_logo_url', logoInput.dataset.logoUrl);
        const sidebarMark = document.querySelector('.mark');
        if (sidebarMark) {
            sidebarMark.innerHTML = `<img src="${logoInput.dataset.logoUrl}" style="width:100%; height:100%; object-fit:cover; border-radius:8px; display:block;">`;
            sidebarMark.style.padding = '0';
            sidebarMark.style.background = 'transparent';
            // Also update logo-preview
            const preview = document.getElementById('logo-preview');
            if (preview) preview.innerHTML = sidebarMark.innerHTML;
        }
    }

    showSettingsMsg('✅ تم حفظ هوية التطبيق بنجاح', 'success');
}

// ── Save Account Settings ─────────────────────────────────────────────────────

async function saveAccountSettings() {
    const currentPassword = document.getElementById('setting-current-password')?.value;
    const newUsername = document.getElementById('setting-new-username')?.value.trim();
    const newPassword = document.getElementById('setting-new-password')?.value;

    if (!currentPassword) {
        showSettingsMsg('❌ يجب إدخال كلمة السر الحالية للتحقق', 'error');
        return;
    }
    if (!newUsername && !newPassword) {
        showSettingsMsg('❌ أدخل اسم مستخدم جديد أو كلمة سر جديدة على الأقل', 'error');
        return;
    }

    try {
        const token = localStorage.getItem('cm_token');
        const payload = { current_password: currentPassword };
        if (newUsername) payload.new_username = newUsername;
        if (newPassword) payload.new_password = newPassword;

        const res = await fetch('/api/auth/update-account', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (!res.ok) {
            showSettingsMsg(`❌ ${data.detail || 'حدث خطأ'}`, 'error');
            return;
        }

        // Update display
        const usernameDisplay = document.getElementById('current-username-display');
        if (usernameDisplay && data.username) usernameDisplay.textContent = data.username;

        // Clear fields
        document.getElementById('setting-current-password').value = '';
        document.getElementById('setting-new-username').value = '';
        document.getElementById('setting-new-password').value = '';

        showSettingsMsg('✅ تم تحديث بيانات الحساب بنجاح', 'success');

        // If password changed, re-login after 2s
        if (newPassword) {
            setTimeout(() => {
                showSettingsMsg('🔄 تم تغيير كلمة السر — سيتم تسجيل الخروج الآن...', 'success');
                setTimeout(() => {
                    localStorage.removeItem('cm_token');
                    window.location.reload();
                }, 2000);
            }, 1000);
        }

    } catch (e) {
        showSettingsMsg('❌ فشل الاتصال بالخادم', 'error');
    }
}

// ── Helper: Show message ──────────────────────────────────────────────────────

function showSettingsMsg(text, type) {
    const el = document.getElementById('settings-msg');
    if (!el) return;
    el.style.display = 'block';
    el.textContent = text;
    if (type === 'success') {
        el.style.background = 'rgba(16,185,129,0.12)';
        el.style.border = '1px solid rgba(16,185,129,0.3)';
        el.style.color = '#34d399';
    } else {
        el.style.background = 'rgba(239,68,68,0.1)';
        el.style.border = '1px solid rgba(239,68,68,0.3)';
        el.style.color = '#f87171';
    }
    setTimeout(() => el.style.display = 'none', 4000);
}

// ── Apply saved identity on page load ────────────────────────────────────────

(function applyStoredIdentity() {
    function doApply() {
        const savedName = localStorage.getItem('app_name');
        const savedTagline = localStorage.getItem('app_tagline');
        const savedLogo = localStorage.getItem('app_logo_url');

        if (savedName) {
            const nameEl = document.querySelector('.name');
            if (nameEl) nameEl.textContent = savedName;
            document.title = savedName;
        }
        if (savedTagline) {
            const tagEl = document.querySelector('.sub');
            if (tagEl) tagEl.textContent = savedTagline;
        }
        if (savedLogo) {
            const sidebarMark = document.querySelector('.mark');
            if (sidebarMark) {
                sidebarMark.innerHTML = `<img src="${savedLogo}" style="width:100%; height:100%; object-fit:cover; border-radius:8px; display:block;">`;
                sidebarMark.style.padding = '0';
                sidebarMark.style.background = 'transparent';
            }
        }
    }
    // Run immediately if DOM ready, otherwise wait
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', doApply);
    } else {
        doApply();
    }
})();

// Hook into go() navigation
const _origGo = window.go;
window.go = function(el) {
    _origGo(el);
    if (el.getAttribute('data-page') === 'page-settings') {
        loadGeneralSettings();
    }
};
