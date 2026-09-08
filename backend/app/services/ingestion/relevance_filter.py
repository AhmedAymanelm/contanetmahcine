"""
Strict AI/Tech relevance filter — final version.
Requires SPECIFIC AI/tech keywords in title. Broad terms like 'technology' are NOT enough.
Also blocks common non-tech science/news patterns.
"""

# ── SPECIFIC AI/Tech STRONG keywords — unique to tech content ───────────────
STRONG_TECH_AR = [
    # AI/ML
    "ذكاء اصطناعي", "ذكاء الاصطناعي", "تعلم آلي", "تعلم الآلة",
    "نموذج لغوي", "خوارزمية ذكاء", "توليد بالذكاء",
    "شات جي بي تي", "chatgpt", "gpt-", "gpt4", "gpt3",
    "gemini", "claude", "llm", "openai", "anthropic", "grok", "xai",
    # Software/Programming
    "برمجة", "برمجيات", "سوفتوير", "كود برمجي", "تطوير تطبيق",
    # Cybersecurity
    "أمن سيبراني", "اختراق إلكتروني", "هجوم سيبراني", "ثغرة أمنية",
    "برمجيات خبيثة", "فيروس إلكتروني", "هكر",
    # Hardware/Chips
    "رقاقة إلكترونية", "شريحة معالج", "بطاقة رسومات", "معالج مخصص",
    "nvidia", "إنفيديا", "gpu", "cpu",
    # Crypto/Blockchain
    "بيتكوين", "بلوكتشين", "عملة رقمية", "كريبتو", "ميمكوين",
    # VR/AR
    "واقع افتراضي", "واقع معزز", "نظارات الواقع",
    # EVs/Autonomous
    "سيارة ذاتية القيادة", "قيادة ذاتية", "سيارة كهربائية", "بطارية ليثيوم",
    # Cloud/Data
    "حوسبة سحابية", "بيانات ضخمة", "خادم سحابي",
    # Quantum
    "حوسبة كمومية", "كيوبت",
    # Connectivity
    "5g", "6g", "إنترنت الأشياء",
    # Robots
    "روبوت ذكي", "روبوتات", "ذراع آلية",
    # Smartphones (specific)
    "هاتف ذكي", "آيفون", "أندرويد",
    # Social platforms (as tech)
    "منصة رقمية", "تطبيق ذكي",
]

STRONG_TECH_EN = [
    # AI/ML
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "large language model", "generative ai",
    "ai model", "ai chip", "ai tool", "ai agent",
    "chatgpt", "openai", "gemini", "claude", "llm", "gpt-", "gpt4",
    # Programming/Software
    "programming", "software", "open source", "source code", "api",
    "developer tool", "coding",
    # Cybersecurity
    "cybersecurity", "data breach", "hacking", "ransomware",
    "zero-day", "vulnerability", "malware", "phishing",
    # Hardware/Chips
    "semiconductor", "microchip", "gpu", "cpu", "processor",
    "arm chip", "quantum chip",
    # Crypto
    "bitcoin", "blockchain", "cryptocurrency", "crypto", "nft", "web3",
    # VR/AR
    "virtual reality", "augmented reality", "metaverse",
    # EVs
    "electric vehicle", "self-driving", "autonomous vehicle", "ev battery",
    # Cloud/Data
    "cloud computing", "big data", "data center",
    # Quantum
    "quantum computing",
    # Connectivity
    "5g", "6g", "iot",
    # Robots
    "robotics", "autonomous robot",
    # Startup/Funding (tech context)
    "tech startup", "ai startup", "seed round", "series a",
]

