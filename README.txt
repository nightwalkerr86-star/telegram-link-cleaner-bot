TELEGRAM ANTI-SPAM BOT

This bot uses Telethon to protect large Telegram groups from spam bots.

What it does:
- deletes spam messages quickly with async batch deletion
- detects fast flood spam
- deletes repeated messages
- detects hidden links, suspicious links, Chinese spam text, and promotional text
- detects sexual, adult, and abuse-related text in English, Chinese, and Khmer
- deletes forwarded messages from channels and bots
- bans spam bots automatically by default
- mutes non-admin spam users by default
- ignores group admins and whitelisted users
- logs deleted spam to anti_spam.log and the terminal
- catches Telegram FloodWait errors and waits safely

IMPORTANT TELEGRAM PERMISSIONS
Add the bot as an admin in every protected group and enable:
- Delete Messages
- Ban Users / Restrict Members

The bot cannot delete messages unless it is an admin.
The bot cannot ban or mute users unless it has restrict/ban permission.

STEP 1 - Create a bot token
1. Open Telegram.
2. Search for BotFather.
3. Send /newbot.
4. Copy the BOT_TOKEN.

STEP 2 - Get API_ID and API_HASH
1. Open https://my.telegram.org
2. Log in with your Telegram account.
3. Open API development tools.
4. Create an app.
5. Copy API_ID and API_HASH.

STEP 3 - Install dependencies
Open Terminal in this folder:

cd /Users/sokmean/Desktop/telegram-link-cleaner-bot-main
python3 -m pip install -r requirements.txt

STEP 4 - Set environment variables
Mac/Linux:

export API_ID="123456"
export API_HASH="your_api_hash"
export BOT_TOKEN="your_bot_token"

Optional settings:

export WHITELIST_IDS="123456789,987654321"
export WHITELIST_USERNAMES="trusteduser,anothertrusteduser"
export BOT_SPAM_ACTION="ban"
export USER_SPAM_ACTION="mute"
export FLOOD_WINDOW_SECONDS="10"
export FLOOD_MESSAGE_LIMIT="8"
export REPEAT_WINDOW_SECONDS="120"
export REPEAT_MESSAGE_LIMIT="3"
export MUTE_SECONDS="86400"
export LOG_LEVEL="INFO"

STEP 5 - Start the bot

python3 bot.py

DEPLOYMENT NOTES
- For Railway, set API_ID, API_HASH, and BOT_TOKEN in Variables.
- Start command: python bot.py
- Do not create a web domain. This is a worker bot, not a website.
- Keep BOT_TOKEN and API_HASH private.

TUNING FOR LARGE GROUPS
- Lower FLOOD_MESSAGE_LIMIT to catch floods faster.
- Raise DELETE_WORKERS if your group receives very heavy spam.
- Keep DELETE_BATCH_SIZE at 100 or lower.
- If Telegram sends FloodWait, the bot will wait and continue automatically.

DEFAULT ACTIONS
- Bots that send spam: banned.
- Normal users that send spam: muted.
- Admins and whitelist users: ignored.

Logs are written to:
anti_spam.log
