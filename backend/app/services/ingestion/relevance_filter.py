"""
Relevance filter — keeps only AI & tech articles.
Checks article title + first 500 chars of content.
"""

# ─── Keywords that MUST match (at least one) ───────────────────────────────
TECH_AI_KEYWORDS_AR = [
    # AI / ML
    "ذكاء اصطناعي", "ذكاء الاصطناعي", "تعلم آلي", "تعلم الآلة", "نموذج لغوي",
    "شات جي بي تي", "chatgpt", "gpt", "جيميناي", "gemini", "claude", "كلود",
    "llm", "openai", "أوبن إي آي", "anthropic", "ميتا ai", "meta ai",
    "روبوت ذكي", "روبوتات", "الروبوت", "نماذج AI", "نموذج AI",
    "توليد المحتوى", "الذكاء", "تقنية الذكاء",
    # Tech general
    "تكنولوجيا", "تقنية", "تقنيات", "برمجيات", "برمجة", "كود", "مطور",
    "تطبيق", "منصة", "سوفتوير", "هاردوير", "خوارزمية",
    # Devices & hardware
    "هاتف", "جهاز", "حاسوب", "لابتوب", "شريحة", "معالج", "رقاقة",
    "أبل", "apple", "سامسونج", "samsung", "قوقل", "google", "مايكروسوفت",
    "microsoft", "أمازون", "amazon", "ميتا", "meta", "nvidia", "إنفيديا",
    "qualcomm", "كوالكوم", "intel", "إنتل", "amd",
    # Connectivity & cloud
    "5g", "6g", "ألياف", "سحابة", "cloud", "خادم", "servers",
    "إنترنت الأشياء", "iot", "واقع افتراضي", "واقع معزز", "vr", "ar", "xr",
    "ميتافيرس", "metaverse",
    # Cybersecurity
    "أمن سيبراني", "اختراق", "قرصنة", "هجوم إلكتروني", "بيانات", "خصوصية",
    "تشفير", "ثغرة", "برمجية خبيثة", "ransomware",
    # Startups & business tech
    "شركة ناشئة", "ستارتب", "startup", "تمويل", "استثمار تقني",
    "ipo", "طرح عام", "يونيكورن", "unicorn",
    # Crypto & blockchain
    "بيتكوين", "bitcoin", "بلوكتشين", "blockchain", "عملة رقمية", "كريبتو",
    "crypto", "nft", "web3",
    # Space tech
    "فضاء", "ناسا", "nasa", "spacex", "سبيس إكس", "صاروخ", "قمر صناعي",
    # Electric vehicles
    "سيارة كهربائية", "ev", "تيسلا", "tesla",
]

TECH_AI_KEYWORDS_EN = [
    "artificial intelligence", "machine learning", "deep learning", "neural network",
    "chatgpt", "openai", "gemini", "claude", "llm", "large language model",
    "generative ai", "ai model", "ai tool", "ai chip", "gpu",
    "technology", "tech", "software", "hardware", "algorithm", "programming",
    "smartphone", "iphone", "android", "laptop", "processor", "chip",
    "apple", "google", "microsoft", "amazon", "meta", "nvidia", "qualcomm",
    "samsung", "intel", "amd", "tsmc",
    "5g", "6g", "cloud computing", "server", "data center",
    "iot", "virtual reality", "augmented reality", "vr", "ar", "metaverse",
    "cybersecurity", "hacking", "data breach", "encryption", "privacy",
    "startup", "venture capital", "ipo", "unicorn", "funding",
    "bitcoin", "blockchain", "crypto", "nft", "web3",
    "spacex", "nasa", "rocket", "satellite",
    "electric vehicle", "ev", "tesla", "autonomous",
    "robotics", "robot", "drone", "automation",
    "quantum computing", "semiconductor",
]

# ─── Keywords that EXCLUDE an article even if tech keyword found ────────────
EXCLUDE_KEYWORDS = [
    "كرة قدم", "رياضة", "دوري", "مباراة", "هدف", "لاعب", "مدرب",
    "فيلم", "مسلسل", "ممثل", "موسيقى", "أغنية",
    "طبخ", "وصفة", "أكل",
    "sport", "football", "soccer", "basketball", "nba", "nfl",
    "movie", "film", "actor", "music", "recipe", "cooking",
    "politics", "election", "president", "minister", "parliament",
    "سياسة", "انتخابات", "رئيس وزراء", "برلمان", "حكومة",
    "حرب", "مقتل", "قتل", "اشتباك", "قصف",
    "war", "killed", "shooting", "bombing",
    "رياضي", "بطولة", "مونديال",
]


def is_tech_relevant(title: str, content: str = "") -> bool:
    """
    Returns True if the article is tech/AI relevant.
    Checks title first (weighted more), then content snippet.
    """
    combined = (title + " " + content[:600]).lower()
    combined_ar = combined  # Arabic is already lower-safe

    # Check exclusions first
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in combined_ar:
            # But only exclude if NO strong tech signal in title
            title_lower = title.lower()
            if not any(kw2 in title_lower for kw2 in TECH_AI_KEYWORDS_AR + TECH_AI_KEYWORDS_EN):
                return False

    # Check tech/AI keywords
    for kw in TECH_AI_KEYWORDS_AR + TECH_AI_KEYWORDS_EN:
        if kw.lower() in combined_ar:
            return True

    return False
