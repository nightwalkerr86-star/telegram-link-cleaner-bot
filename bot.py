import asyncio
import logging
import os
import re
import time
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

from telethon import TelegramClient, events, utils
from telethon.errors import ChatAdminRequiredError, FloodWaitError, UserAdminInvalidError
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "anti_spam.log")

log_handlers = [logging.StreamHandler()]
try:
    log_handlers.append(logging.FileHandler(LOG_FILE, encoding="utf-8"))
except OSError as exc:
    print(f"warning: cannot write log file {LOG_FILE}: {exc}")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    handlers=log_handlers,
)
logger = logging.getLogger("anti_spam")


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_NAME = os.getenv("SESSION_NAME", "anti_spam_bot")

DELETE_WORKERS = int(os.getenv("DELETE_WORKERS", "4"))
DELETE_BATCH_SIZE = int(os.getenv("DELETE_BATCH_SIZE", "100"))
DELETE_BATCH_DELAY = float(os.getenv("DELETE_BATCH_DELAY", "0.15"))
ADMIN_CACHE_TTL = int(os.getenv("ADMIN_CACHE_TTL", "300"))
MAX_FLOOD_WAIT = int(os.getenv("MAX_FLOOD_WAIT", "60"))

FLOOD_WINDOW_SECONDS = int(os.getenv("FLOOD_WINDOW_SECONDS", "10"))
FLOOD_MESSAGE_LIMIT = int(os.getenv("FLOOD_MESSAGE_LIMIT", "8"))
RECENT_MESSAGE_TTL = int(os.getenv("RECENT_MESSAGE_TTL", "180"))
MUTE_SECONDS = int(os.getenv("MUTE_SECONDS", "86400"))
SIMILAR_WINDOW_SECONDS = int(os.getenv("SIMILAR_WINDOW_SECONDS", "300"))
SIMILAR_MESSAGE_LIMIT = int(os.getenv("SIMILAR_MESSAGE_LIMIT", "3"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.72"))
RECENT_SIMILAR_LIMIT = int(os.getenv("RECENT_SIMILAR_LIMIT", "300"))

BOT_SPAM_ACTION = os.getenv("BOT_SPAM_ACTION", "ban").lower()
USER_SPAM_ACTION = os.getenv("USER_SPAM_ACTION", "mute").lower()
ALLOW_CHANNEL_POSTS = env_bool("ALLOW_CHANNEL_POSTS", True)
ALLOW_ANONYMOUS_ADMIN_COMMENTS = env_bool("ALLOW_ANONYMOUS_ADMIN_COMMENTS", True)
ALLOW_CHANNEL_IDENTITY_COMMENTS = env_bool("ALLOW_CHANNEL_IDENTITY_COMMENTS", True)
ALLOW_LINKED_CHANNEL_FORWARDS = env_bool("ALLOW_LINKED_CHANNEL_FORWARDS", True)

WHITELIST_IDS = {
    int(value.strip())
    for value in (os.getenv("WHITELIST_IDS", "") + "," + os.getenv("ADMIN_IDS", "")).split(",")
    if value.strip().lstrip("-").isdigit()
}
WHITELIST_USERNAMES = {
    value.strip().lower().lstrip("@")
    for value in os.getenv("WHITELIST_USERNAMES", "").split(",")
    if value.strip()
}
TRUSTED_CHANNEL_IDS = {
    int(value.strip())
    for value in os.getenv("TRUSTED_CHANNEL_IDS", "").split(",")
    if value.strip().lstrip("-").isdigit()
}

ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u2060]")
URL_RE = re.compile(
    r"(?i)(?:https?://|www\.)\S+"
    r"|(?:t\.me|telegram\.me|telegram\.dog)/\S+"
    r"|(?<!@)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|net|org|io|cc|xyz|top|vip|app|site|shop|link|me|tv|cn)\b(?:/\S*)?"
)
SUSPICIOUS_LINK_RE = re.compile(
    r"(?i)(?:"
    r"bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly|cutt\.ly|shorturl|"
    r"free|bonus|promo|airdrop|casino|bet|vip|adult|watch|live|"
    r"telegram|whatsapp|crypto|usdt|claim|gift|prize|token|wallet|"
    r"login|verify|bonus|giveaway|invite|join"
    r")"
)

TELEGRAM_INVITE_RE = re.compile(
    r"(?i)(?:https?://)?(?:t\.me|telegram\.me|telegram\.dog)/(?:joinchat/|\+|c/)?[a-z0-9_+\-/]{4,}"
)

PROMOTION_KEYWORDS = (
    "promo",
    "promotion",
    "discount",
    "limited time",
    "free trial",
    "free",
    "bonus",
    "offer",
    "click",
    "join",
    "subscribe",
    "dm",
    "inbox",
    "whatsapp",
    "telegram",
    "casino",
    "bet",
    "betting",
    "airdrop",
    "earn",
    "profit",
    "investment",
    "crypto",
    "usdt",
    "loan",
    "vip",
    "advert",
    "advertisement",
    "sponsored",
    "marketing",
    "sale",
    "deal",
    "giveaway",
    "claim",
    "prize",
    "verify",
    "wallet",
    "token",
    "trading",
    "forex",
    "signal",
    "signals",
    "double your money",
    "passive income",
    "guaranteed returns",
    "点击",
    "点头像",
    "链接",
    "搜索",
    "免费",
    "资源",
    "限时",
    "观看",
    "直播",
    "福利",
    "加入",
    "加群",
    "私聊",
    "主页",
    "简介群",
    "优惠",
    "领取",
    "返利",
    "佣金",
    "赚钱",
    "投资",
    "博彩",
    "赌场",
    "下注",
    "开奖",
    "偷拍",
    "广告",
    "推广",
    "折扣",
    "促销",
    "特价",
    "送彩金",
    "注册送",
    "空投",
    "合约",
    "币圈",
    "稳赚",
    "翻倍",
    "收益",
    "理财",
    "开户注册",
    "开户链接",
)

PROMOTION_PHRASES = (
    "limited time",
    "free trial",
    "sign up",
    "join now",
    "click here",
    "buy now",
    "contact me",
    "message me",
    "earn money",
    "make money",
    "guaranteed profit",
    "guaranteed returns",
    "passive income",
    "double your money",
    "crypto giveaway",
    "wallet verify",
    "claim reward",
    "free bonus",
    "casino bonus",
    "betting tips",
    "vip signals",
    "点头像进简介群",
    "进简介群",
    "进主页看",
    "主页看",
    "点击链接",
    "点击搜索",
    "限时免费",
    "开户链接",
    "注册送",
    "稳赚不赔",
    "投资理财",
)

ADVERTISING_RE = re.compile(
    r"(?i)\b(?:"
    r"advertisement|sponsored|promotion|promoted|limited\s+offer|special\s+offer|"
    r"sale|discount|coupon|voucher|giveaway|claim\s+(?:now|reward|bonus)|"
    r"contact\s+(?:me|us)|dm\s+(?:me|us)|message\s+(?:me|us)|subscribe|follow\s+us"
    r")\b"
    r"|(?:广告|推广|促销|优惠|折扣|特价|赞助|联系我|私聊|关注|订阅)"
)

GAMBLING_RE = re.compile(
    r"(?i)\b(?:casino|gambling|betting|sportsbook|slots?|jackpot|poker|roulette|"
    r"blackjack|lottery|wager|odds|bookmaker)\b"
    r"|(?:博彩|赌场|娱乐城|下注|投注|开奖|棋牌|老虎机|百家乐|彩票|赔率)"
)

CRYPTO_SCAM_RE = re.compile(
    r"(?i)\b(?:crypto|bitcoin|btc|ethereum|eth|usdt|airdrop|token|wallet|defi|"
    r"web3|nft|staking|mining|exchange|trading\s+signal|pump|presale)\b"
    r"|(?:空投|钱包|币圈|虚拟币|加密货币|挖矿|合约|交易所|链游)"
)

FAKE_INVESTMENT_RE = re.compile(
    r"(?i)\b(?:investment|invest|forex|binary|roi|profit|returns?|passive\s+income|"
    r"double\s+your\s+money|guaranteed\s+(?:profit|returns?)|risk[-\s]*free|"
    r"financial\s+freedom|copy\s+trading)\b"
    r"|(?:投资|理财|稳赚|收益|回报|翻倍|无风险|跟单|外汇|财务自由)"
)

ADVERTISING_TERMS = ("advertisement", "sponsored", "promotion", "discount", "giveaway", "广告", "推广", "促销", "优惠")
GAMBLING_TERMS = ("casino", "gambling", "betting", "jackpot", "slots", "lottery", "博彩", "赌场", "下注", "投注", "开奖")
CRYPTO_TERMS = ("crypto", "bitcoin", "ethereum", "usdt", "airdrop", "wallet", "token", "defi", "nft", "空投", "钱包", "币圈", "虚拟币")
INVESTMENT_TERMS = ("investment", "forex", "profit", "returns", "passiveincome", "doubleyourmoney", "投资", "理财", "稳赚", "收益", "翻倍")

SENSITIVE_CONTENT_RE = re.compile(
    r"(?i)\b(?:"
    r"porn|porno|xxx|nsfw|nude|nudes|naked|sex|sexy|sexual|adult\s+video|"
    r"hookup|escort|prostitut(?:e|ion)|onlyfans|cocaine|meth|heroin|"
    r"weed|marijuana|drug|gun|weapon"
    r")\b"
    r"|(?:色情|成人|成人视频|裸聊|裸照|裸|性爱|做爱|约炮|黄片|无码|淫|私房|偷拍视频)"
    r"|(?:幼女|初中生|小学生|未成年|未满|未滿|萝莉|蘿莉|破处|破處|处女|處女)"
    r"|(?:私密照|手机相册|手機相冊|邻居小女孩|鄰居小女孩|\d{1,2}\s*岁|\d{1,2}\s*歲)"
    r"|(?:来个弟弟|來個弟弟|陪姐姐聊聊天|有喜欢的|有喜歡的)"
    r"|(?:សិច|អាសអាភាស|អាក្រាត|រូបអាក្រាត)"
)

OBFUSCATED_SENSITIVE_RE = re.compile(
    r"(?i)(?:"
    r"\bs\W*e\W*x\b|"
    r"\bp\W*o\W*r\W*n\b|"
    r"\bn\W*s\W*f\W*w\b|"
    r"\bn\W*u\W*d\W*e\W*s?\b|"
    r"\bx\W*x\W*x\b|"
    r"\ba\W*d\W*u\W*l\W*t\W*v\W*i\W*d\W*e\W*o\b"
    r")"
)

SENSITIVE_COMPACT_PHRASES = (
    "child porn",
    "child abuse",
    "child sexual",
    "sexual content",
    "adult video",
    "underage sex",
    "minor sex",
    "teen sex",
    "看幼女",
    "初中生破处",
    "分享12岁",
    "邻居小女孩",
    "手机相册私密照",
    "陪姐姐聊聊天",
)


@dataclass(frozen=True)
class SpamDecision:
    delete: bool
    reason: str
    punish: bool = False


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = ZERO_WIDTH_RE.sub("", normalized)
    return normalized.lower()


def compact_text(value: str) -> str:
    return "".join(char for char in normalize_text(value) if char.isalnum())


def message_text(message) -> str:
    parts = []
    if getattr(message, "message", None):
        parts.append(message.message)
    if getattr(message, "raw_text", None) and message.raw_text not in parts:
        parts.append(message.raw_text)
    return "\n".join(parts)


def text_ngrams(value: str, size: int = 3) -> set[str]:
    compacted = compact_text(value)
    if not compacted:
        return set()
    if len(compacted) <= size:
        return {compacted}
    return {compacted[index : index + size] for index in range(len(compacted) - size + 1)}


def text_similarity(left: str, right: str) -> float:
    left_grams = text_ngrams(left)
    right_grams = text_ngrams(right)
    if not left_grams or not right_grams:
        return 0.0
    overlap = len(left_grams & right_grams)
    return (2 * overlap) / (len(left_grams) + len(right_grams))


def keyword_matches(keyword: str, normalized: str, compacted: str) -> bool:
    normalized_keyword = normalize_text(keyword)
    compact_keyword = compact_text(keyword)
    is_short_ascii = normalized_keyword.isascii() and normalized_keyword.isalnum() and len(normalized_keyword) <= 4

    if is_short_ascii:
        return bool(re.search(rf"\b{re.escape(normalized_keyword)}\b", normalized))

    return normalized_keyword in normalized or compact_keyword in compacted


def has_hidden_or_entity_link(message) -> bool:
    for entity in getattr(message, "entities", None) or []:
        if isinstance(entity, (MessageEntityUrl, MessageEntityTextUrl)):
            return True
    return False


def has_suspicious_link(text: str) -> bool:
    links = URL_RE.findall(text or "")
    if not links:
        return False
    return any(SUSPICIOUS_LINK_RE.search(link) for link in links) or len(links) >= 2


def promotion_score(text: str) -> int:
    normalized = normalize_text(text)
    compacted = compact_text(text)
    score = 0

    for keyword in PROMOTION_KEYWORDS:
        if keyword_matches(keyword, normalized, compacted):
            score += 1

    for phrase in PROMOTION_PHRASES:
        if compact_text(phrase) in compacted:
            score += 2

    if ADVERTISING_RE.search(normalized) or ADVERTISING_RE.search(compacted):
        score += 3
    elif any(compact_text(term) in compacted for term in ADVERTISING_TERMS):
        score += 3

    if GAMBLING_RE.search(normalized) or GAMBLING_RE.search(compacted):
        score += 4
    elif any(compact_text(term) in compacted for term in GAMBLING_TERMS):
        score += 4

    if CRYPTO_SCAM_RE.search(normalized) or CRYPTO_SCAM_RE.search(compacted):
        score += 3
    elif any(compact_text(term) in compacted for term in CRYPTO_TERMS):
        score += 3

    if FAKE_INVESTMENT_RE.search(normalized) or FAKE_INVESTMENT_RE.search(compacted):
        score += 3
    elif any(compact_text(term) in compacted for term in INVESTMENT_TERMS):
        score += 3

    if TELEGRAM_INVITE_RE.search(text or ""):
        score += 4

    if has_suspicious_link(text):
        score += 2

    lines = [compact_text(line) for line in text.splitlines() if compact_text(line)]
    if len(lines) >= 3 and len(lines) - len(set(lines)) >= 1:
        score += 2

    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    if chinese_chars >= 12 and score >= 1:
        score += 1

    return score


def has_sensitive_content(text: str) -> bool:
    if not text:
        return False

    normalized = normalize_text(text)
    compacted = compact_text(text)

    if SENSITIVE_CONTENT_RE.search(normalized) or SENSITIVE_CONTENT_RE.search(compacted):
        return True
    if OBFUSCATED_SENSITIVE_RE.search(normalized):
        return True
    return any(compact_text(phrase) in compacted for phrase in SENSITIVE_COMPACT_PHRASES)


def is_forwarded(message) -> bool:
    return bool(getattr(message, "fwd_from", None))


def normalized_peer_id(value) -> int | None:
    if value is None:
        return None
    try:
        real_id, _ = utils.resolve_id(int(value))
        return real_id
    except Exception:
        try:
            return abs(int(value))
        except Exception:
            return None


def is_channel_post(message) -> bool:
    return ALLOW_CHANNEL_POSTS and bool(getattr(message, "post", False))


def message_peer_id(message, attr: str) -> int | None:
    peer = getattr(message, attr, None)
    if peer is None:
        return None

    for field in ("user_id", "channel_id", "chat_id"):
        value = getattr(peer, field, None)
        if value is not None:
            return value

    return normalized_peer_id(peer)


def message_sender_id(message) -> int | None:
    direct_sender_id = getattr(message, "sender_id", None)
    if direct_sender_id is not None:
        return normalized_peer_id(direct_sender_id)
    return normalized_peer_id(message_peer_id(message, "from_id"))


def trusted_channel_id(channel_id: int | None) -> bool:
    if channel_id is None:
        return False
    if not TRUSTED_CHANNEL_IDS:
        return True
    normalized = normalized_peer_id(channel_id)
    return channel_id in TRUSTED_CHANNEL_IDS or normalized in TRUSTED_CHANNEL_IDS


def forward_header_channel_id(message) -> int | None:
    forward = getattr(message, "fwd_from", None)
    if forward is None:
        return None

    for attr in ("from_id", "saved_from_peer", "saved_from_id"):
        peer_id = message_peer_id(forward, attr)
        if peer_id is not None:
            return normalized_peer_id(peer_id)

    return None


def is_linked_channel_forward(message) -> bool:
    if not ALLOW_LINKED_CHANNEL_FORWARDS or message is None:
        return False

    forward = getattr(message, "fwd_from", None)
    if forward is None:
        return False

    channel_id = forward_header_channel_id(message)
    if TRUSTED_CHANNEL_IDS:
        return trusted_channel_id(channel_id)

    return (
        channel_id is not None
        or bool(getattr(forward, "channel_post", None))
        or bool(getattr(forward, "post_author", None))
    )


def is_anonymous_admin_comment(chat_id: int, sender) -> bool:
    if not ALLOW_ANONYMOUS_ADMIN_COMMENTS or sender is None:
        return False
    return normalized_peer_id(getattr(sender, "id", None)) == normalized_peer_id(chat_id)


def is_anonymous_admin_message(chat_id: int, message) -> bool:
    if not ALLOW_ANONYMOUS_ADMIN_COMMENTS or message is None:
        return False

    chat_peer_id = normalized_peer_id(chat_id)
    return (
        normalized_peer_id(message_sender_id(message)) == chat_peer_id
        or normalized_peer_id(message_peer_id(message, "from_id")) == chat_peer_id
        or bool(getattr(message, "post_author", None))
        or is_linked_channel_forward(message)
    )


def is_channel_identity_comment(sender) -> bool:
    if not ALLOW_CHANNEL_IDENTITY_COMMENTS or sender is None:
        return False
    return bool(getattr(sender, "broadcast", False))


def is_channel_identity_message(message) -> bool:
    if not ALLOW_CHANNEL_IDENTITY_COMMENTS or message is None:
        return False

    from_id = getattr(message, "from_id", None)
    return from_id is not None and hasattr(from_id, "channel_id")


def base_spam_decision(message) -> SpamDecision:
    text = message_text(message)

    if is_forwarded(message):
        return SpamDecision(True, "forwarded-message", True)

    if has_sensitive_content(text):
        return SpamDecision(True, "sensitive-content", True)

    if has_hidden_or_entity_link(message):
        return SpamDecision(True, "hidden-or-entity-link", True)

    if TELEGRAM_INVITE_RE.search(text or ""):
        return SpamDecision(True, "telegram-invite-link", True)

    if has_suspicious_link(text):
        return SpamDecision(True, "suspicious-url", True)

    if URL_RE.search(text or ""):
        return SpamDecision(True, "link", False)

    score = promotion_score(text)
    if score >= 3:
        return SpamDecision(True, f"promotion-score-{score}", True)

    return SpamDecision(False, "clean")


class RateMemory:
    def __init__(self):
        self.user_times: dict[tuple[int, int], Deque[float]] = defaultdict(deque)
        self.user_messages: dict[tuple[int, int], Deque[tuple[float, int]]] = defaultdict(deque)
        self.chat_similar_messages: dict[int, Deque[tuple[float, int, int, str]]] = defaultdict(deque)

    @staticmethod
    def prune_times(values: Deque[float], cutoff: float) -> None:
        while values and values[0] < cutoff:
            values.popleft()

    @staticmethod
    def prune_messages(values: Deque[tuple[float, int]], cutoff: float) -> None:
        while values and values[0][0] < cutoff:
            values.popleft()

    def remember(self, chat_id: int, user_id: int, message_id: int, text: str) -> SpamDecision:
        now = time.monotonic()
        user_key = (chat_id, user_id)

        times = self.user_times[user_key]
        times.append(now)
        self.prune_times(times, now - FLOOD_WINDOW_SECONDS)

        messages = self.user_messages[user_key]
        messages.append((now, message_id))
        self.prune_messages(messages, now - RECENT_MESSAGE_TTL)

        if len(times) >= FLOOD_MESSAGE_LIMIT:
            return SpamDecision(True, f"flood-{len(times)}-messages", True)

        similar_messages = self.chat_similar_messages[chat_id]
        self.prune_messages(similar_messages, now - SIMILAR_WINDOW_SECONDS)
        while len(similar_messages) > RECENT_SIMILAR_LIMIT:
            similar_messages.popleft()

        compacted = compact_text(text)
        should_compare_similarity = (
            len(compacted) >= 20
            and (
                promotion_score(text) >= 1
                or has_suspicious_link(text)
                or bool(TELEGRAM_INVITE_RE.search(text or ""))
                or len(re.findall(r"[\u4e00-\u9fff]", text)) >= 8
            )
        )

        if should_compare_similarity:
            similar_count = 1
            for _, _, _, previous_text in similar_messages:
                if text_similarity(compacted, previous_text) >= SIMILARITY_THRESHOLD:
                    similar_count += 1

            similar_messages.append((now, user_id, message_id, compacted))
            if similar_count >= SIMILAR_MESSAGE_LIMIT:
                return SpamDecision(True, f"similar-promo-{similar_count}", True)
        elif compacted:
            similar_messages.append((now, user_id, message_id, compacted))

        return SpamDecision(False, "clean")

    def recent_message_ids(self, chat_id: int, user_id: int) -> list[int]:
        now = time.monotonic()
        messages = self.user_messages[(chat_id, user_id)]
        self.prune_messages(messages, now - RECENT_MESSAGE_TTL)
        return [message_id for _, message_id in messages]


class AdminCache:
    def __init__(self, client: TelegramClient):
        self.client = client
        self.cache: dict[tuple[int, int], tuple[float, bool]] = {}

    async def is_admin_or_whitelisted(self, chat_id: int, sender, message=None, chat=None) -> bool:
        if message is not None and is_channel_post(message):
            logger.debug("allow channel post chat=%s msg=%s", chat_id, getattr(message, "id", None))
            return True

        if is_anonymous_admin_comment(chat_id, sender) or is_anonymous_admin_message(chat_id, message):
            logger.debug("allow anonymous admin chat=%s msg=%s", chat_id, getattr(message, "id", None))
            return True

        if is_channel_identity_comment(sender) or is_channel_identity_message(message):
            logger.debug("allow channel identity chat=%s msg=%s", chat_id, getattr(message, "id", None))
            return True

        user_id = getattr(sender, "id", None) if sender is not None else None
        if user_id is None and message is not None:
            user_id = message_sender_id(message)

        username = (getattr(sender, "username", "") or "").lower()

        if user_id in WHITELIST_IDS or username in WHITELIST_USERNAMES:
            return True
        if user_id is None:
            return False

        key = (normalized_peer_id(chat_id) or chat_id, normalized_peer_id(user_id) or user_id)
        now = time.monotonic()
        cached = self.cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

        try:
            permissions = await self.client.get_permissions(chat or chat_id, sender or user_id)
            is_admin = bool(
                getattr(permissions, "is_admin", False)
                or getattr(permissions, "is_creator", False)
                or getattr(permissions, "post_messages", False)
            )
        except (ChatAdminRequiredError, UserAdminInvalidError):
            is_admin = False
        except FloodWaitError as exc:
            await sleep_for_flood_wait(exc)
            return False
        except Exception as exc:
            logger.warning("admin check failed chat=%s user=%s error=%s", chat_id, user_id, exc)
            is_admin = False

        cache_ttl = ADMIN_CACHE_TTL if is_admin else min(ADMIN_CACHE_TTL, 30)
        self.cache[key] = (now + cache_ttl, is_admin)
        return is_admin


class DeleteQueue:
    def __init__(self, client: TelegramClient):
        self.client = client
        self.queue: asyncio.Queue[tuple[int, int, str]] = asyncio.Queue(maxsize=10000)

    async def start(self) -> None:
        for worker_id in range(DELETE_WORKERS):
            asyncio.create_task(self.worker(worker_id), name=f"delete-worker-{worker_id}")

    async def put(self, chat_id: int, message_id: int, reason: str) -> None:
        try:
            self.queue.put_nowait((chat_id, message_id, reason))
        except asyncio.QueueFull:
            logger.error("delete queue full; deleting synchronously chat=%s msg=%s", chat_id, message_id)
            await safe_delete_messages(self.client, chat_id, [message_id], reason)

    async def put_many(self, chat_id: int, message_ids: list[int], reason: str) -> None:
        for message_id in set(message_ids):
            await self.put(chat_id, message_id, reason)

    async def worker(self, worker_id: int) -> None:
        while True:
            chat_id, message_id, reason = await self.queue.get()
            batch = [(message_id, reason)]
            deadline = time.monotonic() + DELETE_BATCH_DELAY

            while len(batch) < DELETE_BATCH_SIZE:
                timeout = max(0, deadline - time.monotonic())
                if timeout == 0:
                    break
                try:
                    next_chat_id, next_message_id, next_reason = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=timeout,
                    )
                except asyncio.TimeoutError:
                    break

                if next_chat_id == chat_id:
                    batch.append((next_message_id, next_reason))
                else:
                    await self.put(next_chat_id, next_message_id, next_reason)
                    break

            message_ids = [item[0] for item in batch]
            reasons = ",".join(sorted(set(item[1] for item in batch)))
            await safe_delete_messages(self.client, chat_id, message_ids, reasons)

            for _ in batch:
                self.queue.task_done()


