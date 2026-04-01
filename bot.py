import os
import re
import logging
from telegram import Update, MessageEntity
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Catch normal links like:
# http://..., https://..., www...., example.com/path, t.me/...
URL_RE = re.compile(
    r"(?i)\b(?:https?://|www\.)\S+\b"
    r"|(?<!@)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?:/\S*)?\b"
)

def has_link_entities(entities) -> bool:
    if not entities:
        return False

    for entity in entities:
        if entity.type in (
            MessageEntity.URL,
            MessageEntity.TEXT_LINK,
        ):
            return True
    return False

def message_has_link(msg) -> bool:
    if not msg:
        return False

    text = msg.text or ""
    caption = msg.caption or ""

    # Check Telegram-detected URL entities
    if has_link_entities(msg.entities):
        return True
    if has_link_entities(msg.caption_entities):
        return True

    # Check raw text with regex
    if text and URL_RE.search(text):
        return True
    if caption and URL_RE.search(caption):
        return True

    # Delete forwarded messages too if you want zero-link policy
    if msg.forward_origin:
        return True

    return False

async def delete_link_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return

    # Ignore messages sent by bots
    if msg.from_user and msg.from_user.is_bot:
        return

    if not message_has_link(msg):
        return

    try:
        await context.bot.delete_message(
            chat_id=msg.chat_id,
            message_id=msg.message_id
        )
        logging.info("Deleted message with link in chat %s", msg.chat_id)
    except Exception as e:
        logging.exception("Failed to delete message: %s", e)

def main():
    if not BOT_TOKEN:
        raise ValueError("Missing BOT_TOKEN environment variable")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Group + supergroup messages (including discussion comments)
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & ~filters.StatusUpdate.ALL,
            delete_link_messages
        )
    )

    # Channel posts
    app.add_handler(
        MessageHandler(
            filters.UpdateType.CHANNEL_POSTS,
            delete_link_messages
        )
    )

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
