"""
Application configuration, categories, payment methods, and theme tokens.
Includes smart keyword-to-symbol auto-detection for user-created categories.
"""
# pyrefly: ignore [missing-import]
import flet as ft
from typing import Dict, Any, Tuple

APP_NAME = "ExpenseFlow"
APP_VERSION = "1.0.0"

# Initial Default Categories
DEFAULT_CATEGORIES = [
    {
        "key": "Food & Dining",
        "label": "Food & Dining",
        "icon_name": "RESTAURANT",
        "icon": ft.Icons.RESTAURANT,
        "color": "#FF6B6B",
        "bg_color": "#2A1F2D",
    },
    {
        "key": "Groceries",
        "label": "Groceries",
        "icon_name": "LOCAL_GROCERY_STORE",
        "icon": ft.Icons.LOCAL_GROCERY_STORE,
        "color": "#4ECDC4",
        "bg_color": "#1C2E30",
    },
    {
        "key": "Transport",
        "label": "Transport",
        "icon_name": "DIRECTIONS_CAR",
        "icon": ft.Icons.DIRECTIONS_CAR,
        "color": "#45B7D1",
        "bg_color": "#1A2B38",
    },
    {
        "key": "Shopping",
        "label": "Shopping",
        "icon_name": "SHOPPING_BAG",
        "icon": ft.Icons.SHOPPING_BAG,
        "color": "#F39C12",
        "bg_color": "#332617",
    },
    {
        "key": "Bills & Utilities",
        "label": "Bills & Utilities",
        "icon_name": "BOLT",
        "icon": ft.Icons.BOLT,
        "color": "#E67E22",
        "bg_color": "#302219",
    },
    {
        "key": "Entertainment",
        "label": "Entertainment",
        "icon_name": "MOVIE",
        "icon": ft.Icons.MOVIE,
        "color": "#9B59B6",
        "bg_color": "#271E30",
    },
    {
        "key": "Health & Medical",
        "label": "Health & Medical",
        "icon_name": "LOCAL_HOSPITAL",
        "icon": ft.Icons.LOCAL_HOSPITAL,
        "color": "#E74C3C",
        "bg_color": "#301D21",
    },
    {
        "key": "Education",
        "label": "Education",
        "icon_name": "SCHOOL",
        "icon": ft.Icons.SCHOOL,
        "color": "#3498DB",
        "bg_color": "#1A2838",
    },
    {
        "key": "Travel",
        "label": "Travel",
        "icon_name": "FLIGHT",
        "icon": ft.Icons.FLIGHT,
        "color": "#1ABC9C",
        "bg_color": "#182C29",
    },
    {
        "key": "Investments",
        "label": "Investments",
        "icon_name": "TRENDING_UP",
        "icon": ft.Icons.TRENDING_UP,
        "color": "#2ECC71",
        "bg_color": "#1B2F23",
    },
    {
        "key": "Other",
        "label": "Other",
        "icon_name": "CATEGORY",
        "icon": ft.Icons.CATEGORY,
        "color": "#95A5A6",
        "bg_color": "#262A2B",
    },
]

# Backward compatibility reference
CATEGORIES = DEFAULT_CATEGORIES
CATEGORY_MAP = {c["key"]: c for c in DEFAULT_CATEGORIES}

