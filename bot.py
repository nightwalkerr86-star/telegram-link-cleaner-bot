import asyncio
import hashlib
import logging
import os
import re
import time
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

from telethon import TelegramClient, events
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
REPEAT_WINDOW_SECONDS = int(os.getenv("REPEAT_WINDOW_SECONDS", "120"))
REPEAT_MESSAGE_LIMIT = int(os.getenv("REPEAT_MESSAGE_LIMIT", "3"))
RECENT_MESSAGE_TTL = int(os.getenv("RECENT_MESSAGE_TTL", "180"))
MUTE_SECONDS = int(os.getenv("MUTE_SECONDS", "86400"))

BOT_SPAM_ACTION = os.getenv("BOT_SPAM_ACTION", "ban").lower()
USER_SPAM_ACTION = os.getenv("USER_SPAM_ACTION", "mute").lower()

WHITELIST_IDS = {
    int(value.strip())
    for value in os.getenv("WHITELIST_IDS", "").split(",")
    if value.strip().lstrip("-").isdigit()
}
WHITELIST_USERNAMES = {
    value.strip().lower().lstrip("@")
    for value in os.getenv("WHITELIST_USERNAMES", "").split(",")
    if value.strip()
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
    r"telegram|whatsapp|crypto|usdt"
    r")"
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
    "点头像进简介群",
    "进简介群",
    "进主页看",
    "主页看",
)

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


def stable_text_hash(text: str) -> str:
    compacted = compact_text(text)
    if not compacted:
        return ""
    return hashlib.blake2b(compacted.encode("utf-8"), digest_size=12).hexdigest()


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
        if normalize_text(keyword) in normalized or compact_text(keyword) in compacted:
            score += 1

    for phrase in PROMOTION_PHRASES:
        if compact_text(phrase) in compacted:
            score += 2

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


def base_spam_decision(message) -> SpamDecision:
    text = message_text(message)

    if is_forwarded(message):
        return SpamDecision(True, "forwarded-message", True)

    if has_sensitive_content(text):
        return SpamDecision(True, "sensitive-content", True)

    if has_hidden_or_entity_link(message):
        return SpamDecision(True, "hidden-or-entity-link", True)

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
        self.user_repeats: dict[tuple[int, int, str], Deque[float]] = defaultdict(deque)
        self.chat_repeats: dict[tuple[int, str], Deque[tuple[float, int]]] = defaultdict(deque)

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

        text_hash = stable_text_hash(text)
        if not text_hash:
            return SpamDecision(False, "clean")

        repeat_key = (chat_id, user_id, text_hash)
        repeats = self.user_repeats[repeat_key]
        repeats.append(now)
        self.prune_times(repeats, now - REPEAT_WINDOW_SECONDS)
        if len(repeats) >= REPEAT_MESSAGE_LIMIT:
            return SpamDecision(True, f"user-repeat-{len(repeats)}", True)

        chat_key = (chat_id, text_hash)
        chat_repeats = self.chat_repeats[chat_key]
        chat_repeats.append((now, message_id))
        self.prune_messages(chat_repeats, now - REPEAT_WINDOW_SECONDS)
        if len(chat_repeats) >= max(REPEAT_MESSAGE_LIMIT + 1, 4):
            return SpamDecision(True, f"chat-repeat-{len(chat_repeats)}", True)

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

    async def is_admin_or_whitelisted(self, chat_id: int, sender) -> bool:
        if sender is None:
            return False

        user_id = getattr(sender, "id", None)
        username = (getattr(sender, "username", "") or "").lower()

        if user_id in WHITELIST_IDS or username in WHITELIST_USERNAMES:
            return True
        if user_id is None:
            return False

        key = (chat_id, user_id)
        now = time.monotonic()
        cached = self.cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

        try:
            permissions = await self.client.get_permissions(chat_id, user_id)
            is_admin = bool(getattr(permissions, "is_admin", False))
        except (ChatAdminRequiredError, UserAdminInvalidError):
            is_admin = False
        except FloodWaitError as exc:
            await sleep_for_flood_wait(exc)
            return False
        except Exception as exc:
            logger.warning("admin check failed chat=%s user=%s error=%s", chat_id, user_id, exc)
            is_admin = False

        self.cache[key] = (now + ADMIN_CACHE_TTL, is_admin)
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
        sender = await event.get_sender()
        user_id = getattr(sender, "id", 0) or 0

        if await admin_cache.is_admin_or_whitelisted(chat_id, sender):
            return

        text = message_text(message)
        decision = base_spam_decision(message)
        rate_decision = memory.remember(chat_id, user_id, message.id, text)

        if rate_decision.delete:
            decision = rate_decision

        if not decision.delete:
            return

        if getattr(sender, "bot", False) and not decision.punish:
            decision = SpamDecision(True, decision.reason, True)

        await delete_queue.put(chat_id, message.id, decision.reason)

        if decision.reason.startswith("flood") or decision.reason.startswith("user-repeat"):
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
