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
)


def strip_links(text: str | None) -> str:
    if not text:
        return ""
    cleaned = URL_RE.sub("", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


async def clean_forwarded_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.channel_post or update.edited_channel_post
    if not msg:
        return

    if not msg.forward_origin:
        return

    chat_id = msg.chat_id

    try:
        if msg.text is not None:
            cleaned_text = strip_links(msg.text)
            if cleaned_text:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=cleaned_text,
                    disable_web_page_preview=True,
                    protect_content=True,
                )
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            return

        if msg.photo:
            cleaned_caption = strip_links(msg.caption)
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=msg.photo[-1].file_id,
                caption=cleaned_caption or None,
                protect_content=True,
            )
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            return

        if msg.video:
            cleaned_caption = strip_links(msg.caption)
            await context.bot.send_video(
                chat_id=chat_id,
                video=msg.video.file_id,
                caption=cleaned_caption or None,
                protect_content=True,
            )
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            return

        if msg.document:
            cleaned_caption = strip_links(msg.caption)
            await context.bot.send_document(
                chat_id=chat_id,
                document=msg.document.file_id,
                caption=cleaned_caption or None,
                protect_content=True,
            )
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            return

        if msg.audio:
            cleaned_caption = strip_links(msg.caption)
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=msg.audio.file_id,
                caption=cleaned_caption or None,
                protect_content=True,
            )
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            return

        if msg.animation:
            cleaned_caption = strip_links(msg.caption)
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=msg.animation.file_id,
                caption=cleaned_caption or None,
                protect_content=True,
            )
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            return

        if msg.voice:
            cleaned_caption = strip_links(msg.caption)
            await context.bot.send_voice(
                chat_id=chat_id,
                voice=msg.voice.file_id,
                caption=cleaned_caption or None,
                protect_content=True,
            )
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            return

        if msg.sticker:
            await context.bot.send_sticker(
                chat_id=chat_id,
                sticker=msg.sticker.file_id,
                protect_content=True,
            )
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            return

        await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=chat_id,
            message_id=msg.message_id,
            protect_content=True,
        )
        await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)

    except Exception as e:
        logging.exception("Error while cleaning forwarded post: %s", e)


def main():
    if not BOT_TOKEN:
        raise ValueError("Missing BOT_TOKEN environment variable")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(
        MessageHandler(filters.UpdateType.CHANNEL_POSTS, clean_forwarded_channel_post)
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