# Comprehensive Keyword-to-Icon Rule Engine for Auto-Detection
SMART_ICON_RULES = [
    # Specific Subject / Hobbies First
    (["pet", "pets", "dog", "dogs", "cat", "cats", "puppy", "kitten", "veterinary", "animal", "petfood"], "PETS", "#F59E0B", "#2D2319"),
    (["gym", "fitness", "workout", "yoga", "sport", "sports", "exercise", "training", "crossfit", "muscle", "zumba", "badminton", "cricket", "football"], "FITNESS_CENTER", "#EC4899", "#2E1A25"),
    (["coffee", "cafe", "starbucks", "tea", "chai", "latte", "espresso", "cappuccino", "brew", "beverage", "drink", "boba", "juice", "shake"], "LOCAL_CAFE", "#A16207", "#28201D"),
    (["fuel", "petrol", "diesel", "gas", "cng", "refuel", "pump"], "LOCAL_GAS_STATION", "#F97316", "#2D201A"),
    (["car", "bike", "taxi", "uber", "ola", "cab", "auto", "vehicle", "ride", "drive", "toll", "parking", "rapido", "transport"], "DIRECTIONS_CAR", "#0EA5E9", "#1A2B38"),
    (["flight", "flights", "airplane", "airport", "airline", "travel", "trip", "tour", "holiday", "vacation", "resort", "hotel", "staycation"], "FLIGHT", "#06B6D4", "#182C29"),
    (["metro", "train", "railway", "subway", "bus", "commute", "transit", "ticket"], "DIRECTIONS_SUBWAY", "#10B981", "#172A27"),
    (["game", "games", "gaming", "steam", "playstation", "xbox", "nintendo", "console", "esports", "arcade"], "SPORTS_ESPORTS", "#C084FC", "#2A1D2E"),
    (["music", "spotify", "song", "concert", "audio", "headphone", "headphones", "sound"], "HEADPHONES", "#D946EF", "#2C1B2E"),
    (["movie", "movies", "cinema", "film", "theatre", "netflix", "prime", "hotstar", "show", "series", "ott", "entertainment"], "MOVIE", "#A855F7", "#271E30"),
    (["salon", "parlour", "barber", "haircut", "beauty", "spa", "cosmetics", "makeup", "skincare", "grooming", "waxing"], "CONTENT_CUT", "#F43F5E", "#2E1B23"),
    (["cloth", "clothes", "clothing", "dress", "shirt", "pant", "jeans", "shoes", "sneakers", "wear", "apparel", "suit", "jacket", "fashion", "footwear"], "CHECKROOM", "#FB923C", "#2D1F1A"),
    (["book", "books", "study", "exam", "course", "tuition", "education", "school", "college", "university", "class", "degree", "learn", "udemy", "coursera"], "SCHOOL", "#3B82F6", "#1A2838"),
    (["doctor", "medicine", "hospital", "pharma", "pharmacy", "medical", "clinic", "health", "dental", "dentist", "pill", "pills", "tablet", "treatment"], "LOCAL_HOSPITAL", "#EF4444", "#2D1A1C"),
    (["rent", "home", "house", "flat", "room", "apartment", "mortgage", "hostel", "stay", "lease", "pg", "property"], "HOME", "#6366F1", "#1C2030"),
    (["grocery", "groceries", "supermarket", "market", "mart", "vegetable", "veggies", "fruit", "fruits", "milk", "dairy", "ration", "kirana"], "LOCAL_GROCERY_STORE", "#14B8A6", "#1C2E30"),
    (["food", "dining", "restaurant", "lunch", "dinner", "breakfast", "meal", "snack", "pizza", "burger", "bakery", "cake", "swiggy", "zomato", "fastfood", "sweet", "sweets"], "RESTAURANT", "#FF6B6B", "#2A1F2D"),
    (["shopping", "shop", "mall", "store", "amazon", "flipkart", "myntra", "meesho", "buy", "purchase"], "SHOPPING_BAG", "#F59E0B", "#332617"),
    (["bill", "bills", "electricity", "power", "current", "light", "energy"], "BOLT", "#F59E0B", "#302219"),
    (["water", "aqua", "utility", "sewage"], "WATER_DROP", "#38BDF8", "#162836"),
    (["wifi", "internet", "broadband", "fiber", "recharge", "mobile", "phone", "sim", "telecom", "jio", "airtel"], "WIFI", "#06B6D4", "#172C2E"),
    (["furniture", "decor", "interior", "bed", "sofa", "chair", "table", "curtain", "mattress"], "WEEKEND", "#8D6E63", "#251F1C"),
    (["repair", "maintenance", "tool", "tools", "plumbing", "hardware", "fix", "mechanic"], "BUILD", "#64748B", "#202528"),
    (["office", "work", "stationery", "print", "xerox", "paper", "pen", "business"], "BUSINESS_CENTER", "#64748B", "#1B2226"),
    (["gadget", "tech", "technology", "laptop", "computer", "pc", "macbook", "ipad", "tablet", "electronics", "software", "apple"], "DEVICES", "#94A3B8", "#1F262B"),
    (["investment", "investments", "sip", "mutual fund", "stock", "stocks", "shares", "trading", "crypto", "bitcoin", "gold", "deposit"], "TRENDING_UP", "#22C55E", "#1B2F23"),
    (["salary", "bonus", "income", "wage", "freelance", "earning", "cashback", "dividend"], "ACCOUNT_BALANCE_WALLET", "#10B981", "#1B2C1F"),
    (["gift", "gifts", "present", "donation", "charity", "ngo", "birthday", "anniversary", "offering"], "CARD_GIFTCARD", "#F43F5E", "#2E1B24"),
    (["tax", "taxes", "gst", "itr", "penalty", "fine", "challan"], "RECEIPT_LONG", "#94A3B8", "#202528"),
    (["insurance", "policy", "lic", "premium", "security"], "SECURITY", "#6366F1", "#1C2030"),
    (["kid", "kids", "baby", "child", "children", "toy", "toys", "daycare", "diaper"], "CHILD_CARE", "#FB7185", "#2E1C1D"),
]

