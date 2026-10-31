// setup_guide.js — دليل استخراج المفاتيح والتوكن لمنصات التواصل الاجتماعي

const GUIDE_PLATFORMS = {
    instagram: {
        id: "instagram",
        name: "Instagram Business",
        arabicName: "إنستغرام للأعمال",
        icon: "📸",
        themeColor: "#E1306C",
        gradient: "linear-gradient(135deg, #833ab4, #fd1d1d, #fcb045)",
        docsUrl: "https://developers.facebook.com/tools/explorer/",
        quickLinkText: "فتح Meta Graph API Explorer ↗",
        requirements: [
            "حساب إنستغرام للأعمال أو منشئ محتوى (Professional / Creator Account) — ليس حساباً شخصياً.",
            "صفحة فيسبوك مرتبطة بهذا الحساب (مرتبطة من إعدادات إنستغرام أو Facebook Pages).",
            "تطبيق مسجل في Meta for Developers (نوع Business أو Consumer)."
        ],
        scopes: [
            { name: "instagram_business_basic", desc: "قراءة معلومات الحساب والمعرّف وعدد المتابعين" },
            { name: "instagram_business_content_publish", desc: "نشر الصور والريلز والكاروسيل تلقائياً" },
            { name: "pages_read_engagement", desc: "قراءة بيانات وتفاعل الصفحة المربوطة بالإنستغرام" },
            { name: "pages_show_list", desc: "اكتشاف صفحات الفيسبوك المتاحة لحسابك" }
        ],
        scopesString: "instagram_business_basic, instagram_business_content_publish, pages_read_engagement, pages_show_list",
        steps: [
            {
                num: 1,
                title: "الدخول إلى Meta Graph API Explorer",
                desc: "اذهب إلى أداة مطوري Meta الرسمية. في الزاوية العلوية اليمنى، تأكد من اختيار <b>Meta App</b> الخاص بك.",
                tip: "إذا لم يكن لديك تطبيق، اضغط 'Create App' واختر نوع 'Business'."
            },
            {
                num: 2,
                title: "إضافة الصلاحيات (User Token Scopes)",
                desc: "في القائمة الجانبية (User or Page Token)، اضغط <b>Add a Permission</b> وأضف الصلاحيات الأربع المذكورة أدناه.",
                hasCopyScopes: true
            },
            {
                num: 3,
                title: "توليد التوكن واختيار الصفحة (Page Token)",
                desc: "اضغط <b>Generate Access Token</b> ووافق على ربط حسابك وصفحتك. بعد ذلك، في خانة <b>User or Page</b>، اختر <b>صفحة الفيسبوك</b> المربوطة بإنستغرام، أو اتركها على الـ User Token.",
                tip: "توكن الصفحة المستخرج يتميز بأنه دائم (Never Expires) عند تحويله إلى Long-Lived Token!"
            },
            {
                num: 4,
                title: "تمديد التوكن إلى Long-Lived Token (اختياري ولكنه موصى به)",
                desc: "للحصول على توكن لا ينتهي أو يمتد لـ 60 يوماً، اطلب الرابط التالي مع استبدال بيانات تطبيقك:",
                codeSnippet: "GET https://graph.facebook.com/v21.0/oauth/access_token?\n  grant_type=fb_exchange_token&\n  client_id={YOUR_APP_ID}&\n  client_secret={YOUR_APP_SECRET}&\n  fb_exchange_token={SHORT_LIVED_TOKEN}"
            },
            {
                num: 5,
                title: "معرفة معرّف الحساب (INSTAGRAM_ACCOUNT_ID)",
                desc: "نظامنا يكتشف المعرّف <b>تلقائياً</b> بمجرد إدخال التوكن! ولكن إذا أردت استخراجه يدوياً، اكتب في الـ Explorer:",
                codeSnippet: "GET me/accounts?fields=id,name,instagram_business_account"
            }
        ],
        faq: [
            {
                q: "لماذا تظهر لي رسالة 'Account ID غير صحيح' أو فشل في الاتصال؟",
                a: "تأكد من أن حساب إنستغرام محول إلى حساب احترافي (Professional/Business) وليس شخصياً (Personal)، وأنه مربوط بصفحة فيسبوك تملك فيها صلاحية الإدارة (Admin)."
            },
            {
                q: "كم مدة صلاحية التوكن؟",
                a: "توكن الـ Explorer الافتراضي ينتهي بعد ساعة إلى ساعتين. لذلك يجب استخدام Long-Lived Token (الخطوة 4) أو استخدام Page Access Token الذي لا ينتهي."
            }
        ]
    },

    facebook: {
        id: "facebook",
        name: "Facebook Pages",
        arabicName: "صفحات فيسبوك",
        icon: "📘",
        themeColor: "#1877F2",
        gradient: "linear-gradient(135deg, #1877F2, #0d5cb6)",
        docsUrl: "https://developers.facebook.com/tools/explorer/",
        quickLinkText: "فتح Meta Graph API Explorer ↗",
        requirements: [
            "صفحة فيسبوك عامة (Facebook Page) أنت مسؤول فيها (Admin).",
            "تطبيق فيسبوك في Meta for Developers."
        ],
        scopes: [
            { name: "pages_manage_posts", desc: "نشر المنشورات والصور على الصفحة تلقائياً" },
            { name: "pages_read_engagement", desc: "قراءة تفاعل المنشورات والتعليقات والمشاركات" },
            { name: "publish_video", desc: "نشر الفيديوهات والمقاطع على صفحة الفيسبوك" }
        ],
        scopesString: "pages_manage_posts, pages_read_engagement, publish_video",
        steps: [
            {
                num: 1,
                title: "فتح أداة Graph API Explorer",
                desc: "اختر تطبيقك في الزاوية العلوية، ثم في قائمة الصلاحيات اختر صلاحيات الصفحات المطلوبة."
            },
            {
                num: 2,
                title: "اختيار الصفحة وتوليد Page Access Token",
                desc: "في خانة <b>User or Page</b>، اختر الصفحة المحددة التي تريد النشر عليها. سينتج توكن خاص بالصفحة يبدأ غالباً بـ <code>EAA...</code>."
            },
            {
                num: 3,
                title: "استخراج معرف الصفحة (FACEBOOK_PAGE_ID)",
                desc: "معرف الصفحة يظهر مباشرة في رابط صفحتك أو يمكنك طلبه بـ:",
                codeSnippet: "GET me?fields=id,name"
            }
        ],
        faq: [
            {
                q: "ما الفرق بين User Token و Page Token؟",
                a: "للنشر على الصفحات، يجب دائماً استخدام Page Token. User Token مخصص للملف الشخصي فقط ولا يسمح بنشر محتوى باسم الصفحة."
            }
        ]
    },

    linkedin: {
        id: "linkedin",
        name: "LinkedIn",
        arabicName: "لينكد إن",
        icon: "💼",
        themeColor: "#0A66C2",
        gradient: "linear-gradient(135deg, #0A66C2, #004182)",
        docsUrl: "https://www.linkedin.com/developers/apps",
        quickLinkText: "فتح LinkedIn Developer Portal ↗",
        requirements: [
            "حساب مطور في LinkedIn Developer Portal.",
            "تطبيق LinkedIn مفعل فيه منتج 'Share on LinkedIn' أو 'Sign In with LinkedIn using OpenID Connect'."
        ],
        scopes: [
            { name: "openid", desc: "التحقق من الهوية الأساسية" },
            { name: "profile", desc: "قراءة الاسم والصورة الشخصية" },
            { name: "email", desc: "قراءة البريد الإلكتروني" },
            { name: "w_member_social", desc: "نشر المقالات والمنشورات والصور على حسابك الشخصي" }
        ],
        scopesString: "openid, profile, email, w_member_social",
        steps: [
            {
                num: 1,
                title: "إنشاء تطبيق في LinkedIn Developer",
                desc: "اضغط <b>Create App</b> وأدخل اسم التطبيق واربطه بصفحة الشركة أو صفحتك الشخصية."
            },
            {
                num: 2,
                title: "إضافة رابط إعادة التوجيه (Redirect URI)",
                desc: "في تبويب <b>Auth</b>، أضف الرابط التالي في خانة <b>Authorized redirect URLs</b>:",
                codeSnippet: "https://contanetmahcine.up.railway.app/api/auth/linkedin/callback"
            },
            {
                num: 3,
                title: "نسخ Client ID و Client Secret",
                desc: "انسخ المفتاحين من تبويب <b>Auth</b> وضعهما في إعدادات الربط في Content Machine."
            },
            {
                num: 4,
                title: "الربط بنقرة واحدة (OAuth)",
                desc: "اضغط زر <b>ربط الحساب</b> في لوحة تحكم Content Machine وسيتم توجيهك للموافقة والربط الدائم تلقائياً!"
            }
        ],
        faq: [
            {
                q: "هل أحتاج لتجديد توكن لينكد إن يدوياً؟",
                a: "لا! نظام Content Machine يحفظ التوكن ويقوم بتجديده تلقائياً عبر Refresh Token قبل انتهائه."
            }
        ]
    },

    threads: {
        id: "threads",
        name: "Threads",
        arabicName: "ثريدز",
        icon: "🧵",
        themeColor: "#000000",
        gradient: "linear-gradient(135deg, #18181b, #27272a)",
        docsUrl: "https://developers.facebook.com/apps/",
        quickLinkText: "فتح Meta Developer Portal (Threads) ↗",
        requirements: [
            "تطبيق Meta مفعل به استخدام Threads API.",
            "حساب Threads نشط مربوط بحساب إنستغرام."
        ],
        scopes: [
            { name: "threads_basic", desc: "قراءة الملف الشخصي والمعلومات الأساسية" },
            { name: "threads_content_publish", desc: "نشر التغريدات والثريدات النصية والصور تلقائياً" }
        ],
        scopesString: "threads_basic, threads_content_publish",
        steps: [
            {
                num: 1,
                title: "تفعيل Threads Use Case في تطبيق Meta",
                desc: "داخل تطبيقك في Meta for Developers، أضف Use Case باسم <b>Threads API</b>."
            },
            {
                num: 2,
                title: "إضافة Redirect URI",
                desc: "أضف رابط العودة المعتمد الخاص بنظامنا:",
                codeSnippet: "https://contanetmahcine.up.railway.app/api/auth/threads/callback"
            },
            {
                num: 3,
                title: "الربط التلقائي بنقرة واحدة",
                desc: "أدخل <code>THREADS_CLIENT_ID</code> و <code>THREADS_CLIENT_SECRET</code> في الإعدادات واضغط زر الربط المباشر."
            }
        ],
        faq: [
            {
                q: "هل يدعم Threads نشر الصور والنصوص معاً؟",
                a: "نعم! يدعم Content Machine نشر المنشورات الفردية، وسلاسل الثريدز المترابطة، والمنشورات المرفقة بصور."
            }
        ]
    },

    twitter: {
        id: "twitter",
        name: "X (Twitter)",
        arabicName: "إكس (تويتر)",
        icon: "🐦",
        themeColor: "#1DA1F2",
        gradient: "linear-gradient(135deg, #1d9bf0, #0c7abf)",
        docsUrl: "https://developer.x.com/en/portal/dashboard",
        quickLinkText: "فتح X Developer Portal ↗",
        requirements: [
            "حساب مطور في X Developer Portal.",
            "مشروع وتطبيق مفعل بصلاحيات Read & Write."
        ],
        scopes: [
            { name: "tweet.read", desc: "قراءة التغريدات" },
            { name: "tweet.write", desc: "نشر التغريدات والثريدات" },
            { name: "users.read", desc: "قراءة بيانات الحساب" }
        ],
        scopesString: "tweet.read, tweet.write, users.read",
        steps: [
            {
                num: 1,
                title: "إنشاء Project & App في X Portal",
                desc: "في لوحة تحكم المطورين في X، أنشئ Project واختر التطبيق التابع له."
            },
            {
                num: 2,
                title: "ضبط صلاحيات User Authentication Settings",
                desc: "اضغط <b>Set up</b> في قسم مصادقة المستخدم، واختر نوع الصلاحيات <b>Read and write</b>، ونوع التطبيق <b>Web App / Bot</b>."
            },
            {
                num: 3,
                title: "توليد المفاتيح الأربعة (Keys & Tokens)",
                desc: "من تبويب <b>Keys and tokens</b>، ولّد وانسخ القيم الأربع التالية:\n1. <code>API Key</code>\n2. <code>API Secret Key</code>\n3. <code>Access Token</code>\n4. <code>Access Token Secret</code>"
            }
        ],
        faq: [
            {
                q: "لماذا يفشل نشر التغريدة برسالة 403 Forbidden؟",
                a: "غالباً لأن الصلاحيات كانت مضبوطة على 'Read' فقط بدلاً من 'Read and write' قبل توليد الـ Access Token. إذا غيرت الصلاحية، يجب إعادة توليد Access Token جديد ليعمل."
            }
        ]
    },

    tiktok: {
        id: "tiktok",
        name: "TikTok",
        arabicName: "تيك توك",
        icon: "🎵",
        themeColor: "#fe2c55",
        gradient: "linear-gradient(135deg, #fe2c55, #25f4ee)",
        docsUrl: "https://developers.tiktok.com/",
        quickLinkText: "فتح TikTok Developer Portal ↗",
        requirements: [
            "حساب مطور TikTok.",
            "تطبيق مفعل به ميزة Content Posting API."
        ],
        scopes: [
            { name: "user.info.basic", desc: "قراءة المعرف والصورة" },
            { name: "video.publish", desc: "نشر مقاطع الفيديو والريلز" },
            { name: "video.upload", desc: "رفع الفيديوهات لحسابك" }
        ],
        scopesString: "user.info.basic, video.publish, video.upload",
        steps: [
            {
                num: 1,
                title: "إنشاء تطبيق في TikTok Developers",
                desc: "سجل تطبيقاً جديداً وأضف منتج <b>Content Posting API</b>."
            },
            {
                num: 2,
                title: "إضافة Redirect URI",
                desc: "أضف الرابط التالي في إعدادات التطبيق:",
                codeSnippet: "https://contanetmahcine.up.railway.app/api/auth/tiktok/callback"
            },
            {
                num: 3,
                title: "نسخ Client Key و Client Secret",
                desc: "انسخ المفاتيح وضعها في الإعدادات، ثم اضغط زر الربط المباشر."
            }
        ],
        faq: [
            {
                q: "هل يمكن نشر فيديوهات TikTok كمسودة أولاً؟",
                a: "نعم! يدعم النظام نشر الفيديوهات كـ 'Private' أو 'Draft' أو 'Public' حسب اختيارك."
            }
        ]
    }
};