async def sleep_for_flood_wait(exc: FloodWaitError) -> None:
    delay = min(int(getattr(exc, "seconds", 1)), MAX_FLOOD_WAIT)
    logger.warning("telegram flood wait: sleeping %s seconds", delay)
    await asyncio.sleep(delay)


async def safe_delete_messages(client: TelegramClient, chat_id: int, message_ids: list[int], reason: str) -> None:
    if not message_ids:
        return

    try:
        await client.delete_messages(chat_id, list(set(message_ids)), revoke=True)
        logger.info("deleted chat=%s count=%s reason=%s ids=%s", chat_id, len(set(message_ids)), reason, message_ids[:8])
    except FloodWaitError as exc:
        await sleep_for_flood_wait(exc)
        await safe_delete_messages(client, chat_id, message_ids, reason)
    except ChatAdminRequiredError:
        logger.error("missing delete permission chat=%s reason=%s", chat_id, reason)
    except Exception as exc:
        logger.exception("delete failed chat=%s reason=%s error=%s", chat_id, reason, exc)


async def punish_sender(client: TelegramClient, chat_id: int, sender, decision: SpamDecision) -> None:
    if sender is None or not decision.punish:
        return

    user_id = getattr(sender, "id", None)
    if user_id is None:
        return

    action = BOT_SPAM_ACTION if getattr(sender, "bot", False) else USER_SPAM_ACTION
    if action not in {"ban", "mute"}:
        return

    try:
        if action == "ban":
            await client.edit_permissions(chat_id, user_id, view_messages=False)
        else:
            await client.edit_permissions(
                chat_id,
                user_id,
                until_date=int(time.time()) + MUTE_SECONDS,
                send_messages=False,
                send_media=False,
                send_stickers=False,
                send_gifs=False,
                send_games=False,
                send_inline=False,
                embed_link_previews=False,
            )
        logger.info("%sed user=%s chat=%s reason=%s", action, user_id, chat_id, decision.reason)
    except FloodWaitError as exc:
        await sleep_for_flood_wait(exc)
        await punish_sender(client, chat_id, sender, decision)
    except (ChatAdminRequiredError, UserAdminInvalidError):
        logger.warning("cannot %s user=%s chat=%s: admin rights missing or target admin", action, user_id, chat_id)
    except Exception as exc:
        logger.exception("failed to %s user=%s chat=%s error=%s", action, user_id, chat_id, exc)