# ── TECH COMPANIES — accept if company name is in title ───────────────────
TECH_COMPANIES = [
    "أبل", "apple", "سامسونج", "samsung", "قوقل", "google", "ألفابيت", "alphabet",
    "مايكروسوفت", "microsoft", "أمازون", "amazon", "aws",
    "ميتا", "meta", "فيسبوك", "facebook", "واتساب", "whatsapp", "إنستغرام", "instagram",
    "تيك توك", "tiktok", "بايت دانس", "bytedance",
    "تيسلا", "tesla", "سبيس إكس", "spacex",
    "هواوي", "huawei", "شاومي", "xiaomi", "أوبو", "oppo",
    "إنتل", "intel", "amd", "snapdragon", "nvidia", "tsmc", "qualcomm",
    "إيلون ماسك", "elon musk", "سام ألتمان", "sam altman",
    "ستارلينك", "starlink", "أوبر", "uber", "airbnb",
    "أوراكل", "oracle", "sap", "ibm", "salesforce",
    "anthropic", "mistral", "deepmind", "cohere",
]

# ── HARD EXCLUDE — patterns that almost never appear in tech news ──────────
HARD_EXCLUDE_AR = [
    # Astronomy/Space (non-tech)
    "جسم جليدي", "مذنب جديد", "كوكب جديد", "نجم جديد", "مجرة بعيدة",
    "تلسكوب يكشف", "فضاء خارجي", "ناسا تكشف",
    # Ancient/Biology
    "حفريات", "ديناصور", "أحفوريات", "تطور الأنواع",
    "سلوك الحيوان", "نباتات جديدة",
    # Weather/Disasters
    "طقس الغد", "درجات الحرارة", "موجة حر", "أمطار غزيرة",
    "زلزال يضرب", "إعصار يتجه", "فيضان",
    # Pure Sports
    "كرة القدم", "دوري أبطال", "مباراة اليوم", "نادي كرة",
    "لاعب كرة", "هدف في مباراة",
    # Entertainment
    "فيلم جديد", "مسلسل جديد", "حفلة موسيقية", "نجوم الغناء",
    # Cooking/Food
    "وصفة طبخ", "مطبخ", "أطباق",
    # Politics/War (specific phrases not general mentions)
    "معركة عسكرية", "قصف المدن", "مستوطنات إسرائيلية",
    "انتخابات رئاسية", "مجلس النواب",
]

HARD_EXCLUDE_EN = [
    # Astronomy (non-tech)
    "comet discovered", "new planet", "new star", "galaxy found",
    "telescope reveals", "nasa discovers", "icy body",
    # Paleontology
    "fossil discovered", "dinosaur", "ancient species",
    # Weather/Disasters
    "weather forecast", "heat wave", "rainfall",
    "earthquake kills", "flood victims", "hurricane",
    # Sports
    "football match", "soccer game", "basketball game",
    "cricket match", "tennis tournament", "golf tournament",
    # Entertainment
    "movie review", "film premiere", "celebrity gossip",
    "music album", "concert tour",
    # Cooking
    "cooking recipe", "restaurant review",
    # Politics/War (specific)
    "military battle", "bombing campaign", "war crimes",
    "presidential election", "parliament vote",
]


def is_tech_relevant(title: str, content: str = "") -> bool:
    """
    Final strict filter: only accept articles with clear AI/tech signals in title.
    """
    title_lower = title.lower().strip()

    # ── Strip common Arabic category prefixes (e.g. "تكنولوجيا | العنوان") ──
    import re
    clean_title = re.sub(r'^[\u0600-\u06FF\w\s]+[|:»–-]\s*', '', title_lower, count=1).strip()
    if not clean_title:
        clean_title = title_lower

    # ── 1. Hard exclusions ───────────────────────────────────────────────────
    for kw in HARD_EXCLUDE_AR + HARD_EXCLUDE_EN:
        if kw.lower() in clean_title or kw.lower() in title_lower:
            return False

    # ── 2. STRONG specific tech keyword in title ────────────────────────────
    for kw in STRONG_TECH_AR + STRONG_TECH_EN:
        if kw.lower() in clean_title or kw.lower() in title_lower:
            return True

    # ── 3. Tech company name in title ───────────────────────────────────────
    for kw in TECH_COMPANIES:
        if kw.lower() in clean_title or kw.lower() in title_lower:
            return True

    return False