FALLBACK_PALETTE = [
    ("#8B5CF6", "#291E3B"),  # Violet
    ("#EC4899", "#2E1A25"),  # Pink
    ("#14B8A6", "#172A27"),  # Teal
    ("#F97316", "#2D201A"),  # Orange
    ("#06B6D4", "#172C2E"),  # Cyan
    ("#84CC16", "#222D16"),  # Lime
    ("#EAB308", "#2E2A15"),  # Yellow
    ("#6366F1", "#1C2030"),  # Indigo
]

def auto_detect_category_info(name: str) -> Dict[str, Any]:
    """
    Intelligently analyzes a category name and automatically assigns the most
    appropriate Material Design icon, primary color, and background tint.
    """
    import re
    clean_name = name.strip()
    name_lower = clean_name.lower()
    words = set(re.findall(r'\b\w+\b', name_lower))

    # Pass 1: exact word match (highest confidence)
    for keywords, icon_name, color, bg_color in SMART_ICON_RULES:
        if any(kw in words for kw in keywords):
            icon_obj = getattr(ft.Icons, icon_name, ft.Icons.CATEGORY)
            return {
                "key": clean_name,
                "label": clean_name,
                "icon_name": icon_name,
                "icon": icon_obj,
                "color": color,
                "bg_color": bg_color,
            }

    # Pass 2: substring match (e.g. compound words or plurals)
    for keywords, icon_name, color, bg_color in SMART_ICON_RULES:
        if any(kw in name_lower for kw in keywords):
            icon_obj = getattr(ft.Icons, icon_name, ft.Icons.CATEGORY)
            return {
                "key": clean_name,
                "label": clean_name,
                "icon_name": icon_name,
                "icon": icon_obj,
                "color": color,
                "bg_color": bg_color,
            }

    # Fallback: compute deterministic color from string hash and use LABEL icon
    hash_idx = abs(hash(clean_name)) % len(FALLBACK_PALETTE)
    fb_color, fb_bg = FALLBACK_PALETTE[hash_idx]

    return {
        "key": clean_name,
        "label": clean_name,
        "icon_name": "LABEL",
        "icon": ft.Icons.LABEL,
        "color": fb_color,
        "bg_color": fb_bg,
    }

# Payment Modes
PAYMENT_MODES = [
    {"key": "UPI", "label": "UPI (GPay / PhonePe)", "icon": ft.Icons.QR_CODE_SCANNER, "color": "#10B981"},
    {"key": "Cash", "label": "Cash", "icon": ft.Icons.PAYMENTS, "color": "#059669"},
    {"key": "Credit Card", "label": "Credit Card", "icon": ft.Icons.CREDIT_CARD, "color": "#6366F1"},
    {"key": "Debit Card", "label": "Debit Card", "icon": ft.Icons.PAYMENT, "color": "#3B82F6"},
    {"key": "Net Banking", "label": "Net Banking", "icon": ft.Icons.ACCOUNT_BALANCE, "color": "#8B5CF6"},
]

PAYMENT_MAP = {p["key"]: p for p in PAYMENT_MODES}

# Supported Currencies
CURRENCIES = ["₹", "$", "€", "£", "¥", "AED", "CAD", "AUD", "SGD"]

# Default App Settings
DEFAULT_SETTINGS = {
    "sheet_name": "ExpenseFlow Tracker & Reports",
    "credentials_path": "credentials.json",
    "currency_symbol": "₹",
    "monthly_budget": "25000",
    "theme_mode": "dark",
    "auto_sync": "true",
    "last_sync_time": "",
    "sheet_url": "",
}

# Theme Colors (Modern Dark / Neon accent palette)
class ModernPalette:
    BG_DARK = "#0F172A"       # Slate 900
    SURFACE_DARK = "#1E293B"  # Slate 800
    CARD_DARK = "#1E293B"
    CARD_BORDER = "#334155"   # Slate 700
    TEXT_PRIMARY = "#F8FAFC"  # Slate 50
    TEXT_MUTED = "#94A3B8"    # Slate 400
    PRIMARY = "#6366F1"       # Indigo 500
    PRIMARY_LIGHT = "#818CF8" # Indigo 400
    ACCENT = "#38BDF8"        # Sky 400
    SUCCESS = "#10B981"       # Emerald 500
    WARNING = "#F59E0B"       # Amber 500
    DANGER = "#EF4444"        # Red 500
    INFO = "#38BDF8"          # Sky 400

# Database Configuration (MySQL Primary with SQLite Offline Fallback)
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "expenseflow_db",
}
USE_MYSQL = True

# Email / SMTP Configuration (Gmail SMTP for Registration OTP & Admin Password Resets)
SMTP_CONFIG = {
    "host": "smtp.gmail.com",
    "port": 587,
    "user": "yashmakwana26@gmail.com",
    "password": "yhhbjseqhpdocztq",
    "sender_name": "ExpenseFlow Security",
    "use_tls": True,
}