async def main() -> None:
    if not API_ID or not API_HASH or not BOT_TOKEN:
        raise RuntimeError("Set API_ID, API_HASH, and BOT_TOKEN environment variables.")

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)

    memory = RateMemory()
    admin_cache = AdminCache(client)
    delete_queue = DeleteQueue(client)
    await delete_queue.start()

    @client.on(events.NewMessage(incoming=True))
    async def on_new_message(event):
        message = event.message
        chat_id = event.chat_id

        if ALLOW_CHANNEL_POSTS and getattr(event, "is_channel", False) and not getattr(event, "is_group", False):
            return

        sender = await event.get_sender()
        chat = getattr(event, "chat", None)
        if chat is None:
            try:
                chat = await event.get_chat()
            except Exception as exc:
                logger.warning("failed to load chat entity chat=%s msg=%s error=%s", chat_id, message.id, exc)

        if await admin_cache.is_admin_or_whitelisted(chat_id, sender, message, chat):
            logger.debug("allowed admin/whitelist message chat=%s msg=%s", chat_id, message.id)
            return

        user_id = getattr(sender, "id", None) or message_sender_id(message) or 0

        text = message_text(message)
        decision = base_spam_decision(message)
        rate_decision = memory.remember(chat_id, user_id, message.id, text)

        if rate_decision.delete:
            decision = rate_decision

        if not decision.delete:
            return

        if getattr(sender, "bot", False) and not decision.punish:
            decision = SpamDecision(True, decision.reason, True)

        logger.info(
            "queue delete chat=%s msg=%s sender=%s message_sender=%s from_id=%s post=%s reason=%s",
            chat_id,
            message.id,
            getattr(sender, "id", None),
            message_sender_id(message),
            getattr(message, "from_id", None),
            getattr(message, "post", None),
            decision.reason,
        )
        await delete_queue.put(chat_id, message.id, decision.reason)

        if decision.reason.startswith("flood"):
            await delete_queue.put_many(
                chat_id,
                memory.recent_message_ids(chat_id, user_id),
                f"cleanup-{decision.reason}",
            )

        asyncio.create_task(punish_sender(client, chat_id, sender, decision))

    me = await client.get_me()
    logger.info("anti-spam bot started as @%s", getattr(me, "username", None) or me.id)
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
