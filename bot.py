import os
import re
import logging
import unicodedata
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

URL_RE = re.compile(
    r"(?i)\b(?:https?://|www\.)\S+\b"
    r"|(?<!@)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?:/\S*)?\b"
    r"|\bt\.me/\S+\b"
    r"|\btelegram\.me/\S+\b"
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
    "成人视频",
)

STRONG_PROMOTION_RE = re.compile(
    r"(?i)\b(?:"
    r"limited\s*time|free\s+trial|sign\s*up|join\s+now|click\s+here|"
    r"earn\s+money|make\s+money|guaranteed\s+profit|"
    r"casino|betting|airdrop|crypto|usdt|whatsapp|telegram"
    r")\b"
    r"|(?:点击|免费|限时|领取|加群|私聊|博彩|赌场|下注|开奖|偷拍|直播)"
)

PROMOTION_COMPACT_PHRASES = (
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
)

SENSITIVE_CONTENT_RE = re.compile(
    r"(?i)\b(?:"
    r"porn|porno|xxx|nsfw|nude|nudes|naked|sex|sexy|sexual|adult\s+video|"
    r"hookup|escort|prostitut(?:e|ion)|onlyfans|blowjob|handjob|anal|boobs|"
    r"pussy|dick|cock|cocaine|meth|heroin|weed|marijuana|drug|gun|weapon"
    r")\b"
    r"|(?:色情|成人|成人视频|裸聊|裸照|裸|性爱|做爱|约炮|黄片|无码|淫|私房|国产自拍|偷拍视频)"
    r"|(?:幼女|初中生|小学生|未成年|未满|未滿|萝莉|蘿莉|破处|破處|处女|處女)"
    r"|(?:私密照|手机相册|手機相冊|邻居小女孩|鄰居小女孩|\d{1,2}\s*岁|\d{1,2}\s*歲)"
    r"|(?:点头像|點頭像|进简介群|進簡介群|简介群|簡介群|进主页|進主頁|主页看|主頁看)"
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
    "点头像进简介群",
    "进简介群",
    "看幼女",
    "初中生破处",
    "分享12岁",
    "邻居小女孩",
    "手机相册私密照",
    "有喜欢的进主页看",
    "进主页看",
    "主页看",
    "来个弟弟",
    "陪姐姐聊聊天",
)

ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u2060]")

CLICKABLE_ENTITY_TYPES = {
    "url",
    "text_link",
    "mention",
    "text_mention",
    "email",
    "phone_number",
}

REMOVABLE_ENTITY_TYPES = {
    "url",
    "text_link",
    "mention",
    "text_mention",
    "email",
    "phone_number",
}

def has_clickable_entities(entities) -> bool:
    if not entities:
        return False
    for entity in entities:
        if entity.type in CLICKABLE_ENTITY_TYPES:
            return True
    return False

def has_link_buttons(reply_markup) -> bool:
    inline_keyboard = getattr(reply_markup, "inline_keyboard", None)
    if not inline_keyboard:
        return False

    for row in inline_keyboard:
        for button in row:
            if (
                getattr(button, "url", None)
                or getattr(button, "login_url", None)
                or getattr(button, "web_app", None)
            ):
                return True
    return False

def utf16_to_py_index(text: str, offset: int) -> int:
    encoded = text.encode("utf-16-le")
    return len(encoded[: offset * 2].decode("utf-16-le"))

def strip_links(value: str, entities=None) -> str:
    if not value:
        return ""

    cleaned = value
    ranges = []
    for entity in entities or []:
        if entity.type in REMOVABLE_ENTITY_TYPES:
            start = utf16_to_py_index(value, entity.offset)
            end = utf16_to_py_index(value, entity.offset + entity.length)
            ranges.append((start, end))

    for start, end in sorted(ranges, reverse=True):
        cleaned = cleaned[:start] + cleaned[end:]

    cleaned = URL_RE.sub("", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)

    lines = [line.strip() for line in cleaned.splitlines()]
    return "\n".join(line for line in lines if line).strip()

def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = ZERO_WIDTH_RE.sub("", normalized)
    return normalized.lower()

def compact_text(value: str) -> str:
    return "".join(char for char in normalize_text(value) if char.isalnum())

def message_text(msg) -> str:
    if not msg:
        return ""
    return "\n".join(part for part in (msg.text or "", msg.caption or "") if part)

def count_promotion_keywords(text: str) -> int:
    normalized = normalize_text(text)
    compacted = compact_text(text)

    return sum(
        1
        for keyword in PROMOTION_KEYWORDS
        if normalize_text(keyword) in normalized or compact_text(keyword) in compacted
    )

def has_repeated_promo_lines(text: str) -> bool:
    lines = [compact_text(line) for line in text.splitlines() if compact_text(line)]
    if len(lines) < 3:
        return False

    repeated_lines = len(lines) - len(set(lines))
    return repeated_lines >= 1 and count_promotion_keywords(text) >= 1

