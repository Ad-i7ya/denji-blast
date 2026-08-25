"""DENJI BLAST v4.0 - ULTRA EDITION (FIXED)
+--------------------------------------------------------------+
¦           SMS BLAST BOT  v4.0 - DENJI ULTRA EDITION          ¦
¦  ✔ FIXED: "message is too long" error                        ¦
¦  ✔ MASTER OWNER PANEL (Only owner can access)               ¦
¦  ✔ COLORED BUTTONS + GREAT FONTS                             ¦
¦  ✔ REAL SMS COUNT SYSTEM                                     ¦
¦  ✔ MULTIPLIER SYSTEM (Hidden from users)                     ¦
¦  ✔ /source owner-only command                                ¦
¦  ✔ Fast + Live progress updates                              ¦
+--------------------------------------------------------------+
"""

import asyncio, json, os, time, logging, random, string
from datetime import datetime, timedelta
import aiohttp
import db
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile,
    BufferedInputFile,
    MessageEntity,
    BotCommand, BotCommandScopeDefault
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ButtonStyle, ParseMode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("DenjiBlast")

# ========== CONFIG ==========
MAIN_OWNER = 8310937786
SUPER_ADMIN_NAME = "@levelopp"    # main owner
SUPER_ADMIN_LINK = f"tg://user?id={MAIN_OWNER}"
SUPER_ADMINS = [8310937786]
PREMIUM_CONTACT = "@te4m1ord"     # contact for premium/payment

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
_DATA_FILE = os.getenv("DATA_FILE", "blast_data.json")
_VERSION = "v4.0-DENJI"
_PROGRESS_UPDATE_INTERVAL = 0.15
_BACKGROUND_SCAN_INTERVAL = 60.0

# ========== PREMIUM MESSAGE EFFECTS ==========
# Telegram Bot API documented example effect ID (party popper 🎉).
EFFECT_PARTY = "5046509860389126442"

SPEED_FAST = 0.015
SPEED_MEDIUM = 0.12
SPEED_SLOW = 0.3
SPEED_DEFAULT = SPEED_MEDIUM

# ========== UI ICONS ==========
I = {
    "crown": "👑", "star": "⭐", "sparkle": "✨", "glow": "🌟",
    "diamond": "💎", "gem": "💠", "fire": "🔥", "bolt": "⚡",
    "fast": "🚀", "heart": "❤️", "money": "💰", "card": "💳",
    "gift": "🎁", "stats": "📊", "shield": "🛡️", "check": "✅",
    "verified": "✔️", "tick": "✅", "cross": "❌", "block": "🚫",
    "stop": "🛑", "send": "📨", "back": "🔙", "home": "🏠",
    "refresh": "🔄", "users": "👥", "user": "👤", "target": "🎯",
    "info": "ℹ️", "warning": "⚠️", "list": "📋", "broadcast": "📢",
    "settings": "⚙️", "add": "➕", "remove": "➖", "edit": "✏️",
    "manage": "🛠️", "speed": "⚡", "slow": "🐢", "protect": "🔒",
    "track": "📡", "history": "📜", "export": "📦", "import": "📥",
    "plan": "💳", "redeem": "🎟️", "refer": "🤝", "help": "❓",
    "sms": "📱", "join": "🔗", "link": "🔗", "sleep": "😴",
}

# ========== BUTTON BUILDERS ==========
def premium_btn(text: str, callback: str, emoji_key: str = None, style: str = "secondary") -> InlineKeyboardButton:
    style_map = {"primary": ButtonStyle.PRIMARY, "success": ButtonStyle.SUCCESS, "danger": ButtonStyle.DANGER, "secondary": None}
    icon = I.get(emoji_key, "") if emoji_key else ""
    label = f"{icon} {text}" if icon else text
    return InlineKeyboardButton(
        text=label,
        callback_data=callback,
        icon_custom_emoji_id=None,
        style=style_map.get(style)
    )

def normal_btn(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        callback_data=callback,
        icon_custom_emoji_id=None,
        style=None
    )

def url_btn(text: str, url: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        url=url,
        icon_custom_emoji_id=None,
        style=None
    )

