"""
Strict tech/AI relevance filter.
Priority: Title match > Content match (requires stronger signals).
"""

# ── STRONG keywords → enough if in title only ──────────────────────────────
STRONG_TECH_TITLE_AR = [
    "ذكاء اصطناعي", "ذكاء الاصطناعي", "تعلم آلي", "تعلم الآلة",
    "نموذج لغوي", "روبوت", "روبوتات", "نموذج AI", "تقنية AI",
    "شات جي بي تي", "chatgpt", "gpt", "gemini", "claude", "llm",
    "openai", "أوبن إي آي", "anthropic", "xai", "grok",
    "برمجة", "برمجيات", "سوفتوير", "تطبيق تقني", "تطبيق ذكي",
    "هاتف ذكي", "شريحة", "معالج", "رقاقة إلكترونية",
    "أمن سيبراني", "اختراق إلكتروني", "هجوم سيبراني", "ثغرة أمنية",
    "بيتكوين", "بلوكتشين", "عملة رقمية", "كريبتو",
    "واقع افتراضي", "واقع معزز", "ميتافيرس",
    "سيارة ذاتية", "سيارة كهربائية",
    "خوارزمية", "بيانات ضخمة", "حوسبة سحابية", "سحابة إلكترونية",
    "حوسبة كمومية",
    "nvidia", "إنفيديا", "qualcomm", "tsmc", "arm",
    "5g", "6g", "إنترنت الأشياء",
]

STRONG_TECH_TITLE_EN = [
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "chatgpt", "openai", "gemini", "claude", "llm",
    "large language model", "generative ai", "ai model", "ai chip",
    "programming", "software", "cybersecurity", "data breach", "hacking",
    "bitcoin", "blockchain", "crypto", "nft", "web3",
    "virtual reality", "augmented reality", "metaverse",
    "electric vehicle", "self-driving", "autonomous vehicle",
    "quantum computing", "semiconductor", "microchip",
    "5g", "6g", "iot", "cloud computing",
    "nvidia", "qualcomm", "tsmc", "arm chip",
    "robotics", "drone automation",
]

# ── COMPANY/PRODUCT names in title (often enough context) ──────────────────
TECH_COMPANIES_IN_TITLE = [
    "أبل", "apple", "سامسونج", "samsung", "قوقل", "google", "ألفابيت", "alphabet",
    "مايكروسوفت", "microsoft", "أمازون", "amazon", "aws",
    "ميتا", "meta", "فيسبوك", "واتساب", "إنستغرام",
    "تيك توك", "tiktok", "بايت دانس", "bytedance",
    "تيسلا", "tesla", "سبيس إكس", "spacex",
    "هواوي", "huawei", "شاومي", "xiaomi", "أوبو", "oppo",
    "آي بي إم", "ibm", "أوراكل", "oracle", "sap",
    "إنتل", "intel", "amd", "snapdragon", "nvidia", "tsmc",
    "أوبر", "uber", "إير بي إن بي", "airbnb",
    "زوكربيرج", "zuckerberg", "إيلون ماسك", "elon musk",
    "سام ألتمان", "sam altman", "ساتيا", "satya nadella",
    "ستارلينك", "starlink",
]

# ── WEAKER keywords — require presence in TITLE ────────────────────────────
WEAK_TECH_TITLE_AR = [
    "تقنية", "تكنولوجيا", "تقنيات جديدة", "هاتف", "أجهزة",
    "تطبيق", "منصة رقمية", "خدمة رقمية",
    "إطلاق", "إصدار جديد", "تحديث", "نسخة جديدة",  # only if also has company
]

WEAK_TECH_TITLE_EN = [
    "tech", "technology", "smartphone", "laptop", "tablet",
    "app", "platform", "digital", "launch", "release", "update",
]

# ── HARD EXCLUSIONS — always reject even if tech keyword present ────────────
HARD_EXCLUDE_AR = [
    "كرة قدم", "دوري", "مباراة", "هدف", "لاعب", "مدرب", "ملعب",
    "فيلم", "مسلسل", "ممثل", "ممثلة", "نجوم", "سينما",
    "طبخ", "وصفة", "أكل", "مطعم",
    "انتخابات", "حزب سياسي", "نائب برلماني", "مجلس الشعب",
    "حرب", "مقتل", "قتل", "اشتباك", "قصف", "جيش",
    "زلزال", "فيضان", "حريق", "كارثة طبيعية",
    "ديناصور", "جليدي", "مذنب", "مجرة",  # pure science, not tech
    "نبات", "حيوان", "حوت", "أسد", "نمر",
    "طقس", "أمطار", "درجة حرارة",
    "صدام الدين", "صدام",
]

HARD_EXCLUDE_EN = [
    "football", "soccer", "basketball", "nba", "nfl", "nhl", "cricket",
    "movie", "film", "actor", "actress", "celebrity", "music", "album",
    "recipe", "cooking", "restaurant",
    "election", "parliament", "senator", "congressman",
    "war", "killed", "bombing", "military", "army",
    "earthquake", "flood", "hurricane", "wildfire",
    "dinosaur", "fossil", "asteroid",
]


def is_tech_relevant(title: str, content: str = "") -> bool:
    """
    Strict two-tier check:
    1. Hard exclusions → reject immediately
    2. Strong tech keyword in TITLE → accept
    3. Tech company name in TITLE → accept
    4. Weak keyword in TITLE + tech keyword anywhere → accept
    5. Everything else → reject
    """
    title_lower = title.lower().strip()
    content_lower = (content[:800]).lower()

    # ── 1. Hard exclusions ──────────────────────────────────────────────────
    for kw in HARD_EXCLUDE_AR + HARD_EXCLUDE_EN:
        if kw.lower() in title_lower:
            return False

    # ── 2. Strong tech keyword in TITLE ─────────────────────────────────────
    for kw in STRONG_TECH_TITLE_AR + STRONG_TECH_TITLE_EN:
        if kw.lower() in title_lower:
            return True

    # ── 3. Tech company name in TITLE ───────────────────────────────────────
    for kw in TECH_COMPANIES_IN_TITLE:
        if kw.lower() in title_lower:
            # Company name in title + at least some tech context in content
            for ckw in STRONG_TECH_TITLE_AR + STRONG_TECH_TITLE_EN + TECH_COMPANIES_IN_TITLE:
                if ckw.lower() in content_lower:
                    return True
            # If company name is prominent in title, accept even without content match
            return True

    # ── 4. Weak keyword in TITLE + strong signal in content ─────────────────
    title_has_weak = any(kw.lower() in title_lower for kw in WEAK_TECH_TITLE_AR + WEAK_TECH_TITLE_EN)
    if title_has_weak:
        strong_in_content = sum(
            1 for kw in STRONG_TECH_TITLE_AR + STRONG_TECH_TITLE_EN
            if kw.lower() in content_lower
        )
        if strong_in_content >= 2:
            return True

    # ── 5. Reject anything else ─────────────────────────────────────────────
    return False