def message_looks_promotional(msg) -> bool:
    text = message_text(msg)
    if not text:
        return False

    normalized = normalize_text(text)
    compacted = compact_text(text)
    keyword_hits = count_promotion_keywords(text)

    if keyword_hits >= 2:
        return True

    if STRONG_PROMOTION_RE.search(normalized) or STRONG_PROMOTION_RE.search(compacted):
        return True

    if any(compact_text(phrase) in compacted for phrase in PROMOTION_COMPACT_PHRASES):
        return True

    if has_repeated_promo_lines(text):
        return True

    return False

def message_has_sensitive_content(msg) -> bool:
    text = message_text(msg)
    if not text:
        return False

    normalized = normalize_text(text)
    compacted = compact_text(text)

    if SENSITIVE_CONTENT_RE.search(normalized) or SENSITIVE_CONTENT_RE.search(compacted):
        return True

    if OBFUSCATED_SENSITIVE_RE.search(normalized):
        return True

    return any(compact_text(phrase) in compacted for phrase in SENSITIVE_COMPACT_PHRASES)

def message_is_forwarded(msg) -> bool:
    return bool(
        getattr(msg, "forward_origin", None)
        or getattr(msg, "forward_from", None)
        or getattr(msg, "forward_from_chat", None)
        or getattr(msg, "forward_sender_name", None)
        or getattr(msg, "forward_date", None)
    )

def message_has_link(msg) -> bool:
    if not msg:
        return False

    text = msg.text or ""
    caption = msg.caption or ""

    if has_clickable_entities(msg.entities):
        return True

    if has_clickable_entities(msg.caption_entities):
        return True

    if has_link_buttons(msg.reply_markup):
        return True

    if text and URL_RE.search(text):
        return True

    if caption and URL_RE.search(caption):
        return True

    if message_is_forwarded(msg):
        return True

    return False

def message_should_be_filtered(msg) -> bool:
    return (
        message_has_link(msg)
        or message_looks_promotional(msg)
        or message_has_sensitive_content(msg)
    )

async def is_admin_message(msg, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if msg.chat.type == "channel":
        return True

    if msg.sender_chat is not None:
        return True

    if msg.from_user is None:
        return False

    try:
        member = await context.bot.get_chat_member(msg.chat_id, msg.from_user.id)
        return member.status in ("administrator", "creator")
    except Exception as e:
        logging.exception("Failed to check admin status: %s", e)
        return False

async def delete_link_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return

    if not message_should_be_filtered(msg):
        return

    if message_is_forwarded(msg):
        try:
            await context.bot.delete_message(
                chat_id=msg.chat_id,
                message_id=msg.message_id,
            )
            logging.info("Deleted forwarded message in chat %s", msg.chat_id)
        except Exception as e:
            logging.exception("Failed to delete forwarded message: %s", e)
        return

    if message_has_sensitive_content(msg):
        try:
            await context.bot.delete_message(
                chat_id=msg.chat_id,
                message_id=msg.message_id,
            )
            logging.info("Deleted sensitive message in chat %s", msg.chat_id)
        except Exception as e:
            logging.exception("Failed to delete sensitive message: %s", e)
        return

    if message_looks_promotional(msg):
        try:
            await context.bot.delete_message(
                chat_id=msg.chat_id,
                message_id=msg.message_id,
            )
            logging.info("Deleted promotional message in chat %s", msg.chat_id)
        except Exception as e:
            logging.exception("Failed to delete promotional message: %s", e)
        return

    if await is_admin_message(msg, context):
        logging.info("Allowed admin filtered-type message in chat %s", msg.chat_id)
        return

    if msg.chat.type == "channel":
        await clean_channel_post(msg, context)
        return

    try:
        await context.bot.delete_message(
            chat_id=msg.chat_id,
            message_id=msg.message_id,
        )
        logging.info("Deleted link/forward/promo/sensitive message in chat %s", msg.chat_id)
    except Exception as e:
        logging.exception("Failed to delete message: %s", e)

async def clean_channel_post(msg, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = strip_links(msg.text or "", msg.entities)
    caption = strip_links(msg.caption or "", msg.caption_entities)

    try:
        if msg.text is not None:
            if text:
                await context.bot.send_message(chat_id=msg.chat_id, text=text)
        else:
            await context.bot.copy_message(
                chat_id=msg.chat_id,
                from_chat_id=msg.chat_id,
                message_id=msg.message_id,
                caption=caption if msg.caption is not None else None,
                caption_entities=[],
            )

        await context.bot.delete_message(
            chat_id=msg.chat_id,
            message_id=msg.message_id,
        )
        logging.info("Cleaned channel post in chat %s", msg.chat_id)
    except Exception as e:
        logging.exception("Failed to clean channel post: %s", e)

def main():
    if not BOT_TOKEN:
        raise ValueError("Missing BOT_TOKEN environment variable")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Group / supergroup / discussion comments
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & ~filters.StatusUpdate.ALL,
            delete_link_messages,
        )
    )

    # Channel posts
    app.add_handler(
        MessageHandler(
            filters.UpdateType.CHANNEL_POSTS,
            delete_link_messages,
        )
    )

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