let currentGuidePlatform = 'instagram';

// ── Initializer ─────────────────────────────────────────────────────────────
function initSetupGuide(targetPlatform = null) {
    if (targetPlatform && GUIDE_PLATFORMS[targetPlatform]) {
        currentGuidePlatform = targetPlatform;
    }
    renderGuideNavigation();
    renderActiveGuidePlatform();
}

// ── Render Platform Tabs ────────────────────────────────────────────────────
function renderGuideNavigation() {
    const nav = document.getElementById('guide-platform-tabs');
    if (!nav) return;

    let html = '';
    for (const [key, p] of Object.entries(GUIDE_PLATFORMS)) {
        const isActive = key === currentGuidePlatform;
        html += `
            <button onclick="switchGuideTab('${key}')" 
                style="display:flex; align-items:center; gap:8px; padding:10px 18px; border-radius:12px; font-weight:700; font-size:0.9rem; cursor:pointer; transition:all 0.2s; font-family:inherit; border:1px solid ${isActive ? 'rgba(56,189,248,0.5)' : 'var(--line)'}; background:${isActive ? 'rgba(56,189,248,0.15)' : 'rgba(255,255,255,0.03)'}; color:${isActive ? '#38bdf8' : 'var(--muted)'};">
                <span style="font-size:1.15rem;">${p.icon}</span>
                <span>${p.name}</span>
            </button>
        `;
    }
    nav.innerHTML = html;
}

