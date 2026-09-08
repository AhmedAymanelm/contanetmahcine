"""
Tech/AI relevance filter — balanced between precision and recall.
Sources are already tech-focused, so filter should only block obvious non-tech content.
"""

# ── STRONG keywords → accept immediately if in title ──────────────────────
STRONG_TECH_TITLE_AR = [
    "ذكاء اصطناعي", "ذكاء الاصطناعي", "تعلم آلي", "تعلم الآلة",
    "نموذج لغوي", "روبوت", "روبوتات", "تقنية AI",
    "شات جي بي تي", "chatgpt", "gpt", "gemini", "claude", "llm",
    "openai", "أوبن إي آي", "anthropic", "xai", "grok",
    "برمجة", "برمجيات", "تطبيق تقني",
    "هاتف ذكي", "شريحة إلكترونية", "معالج", "رقاقة إلكترونية",
    "أمن سيبراني", "اختراق إلكتروني", "هجوم سيبراني", "ثغرة أمنية",
    "بيتكوين", "بلوكتشين", "عملة رقمية", "كريبتو",
    "واقع افتراضي", "واقع معزز", "ميتافيرس",
    "سيارة ذاتية القيادة", "سيارة كهربائية",
    "خوارزمية", "بيانات ضخمة", "حوسبة سحابية",
    "حوسبة كمومية", "nvidia", "إنفيديا",
    "5g", "6g", "إنترنت الأشياء",
    "تقنية", "تكنولوجيا",
]

STRONG_TECH_TITLE_EN = [
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "chatgpt", "openai", "gemini", "claude", "llm",
    "large language model", "generative ai", "ai model", "ai chip",
    "programming", "software", "cybersecurity", "data breach", "hacking",
    "bitcoin", "blockchain", "cryptocurrency", "crypto", "nft", "web3",
    "virtual reality", "augmented reality", "metaverse",
    "electric vehicle", "self-driving", "autonomous vehicle",
    "quantum computing", "semiconductor", "microchip",
    "5g", "6g", "iot", "cloud computing",
    "nvidia", "qualcomm", "tsmc", "arm chip",
    "robotics", "drone", "tech", "technology",
    "startup", "app", "platform", "digital",
]

# ── COMPANY/PRODUCT names in title → accept directly ──────────────────────
TECH_COMPANIES_IN_TITLE = [
    "أبل", "apple", "سامسونج", "samsung", "قوقل", "google", "ألفابيت", "alphabet",
    "مايكروسوفت", "microsoft", "أمازون", "amazon", "aws",
    "ميتا", "meta", "فيسبوك", "facebook", "واتساب", "whatsapp", "إنستغرام", "instagram",
    "تيك توك", "tiktok", "بايت دانس", "bytedance",
    "تيسلا", "tesla", "سبيس إكس", "spacex",
    "هواوي", "huawei", "شاومي", "xiaomi", "أوبو", "oppo",
    "آي بي إم", "ibm", "أوراكل", "oracle",
    "إنتل", "intel", "amd", "snapdragon", "nvidia", "tsmc",
    "أوبر", "uber", "airbnb",
    "زوكربيرج", "zuckerberg", "إيلون ماسك", "elon musk",
    "سام ألتمان", "sam altman", "ساتيا", "satya nadella",
    "ستارلينك", "starlink", "x.com",
]

# ── HARD EXCLUSIONS — only for clearly non-tech content ───────────────────
# Keep this minimal! Tech news can mention elections, politics, war in tech context.
HARD_EXCLUDE_AR = [
    # Sports only
    "كرة القدم", "دوري كرة", "مباراة كرة", "هدف في المباراة",
    # Pure entertainment
    "فيلم سينمائي", "مسلسل تلفزيوني", "حفل موسيقي", "نجوم هوليود",
    # Food
    "وصفة طبخ", "مطعم شهير", "أكلة شعبية",
    # Natural disasters with no tech angle
    "زلزال يضرب", "فيضانات عارمة", "حريق غابات",
]

HARD_EXCLUDE_EN = [
    # Sports only
    "football match", "soccer game", "basketball game", "nba game",
    "cricket match", "tennis tournament", "golf tournament",
    # Pure entertainment
    "movie review", "film premiere", "celebrity gossip", "music album",
    "cooking recipe", "restaurant review",
    # Natural disasters with no tech angle
    "earthquake kills", "flood victims", "hurricane hits",
]


def is_tech_relevant(title: str, content: str = "") -> bool:
    """
    Balanced two-tier check:
    1. Hard exclusions (only obvious non-tech) → reject
    2. Strong tech keyword in TITLE → accept
    3. Tech company name in TITLE → accept
    4. Reject anything else
    """
    title_lower = title.lower().strip()
    content_lower = (content[:2000]).lower()

    # ── 1. Hard exclusions (PHRASES only — not single words) ────────────────
    for kw in HARD_EXCLUDE_AR + HARD_EXCLUDE_EN:
        if kw.lower() in title_lower:
            return False

    # ── 2. Strong tech keyword in TITLE ─────────────────────────────────────
    for kw in STRONG_TECH_TITLE_AR + STRONG_TECH_TITLE_EN:
        if kw.lower() in title_lower:
            return True

    # ── 3. Tech company name in TITLE → accept ──────────────────────────────
    for kw in TECH_COMPANIES_IN_TITLE:
        if kw.lower() in title_lower:
            return True

    # ── 4. Strong keyword anywhere in content (for short/vague titles) ──────
    for kw in STRONG_TECH_TITLE_AR + STRONG_TECH_TITLE_EN:
        if kw.lower() in content_lower:
            return True

    # ── 5. Reject anything else ─────────────────────────────────────────────
    return False
