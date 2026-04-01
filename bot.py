import os
import re
import logging
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

CLICKABLE_ENTITY_TYPES = {
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

def message_has_link(msg) -> bool:
    if not msg:
        return False

    text = msg.text or ""
    caption = msg.caption or ""

    if has_clickable_entities(msg.entities):
        return True

    if has_clickable_entities(msg.caption_entities):
        return True

    if text and URL_RE.search(text):
        return True

    if caption and URL_RE.search(caption):
        return True

    if msg.forward_origin:
        return True

    return False

async def is_admin_or_channel_message(msg, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # Messages sent as channel / anonymous admin
    if msg.sender_chat is not None:
        return True

    # Normal user message: check admin status in this group
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

    if msg.from_user and msg.from_user.is_bot:
        return

    if not message_has_link(msg):
        return

    # Keep admin/channel messages
    if await is_admin_or_channel_message(msg, context):
        logging.info("Allowed admin/channel message in chat %s", msg.chat_id)
        return

    try:
        await context.bot.delete_message(
            chat_id=msg.chat_id,
            message_id=msg.message_id,
        )
        logging.info("Deleted user link message in chat %s", msg.chat_id)
    except Exception as e:
        logging.exception("Failed to delete message: %s", e)

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