// ── Switch Active Tab ───────────────────────────────────────────────────────
function switchGuideTab(platformKey) {
    if (!GUIDE_PLATFORMS[platformKey]) return;
    currentGuidePlatform = platformKey;
    renderGuideNavigation();
    renderActiveGuidePlatform();
}

// ── Open from anywhere in app ──────────────────────────────────────────────
function openGuideFor(platformKey) {
    goId('page-setup-guide');
    switchGuideTab(platformKey);
}

// ── Render Guide Content ───────────────────────────────────────────────────
function renderActiveGuidePlatform() {
    const container = document.getElementById('guide-platform-content');
    if (!container) return;

    const p = GUIDE_PLATFORMS[currentGuidePlatform];
    if (!p) return;

    // Requirements HTML
    const reqsHtml = p.requirements.map(r => `
        <li style="margin-bottom:8px; display:flex; align-items:flex-start; gap:8px;">
            <span style="color:#10b981; font-weight:900;">✓</span>
            <span>${r}</span>
        </li>
    `).join('');

    // Scopes HTML
    const scopesHtml = p.scopes.map(s => `
        <div style="background:rgba(255,255,255,0.04); border:1px solid var(--line); border-radius:8px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
            <div>
                <code style="color:#38bdf8; font-weight:700; font-size:0.85rem;">${s.name}</code>
                <div style="font-size:0.78rem; color:var(--muted); margin-top:2px;">${s.desc}</div>
            </div>
            <button onclick="copyGuideText('${s.name}', this)" style="background:rgba(255,255,255,0.08); border:none; color:#fff; padding:4px 10px; border-radius:6px; font-size:0.75rem; cursor:pointer;">نسخ</button>
        </div>
    `).join('');

    // Steps HTML
    const stepsHtml = p.steps.map(step => `
        <div style="background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:20px; margin-bottom:16px; position:relative;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
                <div style="width:32px; height:32px; border-radius:50%; background:${p.themeColor}; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:900; font-size:0.95rem; flex-shrink:0;">
                    ${step.num}
                </div>
                <h3 style="margin:0; font-size:1.05rem; font-weight:800; color:var(--text);">${step.title}</h3>
            </div>
            <p style="font-size:0.9rem; line-height:1.7; color:var(--text); margin:0 0 10px 0;">${step.desc}</p>
            
            ${step.tip ? `
                <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.25); border-radius:8px; padding:8px 12px; font-size:0.82rem; color:#fbbf24; margin-top:8px;">
                    💡 <b>ملاحظة:</b> ${step.tip}
                </div>
            ` : ''}

            ${step.hasCopyScopes ? `
                <div style="margin-top:12px; padding:12px; background:rgba(56,189,248,0.06); border:1px solid rgba(56,189,248,0.2); border-radius:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="font-size:0.82rem; font-weight:700; color:#38bdf8;">الصلاحيات الأربع المطلوبة:</span>
                        <button onclick="copyGuideText('${p.scopesString}', this)" style="background:#0284c7; border:none; color:#fff; font-weight:700; padding:4px 12px; border-radius:6px; font-size:0.78rem; cursor:pointer;">
                            📋 نسخ الصلاحيات دفعة واحدة
                        </button>
                    </div>
                    <code style="display:block; padding:8px; background:rgba(0,0,0,0.3); border-radius:6px; font-size:0.8rem; color:#f8fafc; word-break:break-all;">${p.scopesString}</code>
                </div>
            ` : ''}

            ${step.codeSnippet ? `
                <div style="margin-top:12px; position:relative;">
                    <button onclick="copyGuideText(\`${step.codeSnippet.replace(/`/g, '\\`')}\`, this)" style="position:absolute; top:8px; left:8px; background:rgba(255,255,255,0.12); border:none; color:#fff; padding:4px 10px; border-radius:6px; font-size:0.75rem; cursor:pointer;">نسخ الكود</button>
                    <pre style="background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:12px 14px; font-size:0.8rem; color:#a5f3fc; overflow-x:auto; margin:0; font-family:monospace; line-height:1.6; text-align:left; direction:ltr;">${step.codeSnippet}</pre>
                </div>
            ` : ''}
        </div>
    `).join('');

    // FAQ HTML
    const faqHtml = p.faq.map(item => `
        <details style="background:rgba(255,255,255,0.03); border:1px solid var(--line); border-radius:10px; padding:14px; margin-bottom:10px; cursor:pointer;">
            <summary style="font-weight:700; font-size:0.9rem; color:var(--text); outline:none;">❓ ${item.q}</summary>
            <p style="margin:10px 0 0 0; font-size:0.85rem; line-height:1.7; color:var(--muted);">${item.a}</p>
        </details>
    `).join('');

    container.innerHTML = `
        <!-- Hero Card -->
        <div style="background:${p.gradient}; border-radius:18px; padding:24px 28px; color:#fff; margin-bottom:28px; box-shadow:0 12px 30px rgba(0,0,0,0.3); display:flex; justify-content:space-between; align-items:center; gap:20px; flex-wrap:wrap;">
            <div>
                <div style="display:flex; align-items:center; gap:12px; margin-bottom:6px;">
                    <span style="font-size:2rem;">${p.icon}</span>
                    <h2 style="margin:0; font-size:1.6rem; font-weight:900;">${p.name} — ${p.arabicName}</h2>
                </div>
                <p style="margin:0; opacity:0.9; font-size:0.95rem; max-width:600px; line-height:1.6;">
                    دليل استخراج التوكن والمفاتيح خطوة بخطوة للربط مع نظام النشر التلقائي في Content Machine.
                </p>
            </div>
            <a href="${p.docsUrl}" target="_blank" rel="noopener noreferrer" 
                style="background:#fff; color:#0f172a; font-weight:800; font-size:0.9rem; padding:12px 22px; border-radius:10px; text-decoration:none; display:inline-flex; align-items:center; gap:8px; box-shadow:0 4px 12px rgba(0,0,0,0.15); transition:transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
                ${p.quickLinkText}
            </a>
        </div>

        <div style="display:grid; grid-template-columns: 1.5fr 1fr; gap:24px;">
            <!-- Left Column: Steps -->
            <div>
                <h3 style="font-size:1.15rem; font-weight:800; margin:0 0 16px 0; display:flex; align-items:center; gap:8px;">
                    <span>📝</span> خطوات الاستخراج خطوة بخطوة
                </h3>
                ${stepsHtml}

                <h3 style="font-size:1.15rem; font-weight:800; margin:24px 0 14px 0; display:flex; align-items:center; gap:8px;">
                    <span>💡</span> الأسئلة الشائعة والأخطاء وحلولها
                </h3>
                ${faqHtml}
            </div>

            <!-- Right Column: Interactive Tester + Requirements + Scopes -->
            <div>
                <!-- LIVE TOKEN TESTER BOX -->
                <div style="background:var(--panel); border:1px solid rgba(56,189,248,0.3); border-radius:16px; padding:20px; margin-bottom:24px; box-shadow:0 8px 24px rgba(0,0,0,0.2);">
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
                        <span style="font-size:1.4rem;">⚡</span>
                        <div>
                            <h4 style="margin:0; font-size:1rem; font-weight:800; color:#38bdf8;">فحص واختبار التوكن المباشر</h4>
                            <span style="font-size:0.75rem; color:var(--muted);">تحقق من صلاحية التوكن وبيانات الحساب فوراً قبل الحفظ</span>
                        </div>
                    </div>

                    <div style="margin-bottom:12px;">
                        <label style="display:block; font-size:0.78rem; font-weight:700; color:var(--muted); margin-bottom:4px;">رمز الوصول (Access Token)</label>
                        <textarea id="tester-token-input" rows="3" placeholder="ألصق التوكن هنا (يبدأ غالباً بـ EAA...)" 
                            style="width:100%; padding:10px; background:rgba(0,0,0,0.3); border:1px solid var(--line); border-radius:8px; color:var(--text); font-family:monospace; font-size:0.8rem; resize:vertical;"></textarea>
                    </div>

                    ${p.id === 'instagram' ? `
                    <div style="margin-bottom:14px;">
                        <label style="display:block; font-size:0.78rem; font-weight:700; color:var(--muted); margin-bottom:4px;">معرّف الحساب INSTAGRAM_ACCOUNT_ID (اختياري - نكتشفه تلقائياً)</label>
                        <input type="text" id="tester-account-id-input" placeholder="مثال: 17841400000000" 
                            style="width:100%; padding:8px 12px; background:rgba(0,0,0,0.3); border:1px solid var(--line); border-radius:8px; color:var(--text); font-family:monospace; font-size:0.8rem;">
                    </div>
                    ` : ''}

                    <button onclick="testTokenLive('${p.id}')" id="btn-test-token"
                        style="width:100%; background:linear-gradient(135deg, #0284c7, #6366f1); border:none; color:#fff; font-weight:800; padding:10px; border-radius:8px; cursor:pointer; font-size:0.88rem; display:flex; align-items:center; justify-content:center; gap:8px;">
                        <span>🔍</span> فحص التوكن الآن
                    </button>

                    <!-- Result Area -->
                    <div id="tester-result-box" style="margin-top:14px; display:none;"></div>
                </div>

                <!-- Requirements Card -->
                <div style="background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:18px; margin-bottom:20px;">
                    <h4 style="margin:0 0 12px 0; font-size:0.95rem; font-weight:800; color:var(--text); display:flex; align-items:center; gap:8px;">
                        <span>📌</span> المتطلبات الأساسية
                    </h4>
                    <ul style="margin:0; padding:0; list-style:none; font-size:0.84rem; line-height:1.7; color:var(--muted);">
                        ${reqsHtml}
                    </ul>
                </div>

                <!-- Scopes Card -->
                <div style="background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:18px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <h4 style="margin:0; font-size:0.95rem; font-weight:800; color:var(--text); display:flex; align-items:center; gap:8px;">
                            <span>🔑</span> الصلاحيات المطلوبة (Permissions)
                        </h4>
                        <button onclick="copyGuideText('${p.scopesString}', this)" style="background:rgba(56,189,248,0.15); border:1px solid rgba(56,189,248,0.3); color:#38bdf8; font-weight:700; padding:3px 8px; border-radius:6px; font-size:0.75rem; cursor:pointer;">نسخ الكل</button>
                    </div>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        ${scopesHtml}
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ── Copy Helper with Toast ──────────────────────────────────────────────────
function copyGuideText(text, btnElement) {
    if (!navigator.clipboard) {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
    } else {
        navigator.clipboard.writeText(text);
    }

    if (btnElement) {
        const origText = btnElement.innerText;
        btnElement.innerText = 'تم النسخ ✓';
        btnElement.style.background = '#10b981';
        btnElement.style.color = '#fff';
        setTimeout(() => {
            btnElement.innerText = origText;
            btnElement.style.background = '';
            btnElement.style.color = '';
        }, 1800);
    }

    if (window.showToast) {
        window.showToast('📋 تم نسخ النص إلى الحافظة بنجاح');
    }
}

// ── Live Token Tester ───────────────────────────────────────────────────────
async function testTokenLive(platformKey) {
    const tokenInput = document.getElementById('tester-token-input');
    const accountInput = document.getElementById('tester-account-id-input');
    const resultBox = document.getElementById('tester-result-box');
    const testBtn = document.getElementById('btn-test-token');

    const tokenVal = tokenInput ? tokenInput.value.trim() : '';
    const accountIdVal = accountInput ? accountInput.value.trim() : '';

    if (!tokenVal) {
        alert('يرجى لصق رمز التوكن في الخانة أولاً للاختبار.');
        return;
    }

    resultBox.style.display = 'block';
    resultBox.innerHTML = `
        <div style="padding:14px; background:rgba(255,255,255,0.03); border:1px solid var(--line); border-radius:8px; text-align:center; color:var(--muted); font-size:0.85rem;">
            ⏳ جاري فحص التوكن مع خوادم Meta...
        </div>
    `;
    testBtn.disabled = true;
    testBtn.style.opacity = '0.6';

    try {
        const authToken = localStorage.getItem('cm_token');
        const res = await fetch('/api/social/test-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                platform: platformKey,
                access_token: tokenVal,
                account_id: accountIdVal || null
            })
        });

        const data = await res.json();
        testBtn.disabled = false;
        testBtn.style.opacity = '1';

        if (data.valid) {
            const ig = data.instagram_details || {};
            const discoveredId = data.discovered_instagram_id || '';
            const pagesCount = (data.pages || []).length;

            const targetAccId = discoveredId || accountIdVal || '';

            resultBox.innerHTML = `
                <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.35); border-radius:10px; padding:14px; font-size:0.85rem;">
                    <div style="display:flex; align-items:center; gap:8px; color:#34d399; font-weight:800; font-size:0.95rem; margin-bottom:8px;">
                        <span>✅</span> التوكن سليم وصالح تماماً!
                    </div>
                    <div style="color:var(--text); line-height:1.7;">
                        <div><b>المستخدم / الصفحة:</b> ${data.name || 'حساب Meta'}</div>
                        ${targetAccId ? `<div><b>معرّف إنستغرام للأعمال:</b> <code style="color:#38bdf8;">${targetAccId}</code></div>` : ''}
                        ${ig.username ? `<div><b>اسم المستخدم:</b> @${ig.username}</div>` : ''}
                        ${ig.followers_count !== undefined ? `<div><b>المتابعون:</b> ${ig.followers_count.toLocaleString()} متابع</div>` : ''}
                        <div><b>الصفحات المربوطة المكتشفة:</b> ${pagesCount} صفحة</div>
                    </div>

                    <button onclick="applyTestedToken('${platformKey}', '${encodeURIComponent(tokenVal)}', '${encodeURIComponent(targetAccId)}')"
                        style="width:100%; margin-top:12px; background:#10b981; border:none; color:#fff; font-weight:800; padding:9px; border-radius:8px; cursor:pointer; font-size:0.85rem; display:flex; align-items:center; justify-content:center; gap:8px;">
                        <span>💾</span> تطبيق وحفظ هذا الحساب في النظام الآن
                    </button>
                </div>
            `;
        } else {
            resultBox.innerHTML = `
                <div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.35); border-radius:10px; padding:14px; font-size:0.85rem;">
                    <div style="display:flex; align-items:center; gap:8px; color:#f87171; font-weight:800; font-size:0.95rem; margin-bottom:6px;">
                        <span>❌</span> فشل التحقق من التوكن
                    </div>
                    <div style="color:#fca5a5; margin-bottom:6px;">${data.message || 'خطأ غير محدد'}</div>
                    ${data.hint ? `<div style="font-size:0.8rem; color:var(--muted); line-height:1.5;">💡 <b>نصيحة:</b> ${data.hint}</div>` : ''}
                </div>
            `;
        }
    } catch (e) {
        testBtn.disabled = false;
        testBtn.style.opacity = '1';
        resultBox.innerHTML = `
            <div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); border-radius:10px; padding:12px; color:#f87171; font-size:0.85rem;">
                حدث خطأ في الاتصال بالسيرفر أثناء فحص التوكن: ${e.message}
            </div>
        `;
    }
}

// ── Apply Tested Token Directly ─────────────────────────────────────────────
async function applyTestedToken(platformKey, encodedToken, encodedAccountId) {
    const token = decodeURIComponent(encodedToken);
    const accountId = decodeURIComponent(encodedAccountId);

    const payload = {};
    if (platformKey === 'instagram') {
        payload.INSTAGRAM_ACCESS_TOKEN = token;
        if (accountId) payload.INSTAGRAM_ACCOUNT_ID = accountId;
    } else if (platformKey === 'facebook') {
        payload.FACEBOOK_ACCESS_TOKEN = token;
    }

    try {
        const authToken = localStorage.getItem('cm_token');
        const res = await fetch(`/api/settings/platforms/${platformKey}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            if (window.showToast) {
                window.showToast(`🎉 تم حفظ وربط ${platformKey} بنجاح! سيتم تحديث الحالة فوراً.`);
            }
            if (typeof fetchPlatformStatus === 'function') {
                fetchPlatformStatus();
            }
            if (typeof loadApiSettings === 'function') {
                loadApiSettings();
            }
        } else {
            alert('حدث خطأ أثناء حفظ المفتاح في السيرفر.');
        }
    } catch (e) {
        alert('خطأ أثناء الحفظ: ' + e.message);
    }
}