def make_kb(rows: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ========== PER-USER SESSIONS ==========
class UserSession:
    __slots__ = ['uid', 'cancelled', 'sent', 'failed', 'task', 'start_time', 'lock', 'number']
    def __init__(self, uid: int):
        self.uid = uid
        self.cancelled = False
        self.sent = 0
        self.failed = 0
        self.task = None
        self.start_time = time.time()
        self.lock = asyncio.Lock()
        self.number = None

USER_SESSIONS = {}
SESSIONS_LOCK = asyncio.Lock()
CACHED_DEVICES = []
LAST_SCAN_TIME = 0
SCANNING_IN_PROGRESS = False
SCAN_STATUS = "Not started"
FB_DEVICE_COUNTS = {}
SCAN_LOCK = asyncio.Lock()
PROTECTED_NUMBERS = {}

# ========== STATES ==========
class S(StatesGroup):
    send_number = State()
    send_message = State()
    send_speed = State()
    send_count = State()
    owner_send_number = State()
    owner_send_message = State()
    owner_send_speed = State()
    owner_send_count = State()
    admin_send_number = State()
    admin_send_message = State()
    admin_send_speed = State()
    admin_send_count = State()
    redeem_code = State()
    add_firebase = State()
    add_firebase_batch = State()
    add_owner = State()
    add_admin = State()
    ban_user = State()
    unban_user = State()
    broadcast = State()
    fj_add_channel = State()
    fj_add_link = State()
    add_plan_name = State()
    add_plan_price = State()
    add_plan_credits = State()
    add_plan_link = State()
    add_credits_uid = State()
    add_credits_amount = State()
    deduct_credits_uid = State()
    deduct_credits_amount = State()
    gen_redeem_credits = State()
    gen_redeem_uses = State()
    set_ref_credits = State()
    protect_number = State()
    track_number = State()
    transfer_credits_uid = State()
    transfer_credits_amount = State()
    add_all_credits_amount = State()
    deduct_all_credits_amount = State()
    toggle_transfer = State()
    set_multiplier = State()
    set_daily_limit = State()
    add_template_name = State()
    add_template_text = State()

# ========== DATA FUNCTIONS ==========
def _default_data() -> dict:
    return {
        "owners": [MAIN_OWNER],
        "admins": [],
        "banned": [],
        "free_mode": False,
        "approved": [],
        "firebases": [],
        "users": {},
        "stats": {"total_sent": 0, "total_failed": 0, "api_usage": {}},
        "premium": {"ref_credits": 3},
        "force_join": {"enabled": False, "channels": []},
        "pricing": {"plans": []},
        "redeem_codes": {},
        "settings": {
            "ref_credits": 3,
            "max_owners": 6,
            "transfer_enabled": True,
            "multiplier": 3,
            "daily_limit": 0
        },
        "sms_history": {},
        "activity_log": [],
        "protected_numbers": {}
    }

def _load_firebases_from_env(d: dict):
    """Load firebases from the FIREBASES env var if the JSON file has none.
    Format: one per line -> Label | https://url.firebaseio.com
    This gives a fallback so firebases survive even if blast_data.json is wiped.
    """
    raw = os.getenv("FIREBASES", "").strip()
    if not raw:
        return
    fbs = d.get("firebases", [])
    if fbs:
        return  # file already has firebases, keep them
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            parts = line.split("|", 1)
            label = parts[0].strip()
            url = parts[1].strip()
        else:
            url = line
            label = url.replace("https://", "").split(".")[0][:20]
        if not url.startswith("http"):
            continue
        url = url.rstrip("/")
        if any(fb["url"] == url for fb in fbs):
            continue
        fb_id = str(int(time.time())) + str(random.randint(100, 999))
        fbs.append({"id": fb_id, "url": url, "label": label, "added_at": int(time.time())})
    d["firebases"] = fbs
    if fbs:
        log.info(f"✅ Loaded {len(fbs)} firebases from FIREBASES env var")

def load() -> dict:
    """Load all state from MongoDB, retaining the existing schema/defaults."""
    remote = db.load()
    if remote:
        data = remote
    elif os.getenv("MONGODB_URI", "").strip():
        data = {}
    elif os.path.exists(_DATA_FILE):
        try:
            with open(_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            default = _default_data()
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            if MAIN_OWNER not in data.get("owners", []):
                data["owners"].insert(0, MAIN_OWNER)
            if "transfer_enabled" not in data.get("settings", {}):
                data.setdefault("settings", {})["transfer_enabled"] = True
            if "multiplier" not in data.get("settings", {}):
                data.setdefault("settings", {})["multiplier"] = 3
            if "daily_limit" not in data.get("settings", {}):
                data.setdefault("settings", {})["daily_limit"] = 0
            _load_firebases_from_env(data)
            return data
        except Exception as e:
            log.error(f"Load error: {e}")
    d = _default_data()
    _load_firebases_from_env(d)
    save(d)
    return d

def save(d: dict):
    """Persist the complete bot state in MongoDB; use atomic JSON only locally."""
    db.save(d)

def reg_user(uid: int, name: str, d: dict, username: str = ""):
    k = str(uid)
    if k not in d["users"]:
        d["users"][k] = {
            "name": name, "username": username or "", "uses": 0, "credits": 0,
            "joined_at": int(time.time()),
            "refer_code": None, "referred_by": None,
            "sms_history": [], "device_limit": 0
        }
    else:
        d["users"][k]["name"] = name
        if username:
            d["users"][k]["username"] = username
        d["users"][k].setdefault("device_limit", 0)

def is_main_owner(uid: int) -> bool:
    return uid == MAIN_OWNER

def is_owner(uid: int, d: dict) -> bool:
    return uid in d.get("owners", [MAIN_OWNER]) or uid in SUPER_ADMINS

def is_admin(uid: int, d: dict) -> bool:
    return is_owner(uid, d) or uid in d.get("admins", [])

def is_banned(uid: int, d: dict) -> bool:
    return uid in d.get("banned", [])

def can_use(uid: int, d: dict) -> bool:
    if is_banned(uid, d):
        return False
    if is_admin(uid, d):
        return True
    if d.get("free_mode"):
        return True
    if uid in d.get("approved", []):
        return True
    return False

def get_user_credits(uid: int, d: dict) -> int:
    return d.get("users", {}).get(str(uid), {}).get("credits", 0)

def add_credits(uid: int, amount: int, d: dict):
    k = str(uid)
    if k not in d.get("users", {}):
        d["users"][k] = {"credits": 0}
    d["users"][k]["credits"] = d["users"][k].get("credits", 0) + amount

def deduct_credits(uid: int, amount: int, d: dict) -> bool:
    k = str(uid)
    if k in d.get("users", {}):
        current = d["users"][k].get("credits", 0)
        if current >= amount:
            d["users"][k]["credits"] = current - amount
            return True
    return False

def generate_user_refer_code(uid: int, d: dict) -> str:
    k = str(uid)
    if k in d.get("users", {}) and d["users"][k].get("refer_code"):
        return d["users"][k]["refer_code"]
    while True:
        code = "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        exists = any(u.get("refer_code") == code for u in d.get("users", {}).values())
        if not exists:
            break
    if k in d.get("users", {}):
        d["users"][k]["refer_code"] = code
    return code

def process_referral(new_uid: int, code: str, d: dict) -> tuple:
    referrer_uid = None
    for uid_str, udata in d.get("users", {}).items():
        if udata.get("refer_code") == code:
            referrer_uid = int(uid_str)
            break
    if not referrer_uid:
        return False, "Invalid referral code!", None
    if referrer_uid == new_uid:
        return False, "You cannot use your own code!", None
    if d["users"].get(str(new_uid), {}).get("referred_by"):
        return False, "You have already been referred!", None
    ref_credits = d.get("settings", {}).get("ref_credits", 3)
    add_credits(new_uid, ref_credits, d)
    add_credits(referrer_uid, ref_credits, d)
    d["users"][str(new_uid)]["referred_by"] = referrer_uid
    save(d)
    return True, f"Welcome! You got {ref_credits} credits!", referrer_uid

def fmt_time(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")


def user_name(uid: int, d: dict) -> str:
    """Return best display name: @username > full name > chat ID."""
    u = d.get("users", {}).get(str(uid), {})
    uname = u.get("username", "")
    if uname:
        return f"@{uname}"
    uname = u.get("name", "")
    if uname:
        return uname[:24]
    return str(uid)

def fmt_device_count(count: int) -> str:
    """Compact device count: 50+, 1.1k, 1.2k, etc."""
    count = max(0, int(count))
    if count > 50 and count < 1000:
        return "50+"
    if count >= 1000:
        # Truncate, rather than round, so 1,050 displays as 1k and
        # 1,100 displays as 1.1k.
        tenths = count // 100
        whole, remainder = divmod(tenths, 10)
        formatted = str(whole) if remainder == 0 else f"{whole}.{remainder}"
        return f"{formatted}k"
    return str(count)

def fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60}s"

def mask_number(number: str) -> str:
    if len(number) <= 4:
        return number
    return number[:2] + "******" + number[-4:]

def normalize_number(raw: str) -> tuple:
    """Indian-friendly number normalizer.
    Accepts +91XXXXXXXXXX, 91XXXXXXXXXX, 0XXXXXXXXXX and plain 10-digit
    Indian mobile numbers. Returns (ok, normalized, error).
    """
    cleaned = "".join(ch for ch in (raw or "").strip() if ch.isdigit() or ch == "+")
    if not cleaned:
        return False, "", "❌ Number is empty! Try again."
    if cleaned.startswith("+"):
        digits = cleaned[1:]
        if not digits.isdigit() or len(digits) < 7 or len(digits) > 15:
            return False, "", "❌ Invalid number. Format: +91XXXXXXXXXX"
        return True, "+" + digits, ""
    if not cleaned.isdigit():
        return False, "", "❌ Use only digits (and +)."
    if len(cleaned) == 10 and cleaned[0] in "6789":
        return True, "+91" + cleaned, ""
    if len(cleaned) == 12 and cleaned.startswith("91"):
        return True, "+91" + cleaned[2:], ""
    if len(cleaned) == 11 and cleaned.startswith("0") and cleaned[1] in "6789":
        return True, "+91" + cleaned[1:], ""
    return False, "", "❌ Invalid number. Format: +91XXXXXXXXXX or a 10-digit Indian number."

def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def get_daily_used(uid: int, d: dict) -> int:
    du = d.get("users", {}).get(str(uid), {}).get("daily_used") or {}
    if du.get("date") != today_str():
        return 0
    return du.get("count", 0)

def get_daily_remaining(uid: int, d: dict):
    """Returns remaining daily quota for regular users, or None if unlimited."""
    limit = d.get("settings", {}).get("daily_limit", 0)
    if limit <= 0:
        return None
    return max(0, limit - get_daily_used(uid, d))

def add_daily_used(uid: int, amount: int, d: dict):
    u = d.setdefault("users", {}).setdefault(str(uid), {})
    du = u.get("daily_used") or {}
    if du.get("date") != today_str():
        du = {"date": today_str(), "count": 0}
        u["daily_used"] = du
    du["count"] = du.get("count", 0) + amount

def get_scan_status() -> str:
    global SCAN_STATUS, CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS
    if SCANNING_IN_PROGRESS:
        return "Scanning..."
    if not CACHED_DEVICES:
        return "No devices"
    device_count = len(CACHED_DEVICES)
    time_diff = time.time() - LAST_SCAN_TIME
    if time_diff < 60:
        return f"{fmt_device_count(device_count)} devices"
    else:
        return f"{fmt_device_count(device_count)} devices ({int(time_diff/60)}m old)"

def log_activity(d: dict, action: str, uid: int, details: str = ""):
    d.setdefault("activity_log", []).append({
        "timestamp": int(time.time()), "uid": uid, "action": action, "details": details
    })
    if len(d["activity_log"]) > 1000:
        d["activity_log"] = d["activity_log"][-1000:]

def progress_bar(current: int, total: int, width: int = 14) -> str:
    if total <= 0:
        return "█" * width
    filled = min(width, int(width * current / total))
    return "█" * filled + "░" * (width - filled)

def progress_text(sent: int, failed: int, total: int, credits: int = None, speed_label: str = "MEDIUM") -> str:
    total_sent = sent + failed
    bar = progress_bar(total_sent, total)
    percent = int((total_sent / total) * 100) if total > 0 else 0

    lines = [
        f"⚡ <b>DENJI BLAST - Sending SMS...</b>\n",
        f"<code>{bar}</code> <b>{percent}%</b>\n",
        f"✅ Sent: <b>{sent}</b>",
        f"❌ Failed: <b>{failed}</b>",
        f"📊 Progress: <b>{total_sent} / {total}</b>",
        f"🚀 Speed: <b>{speed_label}</b>\n",
    ]
    if credits is not None:
        lines.append(f"💰 Credits Left: <b>{credits}</b>")
    lines.append(f"\n🛑 Press the stop button if you want to stop midway.")
    return "\n".join(lines)

# ========== FORCE JOIN FUNCTIONS ==========
async def check_membership(bot: Bot, uid: int, channel_id: str) -> bool:
    """Check membership for @username, t.me links, or numeric channel IDs."""
    value = str(channel_id).strip()
    if "t.me/" in value:
        value = value.split("t.me/", 1)[1].split("/", 1)[0].split("?", 1)[0]
        if not value.startswith("@"):
            value = "@" + value
    attempts = [value]
    if value.startswith("@"):
        attempts.append(value[1:])
    elif value.lstrip("-").isdigit():
        attempts.append(int(value))
    for chat in attempts:
        try:
            member = await bot.get_chat_member(chat, uid)
            if member.status in ("member", "administrator", "creator"):
                return True
        except Exception:
            continue
    return False

async def user_joined_all(bot: Bot, uid: int, d: dict) -> tuple[bool, list]:
    fj = d.get("force_join", {})
    if not fj.get("enabled", False):
        return True, []
    channels = fj.get("channels", [])
    missing = []
    for ch in channels:
        if ch.get("required", True):
            if not await check_membership(bot, uid, ch["id"]):
                missing.append(ch)
    return len(missing) == 0, missing

def force_join_text(missing: list) -> str:
    lines = [
        "🔒 <b>Join First To Use The Bot!</b>\n\n",
        "👇 Join the channels/groups below:\n"
    ]
    for ch in missing:
        lines.append(f"• <a href='{ch['link']}'>{ch.get('title', 'Channel')}</a>")
    lines.append("\n\nAfter joining, press /start or hit Refresh.")
    return "\n".join(lines)

def force_join_kb(missing: list) -> InlineKeyboardMarkup:
    rows = []
    row = []
    count = 0

    for ch in missing:
        btn = url_btn(
            text="🔗 Join Channel",
            url=ch["link"]
        )
        row.append(btn)
        count += 1

        if count == 2:
            rows.append(row)
            row = []
            count = 0

    if row:
        rows.append(row)

    rows.append([
        premium_btn(
            text="Joined! Check Now",
            callback="fj:check",
            emoji_key="check",
            style="success"
        )
    ])

    return make_kb(rows)

# ========== KEYBOARD BUILDERS ==========

def owner_kb(d: dict) -> InlineKeyboardMarkup:
    mode_text = "Disable Free Mode" if d.get("free_mode") else "Enable Free Mode"
    mode_cb = "owner:free:off" if d.get("free_mode") else "owner:free:on"

    transfer_enabled = d.get("settings", {}).get("transfer_enabled", True)
    transfer_text = "Disable Transfer" if transfer_enabled else "Enable Transfer"
    transfer_cb = "owner:toggle_transfer:off" if transfer_enabled else "owner:toggle_transfer:on"

    multiplier = d.get("settings", {}).get("multiplier", 3)
    daily_limit = d.get("settings", {}).get("daily_limit", 0)

    rows = [
        [
            premium_btn("Send SMS", "owner:send", "send", "danger"),
            premium_btn("Firebase DBs", "owner:fb:menu", "manage", "primary")
        ],
        [
            premium_btn("Super Admins", "owner:owners:menu", "crown", "primary"),
            premium_btn("Admins", "owner:admins:menu", "shield", "primary")
        ],
        [
            premium_btn("View Users", "owner:users:list", "users", "primary"),
            premium_btn("API Stats", "owner:stats", "stats", "primary")
        ],
        [
            premium_btn("Ban User", "owner:ban", "block", "danger"),
            premium_btn("Unban User", "owner:unban:menu", "check", "success")
        ],
        [
            premium_btn("Broadcast", "owner:broadcast", "broadcast", "success"),
            premium_btn("Activity Log", "owner:activity", "list", "primary")
        ],
        [
            premium_btn("Pricing Plans", "owner:pricing:menu", "plan", "primary"),
            premium_btn("Redeem Codes", "owner:redeem:menu", "redeem", "success")
        ],
        [
            premium_btn("Add Credits", "owner:credits:add", "add", "success"),
            premium_btn("Deduct Credits", "owner:credits:deduct", "remove", "danger")
        ],
        [
            premium_btn("Force Join", "owner:fj:menu", "join", "primary"),
            premium_btn("Settings", "owner:settings", "settings", "primary")
        ],
        [
            premium_btn("SMS History", "owner:sms_history", "history", "primary"),
            premium_btn("Export Script", "owner:export_script", "export", "success")
        ],
        [
            premium_btn("Protect Number", "owner:protect", "protect", "primary"),
            premium_btn("Protected List", "owner:protected_list", "shield", "primary")
        ],
        [
            premium_btn("Track Number", "owner:track", "track", "primary"),
            premium_btn("Add Credits All", "owner:add_all_credits", "users", "success")
        ],
        [
            premium_btn("Deduct All", "owner:deduct_all_credits", "users", "danger"),
            premium_btn(f"Multiplier ({multiplier}x)", "owner:set_multiplier", "bolt", "primary")
        ],
        [
            premium_btn(f"Transfer: {'ON' if transfer_enabled else 'OFF'}", transfer_cb, "money", "primary"),
            premium_btn(mode_text, mode_cb, "sparkle", "primary")
        ],
        [
            premium_btn(f"Daily Limit: {'∞' if daily_limit <= 0 else daily_limit}", "owner:daily_limit", "users", "primary")
        ],
        [
            premium_btn("Refresh", "owner:refresh", "refresh", "primary")
        ],
    ]
    return make_kb(rows)

def admin_kb(d: dict) -> InlineKeyboardMarkup:
    rows = [
        [
            premium_btn("Send SMS", "admin:send", "send", "danger")
        ],
        [
            premium_btn("View Users", "admin:users:list", "users", "primary"),
            premium_btn("API Stats", "admin:stats", "stats", "primary")
        ],
        [
            premium_btn("Ban User", "admin:ban", "block", "danger"),
            premium_btn("Unban User", "admin:unban:menu", "check", "success")
        ],
        [
            premium_btn("Protect Number", "admin:protect", "protect", "primary"),
            premium_btn("Protected List", "admin:protected_list", "shield", "primary")
        ],
        [
            premium_btn("Broadcast", "admin:broadcast", "broadcast", "success")
        ],
        [
            premium_btn("Refresh", "admin:refresh", "refresh", "primary")
        ],
    ]
    return make_kb(rows)

def fb_menu_kb(d: dict) -> InlineKeyboardMarkup:
    fbs = d.get("firebases", [])
    rows = [
        [premium_btn("Add Firebase", "owner:fb:add", "add", "success")],
        [premium_btn("Add Multiple (Batch)", "owner:fb:batch_add", "import", "primary")]
    ]
    for fb in fbs:
        label = fb.get("label", fb["url"][:28])
        rows.append([
            normal_btn(f"🔥 {label[:26]}", "noop"),
            premium_btn("Remove", f"owner:fb:del:{fb['id']}", "remove", "danger")
        ])
    rows.append([premium_btn("Back", "owner:home", "back", "secondary")])
    return make_kb(rows)

def owners_menu_kb(d: dict) -> InlineKeyboardMarkup:
    owners = d.get("owners", [])
    rows = []
    if len(owners) < 6:
        rows.append([premium_btn("Add Super Admin", "owner:owners:add", "add", "success")])
    for oid in owners:
        if oid == MAIN_OWNER:
            rows.append([normal_btn(f"👑 {oid} (Main Owner)", "noop")])
        else:
            rows.append([
                normal_btn(f"👑 {oid}", "noop"),
                premium_btn("Remove", f"owner:owners:del:{oid}", "remove", "danger")
            ])
    rows.append([premium_btn("Back", "owner:home", "back", "secondary")])
    return make_kb(rows)

def admins_menu_kb(d: dict) -> InlineKeyboardMarkup:
    admins = d.get("admins", [])
    rows = [[premium_btn("Add Admin", "owner:admins:add", "add", "success")]]
    for aid in admins:
        rows.append([
            normal_btn(f"🛡️ {aid}", "noop"),
            premium_btn("Remove", f"owner:admins:del:{aid}", "remove", "danger")
        ])
    rows.append([premium_btn("Back", "owner:home", "back", "secondary")])
    return make_kb(rows)

def unban_menu_kb(d: dict, prefix: str) -> InlineKeyboardMarkup:
    banned = d.get("banned", [])
    rows = []
    for bid in banned:
        rows.append([premium_btn(f"✅ Unban {bid}", f"{prefix}:unban:do:{bid}", "check", "success")])
    rows.append([premium_btn("Back", f"{prefix}:home", "back", "secondary")])
    return make_kb(rows)

def users_list_kb(d: dict, prefix: str, page: int = 0) -> tuple:
    users = d.get("users", {})
    items = list(users.items())
    per = 10
    start = page * per
    chunk = items[start:start + per]
    approved = d.get("approved", [])
    banned = d.get("banned", [])

    lines = [f"👥 <b>Users ({len(items)} total)</b>\n"]
    for uid_str, udata in chunk:
        uid = int(uid_str)
        name = udata.get("name", "Unknown")
        uses = udata.get("uses", 0)
        credits = udata.get("credits", 0)
        if uid in banned: status = "🚫"
        elif uid in approved: status = "✅"
        elif is_owner(uid, d): status = "👑"
        elif uid in d["admins"]: status = "🛡️"
        else: status = "👤"
        lines.append(f"{status} <code>{uid}</code> - {name[:18]} | 💰{credits} | 📨{uses}")

    text = "\n".join(lines)
    rows = []
    nav = []
    if page > 0: nav.append(premium_btn("◀ Prev", f"{prefix}:users:pg:{page-1}", "back", "primary"))
    if start + per < len(items): nav.append(premium_btn("Next ▶", f"{prefix}:users:pg:{page+1}", "forward", "primary"))
    if nav: rows.append(nav)
    rows.append([premium_btn("Back", f"{prefix}:home", "back", "secondary")])
    return text, make_kb(rows)

def speed_kb(prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [
            premium_btn("🚀 FAST", f"{prefix}:speed:fast", "fast", "danger"),
            premium_btn("⚡ MEDIUM", f"{prefix}:speed:medium", "bolt", "success"),
            premium_btn("🐢 SLOW", f"{prefix}:speed:slow", "slow", "primary")
        ],
        [premium_btn("Cancel", f"{prefix}:home", "cross", "danger")]
    ]
    return make_kb(rows)

def stop_send_kb() -> InlineKeyboardMarkup:
    return make_kb([
        [premium_btn("🛑 STOP SENDING", "user:stop_send", "stop", "danger")]
    ])


def user_reply_kb():
    """Rich reply keyboard for regular users."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📨 Send SMS"), KeyboardButton(text="💰 Credits")],
            [KeyboardButton(text="🎟️ Redeem Code"), KeyboardButton(text="🤝 Referral")],
            [KeyboardButton(text="📊 Stats"), KeyboardButton(text="💳 Buy Credits")],
            [KeyboardButton(text="🆔 My Chat ID")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Tap a button..."
    )

def user_kb() -> InlineKeyboardMarkup:
    rows = [
        [premium_btn("Send SMS", "user:send", "send", "danger")],
        [
            premium_btn("Credits", "user:credits", "money", "primary"),
            premium_btn("Redeem", "user:redeem", "redeem", "success")
        ],
        [
            premium_btn("Refer", "user:refer", "refer", "primary"),
            premium_btn("Stats", "user:stats", "stats", "primary")
        ],
        [premium_btn("My History", "user:sms_history", "history", "danger")],
        [premium_btn("Templates", "user:templates", "list", "primary")],
        [premium_btn("Buy Credits", "user:pricing", "plan", "success")],
        [premium_btn("Transfer Credits", "user:transfer", "money", "success")],
        [premium_btn("Info", "user:info", "info", "primary")],
    ]
    return make_kb(rows)

# ========== PANEL TEXTS ==========
def owner_panel_text(d: dict) -> str:
    fbs = d.get("firebases", [])
    owners = d.get("owners", [])
    admins = d.get("admins", [])
    users = d.get("users", {})
    stats = d.get("stats", {})
    mode = "FREE" if d.get("free_mode") else "Approval Required"
    fj = d.get("force_join", {})
    fj_status = "ON" if fj.get("enabled") else "OFF"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    scan_info = get_scan_status()

    transfer_enabled = d.get("settings", {}).get("transfer_enabled", True)
    transfer_status = "ON" if transfer_enabled else "OFF"
    multiplier = d.get("settings", {}).get("multiplier", 3)
    daily_limit = d.get("settings", {}).get("daily_limit", 0)

    protected_count = len(PROTECTED_NUMBERS)

    return (
        f"👑 <b>DENJI BLAST - OWNER PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 Firebase DBs   : <b>{len(fbs)}</b>\n"
        f"👑 Super Admins   : <b>{len(owners)}/6</b>\n"
        f"🛡️ Admins         : <b>{len(admins)}</b>\n"
        f"👥 Total Users    : <b>{len(users)}</b>\n"
        f"📨 Total Sent     : <b>{stats.get('total_sent', 0)}</b>\n"
        f"❌ Total Failed   : <b>{stats.get('total_failed', 0)}</b>\n"
        f"⚡ Active Sends   : <b>{active_sessions}</b>\n"
        f"🔐 Access Mode    : <b>{mode}</b>\n"
        f"📢 Force Join     : <b>{fj_status}</b>\n"
        f"💸 Transfer       : <b>{transfer_status}</b>\n"
        f"✖️ Multiplier     : <b>{multiplier}x</b>\n"
        f"📊 Daily Limit    : <b>{'∞' if daily_limit <= 0 else daily_limit}</b>\n"
        f"🔒 Protected      : <b>{protected_count}</b>\n"
        f"📱 Devices        : <b>{scan_info}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )

def admin_panel_text(d: dict) -> str:
    users = d.get("users", {})
    stats = d.get("stats", {})
    banned = d.get("banned", [])
    mode = "FREE" if d.get("free_mode") else "Approval Required"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    scan_info = get_scan_status()
    protected_count = len(PROTECTED_NUMBERS)

    return (
        f"🛡️ <b>DENJI BLAST - ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users    : <b>{len(users)}</b>\n"
        f"🚫 Banned         : <b>{len(banned)}</b>\n"
        f"📨 Total Sent     : <b>{stats.get('total_sent', 0)}</b>\n"
        f"❌ Total Failed   : <b>{stats.get('total_failed', 0)}</b>\n"
        f"⚡ Active Sends   : <b>{active_sessions}</b>\n"
        f"🔥 Firebase DBs   : <b>{len(d.get('firebases', []))}</b>\n"
        f"🔒 Protected      : <b>{protected_count}</b>\n"
        f"🔐 Access Mode    : <b>{mode}</b>\n"
        f"📱 Devices        : <b>{scan_info}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )

def user_home_text(uid: int, d: dict) -> str:
    udata = d["users"].get(str(uid), {})
    fbs = d.get("firebases", [])
    credits = udata.get("credits", 0)
    scan_info = get_scan_status()
    extra = ""
    daily_left = get_daily_remaining(uid, d)
    if daily_left is not None:
        extra += f"📊 Today Left : <b>{daily_left}</b>\n"
    tpl_count = len(udata.get("templates", []))
    if tpl_count:
        extra += f"📋 Templates : <b>{tpl_count}</b>\n"
    return (
        f"⚡ <b>DENJI BLAST {_VERSION}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Role    : <b>{role_tag(uid, d)}</b>\n"
        f"💰 Credits : <b>{credits}</b>\n"
        f"📨 Uses    : <b>{udata.get('uses', 0)}</b>\n"
        f"🔥 APIs    : <b>{len(fbs)} firebase(s)</b>\n"
        f"📱 Devices : <b>{scan_info}</b>\n"
        f"{extra}"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Tap <b>Send SMS</b> to start"
    )

def role_tag(uid: int, d: dict) -> str:
    if is_main_owner(uid): return "👑 Master Owner"
    if is_owner(uid, d): return "👑 Owner"
    if uid in d.get("admins", []): return "🛡️ Admin"
    if uid in d.get("approved", []): return "✅ Approved"
    if d.get("free_mode"): return "👤 Free User"
    return "🚫 No Access"

def api_stats_text(d: dict) -> str:
    stats = d.get("stats", {})
    api_use = stats.get("api_usage", {})
    fbs = {fb["id"]: fb for fb in d.get("firebases", [])}

    lines = [
        f"📊 <b>API Stats</b>\n",
        f"📨 Total Sent   : <b>{stats.get('total_sent', 0)}</b>",
        f"❌ Total Failed : <b>{stats.get('total_failed', 0)}</b>\n",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "<b>Per Firebase:</b>"
    ]
    if not api_use:
        lines.append("  No usage yet.")
    for fb_id, fb_stats in api_use.items():
        fb = fbs.get(fb_id)
        label = fb.get("label", fb_id[:20]) if fb else fb_id[:20]
        label = label.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
        sent = fb_stats.get("sent", 0)
        failed = fb_stats.get("failed", 0)
        lines.append(f"🔥 {label}\n   ✅ {sent} sent | ❌ {failed} failed")
    return "\n".join(lines)

def trend_stats_text(d: dict) -> str:
    """Top users + last-7-days send counts for the owner/admin stats panel."""
    users = d.get("users", {})
    lines = ["\n━━━━━━━━━━━━━━━━━━━━━━", "🏆 <b>Top Users</b>"]
    top = sorted(users.items(), key=lambda kv: kv[1].get("uses", 0), reverse=True)[:5]
    if not top or top[0][1].get("uses", 0) == 0:
        lines.append("  No sends yet.")
    else:
        for uid_str, udata in top:
            name = (udata.get("name") or "?")[:15].replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f"  <code>{uid_str}</code> - {name} - 📨 {udata.get('uses', 0)}")
    today = datetime.now().date()
    day_counts = {}
    for hist in d.get("sms_history", {}).values():
        for entry in hist:
            if entry.get("status") != "sent":
                continue
            ts = entry.get("timestamp", 0)
            if ts:
                d_ = datetime.fromtimestamp(ts).date()
                day_counts[d_] = day_counts.get(d_, 0) + 1
    lines.append("\n📅 <b>Daily Sends (7 days)</b>")
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = day_counts.get(day, 0)
        lines.append(f"  {day.strftime('%d/%m')}: <b>{count}</b>")
    return "\n".join(lines)

# ========== BACKGROUND SCANNER ==========
async def background_firebase_scanner(bot: Bot):
    global CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS, SCAN_STATUS
    log.info("Background Firebase Scanner STARTED - scans every 1 minute")

    while True:
        async with SCAN_LOCK:
            if SCANNING_IN_PROGRESS:
                await asyncio.sleep(5)
                continue
            SCANNING_IN_PROGRESS = True

        SCAN_STATUS = "Scanning Firebase APIs..."
        start_scan = time.time()

        try:
            d = load()
            fbs = d.get("firebases", [])

            if not fbs:
                SCAN_STATUS = "No Firebase DBs configured"
                CACHED_DEVICES = []
                async with SCAN_LOCK:
                    SCANNING_IN_PROGRESS = False
                await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)
                continue

            devices = await get_all_online_devices(d)
            scan_duration = time.time() - start_scan

            CACHED_DEVICES = devices

            for fb in fbs:
                fb_id = fb["id"]
                fb_label = fb.get("label", fb["url"][:30])
                fb_online = sum(1 for dv in devices if dv["fb_id"] == fb_id)
                FB_DEVICE_COUNTS[fb_id] = {
                    "label": fb_label,
                    "online": fb_online,
                    "last_update": int(time.time())
                }
            LAST_SCAN_TIME = time.time()

            if devices:
                SCAN_STATUS = f"{len(devices)} devices"
                log.info(f"[BG-SCAN] {len(devices)} devices online | {len(fbs)} DBs | {scan_duration:.1f}s")

                current_fb_ids = {fb["id"] for fb in fbs}
                stale_fb_ids = [k for k in FB_DEVICE_COUNTS if k not in current_fb_ids]
                for stale in stale_fb_ids:
                    FB_DEVICE_COUNTS.pop(stale, None)
            else:
                SCAN_STATUS = "No devices online"
                log.warning(f"[BG-SCAN] No devices found | {len(fbs)} DBs scanned")

        except Exception as e:
            SCAN_STATUS = f"Error: {str(e)[:30]}"
            log.error(f"[BG-SCAN] Error: {e}")
        finally:
            async with SCAN_LOCK:
                SCANNING_IN_PROGRESS = False

        await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)

def get_cached_devices() -> list:
    return CACHED_DEVICES

async def fb_get(base_url: str, path: str) -> dict:
    url = base_url.rstrip("/") + path
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    txt = (await r.text()).strip()
                    if txt == "null" or not txt:
                        return {}
                    return json.loads(txt)
    except Exception as e:
        log.warning(f"fb_get {url}: {e}")
    return {}

async def fb_put(base_url: str, path: str, payload: dict) -> bool:
    """Write to Firebase and only report success for a valid Firebase response."""
    url = base_url.rstrip("/") + path
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.put(url, json=payload, timeout=aiohttp.ClientTimeout(total=6)) as r:
                    body = await r.text()
                    if 200 <= r.status < 300:
                        try:
                            response = json.loads(body) if body else None
                        except json.JSONDecodeError:
                            response = body
                        # Firebase REST writes return JSON; reject explicit errors/null failures.
                        if isinstance(response, dict) and response.get("error"):
                            log.error("Firebase rejected SMS write (%s): %s", r.status, body[:500])
                            continue
                        log.info("Firebase SMS request accepted: %s", url)
                        return True
                    log.error("Firebase SMS write failed (%s): %s", r.status, body[:500])
        except Exception as e:
            log.warning(f"fb_put attempt {attempt+1} failed for {url}: {e}")
        await asyncio.sleep(0.5 * (attempt + 1))
    return False

def device_is_online(device_data: dict) -> bool:
    return any([
        device_data.get("isOnline"),
        device_data.get("online"),
        device_data.get("connected"),
        device_data.get("status") in ("online", "active", True, 1)
    ])

async def get_all_online_devices(d: dict) -> list:
    fbs = d.get("firebases", [])
    if not fbs:
        return []
    results = []
    current_fb_ids = {fb["id"] for fb in fbs}
    global CACHED_DEVICES
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") in current_fb_ids]

    _dev_sem = asyncio.Semaphore(20)

    async def fetch_one(fb: dict):
        shallow_url = fb["url"].rstrip("/") + "/clients.json?shallow=true"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(shallow_url, timeout=aiohttp.ClientTimeout(total=6)) as r:
                    if r.status != 200:
                        return
                    txt = (await r.text()).strip()
                    if txt == "null" or not txt:
                        return
                    device_ids = json.loads(txt)
                    if not isinstance(device_ids, dict):
                        return

                    async def fetch_dev(dev_id: str):
                        try:
                            url = fb["url"].rstrip("/") + f"/clients/{dev_id}.json"
                            async with _dev_sem:
                                async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r2:
                                    if r2.status == 200:
                                        txt2 = (await r2.text()).strip()
                                        if txt2 == "null" or not txt2:
                                            return None
                                        dev_data = json.loads(txt2)
                                        if isinstance(dev_data, dict) and device_is_online(dev_data):
                                            name = dev_data.get("deviceName") or dev_data.get("name") or dev_id[:16]
                                            sims = dev_data.get("sims", [])
                                            return {
                                                "fb_id": fb["id"],
                                                "fb_url": fb["url"],
                                                "fb_label": fb.get("label", fb["url"][:30]),
                                                "dev_id": dev_id,
                                                "dev_name": name,
                                                "sims": sims,
                                            }
                        except Exception as e:
                            log.warning(f"Device fetch {dev_id}: {e}")
                        return None

                    dev_ids = list(device_ids.keys())
                    for i in range(0, len(dev_ids), 20):
                        batch = dev_ids[i:i+20]
                        dev_tasks = [fetch_dev(dev_id) for dev_id in batch]
                        dev_results = await asyncio.gather(*dev_tasks)
                        for res in dev_results:
                            if res:
                                results.append(res)
        except Exception as e:
            log.warning(f"fb_shallow_get {fb['url']}: {e}")

    await asyncio.gather(*(fetch_one(fb) for fb in fbs))
    return results

async def send_sms_via_device(fb_url: str, dev_id: str, sim_slot: int, to: str, message: str) -> bool:
    """Queue exactly one SMS request in the device webhook queue."""
    return await fb_put(
        fb_url,
        f"/clients/{dev_id}/webhookEvent/sendSms.json",
        {
            "from": int(sim_slot),
            "to": to.strip(),
            "message": message.strip(),
            "isSended": False,
            "timestamp": int(time.time() * 1000)
        }
    )

# ========== MAIN SENDING FUNCTION ==========
async def run_sms_blast_with_progress(bot: Bot, msg: Message, uid: int, number: str, message: str, count: int, devices: list, speed: float = SPEED_DEFAULT):
    d = load()
    multiplier = d.get("settings", {}).get("multiplier", 3)
    actual_total = count  # no multiplier, exact count

    try:
        user_name = d.get("users", {}).get(str(uid), {}).get("name", "Unknown")
        await bot.send_message(
            MAIN_OWNER,
            f"⚡ <b>SMS Blast Started!</b>\n\n"
            f"👤 User: {user_name}\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"🎯 Target: <code>{number}</code>\n"
            f"📊 User Count: {count}\n"
            f"✖️ Multiplier: {multiplier}x\n"
            f"📨 Actual SMS: {actual_total}\n"
            f"🕐 Time: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            parse_mode="HTML",
            message_effect_id=EFFECT_PARTY
        )
    except Exception as e:
        log.warning(f"SMS start notification failed: {e}")

    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            old_session = USER_SESSIONS[uid]
            if old_session.task and not old_session.task.done():
                await msg.answer("⚡ A sending is already running!", parse_mode="HTML")
                return
            del USER_SESSIONS[uid]
        session = UserSession(uid)
        session.number = number
        USER_SESSIONS[uid] = session

    is_regular_user = not is_admin(uid, load()) and not is_owner(uid, load())
    current_credits = get_user_credits(uid, load()) if is_regular_user else None
    speed_label_display = "FAST" if speed == SPEED_FAST else "MEDIUM" if speed == SPEED_MEDIUM else "SLOW"

    try:
        progress_msg = await msg.answer(
            progress_text(0, 0, count, current_credits, speed_label_display),
            reply_markup=stop_send_kb(),
            parse_mode="HTML"
        )
    except Exception as e:
        log.error(f"Failed to send progress message: {e}")
        async with SESSIONS_LOCK:
            if uid in USER_SESSIONS:
                del USER_SESSIONS[uid]
        return

    sent_ok = 0
    sent_fail = 0
    msgs_left = actual_total
    api_usage_delta = {}
    last_update_time = time.time()
    start_time = time.time()

    async def do_send():
        nonlocal sent_ok, sent_fail, msgs_left, last_update_time
        try:
            if not devices:
                return
            # Cycle through every device/SIM repeatedly until the exact requested
            # count is attempted. A device is not limited to one pass.
            routes = []
            for device in devices:
                sims = device.get("sims") or [{"simSlotIndex": 0}]
                for sim_data in sims:
                    routes.append((device, int(sim_data.get("simSlotIndex", 0))))
            if not routes:
                routes = [(device, 0) for device in devices]
            route_index = 0
            while msgs_left > 0:
                async with session.lock:
                    if session.cancelled:
                        break
                device, sim = routes[route_index % len(routes)]
                route_index += 1
                fb_id = device["fb_id"]
                fb_url = device["fb_url"]
                dev_id = device["dev_id"]
                ok = await send_sms_via_device(fb_url, dev_id, sim, number, message)
                async with session.lock:
                    if ok:
                        sent_ok += 1
                        msgs_left -= 1
                        if is_regular_user and sent_ok <= count:
                            d_temp = load()
                            deduct_credits(uid, 1, d_temp)
                            add_daily_used(uid, 1, d_temp)
                            d_temp["stats"]["total_sent"] = d_temp["stats"].get("total_sent", 0) + 1
                            k = str(uid)
                            if k in d_temp["users"]:
                                d_temp["users"][k]["uses"] = d_temp["users"][k].get("uses", 0) + 1
                            d_temp.setdefault("sms_history", {}).setdefault(str(uid), []).append({
                                "number": number, "message": message[:100],
                                "timestamp": int(time.time()), "status": "sent"
                            })
                            save(d_temp)
                    else:
                        sent_fail += 1
                        msgs_left -= 1
                    if fb_id not in api_usage_delta:
                        api_usage_delta[fb_id] = {"sent": 0, "failed": 0}
                    api_usage_delta[fb_id]["sent" if ok else "failed"] += 1
                    now = time.time()
                    progress_sent = min(sent_ok, count)
                    if (now - last_update_time >= _PROGRESS_UPDATE_INTERVAL or msgs_left <= 0 or session.cancelled):
                        current_credits_live = get_user_credits(uid, load()) if is_regular_user else None
                        try:
                            await progress_msg.edit_text(
                                progress_text(progress_sent, min(sent_fail, count - progress_sent), count, current_credits_live, speed_label_display),
                                reply_markup=stop_send_kb() if not session.cancelled else None,
                                parse_mode="HTML"
                            )
                        except TelegramBadRequest:
                            pass
                        last_update_time = now
                await asyncio.sleep(speed)
        except Exception as e:
            log.error(f"Error in send loop: {e}")
        finally:
            async with session.lock:
                session.sent = sent_ok
                session.failed = sent_fail

    task = asyncio.create_task(do_send())
    session.task = task
    await task
    was_cancelled = session.cancelled

    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            del USER_SESSIONS[uid]

    if not is_regular_user:
        d_final = load()
        d_final["stats"]["total_sent"] = d_final["stats"].get("total_sent", 0) + sent_ok
        d_final["stats"]["total_failed"] = d_final["stats"].get("total_failed", 0) + sent_fail
        for fb_id, delta in api_usage_delta.items():
            d_final["stats"].setdefault("api_usage", {}).setdefault(fb_id, {"sent": 0, "failed": 0})
            d_final["stats"]["api_usage"][fb_id]["sent"] += delta["sent"]
            d_final["stats"]["api_usage"][fb_id]["failed"] += delta["failed"]
        k = str(uid)
        if k in d_final["users"]:
            d_final["users"][k]["uses"] = d_final["users"][k].get("uses", 0) + sent_ok
        d_final.setdefault("sms_history", {}).setdefault(str(uid), []).append({
            "number": number,
            "message": message[:100],
            "timestamp": int(time.time()),
            "status": "completed" if not was_cancelled else "stopped"
        })
        save(d_final)
    else:
        d_final = load()
        d_final["stats"]["total_failed"] = d_final["stats"].get("total_failed", 0) + sent_fail
        for fb_id, delta in api_usage_delta.items():
            d_final["stats"].setdefault("api_usage", {}).setdefault(fb_id, {"sent": 0, "failed": 0})
            d_final["stats"]["api_usage"][fb_id]["failed"] += delta["failed"]
        save(d_final)

    d_log = load()
    duration = int(time.time() - start_time)
    log_activity(d_log, "sms_blast", uid, f"Sent: {sent_ok}, Failed: {sent_fail}")
    save(d_log)

    if sent_ok >= actual_total:
        display_sent = count
    else:
        display_sent = sent_ok
        display_sent = min(display_sent, count)

    icon = "✅" if sent_fail == 0 and sent_ok > 0 else "⚠️" if sent_ok > 0 else "❌"
    credit_text = ""
    if is_regular_user:
        remaining = get_user_credits(uid, load())
        credit_text = f"\n💰 Credits Used: {sent_ok if sent_ok <= count else count}\n💰 Remaining: {remaining}"
    stopped_text = f"\n🛑 User stopped it midway!" if was_cancelled else ""
    duration_text = f"\n⏱️ Duration: {fmt_duration(int(time.time() - start_time))}"

    if is_owner(uid, load()):
        back_btn = [("Owner Panel", "owner:home")]
    elif is_admin(uid, load()):
        back_btn = [("Admin Panel", "admin:home")]
    else:
        back_btn = [("Send Another", "user:send"), ("Home", "user:home")]

    try:
        await progress_msg.edit_text(
            f"{icon} <b>SMS Blast Result</b>{stopped_text}\n\n"
            f"🎯 To: <code>{mask_number(number)}</code>\n"
            f"📨 Message: <code>{message[:50]}{'...' if len(message)>50 else ''}</code>\n"
            f"✅ Sent: <b>{display_sent}</b>\n"
            f"❌ Failed: <b>{sent_fail}</b>\n"
            f"🔥 APIs used: <b>{len(api_usage_delta)}</b>"
            f"{duration_text}{credit_text}",
            reply_markup=make_kb([[InlineKeyboardButton(text=t, callback_data=c) for t, c in back_btn]]),
            parse_mode="HTML"
        )
    except Exception as e:
        log.error(f"Failed to edit final progress message: {e}")

# ========== BOT COMMANDS & HANDLERS ==========
R = Router()

# ========== BOT COMMANDS MENU ==========
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 Start the bot"),
        BotCommand(command="help", description="❓ Help & info"),
        BotCommand(command="commands", description="📋 All commands"),
        BotCommand(command="source", description="📦 Get bot source (Owner only)"),
        BotCommand(command="broadcast", description="📢 Broadcast message (Admin)"),
        BotCommand(command="panel", description="👑 Owner panel (Owner only)"),
    ]
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        log.info("Bot commands menu set")
    except Exception as e:
        log.warning(f"Failed to set commands: {e}")

# ========== HELP / COMMANDS ==========
@R.message(Command("help"))
async def cmd_help(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    d = load()
    if is_main_owner(uid):
        text = (
            f"👑 <b>DENJI BLAST {_VERSION} - HELP</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Master Owner Commands:</b>\n"
            f"  /start - Bot panel\n"
            f"  /source - Get bot source file\n"
            f"  /broadcast - Broadcast message\n"
            f"  /panel - Owner panel\n"
            f"  /help - This help\n"
            f"  /commands - All commands\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ You have <b>FULL OWNER ACCESS</b>"
        )
    elif is_owner(uid, d):
        text = (
            f"👑 <b>DENJI BLAST {_VERSION} - HELP</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Owner Commands:</b>\n"
            f"  /start - Bot panel\n"
            f"  /broadcast - Broadcast message\n"
            f"  /panel - Owner panel\n"
            f"  /help - This help\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️ /source is <b>MASTER OWNER ONLY</b>"
        )
    elif is_admin(uid, d):
        text = (
            f"🛡️ <b>DENJI BLAST {_VERSION} - HELP</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Admin Commands:</b>\n"
            f"  /start - Bot panel\n"
            f"  /broadcast - Broadcast message\n"
            f"  /help - This help\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️ /source is <b>MASTER OWNER ONLY</b>"
        )
    else:
        text = (
            f"⚡ <b>DENJI BLAST {_VERSION} - HELP</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>User Commands:</b>\n"
            f"  /start - Bot panel\n"
            f"  /help - This help\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Use the buttons in the main menu to send SMS."
        )
    await msg.answer(text, parse_mode="HTML")

@R.message(Command("commands"))
async def cmd_commands(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    d = load()
    if is_main_owner(uid):
        text = (
            f"📋 <b>ALL COMMANDS - MASTER OWNER</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>General:</b>\n"
            f"  /start - Start bot\n"
            f"  /help - Help menu\n"
            f"  /commands - This list\n"
            f"  /source - 📦 Get bot source (ONLY YOU)\n"
            f"  /panel - 👑 Open owner panel\n"
            f"  /broadcast - 📢 Broadcast to users\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>You are the MASTER OWNER</b> - full access"
        )
    elif is_owner(uid, d):
        text = (
            f"📋 <b>ALL COMMANDS - OWNER</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  /start - Start bot\n"
            f"  /help - Help menu\n"
            f"  /panel - Open owner panel\n"
            f"  /broadcast - Broadcast to users\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️ /source is <b>MASTER OWNER ONLY</b>"
        )
    elif is_admin(uid, d):
        text = (
            f"📋 <b>ALL COMMANDS - ADMIN</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  /start - Start bot\n"
            f"  /help - Help menu\n"
            f"  /broadcast - Broadcast to users\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️ /source is <b>MASTER OWNER ONLY</b>"
        )
    else:
        text = (
            f"📋 <b>ALL COMMANDS - USER</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  /start - Start bot\n"
            f"  /help - Help menu\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Use /start to open the main menu."
        )
    await msg.answer(text, parse_mode="HTML")

# ========== SOURCE COMMAND (MASTER OWNER ONLY) ==========
@R.message(Command("source"))
async def cmd_source(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    if uid != MAIN_OWNER:
        await msg.answer(
            f"🚫 <b>Access Denied!</b>\n\n"
            f"This command is only for <b>MASTER OWNER</b>.\n"
            f"Contact: {SUPER_ADMIN_NAME}",
            parse_mode="HTML"
        )
        return
    try:
        script_path = os.path.abspath(__file__)
        if not os.path.exists(script_path):
            await msg.answer("❌ Source file not found!", parse_mode="HTML")
            return
        await msg.answer("📦 <b>Here is your bot source!</b>\n\nSending file...", parse_mode="HTML")
        await msg.answer_document(document=FSInputFile(script_path), caption=f"⚡ <b>DENJI BLAST {_VERSION} - SOURCE</b>\n\n🔒 Only for Master Owner", parse_mode="HTML")
        log_activity(load(), "source_export", uid, "Master owner downloaded source")
    except Exception as e:
        await msg.answer(f"❌ Export failed: {str(e)[:50]}", parse_mode="HTML")

# ========== PANEL COMMAND ==========
@R.message(Command("panel"))
async def cmd_panel(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    d = load()
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    elif not can_use(uid, d):
        await msg.answer(f"🚫 No access!\nContact: {SUPER_ADMIN_NAME}", parse_mode="HTML")
    else:
        await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")
        try:
            await msg.answer("Use the buttons below:", reply_markup=user_reply_kb())
        except:
            pass

# ========== MULTIPLIER SET ==========
@R.callback_query(F.data == "owner:set_multiplier")
async def owner_set_multiplier(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d):
        await cq.answer("Owner only!", show_alert=True)
        return
    current_multiplier = d.get("settings", {}).get("multiplier", 3)
    await state.set_state(S.set_multiplier)
    await cq.message.edit_text(
        f"⚡ <b>Set Multiplier</b>\n\nCurrent: <b>{current_multiplier}x</b>\n\nSend the new multiplier:",
        reply_markup=make_kb([[premium_btn("Cancel", "owner:home", "cross", "danger")]]),
        parse_mode="HTML"
    )

@R.message(S.set_multiplier)
async def owner_set_multiplier_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        multiplier = int(msg.text.strip())
        if multiplier < 1:
            raise ValueError
    except:
        await msg.answer("❓ Send a valid number (at least 1):")
        return
    d.setdefault("settings", {})["multiplier"] = multiplier
    save(d)
    await state.clear()
    await msg.answer(f"✅ Multiplier Updated! New: <b>{multiplier}x</b>", reply_markup=make_kb([[premium_btn("Owner Panel", "owner:home", "home", "primary")]]), parse_mode="HTML")
    log_activity(d, "set_multiplier", uid, f"Set multiplier to {multiplier}")

# ========== TRANSFER TOGGLE ==========
@R.callback_query(F.data.startswith("owner:toggle_transfer:"))
async def owner_toggle_transfer(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d):
        await cq.answer("Owner only!", show_alert=True)
        return
    action = cq.data.split(":")[2]
    enabled = (action == "on")
    d.setdefault("settings", {})["transfer_enabled"] = enabled
    save(d)
    status = "ENABLED" if enabled else "DISABLED"
    await cq.answer(f"Transfer Credits {status}!", show_alert=True)
    await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")

# ========== TRANSFER CREDITS ==========
@R.callback_query(F.data == "user:transfer")
async def user_transfer_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    transfer_enabled = d.get("settings", {}).get("transfer_enabled", True)
    if not transfer_enabled:
        await cq.answer("Transfer disabled!", show_alert=True)
        return
    if is_banned(uid, d) or not can_use(uid, d):
        await cq.answer("Access denied!", show_alert=True)
        return
    current_credits = get_user_credits(uid, d)
    if current_credits < 2:
        await cq.answer("Minimum 2 credits required!", show_alert=True)
        return
    await state.set_state(S.transfer_credits_uid)
    await cq.message.edit_text(
        f"💸 <b>Transfer Credits</b>\n\nYour Credits: <b>{current_credits}</b>\n\nStep 1/2: Send the target User ID:",
        reply_markup=make_kb([[premium_btn("Cancel", "user:home", "cross", "danger")]]),
        parse_mode="HTML"
    )

@R.message(S.transfer_credits_uid)
async def user_transfer_uid(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    try:
        target_uid = int(msg.text.strip())
    except:
        await msg.answer("❓ Send a valid User ID:")
        return
    if target_uid == uid or str(target_uid) not in d.get("users", {}):
        await msg.answer("❌ Invalid user!")
        return
    current_credits = get_user_credits(uid, d)
    await state.update_data(transfer_target=target_uid)
    await state.set_state(S.transfer_credits_amount)
    half = current_credits // 2
    await msg.answer(f"Step 2/2 - Amount\n\nTarget: <code>{target_uid}</code>\nMax Transfer: <b>{half}</b>\n\nHow many credits do you want to transfer?",
        reply_markup=make_kb([[premium_btn("Cancel", "user:home", "cross", "danger")]]),
        parse_mode="HTML"
    )

@R.message(S.transfer_credits_amount)
async def user_transfer_amount(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    try:
        amount = int(msg.text.strip())
        if amount <= 0:
            raise ValueError
    except:
        await msg.answer("❓ Send a valid positive number:")
        return
    fsmd = await state.get_data()
    target_uid = fsmd.get("transfer_target")
    current_credits = get_user_credits(uid, d)
    max_transfer = current_credits // 2
    if amount > max_transfer or not deduct_credits(uid, amount, d):
        await msg.answer(f"❌ Insufficient credits! Max: {max_transfer}")
        return
    add_credits(target_uid, amount, d)
    save(d)
    await state.clear()
    try:
        await msg.bot.send_message(target_uid, f"💸 <b>Credits Received!</b>\n\nFrom: <code>{uid}</code>\nAmount: {amount}\nBalance: {get_user_credits(target_uid, d)}", parse_mode="HTML", message_effect_id=EFFECT_PARTY)
    except:
        pass
    await msg.answer(f"✅ <b>Transfer Successful!</b>\n\nTo: <code>{target_uid}</code>\nAmount: {amount}\nBalance: {get_user_credits(uid, d)}",
        reply_markup=make_kb([[premium_btn("Home", "user:home", "home", "primary")]]),
        parse_mode="HTML"
    )
    log_activity(d, "credit_transfer", uid, f"Transferred {amount} to {target_uid}")

# ========== BATCH FIREBASE ADD ==========
@R.callback_query(F.data == "owner:fb:batch_add")
async def owner_fb_batch_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("Owner only!", show_alert=True)
        return
    await state.set_state(S.add_firebase_batch)
    await cq.message.edit_text(
        "🔥 <b>Batch Add Firebase</b>\n\nFormat:\n<code>Label | https://app.firebaseio.com</code>\n\nExample:\n<code>MyApp | https://myapp.firebaseio.com\nTestApp | https://testapp.firebaseio.com</code>",
        reply_markup=make_kb([[premium_btn("Back", "owner:fb:menu", "back", "secondary")]]),
        parse_mode="HTML"
    )

@R.message(S.add_firebase_batch)
async def owner_fb_batch_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    text = msg.text.strip()
    lines = text.splitlines()
    added = 0
    failed = 0
    errors = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            parts = line.split("|", 1)
            label = parts[0].strip()
            url = parts[1].strip()
        else:
            url = line
            label = url.replace("https://", "").split(".")[0][:20]
        if not url.startswith("http"):
            failed += 1
            errors.append(f"{label}: Invalid URL")
            continue
        url = url.rstrip("/")
        fbs = d.get("firebases", [])
        if any(fb["url"] == url for fb in fbs):
            failed += 1
            errors.append(f"{label}: Already exists")
            continue
        fb_id = str(int(time.time())) + str(random.randint(100, 999))
        fbs.append({"id": fb_id, "url": url, "label": label, "added_at": int(time.time())})
        d["firebases"] = fbs
        added += 1
    save(d)
    await state.clear()
    result_msg = f"✅ <b>Batch Firebase Add Complete!</b>\n\nAdded: <b>{added}</b>\nFailed: <b>{failed}</b>"
    if errors:
        result_msg += "\n\nDetails:\n" + "\n".join(errors[:5])
    await msg.answer(result_msg, reply_markup=make_kb([[premium_btn("Refresh", "owner:fb:menu", "refresh", "primary")]]), parse_mode="HTML")

# ========== START COMMANDS ==========
@R.message(CommandStart(deep_link=True))
async def cmd_start_deep(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    name = msg.from_user.full_name or "User"
    d = load()
    is_new_user = str(uid) not in d.get("users", {})
    reg_user(uid, name, d, msg.from_user.username or "")
    save(d)
    if is_new_user:
        try:
            await msg.bot.send_message(MAIN_OWNER, f"👤 <b>New User!</b>\n\nName: {name}\nID: <code>{uid}</code>", parse_mode="HTML")
        except:
            pass
    args = msg.text.split()
    code = args[1] if len(args) > 1 else ""
    if code.startswith("REF"):
        if not d["users"].get(str(uid), {}).get("referred_by"):
            success, msg_text, referrer = process_referral(uid, code, d)
            if success and referrer:
                try:
                    await msg.bot.send_message(referrer, f"{name} used your referral! You got +{d['settings']['ref_credits']} credits!", parse_mode="HTML")
                except:
                    pass
    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        return
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    elif is_banned(uid, d):
        await msg.answer("🚫 You have been banned.", parse_mode="HTML")
    elif not can_use(uid, d):
        await msg.answer(f"🚫 No access!\nContact: {SUPER_ADMIN_NAME}", parse_mode="HTML")
    else:
        await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")
        try:
            await msg.answer("Use the buttons below:", reply_markup=user_reply_kb())
        except:
            pass

@R.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    name = msg.from_user.full_name or "User"
    d = load()
    is_new_user = str(uid) not in d.get("users", {})
    reg_user(uid, name, d, msg.from_user.username or "")
    save(d)
    if is_new_user:
        try:
            await msg.bot.send_message(MAIN_OWNER, f"👤 <b>New User!</b>\n\nName: {name}\nID: <code>{uid}</code>", parse_mode="HTML")
        except:
            pass
    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        return
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    elif is_banned(uid, d):
        await msg.answer("🚫 You have been banned.", parse_mode="HTML")
    elif not can_use(uid, d):
        await msg.answer(f"🚫 No access!\nContact: {SUPER_ADMIN_NAME}", parse_mode="HTML")
    else:
        await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")
        try:
            await msg.answer("Use the buttons below:", reply_markup=user_reply_kb())
        except:
            pass

# ========== FJ CHECK ==========

# ========== REPLY KEYBOARD HANDLERS ==========
@R.message(F.text == "📨 Send SMS")
async def reply_send_sms(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not can_use(uid, d):
        await msg.answer("Access denied!", parse_mode="HTML")
        return
    await state.set_state(S.send_number)
    await msg.answer(
        "📨 <b>Step 1/4 - Number</b>\n\nEnter the number to send SMS to:",
        reply_markup=make_kb([[premium_btn("Cancel", "user:home", "cross", "danger")]]),
        parse_mode="HTML"
    )

@R.message(F.text == "💰 Credits")
async def reply_credits(msg: Message, state: FSMContext):
    await state.clear()
    d = load()
    uid = msg.from_user.id
    await msg.answer(f"💰 <b>Your Credits</b>: {get_user_credits(uid, d)}", reply_markup=user_kb(), parse_mode="HTML")

@R.message(F.text == "🎟️ Redeem Code")
async def reply_redeem(msg: Message, state: FSMContext):
    await state.set_state(S.redeem_code)
    await msg.answer("🎟️ Send your redeem code:", reply_markup=make_kb([[premium_btn("Cancel", "user:home", "cross", "danger")]]))

@R.message(F.text == "🤝 Referral")
async def reply_referral(msg: Message, state: FSMContext):
    await state.clear()
    d = load()
    uid = msg.from_user.id
    code = generate_user_refer_code(uid, d)
    ref_credits = d.get("settings", {}).get("ref_credits", 3)
    count = sum(1 for u in d.get("users", {}).values() if u.get("referred_by") == uid)
    me = await msg.bot.get_me()
    await msg.answer(
        f"🤝 <b>Referral Program</b>\n\n"
        f"Your Code: <code>{code}</code>\n"
        f"Reward: <b>{ref_credits} credits</b> each\n"
        f"Referred: <b>{count}</b> users\n\n"
        f"Share: <code>https://t.me/{me.username}?start={code}</code>",
        reply_markup=user_kb(),
        parse_mode="HTML"
    )
    save(d)

@R.message(F.text == "📊 Stats")
async def reply_stats(msg: Message, state: FSMContext):
    await state.clear()
    d = load()
    uid = msg.from_user.id
    udata = d.get("users", {}).get(str(uid), {})
    await msg.answer(
        f"📊 <b>Your Stats</b>\n\n"
        f"💰 Credits: <b>{udata.get('credits', 0)}</b>\n"
        f"📨 Total Uses: <b>{udata.get('uses', 0)}</b>\n"
        f"📅 Joined: <b>{fmt_time(udata.get('joined_at', 0)) if udata.get('joined_at') else 'N/A'}</b>",
        reply_markup=user_kb(),
        parse_mode="HTML"
    )

@R.message(F.text == "💳 Buy Credits")
async def reply_buy(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        f"💳 <b>Buy Credits</b>\n\nContact <b>{PREMIUM_CONTACT}</b> to purchase credits.",
        reply_markup=user_kb(),
        parse_mode="HTML"
    )

@R.message(F.text == "🆔 My Chat ID")
async def reply_myid(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    await msg.answer(f"🆔 <b>Your Chat ID</b>\n\n<code>{uid}</code>", parse_mode="HTML")

@R.callback_query(F.data == "fj:check")
async def fj_check(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    d = load()
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        await cq.answer("You still haven't joined!", show_alert=True)
        await cq.message.edit_text(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        return
    await cq.answer("Verified!", show_alert=True)
    if is_owner(uid, d):
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d):
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    else:
        await cq.message.edit_text(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

# ========== USER SEND ==========
@R.callback_query(F.data == "user:send")
async def user_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not can_use(uid, d):
        await cq.answer("Access denied!", show_alert=True)
        return
    await state.set_state(S.send_number)
    await cq.message.edit_text(
        "📨 <b>Step 1/4 - Number</b>\n\nEnter the number to send SMS to:",
        reply_markup=make_kb([[premium_btn("Cancel", "user:home", "cross", "danger")]]),
        parse_mode="HTML"
    )

@R.message(S.send_number)
async def user_got_number(msg: Message, state: FSMContext):
    ok, number, err = normalize_number(msg.text)
    if not ok:
        await msg.answer(err, parse_mode="HTML")
        return
    if number in PROTECTED_NUMBERS:
        await msg.answer("🔒 This number is protected!", parse_mode="HTML")
        return
    await state.update_data(number=number)
    await state.set_state(S.send_message)
    d = load()
    kb_rows = [[premium_btn("Cancel", "user:home", "cross", "danger")]]
    if d.get("users", {}).get(str(msg.from_user.id), {}).get("templates"):
        kb_rows.insert(0, [premium_btn("📋 Use Template", "user:template_pick", "list", "primary")])
    await msg.answer(f"✅ Number: <code>{mask_number(number)}</code>\n\n📨 <b>Step 2/4 - Message</b>\n\nType the message to send (or use a template):",
        reply_markup=make_kb(kb_rows),
        parse_mode="HTML"
    )

@R.message(S.send_message)
async def user_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.send_speed)
    await msg.answer("✅ Message saved!\n\n🚀 <b>Step 3/4 - Speed</b>\n\nSelect the sending speed:",
        reply_markup=speed_kb("user"), parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"user:speed:fast", "user:speed:medium", "user:speed:slow"}))
async def user_speed_selected(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    speed_map = {"user:speed:fast": SPEED_FAST, "user:speed:medium": SPEED_MEDIUM, "user:speed:slow": SPEED_SLOW}
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "FAST" if selected_speed == SPEED_FAST else "MEDIUM" if selected_speed == SPEED_MEDIUM else "SLOW"
    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.send_count)
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    count = len(devices)
    credit_info = ""
    if not is_admin(uid, d) and not is_owner(uid, d):
        user_credits = get_user_credits(uid, d)
        credit_info = f"\n💰 Your Credits: <b>{user_credits}</b>"
        daily_left = get_daily_remaining(uid, d)
        if daily_left is not None:
            credit_info += f"\n📊 Today Left: <b>{daily_left}</b>"
    await cq.message.edit_text(
        f"⚡ <b>{speed_label}</b> selected!\n\n📨 <b>Step 4/4 - Count</b>\n\n🔥 Online APIs: <b>{count}</b>\n📱 Device Capacity: <b>{count * 3}</b>{credit_info}\n\nHow many SMS do you want to send?",
        reply_markup=make_kb([[premium_btn("Cancel", "user:home", "cross", "danger")]]),
        parse_mode="HTML"
    )

@R.message(S.send_count)
async def user_got_count(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    fsmd = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except:
        await msg.answer("❓ Send a number only:")
        return
    await state.clear()
    number = fsmd.get("number", "")
    message_text = fsmd.get("message", "")
    send_speed = fsmd.get("send_speed", SPEED_DEFAULT)
    if not is_admin(uid, d) and not is_owner(uid, d):
        daily_left = get_daily_remaining(uid, d)
        if daily_left is not None:
            if daily_left <= 0:
                await msg.answer("📊 Today's daily limit is over! Try again tomorrow.", reply_markup=make_kb([[premium_btn("Home", "user:home", "home", "primary")]]), parse_mode="HTML")
                return
            if count > daily_left:
                await msg.answer(f"⚠️ You can only send {daily_left} SMS today. Count set to {daily_left}.", parse_mode="HTML")
                count = daily_left
        current_credits = get_user_credits(uid, d)
        if current_credits <= 0:
            await msg.answer("❌ You don't have credits!", parse_mode="HTML")
            return
        if count > current_credits:
            await msg.answer(f"❌ You only have {current_credits} credits! Max you can send: {current_credits}.", parse_mode="HTML")
            count = current_credits
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    if not devices:
        await msg.answer("❌ No API is online!", reply_markup=make_kb([[premium_btn("Home", "user:home", "home", "primary")]]))
        return
    await run_sms_blast_with_progress(msg.bot, msg, uid, number, message_text, count, devices, send_speed)

# ========== OWNER SEND ==========
@R.callback_query(F.data == "owner:send")
async def owner_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d):
        await cq.answer("Owner only!", show_alert=True)
        return
    await state.set_state(S.owner_send_number)
    await cq.message.edit_text(
        "👑 <b>Super Admin SMS Send</b>\n\n📨 <b>Step 1/4 - Number</b>\n\nEnter the number to send SMS to:",
        reply_markup=make_kb([[premium_btn("Cancel", "owner:home", "cross", "danger")]]),
        parse_mode="HTML"
    )

@R.message(S.owner_send_number)
async def owner_got_number(msg: Message, state: FSMContext):
    ok, number, err = normalize_number(msg.text)
    if not ok:
        await msg.answer(err, parse_mode="HTML")
        return
    await state.update_data(number=number)
    await state.set_state(S.owner_send_message)
    d = load()
    kb_rows = [[premium_btn("Cancel", "owner:home", "cross", "danger")]]
    if d.get("users", {}).get(str(msg.from_user.id), {}).get("templates"):
        kb_rows.insert(0, [premium_btn("📋 Use Template", "owner:template_pick", "list", "primary")])
    await msg.answer(f"✅ Number: <code>{mask_number(number)}</code>\n\n📨 <b>Step 2/4 - Message</b>\n\nType the message to send (or use a template):",
        reply_markup=make_kb(kb_rows),
        parse_mode="HTML"
    )

@R.message(S.owner_send_message)
async def owner_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.owner_send_speed)
    await msg.answer("✅ Message saved!\n\n🚀 <b>Step 3/4 - Speed</b>\n\nSelect the sending speed:",
        reply_markup=speed_kb("owner"), parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"owner:speed:fast", "owner:speed:medium", "owner:speed:slow"}))
async def owner_speed_selected(cq: CallbackQuery, state: FSMContext):
    speed_map = {"owner:speed:fast": SPEED_FAST, "owner:speed:medium": SPEED_MEDIUM, "owner:speed:slow": SPEED_SLOW}
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "FAST" if selected_speed == SPEED_FAST else "MEDIUM" if selected_speed == SPEED_MEDIUM else "SLOW"
    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.owner_send_count)
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(load())
    count = len(devices)
    await cq.message.edit_text(
        f"⚡ <b>{speed_label}</b> selected!\n\n📨 <b>Step 4/4 - Count</b>\n\n🔥 Online APIs: <b>{count}</b>\n📱 Device Capacity: <b>{count * 3}</b>\n\nHow many SMS do you want to send?",
        reply_markup=make_kb([[premium_btn("Cancel", "owner:home", "cross", "danger")]]),
        parse_mode="HTML"
    )

@R.message(S.owner_send_count)
async def owner_got_count(msg: Message, state: FSMContext):
    fsmd = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except:
        await msg.answer("❓ Send a number only:", parse_mode="HTML")
        return
    await state.clear()
    number = fsmd.get("number", "")
    message_text = fsmd.get("message", "")
    send_speed = fsmd.get("send_speed", SPEED_DEFAULT)
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(load())
    if not devices:
        await msg.answer("❌ No API is online!", reply_markup=make_kb([[premium_btn("Owner Panel", "owner:home", "home", "primary")]]))
        return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, number, message_text, count, devices, send_speed)

# ========== ADMIN SEND ==========
@R.callback_query(F.data == "admin:send")
async def admin_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("Admin only!", show_alert=True)
        return
    await state.set_state(S.admin_send_number)
    await cq.message.edit_text(
        "🛡️ <b>Admin SMS Send</b>\n\n📨 <b>Step 1/4 - Number</b>\n\nEnter the number to send SMS to:",
        reply_markup=make_kb([[premium_btn("Cancel", "admin:home", "cross", "danger")]]),
        parse_mode="HTML"
    )

@R.message(S.admin_send_number)
async def admin_got_number(msg: Message, state: FSMContext):
    ok, number, err = normalize_number(msg.text)
    if not ok:
        await msg.answer(err, parse_mode="HTML")
        return
    if number in PROTECTED_NUMBERS:
        protector_uid = PROTECTED_NUMBERS[number]
        if not is_owner(msg.from_user.id, load()) and msg.from_user.id != protector_uid:
            await msg.answer("🔒 This number is protected!", parse_mode="HTML")
            return
    await state.update_data(number=number)
    await state.set_state(S.admin_send_message)
    d = load()
    kb_rows = [[premium_btn("Cancel", "admin:home", "cross", "danger")]]
    if d.get("users", {}).get(str(msg.from_user.id), {}).get("templates"):
        kb_rows.insert(0, [premium_btn("📋 Use Template", "admin:template_pick", "list", "primary")])
    await msg.answer(f"✅ Number: <code>{mask_number(number)}</code>\n\n📨 <b>Step 2/4 - Message</b>\n\nType the message to send (or use a template):",
        reply_markup=make_kb(kb_rows),
        parse_mode="HTML"
    )

@R.message(S.admin_send_message)
async def admin_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.admin_send_speed)
    await msg.answer("✅ Message saved!\n\n🚀 <b>Step 3/4 - Speed</b>\n\nSelect the sending speed:",
        reply_markup=speed_kb("admin"), parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"admin:speed:fast", "admin:speed:medium", "admin:speed:slow"}))
async def admin_speed_selected(cq: CallbackQuery, state: FSMContext):
    speed_map = {"admin:speed:fast": SPEED_FAST, "admin:speed:medium": SPEED_MEDIUM, "admin:speed:slow": SPEED_SLOW}
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "FAST" if selected_speed == SPEED_FAST else "MEDIUM" if selected_speed == SPEED_MEDIUM else "SLOW"
    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.admin_send_count)
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(load())
    count = len(devices)
    await cq.message.edit_text(
        f"⚡ <b>{speed_label}</b> selected!\n\n📨 <b>Step 4/4 - Count</b>\n\n🔥 Online APIs: <b>{count}</b>\n📱 Device Capacity: <b>{count * 3}</b>\n\nHow many SMS do you want to send?",
        reply_markup=make_kb([[premium_btn("Cancel", "admin:home", "cross", "danger")]]),
        parse_mode="HTML"
    )

@R.message(S.admin_send_count)
async def admin_got_count(msg: Message, state: FSMContext):
    fsmd = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except:
        await msg.answer("❓ Send a number only:", parse_mode="HTML")
        return
    await state.clear()
    number = fsmd.get("number", "")
    message_text = fsmd.get("message", "")
    send_speed = fsmd.get("send_speed", SPEED_DEFAULT)
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(load())
    if not devices:
        await msg.answer("❌ No API is online!", reply_markup=make_kb([[premium_btn("Admin Panel", "admin:home", "home", "primary")]]))
        return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, number, message_text, count, devices, send_speed)

# ========== DAILY SMS LIMIT ==========
@R.callback_query(F.data == "owner:daily_limit")
async def owner_daily_limit_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    current = d.get("settings", {}).get("daily_limit", 0)
    await state.set_state(S.set_daily_limit)
    await cq.message.edit_text(
        f"📊 <b>Set Daily SMS Limit</b>\n\nCurrent: <b>{current if current > 0 else 'Unlimited (0)'}</b>\n\nSend the daily SMS cap for regular users (0 = unlimited):",
        reply_markup=make_kb([[premium_btn("Cancel", "owner:home", "cross", "danger")]]),
        parse_mode="HTML"
    )

@R.message(S.set_daily_limit)
async def owner_daily_limit_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        limit = int(msg.text.strip())
        if limit < 0:
            raise ValueError
    except:
        await msg.answer("❓ Send a valid number (0 = unlimited).", parse_mode="HTML")
        return
    d.setdefault("settings", {})["daily_limit"] = limit
    save(d)
    await state.clear()
    await msg.answer(f"✅ <b>Daily Limit Updated!</b>\n\n{limit if limit > 0 else 'Unlimited'}", reply_markup=make_kb([[premium_btn("Owner Panel", "owner:home", "home", "primary")]]), parse_mode="HTML")
    log_activity(d, "set_daily_limit", uid, f"Daily limit -> {limit}")

# ========== SMS TEMPLATES ==========
def templates_kb(d: dict, uid: int, prefix: str) -> InlineKeyboardMarkup:
    tpls = d.get("users", {}).get(str(uid), {}).get("templates", [])
    rows = []
    for i, t in enumerate(tpls):
        rows.append([
            premium_btn(f"📋 {t.get('name', f'Template {i+1}')[:18]}", f"{prefix}:template_use:{i}", "list", "primary"),
            premium_btn("🗑", f"{prefix}:template_del:{i}", "remove", "danger")
        ])
    rows.append([premium_btn("➕ Add Template", f"{prefix}:template_add", "add", "success")])
    rows.append([premium_btn("Back", f"{prefix}:home", "back", "secondary")])
    return make_kb(rows)

def templates_menu_text(d: dict, uid: int) -> str:
    tpls = d.get("users", {}).get(str(uid), {}).get("templates", [])
    if not tpls:
        return "📋 <b>SMS Templates</b>\n\nNo templates yet.\n\nTap ➕ Add Template to create one - no more retyping messages!"
    lines = ["📋 <b>SMS Templates</b>\n"]
    for i, t in enumerate(tpls, 1):
        text = t.get("text", "")
        lines.append(f"{i}. <b>{t.get('name', f'Template {i}')}</b>\n   <code>{text[:40]}{'...' if len(text) > 40 else ''}</code>\n")
    return "\n".join(lines)

@R.callback_query(F.data.regexp(r"^(user|owner|admin):(templates|template_pick)$"))
async def templates_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    prefix = cq.data.split(":")[0]
    await state.update_data(template_prefix=prefix)
    await cq.message.edit_text(templates_menu_text(d, uid), reply_markup=templates_kb(d, uid, prefix), parse_mode="HTML")

@R.callback_query(F.data.regexp(r"^(user|owner|admin):template_add$"))
async def template_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    prefix = cq.data.split(":")[0]
    tpls = d.get("users", {}).get(str(uid), {}).get("templates", [])
    if len(tpls) >= 20:
        await cq.answer("Max 20 templates!", show_alert=True)
        return
    await state.update_data(template_prefix=prefix)
    await state.set_state(S.add_template_name)
    back = "owner:home" if prefix == "owner" else "admin:home" if prefix == "admin" else "user:home"
    await cq.message.edit_text("📋 <b>Add Template</b>\n\nStep 1/2: Send the template name:", reply_markup=make_kb([[premium_btn("Cancel", back, "cross", "danger")]]), parse_mode="HTML")

@R.message(S.add_template_name)
async def template_add_name(msg: Message, state: FSMContext):
    name = msg.text.strip()[:25]
    if not name:
        await msg.answer("❓ Name is empty. Try again:")
        return
    fsmd = await state.get_data()
    prefix = fsmd.get("template_prefix", "user")
    await state.update_data(template_name=name)
    await state.set_state(S.add_template_text)
    back = "owner:home" if prefix == "owner" else "admin:home" if prefix == "admin" else "user:home"
    await msg.answer("Step 2/2: Send the template message text:", reply_markup=make_kb([[premium_btn("Cancel", back, "cross", "danger")]]), parse_mode="HTML")

@R.message(S.add_template_text)
async def template_add_text(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    text = msg.text.strip()
    if not text:
        await msg.answer("❓ Text is empty. Try again:")
        return
    fsmd = await state.get_data()
    name = fsmd.get("template_name", "Template")
    prefix = fsmd.get("template_prefix", "user")
    tpls = d.setdefault("users", {}).setdefault(str(uid), {}).setdefault("templates", [])
    tpls.append({"name": name, "text": text})
    save(d)
    await state.clear()
    await msg.answer(f"✅ <b>Template Saved!</b>\n\n📋 {name}", reply_markup=templates_kb(load(), uid, prefix), parse_mode="HTML")

@R.callback_query(F.data.regexp(r"^(user|owner|admin):template_use:(\d+)$"))
async def template_use(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    prefix = cq.data.split(":")[0]
    idx = int(cq.data.split(":")[2])
    tpls = d.get("users", {}).get(str(uid), {}).get("templates", [])
    if idx >= len(tpls):
        await cq.answer("Template not found!", show_alert=True)
        return
    fsmd = await state.get_data()
    if not fsmd.get("number"):
        await cq.answer("Start Send SMS first!", show_alert=True)
        return
    t = tpls[idx]
    speed_state = {"user": S.send_speed, "owner": S.owner_send_speed, "admin": S.admin_send_speed}.get(prefix)
    await state.update_data(message=t["text"])
    await state.set_state(speed_state)
    await cq.message.edit_text(
        f"✅ Template <b>{t['name']}</b> applied!\n\n📨 <b>Step 3/4 - Speed</b>\n\nSelect the sending speed:",
        reply_markup=speed_kb(prefix), parse_mode="HTML"
    )

@R.callback_query(F.data.regexp(r"^(user|owner|admin):template_del:(\d+)$"))
async def template_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    prefix = cq.data.split(":")[0]
    idx = int(cq.data.split(":")[2])
    tpls = d.setdefault("users", {}).setdefault(str(uid), {}).setdefault("templates", [])
    if idx < len(tpls):
        del tpls[idx]
        save(d)
    await cq.answer("Deleted!")
    await cq.message.edit_text(templates_menu_text(load(), uid), reply_markup=templates_kb(load(), uid, prefix), parse_mode="HTML")

# ========== USER: STOP SEND ==========
@R.callback_query(F.data == "user:stop_send")
async def user_stop_send(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    async with SESSIONS_LOCK:
        session = USER_SESSIONS.get(uid)
        if not session or (session.task and session.task.done()):
            await cq.answer("No active sending!", show_alert=True)
            return
        session.cancelled = True
    await cq.answer("Stopping...", show_alert=True)

# ========== OWNER HOME ==========
@R.callback_query(F.data.in_({"owner:home", "owner:refresh"}))
async def owner_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    try:
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    except TelegramBadRequest:
        pass

# ========== OWNER FB MENU ==========
@R.callback_query(F.data == "owner:fb:menu")
async def owner_fb_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await state.clear()
    await cq.message.edit_text(f"🔥 <b>Firebase Manager</b>\n\nTotal: <b>{len(d.get('firebases', []))}</b>", reply_markup=fb_menu_kb(d), parse_mode="HTML")

# ========== OWNER FB ADD ==========
@R.callback_query(F.data == "owner:fb:add")
async def owner_fb_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await state.set_state(S.add_firebase)
    await cq.message.edit_text("🔥 <b>Add Firebase</b>\n\nFormat: Label | URL", reply_markup=make_kb([[premium_btn("Cancel", "owner:fb:menu", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.add_firebase)
async def owner_fb_add_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    text = msg.text.strip()
    if "|" in text:
        parts = text.split("|", 1)
        label = parts[0].strip()
        url = parts[1].strip()
    else:
        url = text
        label = url.replace("https://", "").split(".")[0][:20]
    if not url.startswith("http"):
        await msg.answer("❌ URL must start with https://", parse_mode="HTML")
        return
    url = url.rstrip("/")
    fbs = d.get("firebases", [])
    if any(fb["url"] == url for fb in fbs):
        await state.clear()
        await msg.answer("❌ Already added!", reply_markup=fb_menu_kb(d), parse_mode="HTML")
        return
    fb_id = str(int(time.time()))
    fbs.append({"id": fb_id, "url": url, "label": label, "added_at": int(time.time())})
    d["firebases"] = fbs
    save(d)
    await state.clear()
    await msg.answer(f"✅ <b>Firebase Added!</b>\n\n{label}\n<code>{url}</code>", reply_markup=fb_menu_kb(load()), parse_mode="HTML")

# ========== OWNER FB DELETE ==========
@R.callback_query(F.data.startswith("owner:fb:del:"))
async def owner_fb_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    fb_id = cq.data.split("owner:fb:del:", 1)[1]
    d["firebases"] = [fb for fb in d["firebases"] if fb["id"] != fb_id]
    save(d)
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") != fb_id]
    FB_DEVICE_COUNTS.pop(fb_id, None)
    await cq.answer("Removed!")
    await owner_fb_menu(cq, state)

# ========== OWNER STATS ==========
@R.callback_query(F.data == "owner:stats")
async def owner_stats_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await cq.answer("Fetching...")
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    stats_text = api_stats_text(d)
    dev_lines = [f"\n📱 <b>Online Devices ({fmt_device_count(len(devices))})</b>\n"]
    if not devices:
        dev_lines.append("  ❌ No device online")
    for dv in devices:
        dev_lines.append(f"  📱 {dv['dev_name'][:20]}\n     🔥 {dv['fb_label'][:25]}\n     📶 SIMs: {len(dv['sims']) or 1}")
    full = stats_text + trend_stats_text(d) + "\n" + "\n".join(dev_lines)
    if len(full) > 4000:
        full = full[:3990] + "\n...truncated"
    await cq.message.edit_text(full, reply_markup=make_kb([[premium_btn("Refresh", "owner:stats", "refresh", "primary")], [premium_btn("Back", "owner:home", "back", "secondary")]]), parse_mode="HTML")

# ========== OWNER OWNERS MENU ==========
@R.callback_query(F.data == "owner:owners:menu")
async def owner_owners_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await cq.message.edit_text(f"👑 <b>Super Admins</b>\n\nTotal: <b>{len(d.get('owners', []))}/6</b>", reply_markup=owners_menu_kb(d), parse_mode="HTML")

# ========== OWNER OWNERS ADD ==========
@R.callback_query(F.data == "owner:owners:add")
async def owner_owners_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    if len(d.get("owners", [])) >= 6:
        await cq.answer("Max 6!", show_alert=True)
        return
    await state.set_state(S.add_owner)
    await cq.message.edit_text("👑 <b>Add Super Admin</b>\n\nSend the chat ID:", reply_markup=make_kb([[premium_btn("Cancel", "owner:owners:menu", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.add_owner)
async def owner_owners_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        new_id = int(msg.text.strip())
    except:
        await msg.answer("❓ Send a valid ID.", parse_mode="HTML")
        return
    if is_owner(new_id, d) or len(d.get("owners", [])) >= 6:
        await state.clear()
        await msg.answer("❌ Already admin or max limit!", parse_mode="HTML")
        return
    d["owners"].append(new_id)
    save(d)
    await state.clear()
    await msg.answer(f"✅ <b>Super Admin Added!</b>\n<code>{new_id}</code>", reply_markup=owners_menu_kb(load()), parse_mode="HTML")
    try:
        await msg.bot.send_message(new_id, "👑 You've been made a Super Admin!", parse_mode="HTML", message_effect_id=EFFECT_PARTY)
    except:
        pass

# ========== OWNER OWNERS DELETE ==========
@R.callback_query(F.data.startswith("owner:owners:del:"))
async def owner_owners_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    del_id = int(cq.data.split("owner:owners:del:", 1)[1])
    if not is_owner(uid, d) or del_id == MAIN_OWNER or del_id in SUPER_ADMINS:
        await cq.answer("Cannot remove main owner!", show_alert=True)
        return
    if del_id in d["owners"]:
        d["owners"].remove(del_id)
        save(d)
        await cq.answer("Removed!")
        try:
            await cq.bot.send_message(del_id, "👑 Your Super Admin access has been removed.", parse_mode="HTML")
        except:
            pass
    await owner_owners_menu(cq, state)

# ========== OWNER ADMINS MENU ==========
@R.callback_query(F.data == "owner:admins:menu")
async def owner_admins_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await cq.message.edit_text(f"🛡️ <b>Admins</b>\n\nTotal: <b>{len(d.get('admins', []))}</b>", reply_markup=admins_menu_kb(d), parse_mode="HTML")

# ========== OWNER ADMINS ADD ==========
@R.callback_query(F.data == "owner:admins:add")
async def owner_admins_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await state.set_state(S.add_admin)
    await cq.message.edit_text("🛡️ <b>Add Admin</b>\n\nSend the user ID:", reply_markup=make_kb([[premium_btn("Cancel", "owner:admins:menu", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.add_admin)
async def owner_admins_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        new_id = int(msg.text.strip())
    except:
        await msg.answer("❓ Send a valid ID.", parse_mode="HTML")
        return
    if new_id in d.get("admins", []) or is_owner(new_id, d):
        await state.clear()
        await msg.answer("❌ Already admin/owner!", parse_mode="HTML")
        return
    d["admins"].append(new_id)
    save(d)
    await state.clear()
    await msg.answer(f"✅ <b>Admin Added!</b>\n<code>{new_id}</code>", reply_markup=admins_menu_kb(load()), parse_mode="HTML")
    try:
        await msg.bot.send_message(new_id, "🛡️ You've been made an Admin!", parse_mode="HTML", message_effect_id=EFFECT_PARTY)
    except:
        pass

# ========== OWNER ADMINS DELETE ==========
@R.callback_query(F.data.startswith("owner:admins:del:"))
async def owner_admins_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    del_id = int(cq.data.split("owner:admins:del:", 1)[1])
    if not is_owner(uid, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    if del_id in d.get("admins", []):
        d["admins"].remove(del_id)
        save(d)
        await cq.answer("Removed!")
        try:
            await cq.bot.send_message(del_id, "🛡️ Your Admin access has been removed.", parse_mode="HTML")
        except:
            pass
    await owner_admins_menu(cq, state)

# ========== OWNER FREE TOGGLE ==========
@R.callback_query(F.data.in_({"owner:free:on", "owner:free:off"}))
async def owner_free_toggle(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    d["free_mode"] = (cq.data == "owner:free:on")
    save(d)
    await cq.answer(f"Done! {'FREE MODE ON' if d['free_mode'] else 'Approval Required'}", show_alert=True)
    await owner_home(cq, state)

# ========== USERS LIST ==========
@R.callback_query(F.data.in_({"owner:users:list", "admin:users:list"}))
async def panel_users_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    prefix = "owner" if is_owner(uid, d) else "admin"
    if not is_admin(uid, d):
        await cq.answer("🔒 Access denied!", show_alert=True)
        return
    text, markup = users_list_kb(d, prefix, 0)
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

# ========== USERS PAGE ==========
@R.callback_query(F.data.regexp(r"^(owner|admin):users:pg:(\d+)$"))
async def panel_users_page(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🔒 Access denied!", show_alert=True)
        return
    parts = cq.data.split(":")
    prefix = parts[0]
    page = int(parts[3])
    text, markup = users_list_kb(d, prefix, page)
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

# ========== BAN USER ==========
@R.callback_query(F.data.in_({"owner:ban", "admin:ban"}))
async def panel_ban_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🔒 Access denied!", show_alert=True)
        return
    await state.set_state(S.ban_user)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await cq.message.edit_text("🚫 <b>Ban User</b>\n\nSend the user ID:", reply_markup=make_kb([[premium_btn("Cancel", back, "cross", "danger")]]), parse_mode="HTML")

@R.message(S.ban_user)
async def panel_ban_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    try:
        ban_id = int(msg.text.strip())
    except:
        await msg.answer("❓ Send a valid ID.", parse_mode="HTML")
        return
    if is_owner(ban_id, d) or is_admin(ban_id, d):
        await state.clear()
        await msg.answer("❌ You can't ban an Admin/Owner!", parse_mode="HTML")
        return
    if ban_id not in d.get("banned", []):
        d.setdefault("banned", []).append(ban_id)
        save(d)
    await state.clear()
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await msg.answer(f"🚫 <b>Banned!</b>\n<code>{ban_id}</code>", reply_markup=back_kb, parse_mode="HTML")
    try:
        await msg.bot.send_message(ban_id, "🚫 You have been banned.")
    except:
        pass

# ========== UNBAN MENU ==========
@R.callback_query(F.data.in_({"owner:unban:menu", "admin:unban:menu"}))
async def panel_unban_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🔒 Access denied!", show_alert=True)
        return
    banned = d.get("banned", [])
    if not banned:
        await cq.answer("Nobody is banned!", show_alert=True)
        return
    prefix = "owner" if is_owner(cq.from_user.id, d) else "admin"
    await cq.message.edit_text(f"✅ <b>Unban User</b>\n\nBanned: <b>{len(banned)}</b>", reply_markup=unban_menu_kb(d, prefix), parse_mode="HTML")

# ========== UNBAN DO ==========
@R.callback_query(F.data.regexp(r"^(owner|admin):unban:do:(\d+)$"))
async def panel_unban_do(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🔒 Access denied!", show_alert=True)
        return
    ban_id = int(cq.data.split(":")[-1])
    if ban_id in d.get("banned", []):
        d["banned"].remove(ban_id)
        save(d)
    await cq.answer(f"✅ {ban_id} unbanned!", show_alert=True)
    back_text = owner_panel_text(d) if is_owner(uid, d) else admin_panel_text(d)
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await cq.message.edit_text(back_text, reply_markup=back_kb, parse_mode="HTML")
    try:
        await cq.bot.send_message(ban_id, "✅ Your ban has been removed.")
    except:
        pass

# ========== ADMIN HOME ==========
@R.callback_query(F.data.in_({"admin:home", "admin:refresh"}))
async def admin_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🔒 Admin only!", show_alert=True)
        return
    try:
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    except TelegramBadRequest:
        pass

# ========== ADMIN STATS ==========
@R.callback_query(F.data == "admin:stats")
async def admin_stats_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🔒 Admin only!", show_alert=True)
        return
    await cq.answer("Fetching...")
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    stats_text = api_stats_text(d)
    dev_lines = [f"\n📱 <b>Online Devices ({fmt_device_count(len(devices))})</b>\n"]
    if not devices:
        dev_lines.append("  ❌ No device online")
    for dv in devices:
        dev_lines.append(f"  📱 {dv['dev_name'][:20]} - 🔥 {dv['fb_label'][:20]}")
    full = stats_text + trend_stats_text(d) + "\n" + "\n".join(dev_lines)
    if len(full) > 4000:
        full = full[:3990] + "\n...truncated"
    await cq.message.edit_text(full, reply_markup=make_kb([[premium_btn("Refresh", "admin:stats", "refresh", "primary")], [premium_btn("Back", "admin:home", "back", "secondary")]]), parse_mode="HTML")

# ========== USER HOME ==========
@R.callback_query(F.data.in_({"user:home", "user:cancel"}))
async def user_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    uid = cq.from_user.id
    if is_owner(uid, d):
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d):
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    elif not can_use(uid, d):
        await cq.message.edit_text(f"🚫 No access!\nContact: {SUPER_ADMIN_NAME}", parse_mode="HTML")
    else:
        await cq.message.edit_text(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

# ========== USER CREDITS ==========
@R.callback_query(F.data == "user:credits")
async def user_credits(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    credits = get_user_credits(uid, d)
    await cq.answer(f"💰 Credits: {credits}", show_alert=True)

# ========== USER REDEEM ==========
@R.callback_query(F.data == "user:redeem")
async def user_redeem_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.redeem_code)
    await cq.message.edit_text("🎟️ <b>Redeem Code</b>\n\nEnter your redeem code:", reply_markup=make_kb([[premium_btn("Cancel", "user:home", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.redeem_code)
async def user_redeem_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    code = msg.text.strip().upper()
    await state.clear()
    codes = d.get("redeem_codes", {})
    if code not in codes:
        await msg.answer("❌ Invalid redeem code!", reply_markup=make_kb([[premium_btn("Home", "user:home", "home", "primary")]]))
        return
    code_data = codes[code]
    if code_data.get("uses_left", 0) <= 0 or uid in code_data.get("used_by", []):
        await msg.answer("❌ Code expired or already used!", reply_markup=make_kb([[premium_btn("Home", "user:home", "home", "primary")]]))
        return
    credits = code_data["credits"]
    add_credits(uid, credits, d)
    code_data["uses_left"] -= 1
    code_data.setdefault("used_by", []).append(uid)
    save(d)
    await msg.answer(f"✅ <b>Redeem Successful!</b>\n\n+{credits} credits added!\nBalance: {get_user_credits(uid, d)}", reply_markup=make_kb([[premium_btn("Home", "user:home", "home", "primary")]]), parse_mode="HTML", message_effect_id=EFFECT_PARTY)

# ========== USER REFER ==========
@R.callback_query(F.data == "user:refer")
async def user_refer(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    code = generate_user_refer_code(uid, d)
    save(d)
    ref_credits = d.get("settings", {}).get("ref_credits", 3)
    me = await cq.bot.get_me()
    await cq.message.edit_text(
        f"🤝 <b>Referral Program</b>\n\nYour Code: <code>{code}</code>\n\nShare Link:\nhttps://t.me/{me.username}?start={code}\n\nEvery referral gives {ref_credits} credits!",
        reply_markup=make_kb([[premium_btn("Back", "user:home", "back", "secondary")]]),
        parse_mode="HTML"
    )

# ========== USER STATS ==========
@R.callback_query(F.data == "user:stats")
async def user_stats(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    udata = d["users"].get(str(uid), {})
    stats = d.get("stats", {})
    await cq.message.edit_text(
        f"📊 <b>Your Stats</b>\n\n💰 Credits: <b>{udata.get('credits', 0)}</b>\n📨 SMS Sent: <b>{udata.get('uses', 0)}</b>\n🕐 Joined: <b>{fmt_time(udata.get('joined_at', 0))}</b>\n\n⚡ Bot Total Sent: <b>{stats.get('total_sent', 0)}</b>",
        reply_markup=make_kb([[premium_btn("Back", "user:home", "back", "secondary")]]),
        parse_mode="HTML"
    )

# ========== USER SMS HISTORY ==========
@R.callback_query(F.data == "user:sms_history")
async def user_sms_history(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    history = d.get("sms_history", {}).get(str(uid), [])[-10:]
    if not history:
        text = "📜 <b>Your SMS History</b>\n\nYou haven't sent any SMS yet."
    else:
        lines = ["📜 <b>Your SMS History (Last 10)</b>\n"]
        for i, entry in enumerate(reversed(history), 1):
            ts = fmt_time(entry.get("timestamp", 0))
            num = entry.get("number", "Unknown")
            msg_preview = entry.get("message", "")[:30]
            status_icon = "✅" if entry.get("status") == "sent" else "❌"
            lines.append(f"{i}. [{ts}] {status_icon} <code>{mask_number(num)}</code> - {msg_preview}...")
        text = "\n".join(lines)
    await cq.message.edit_text(text, reply_markup=make_kb([[premium_btn("Back", "user:home", "back", "secondary")]]), parse_mode="HTML")

# ========== USER PRICING ==========
@R.callback_query(F.data == "user:pricing")
async def user_pricing(cq: CallbackQuery, state: FSMContext):
    d = load()
    plans = d.get("pricing", {}).get("plans", [])
    if not plans:
        await cq.answer("❌ No plans available!", show_alert=True)
        return
    text = "💳 <b>Buy Credits</b>\n\n"
    for plan in plans:
        text += f"🔥 {plan['name']}\n   💰 Price: {plan['price']} {plan.get('currency', 'INR')}\n   💎 Credits: {plan['credits']}\n\n"
    rows = []
    for plan in plans:
        rows.append([premium_btn(f"Buy {plan['name'][:20]}", f"plan:buy:{plan['id']}", "plan", "success")])
    rows.append([premium_btn("Back", "user:home", "back", "secondary")])
    await cq.message.edit_text(text, reply_markup=make_kb(rows), parse_mode="HTML")

# ========== USER INFO ==========
@R.callback_query(F.data == "user:info")
async def user_info(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text(
        f"⚡ <b>DENJI BLAST {_VERSION}</b>\n\nBot for sending bulk SMS via Firebase.\n\n👑 Developer: <a href='{SUPER_ADMIN_LINK}'>{SUPER_ADMIN_NAME}</a>\n\nCredits are required to use the bot.",
        reply_markup=make_kb([[premium_btn("Back", "user:home", "back", "secondary")]]),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# ========== BROADCAST ==========
@R.callback_query(F.data.in_({"owner:broadcast", "admin:broadcast"}))
async def panel_broadcast_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("Admin Only!", show_alert=True)
        return
    await state.set_state(S.broadcast)
    back = "owner:home" if is_owner(uid, d) else "admin:home"
    await cq.message.edit_text("📢 <b>Broadcast</b>\n\nType the message to broadcast:", reply_markup=make_kb([[premium_btn("Cancel", back, "cross", "danger")]]), parse_mode="HTML")

@R.message(S.broadcast)
async def panel_broadcast_do(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        await msg.answer("Admin Only!", parse_mode="HTML")
        return
    broadcast_text = msg.text.strip()
    if msg.reply_to_message:
        replied = msg.reply_to_message
        if replied.text:
            broadcast_text = replied.text
        else:
            await msg.answer("Reply to a message with text!", parse_mode="HTML")
            return
    else:
        broadcast_text = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else None
        if not broadcast_text:
            await msg.answer("Use: /broadcast [message]", parse_mode="HTML")
            return
    users = d.get("users", {})
    total = len(users)
    if total == 0:
        await msg.answer("No users found!", parse_mode="HTML")
        return
    await state.clear()
    progress_msg = await msg.answer(f"📢 <b>Broadcast Started!</b>\n\nTotal: <b>{total}</b>\nProgress: 0/{total}", parse_mode="HTML")
    success = 0
    fail = 0
    for idx, (uid_str, _) in enumerate(users.items(), 1):
        try:
            await msg.bot.send_message(int(uid_str), f"📢 <b>Broadcast</b>\n\n{broadcast_text}", parse_mode="HTML", disable_notification=True)
            success += 1
        except:
            fail += 1
        if idx % 20 == 0 or idx == total:
            try:
                await progress_msg.edit_text(f"📢 <b>Broadcast in progress...</b>\n\nTotal: <b>{total}</b>\nProgress: {idx}/{total}\n✅ Success: {success}\n❌ Failed: {fail}", parse_mode="HTML")
            except:
                pass
        await asyncio.sleep(0.02)
    await progress_msg.edit_text(f"✅ <b>Broadcast Completed!</b>\n\nTotal: <b>{total}</b>\n✅ Success: <b>{success}</b>\n❌ Failed: <b>{fail}</b>", parse_mode="HTML")
    log_activity(d, "broadcast", uid, f"Sent to {success} users")

@R.message(Command("broadcast"))
async def cmd_broadcast(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await msg.answer("Admin Only!", parse_mode="HTML")
        return
    await state.set_state(S.broadcast)
    if msg.reply_to_message:
        await panel_broadcast_do(msg, state)
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("📢 <b>Broadcast System</b>\n\nUse: /broadcast [message]", parse_mode="HTML")
        await state.clear()
        return
    await panel_broadcast_do(msg, state)

# ========== PRICING PLANS MENU ==========
@R.callback_query(F.data == "owner:pricing:menu")
async def owner_pricing_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    plans = d.get("pricing", {}).get("plans", [])
    text = f"💳 <b>Pricing Plans</b>\n\nTotal: <b>{len(plans)}</b>\n\n"
    for i, plan in enumerate(plans, 1):
        text += f"{i}. {plan['name']}\n   💰 {plan['price']} = {plan['credits']} credits\n   🔗 {plan['payment_link']}\n\n"
    rows = [
        [premium_btn("Add Plan", "owner:pricing:add", "add", "success")],
        [premium_btn("Remove Plan", "owner:pricing:remove", "remove", "danger")],
        [premium_btn("Back", "owner:home", "back", "secondary")]
    ]
    await cq.message.edit_text(text, reply_markup=make_kb(rows), parse_mode="HTML")

# ========== ADD PLAN ==========
@R.callback_query(F.data == "owner:pricing:add")
async def owner_pricing_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await state.set_state(S.add_plan_name)
    await cq.message.edit_text("💳 <b>Add Plan</b>\n\nStep 1/4: Plan name:", reply_markup=make_kb([[premium_btn("Cancel", "owner:pricing:menu", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.add_plan_name)
async def owner_pricing_name(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    await state.update_data(plan_name=msg.text.strip())
    await state.set_state(S.add_plan_price)
    await msg.answer("Step 2/4: Price:", reply_markup=make_kb([[premium_btn("Cancel", "owner:pricing:menu", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.add_plan_price)
async def owner_pricing_price(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        price = float(msg.text.strip())
        await state.update_data(plan_price=price)
    except:
        await msg.answer("❓ Send a valid price.", parse_mode="HTML")
        return
    await state.set_state(S.add_plan_credits)
    await msg.answer("Step 3/4: Credits:", reply_markup=make_kb([[premium_btn("Cancel", "owner:pricing:menu", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.add_plan_credits)
async def owner_pricing_credits(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        credits = int(msg.text.strip())
        await state.update_data(plan_credits=credits)
    except:
        await msg.answer("❓ Send a valid number.", parse_mode="HTML")
        return
    await state.set_state(S.add_plan_link)
    await msg.answer("Step 4/4: Payment link:", reply_markup=make_kb([[premium_btn("Cancel", "owner:pricing:menu", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.add_plan_link)
async def owner_pricing_link(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    link = msg.text.strip()
    if not link.startswith("http"):
        await msg.answer("❓ Send a valid URL.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    plan = {"id": str(int(time.time())), "name": fsmd.get("plan_name", "Plan"), "price": fsmd.get("plan_price", 0), "credits": fsmd.get("plan_credits", 0), "currency": "INR", "payment_link": link}
    d.setdefault("pricing", {}).setdefault("plans", []).append(plan)
    save(d)
    await state.clear()
    await msg.answer(f"✅ <b>Plan Added!</b>\n\n{plan['name']}\n💰 {plan['price']} INR = {plan['credits']} credits", reply_markup=make_kb([[premium_btn("Back", "owner:pricing:menu", "back", "secondary")]]), parse_mode="HTML")

# ========== REMOVE PLAN ==========
@R.callback_query(F.data == "owner:pricing:remove")
async def owner_pricing_remove(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    plans = d.get("pricing", {}).get("plans", [])
    if not plans:
        await cq.answer("No plans!", show_alert=True)
        return
    rows = []
    for plan in plans:
        rows.append([premium_btn(f"Remove {plan['name'][:25]}", f"owner:pricing:del:{plan['id']}", "remove", "danger")])
    rows.append([premium_btn("Back", "owner:pricing:menu", "back", "secondary")])
    await cq.message.edit_text("🗑️ <b>Remove Plan</b>", reply_markup=make_kb(rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:pricing:del:"))
async def owner_pricing_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    plan_id = cq.data.split("owner:pricing:del:", 1)[1]
    d["pricing"]["plans"] = [p for p in d.get("pricing", {}).get("plans", []) if p["id"] != plan_id]
    save(d)
    await cq.answer("Removed!")
    await owner_pricing_menu(cq, state)

# ========== REDEEM MENU ==========
@R.callback_query(F.data == "owner:redeem:menu")
async def owner_redeem_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    codes = d.get("redeem_codes", {})
    text = f"🎟️ <b>Redeem Codes</b>\n\nTotal: <b>{len(codes)}</b>\n\n"
    for code, data in list(codes.items())[:10]:
        status = "✅ Active" if data.get("uses_left", 0) > 0 else "❌ Expired"
        text += f"<code>{code}</code> - 💰{data['credits']} - {status}\n"
    rows = [
        [premium_btn("Generate Code", "owner:redeem:gen", "add", "success")],
        [premium_btn("Delete Code", "owner:redeem:del", "remove", "danger")],
        [premium_btn("Back", "owner:home", "back", "secondary")]
    ]
    await cq.message.edit_text(text, reply_markup=make_kb(rows), parse_mode="HTML")

# ========== GENERATE REDEEM ==========
@R.callback_query(F.data == "owner:redeem:gen")
async def owner_redeem_gen_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await state.set_state(S.gen_redeem_credits)
    await cq.message.edit_text("🎟️ <b>Generate Code</b>\n\nStep 1/2: Credits:", reply_markup=make_kb([[premium_btn("Cancel", "owner:redeem:menu", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.gen_redeem_credits)
async def owner_redeem_credits(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        credits = int(msg.text.strip())
        await state.update_data(gen_credits=credits)
    except:
        await msg.answer("❓ Send a valid number.", parse_mode="HTML")
        return
    await state.set_state(S.gen_redeem_uses)
    await msg.answer("Step 2/2: Uses (more than 1):", reply_markup=make_kb([[premium_btn("Cancel", "owner:redeem:menu", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.gen_redeem_uses)
async def owner_redeem_uses(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        uses = int(msg.text.strip())
        if uses < 1:
            raise ValueError
    except:
        await msg.answer("❓ Send a valid number.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    credits = fsmd.get("gen_credits", 10)
    while True:
        code = "GIFT" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if code not in d.get("redeem_codes", {}):
            break
    d.setdefault("redeem_codes", {})[code] = {"credits": credits, "uses_left": uses, "created_by": msg.from_user.id, "created_at": int(time.time()), "used_by": []}
    save(d)
    await state.clear()
    await msg.answer(f"✅ <b>Code Generated!</b>\n\n<code>{code}</code>\n💰 {credits} credits\n🔁 {uses} uses", reply_markup=make_kb([[premium_btn("Back", "owner:redeem:menu", "back", "secondary")]]), parse_mode="HTML")

# ========== DELETE REDEEM ==========
@R.callback_query(F.data == "owner:redeem:del")
async def owner_redeem_del_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    codes = d.get("redeem_codes", {})
    if not codes:
        await cq.answer("No codes!", show_alert=True)
        return
    rows = []
    for code in list(codes.keys())[:20]:
        rows.append([premium_btn(f"Delete {code}", f"owner:redeem:deldo:{code}", "remove", "danger")])
    rows.append([premium_btn("Back", "owner:redeem:menu", "back", "secondary")])
    await cq.message.edit_text("🗑️ <b>Delete Code</b>", reply_markup=make_kb(rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:redeem:deldo:"))
async def owner_redeem_del_do(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    code = cq.data.split("owner:redeem:deldo:", 1)[1]
    if code in d.get("redeem_codes", {}):
        del d["redeem_codes"][code]
        save(d)
        await cq.answer("Deleted!")
    await owner_redeem_menu(cq, state)

# ========== ADD CREDITS ==========
@R.callback_query(F.data == "owner:credits:add")
async def owner_credits_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await state.set_state(S.add_credits_uid)
    await cq.message.edit_text("➕ <b>Add Credits</b>\n\nStep 1/2: User ID:", reply_markup=make_kb([[premium_btn("Cancel", "owner:home", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.add_credits_uid)
async def owner_credits_add_uid(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        uid = int(msg.text.strip())
        await state.update_data(credit_uid=uid)
    except:
        await msg.answer("❓ Send a valid ID.", parse_mode="HTML")
        return
    await state.set_state(S.add_credits_amount)
    await msg.answer("Step 2/2: Amount:", reply_markup=make_kb([[premium_btn("Cancel", "owner:home", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.add_credits_amount)
async def owner_credits_add_amount(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        amount = int(msg.text.strip())
    except:
        await msg.answer("❓ Send a valid number.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    uid = fsmd.get("credit_uid")
    add_credits(uid, amount, d)
    save(d)
    await state.clear()
    try:
        await msg.bot.send_message(uid, f"💰 <b>Credits Added!</b>\n\n+{amount} credits!\nBalance: {get_user_credits(uid, d)}\n\nAdded by the owner.", parse_mode="HTML", message_effect_id=EFFECT_PARTY)
    except:
        pass
    await msg.answer(f"✅ {amount} credits added to <code>{uid}</code>!", reply_markup=make_kb([[premium_btn("Back", "owner:home", "back", "secondary")]]), parse_mode="HTML")

# ========== DEDUCT CREDITS ==========
@R.callback_query(F.data == "owner:credits:deduct")
async def owner_credits_deduct_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await state.set_state(S.deduct_credits_uid)
    await cq.message.edit_text("➖ <b>Deduct Credits</b>\n\nStep 1/2: User ID:", reply_markup=make_kb([[premium_btn("Cancel", "owner:home", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.deduct_credits_uid)
async def owner_credits_deduct_uid(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        uid = int(msg.text.strip())
        await state.update_data(deduct_uid=uid)
    except:
        await msg.answer("❓ Send a valid ID.", parse_mode="HTML")
        return
    await state.set_state(S.deduct_credits_amount)
    await msg.answer("Step 2/2: Amount:", reply_markup=make_kb([[premium_btn("Cancel", "owner:home", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.deduct_credits_amount)
async def owner_credits_deduct_amount(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        amount = int(msg.text.strip())
    except:
        await msg.answer("❓ Send a valid number.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    uid = fsmd.get("deduct_uid")
    success = deduct_credits(uid, amount, d)
    save(d)
    await state.clear()
    if success:
        try:
            await msg.bot.send_message(uid, f"➖ <b>Credits Deducted!</b>\n\n-{amount} credits\nBalance: {get_user_credits(uid, d)}", parse_mode="HTML")
        except:
            pass
        await msg.answer(f"✅ {amount} credits deducted from <code>{uid}</code>!", reply_markup=make_kb([[premium_btn("Back", "owner:home", "back", "secondary")]]), parse_mode="HTML")
    else:
        await msg.answer(f"❌ Insufficient credits! User has {get_user_credits(uid, d)}", reply_markup=make_kb([[premium_btn("Back", "owner:home", "back", "secondary")]]), parse_mode="HTML")

# ========== ADD CREDITS ALL ==========
@R.callback_query(F.data == "owner:add_all_credits")
async def owner_add_all_credits_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await state.set_state(S.add_all_credits_amount)
    await cq.message.edit_text("➕ <b>Add Credits to ALL Users</b>\n\nHow many credits to give to all users?", reply_markup=make_kb([[premium_btn("Cancel", "owner:home", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.add_all_credits_amount)
async def owner_add_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        amount = int(msg.text.strip())
        if amount <= 0:
            raise ValueError
    except:
        await msg.answer("❓ Send a valid positive number.", parse_mode="HTML")
        return
    await state.clear()
    users = d.get("users", {})
    if not users:
        await msg.answer("❌ There are no users!", reply_markup=make_kb([[premium_btn("Back", "owner:home", "back", "secondary")]]))
        return
    count = 0
    for uid_str in users:
        add_credits(int(uid_str), amount, d)
        count += 1
    save(d)
    notification = f"💰 <b>Credits Added!</b>\n\nYou received {amount} credits!\n\nAdded by the owner of this bot."
    success = 0
    for uid_str in users:
        try:
            await msg.bot.send_message(int(uid_str), notification, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.03)
        except:
            pass
    await msg.answer(f"✅ <b>Credits Added!</b>\n\n{amount} credits each\nTotal users: <b>{count}</b>\nNotified: <b>{success}</b>", reply_markup=make_kb([[premium_btn("Back", "owner:home", "back", "secondary")]]), parse_mode="HTML")
    log_activity(d, "add_credits_all", uid, f"Added {amount} to {count} users")

# ========== DEDUCT CREDITS ALL ==========
@R.callback_query(F.data == "owner:deduct_all_credits")
async def owner_deduct_all_credits_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await state.set_state(S.deduct_all_credits_amount)
    await cq.message.edit_text("➖ <b>Deduct Credits from ALL Users</b>\n\nHow many credits to deduct from all users?\n\n👑 Credits won't be deducted from Owners/Admins!", reply_markup=make_kb([[premium_btn("Cancel", "owner:home", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.deduct_all_credits_amount)
async def owner_deduct_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        amount = int(msg.text.strip())
        if amount <= 0:
            raise ValueError
    except:
        await msg.answer("❓ Send a valid positive number.", parse_mode="HTML")
        return
    await state.clear()
    users = d.get("users", {})
    if not users:
        await msg.answer("❌ There are no users!", reply_markup=make_kb([[premium_btn("Back", "owner:home", "back", "secondary")]]))
        return
    count = 0
    total_deducted = 0
    owners = d.get("owners", [MAIN_OWNER])
    admins = d.get("admins", [])
    for uid_str, udata in users.items():
        user_id = int(uid_str)
        if user_id in owners or user_id in admins:
            continue
        current = udata.get("credits", 0)
        if current >= amount:
            udata["credits"] = current - amount
            count += 1
            total_deducted += amount
        elif current > 0:
            udata["credits"] = 0
            count += 1
            total_deducted += current
    save(d)
    await msg.answer(f"➖ <b>Credits Deducted!</b>\n\n{amount} credits each\nTotal users affected: <b>{count}</b>\nTotal deducted: <b>{total_deducted}</b>\n👑 Owners/Admins: Skipped", reply_markup=make_kb([[premium_btn("Back", "owner:home", "back", "secondary")]]), parse_mode="HTML")
    log_activity(d, "deduct_credits_all", uid, f"Deducted {total_deducted} from {count} users")

# ========== SETTINGS ==========
@R.callback_query(F.data == "owner:settings")
async def owner_settings(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    settings = d.get("settings", {})
    text = f"⚙️ <b>Settings</b>\n\nReferral Credits: <b>{settings.get('ref_credits', 3)}</b>\nMax Owners: <b>{settings.get('max_owners', 6)}</b>"
    rows = [
        [premium_btn("Set Referral Credits", "owner:settings:ref", "edit", "primary")],
        [premium_btn("Back", "owner:home", "back", "secondary")]
    ]
    await cq.message.edit_text(text, reply_markup=make_kb(rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:settings:ref")
async def owner_settings_ref(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await state.set_state(S.set_ref_credits)
    await cq.message.edit_text("⚙️ <b>Set Referral Credits</b>\n\nHow many credits per referral?", reply_markup=make_kb([[premium_btn("Cancel", "owner:settings", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.set_ref_credits)
async def owner_settings_ref_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        credits = int(msg.text.strip())
        if credits < 0:
            raise ValueError
    except:
        await msg.answer("❓ Send a valid positive number.", parse_mode="HTML")
        return
    d.setdefault("settings", {})["ref_credits"] = credits
    d["premium"]["ref_credits"] = credits
    save(d)
    await state.clear()
    await msg.answer(f"✅ <b>Referral Credits Updated!</b>\n\nNow every referral gives {credits} credits.", reply_markup=make_kb([[premium_btn("Back", "owner:settings", "back", "secondary")]]), parse_mode="HTML")

# ========== ACTIVITY LOG ==========
@R.callback_query(F.data == "owner:activity")
async def owner_activity_log(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    log_entries = d.get("activity_log", [])[-20:]
    if not log_entries:
        text = "📋 <b>Activity Log</b>\n\nNo activity yet."
    else:
        lines = ["📋 <b>Recent Activity</b>\n"]
        for entry in reversed(log_entries):
            ts = fmt_time(entry.get("timestamp", 0))
            action = entry.get("action", "unknown")
            uid = entry.get("uid", 0)
            details = entry.get("details", "")
            lines.append(f"[{ts}] <code>{uid}</code> - {action} - {details}")
        text = "\n".join(lines)
    await cq.message.edit_text(text, reply_markup=make_kb([[premium_btn("Refresh", "owner:activity", "refresh", "primary")], [premium_btn("Back", "owner:home", "back", "secondary")]]), parse_mode="HTML")

# ========== SMS HISTORY ==========
@R.callback_query(F.data == "owner:sms_history")
async def owner_sms_history(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    all_history = d.get("sms_history", {})
    total_entries = sum(len(v) for v in all_history.values())
    text = f"📜 <b>Global SMS History</b>\n\nTotal Records: <b>{total_entries}</b>\n\nPer-user history is available in their Stats."
    await cq.message.edit_text(text, reply_markup=make_kb([[premium_btn("Back", "owner:home", "back", "secondary")]]), parse_mode="HTML")

# ========== FORCE JOIN MENU ==========
@R.callback_query(F.data == "owner:fj:menu")
async def owner_fj_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    fj = d.get("force_join", {})
    channels = fj.get("channels", [])
    status = "ON" if fj.get("enabled") else "OFF"
    text = f"🔗 <b>Force Join Settings</b>\n\nStatus: <b>{status}</b>\nChannels: <b>{len(channels)}</b>\n\n"
    for ch in channels:
        req = "Required" if ch.get("required", True) else "Optional"
        text += f"• {ch.get('title', 'Channel')} (<code>{ch['id']}</code>)\n  {req} | {ch['link']}\n\n"
    rows = [
        [premium_btn("Add Channel", "owner:fj:add", "add", "success")],
        [premium_btn("Remove Channel", "owner:fj:remove", "remove", "danger")],
        [premium_btn("Enable" if not fj.get("enabled") else "Disable", "owner:fj:toggle", "bolt", "primary")],
        [premium_btn("Back", "owner:home", "back", "secondary")]
    ]
    await cq.message.edit_text(text, reply_markup=make_kb(rows), parse_mode="HTML")

# ========== FORCE JOIN ADD ==========
@R.callback_query(F.data == "owner:fj:add")
async def owner_fj_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await state.set_state(S.fj_add_channel)
    await cq.message.edit_text("🔗 <b>Add Channel</b>\n\nStep 1/2: Channel ID (e.g. -1001234567890):", reply_markup=make_kb([[premium_btn("Cancel", "owner:fj:menu", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.fj_add_channel)
async def owner_fj_add_channel(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        ch_id = int(msg.text.strip())
    except:
        await msg.answer("❓ Send a valid channel ID.", parse_mode="HTML")
        return
    await state.update_data(fj_channel_id=ch_id)
    await state.set_state(S.fj_add_link)
    await msg.answer("Step 2/2: Invite link:", reply_markup=make_kb([[premium_btn("Cancel", "owner:fj:menu", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.fj_add_link)
async def owner_fj_add_link(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    link = msg.text.strip()
    if not link.startswith("http"):
        await msg.answer("❓ Send a valid link.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    ch_id = str(fsmd.get("fj_channel_id"))
    try:
        chat = await msg.bot.get_chat(int(ch_id))
        title = chat.title or "Channel"
    except:
        title = "Channel"
    channels = d.setdefault("force_join", {}).setdefault("channels", [])
    channels = [c for c in channels if str(c["id"]) != ch_id]
    channels.append({"id": ch_id, "link": link, "title": title, "required": True})
    d["force_join"]["channels"] = channels
    save(d)
    await state.clear()
    await msg.answer(f"✅ <b>Channel Added!</b>\n\n{title}\n{link}", reply_markup=make_kb([[premium_btn("Back", "owner:fj:menu", "back", "secondary")]]), parse_mode="HTML")

# ========== FORCE JOIN REMOVE ==========
@R.callback_query(F.data == "owner:fj:remove")
async def owner_fj_remove_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    channels = d.get("force_join", {}).get("channels", [])
    if not channels:
        await cq.answer("No channels!", show_alert=True)
        return
    rows = []
    for ch in channels:
        rows.append([premium_btn(f"Remove {ch.get('title', 'Channel')[:25]}", f"owner:fj:del:{ch['id']}", "remove", "danger")])
    rows.append([premium_btn("Back", "owner:fj:menu", "back", "secondary")])
    await cq.message.edit_text("🗑️ <b>Remove Channel</b>", reply_markup=make_kb(rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:fj:del:"))
async def owner_fj_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    ch_id = cq.data.split("owner:fj:del:", 1)[1]
    d["force_join"]["channels"] = [c for c in d.get("force_join", {}).get("channels", []) if str(c["id"]) != ch_id]
    save(d)
    await cq.answer("Removed!")
    await owner_fj_menu(cq, state)

# ========== FORCE JOIN TOGGLE ==========
@R.callback_query(F.data == "owner:fj:toggle")
async def owner_fj_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    fj = d.setdefault("force_join", {})
    fj["enabled"] = not fj.get("enabled", False)
    save(d)
    status = "ENABLED" if fj["enabled"] else "DISABLED"
    await cq.answer(f"Force Join {status}!", show_alert=True)
    await owner_fj_menu(cq, state)

# ========== NUMBER PROTECTION ==========
@R.callback_query(F.data.in_({"owner:protect", "admin:protect"}))
async def owner_protect_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🔒 Admin only!", show_alert=True)
        return
    back = "owner:home" if is_owner(uid, d) else "admin:home"
    await state.update_data(protect_back=back)
    await state.set_state(S.protect_number)
    await cq.message.edit_text("🔒 <b>Protect Number</b>\n\nEnter the number to protect:", reply_markup=make_kb([[premium_btn("Cancel", back, "cross", "danger")]]), parse_mode="HTML")

@R.message(S.protect_number)
async def owner_protect_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    ok, number, err = normalize_number(msg.text)
    if not ok:
        await msg.answer(err, parse_mode="HTML")
        return
    PROTECTED_NUMBERS[number] = uid
    d["protected_numbers"] = PROTECTED_NUMBERS
    save(d)
    fsmd = await state.get_data()
    back = fsmd.get("protect_back", "owner:home")
    await state.clear()
    await msg.answer(f"🔒 <b>Number Protected!</b>\n\n<code>{number}</code>", reply_markup=make_kb([[premium_btn("Back", back, "back", "secondary")]]), parse_mode="HTML")
    log_activity(d, "number_protected", uid, f"Protected {number}")

# ========== PROTECTED LIST ==========
@R.callback_query(F.data.in_({"owner:protected_list", "admin:protected_list"}))
async def owner_protected_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("Access denied!", show_alert=True)
        return
    back = "owner:home" if is_owner(uid, d) else "admin:home"
    protected = d.get("protected_numbers", {})
    if not protected:
        await cq.message.edit_text("🔒 <b>Protected Numbers List</b>\n\nNo numbers are protected.", reply_markup=make_kb([[premium_btn("Back", back, "back", "secondary")]]), parse_mode="HTML")
        return
    lines = ["🔒 <b>Protected Numbers List</b>\n\n"]
    is_owner_user = is_owner(uid, d) or is_main_owner(uid)
    for number, protector_uid in protected.items():
        display_number = number if is_owner_user else mask_number(number)
        protector_data = d.get("users", {}).get(str(protector_uid), {})
        protector_name = protector_data.get("name", "Unknown")
        lines.append(f"🔒 <code>{display_number}</code>\n   🛡️ Protected by: <code>{protector_uid}</code> ({protector_name})\n")
    rows = []
    if is_owner_user:
        rows.append([premium_btn("Remove Protection", "owner:protected_remove", "remove", "danger")])
    rows.append([premium_btn("Back", back, "back", "secondary")])
    await cq.message.edit_text("\n".join(lines), reply_markup=make_kb(rows), parse_mode="HTML")

# ========== REMOVE PROTECTION ==========
@R.callback_query(F.data == "owner:protected_remove")
async def owner_protected_remove_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d) and not is_main_owner(uid):
        await cq.answer("Owner only!", show_alert=True)
        return
    protected = d.get("protected_numbers", {})
    if not protected:
        await cq.answer("No protected numbers!", show_alert=True)
        return
    rows = []
    for number in protected:
        rows.append([premium_btn(f"Remove {number}", f"owner:protected_del:{number}", "remove", "danger")])
    rows.append([premium_btn("Back", "owner:protected_list", "back", "secondary")])
    await cq.message.edit_text("🗑️ <b>Remove Protected Number</b>", reply_markup=make_kb(rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:protected_del:"))
async def owner_protected_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d) and not is_main_owner(uid):
        await cq.answer("Owner only!", show_alert=True)
        return
    number = cq.data.split("owner:protected_del:", 1)[1]
    if number in d.get("protected_numbers", {}):
        del d["protected_numbers"][number]
        save(d)
        global PROTECTED_NUMBERS
        PROTECTED_NUMBERS = d["protected_numbers"]
        await cq.answer(f"✅ Protection removed for {number}!", show_alert=True)
    await owner_protected_list(cq, state)

# ========== TRACK NUMBER ==========
@R.callback_query(F.data == "owner:track")
async def owner_track_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("Owner only!", show_alert=True)
        return
    await state.set_state(S.track_number)
    await cq.message.edit_text("📡 <b>Number Tracker</b>\n\nEnter the number to track:", reply_markup=make_kb([[premium_btn("Cancel", "owner:home", "cross", "danger")]]), parse_mode="HTML")

@R.message(S.track_number)
async def owner_track_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    ok, number, err = normalize_number(msg.text)
    if not ok:
        await msg.answer(err, parse_mode="HTML")
        return
    await state.clear()
    all_history = d.get("sms_history", {})
    users_who_sent = []
    for uid_str, history_list in all_history.items():
        for entry in history_list:
            if entry.get("number") == number:
                user_data = d.get("users", {}).get(uid_str, {})
                users_who_sent.append({"uid": int(uid_str), "name": user_data.get("name", "Unknown"), "timestamp": entry.get("timestamp", 0)})
                break
    if not users_who_sent:
        await msg.answer(f"📡 <b>Number Tracker</b>\n\n<code>{number}</code>\n\nNobody has sent an SMS to this number.", reply_markup=make_kb([[premium_btn("Back", "owner:home", "back", "secondary")]]), parse_mode="HTML")
        return
    lines = [f"📡 <b>Number Tracker</b>\n\n<code>{number}</code>\n\nUsers who sent to this number:\n"]
    for entry in users_who_sent:
        ts = fmt_time(entry["timestamp"])
        lines.append(f"• <code>{entry['uid']}</code> - {entry['name'][:20]} - {ts}")
    await msg.answer("\n".join(lines), reply_markup=make_kb([[premium_btn("Back", "owner:home", "back", "secondary")]]), parse_mode="HTML")

# ========== EXPORT SCRIPT ==========
@R.callback_query(F.data == "owner:export_script")
async def owner_export_script(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🔒 Owner only!", show_alert=True)
        return
    await cq.answer("Exporting...")
    try:
        script_path = os.path.abspath(__file__)
        if not os.path.exists(script_path):
            script_path = _DATA_FILE.replace(".json", ".py")
        await cq.message.reply_document(document=FSInputFile(script_path), caption=f"⚡ <b>Script Export - {_VERSION}</b>", parse_mode="HTML")
    except Exception as e:
        await cq.answer(f"Export failed: {str(e)[:40]}", show_alert=True)

# ========== WEB SERVER (keep-alive + webhook mode for Wasmer/edge hosts) ==========
from aiohttp import web
from aiogram.types import Update

async def handle_ping(request):
    """Health endpoint includes database state without exposing secrets."""
    try:
        health = db.health()
        if health.get("required") and not health.get("connected"):
            return web.json_response({"status": "unhealthy", "database": health}, status=503)
        return web.json_response({"status": "ok", "database": health})
    except Exception as exc:
        return web.json_response({"status": "unhealthy", "database": {"error": str(exc)}}, status=503)

async def handle_webhook(request: web.Request, dp: Dispatcher, bot: Bot):
    try:
        update = Update.model_validate(await request.json())
        await dp.feed_webhook_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        log.error(f"Webhook error: {e}")
        return web.Response(status=500)

async def run_web_server(dp: Dispatcher, bot: Bot):
    """Runs an HTTP server used for BOTH:
    1. Keep-alive pings (free hosts like HF Spaces, Render)
    2. Webhook mode (Wasmer Edge / serverless hosts) via POST /webhook
    """
    port = int(os.getenv("PORT", "8000"))
    webhook_path = os.getenv("WEBHOOK_PATH", "/webhook")
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    app.router.add_post(webhook_path, lambda r: handle_webhook(r, dp, bot))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info(f"✅ Web server running on port {port} (webhook path: {webhook_path})")
    while True:
        await asyncio.sleep(3600)

# ========== MAIN ==========
async def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN env var is required. Set it in the host's secrets/dashboard before starting.")
        return
    bot = Bot(token=BOT_TOKEN)
    # Fail closed in production: never run with temporary local storage.
    if os.getenv("REQUIRE_MONGODB", "true").lower() not in {"0", "false", "no"}:
        db.health()  # raises with a clear startup error if MongoDB is unavailable
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(R)
    me = await bot.get_me()
    log.info(f"⚡ @{me.username} - DENJI BLAST {_VERSION} started!")
    scanner_task = asyncio.create_task(background_firebase_scanner(bot))
    log.info("✅ Background scanner task created")
    await set_bot_commands(bot)
    try:
        await bot.send_message(MAIN_OWNER, f"👑 <b>DENJI BLAST {_VERSION} Online!</b>\n\n⚡ @{me.username}\n\n✅ You are the MASTER OWNER - full access!", parse_mode="HTML", message_effect_id=EFFECT_PARTY)
    except Exception as e:
        log.warning(f"Owner notify: {e}")

    webhook_url = os.getenv("WEBHOOK_URL", "").strip() or os.getenv("RENDER_EXTERNAL_URL", "").strip()
    if webhook_url:
        # WEBHOOK MODE - for Wasmer Edge / serverless hosts
        webhook_path = os.getenv("WEBHOOK_PATH", "/webhook")
        full_webhook = webhook_url.rstrip("/") + webhook_path
        await bot.set_webhook(full_webhook)
        log.info(f"🌐 Webhook set: {full_webhook}")
        await run_web_server(dp, bot)  # runs forever, handles updates via webhook
    else:
        # POLLING MODE - for local/VPS/Cloud Shell
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
