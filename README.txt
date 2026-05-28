TELEGRAM ANTI-SPAM BOT

This bot uses Telethon to protect large Telegram groups from spam bots.

What it does:
- deletes spam messages quickly with async batch deletion
- detects fast flood spam
- detects hidden links, suspicious links, Chinese spam text, and promotional text
- detects advertisement sentences, casino/gambling promotion, crypto scams, fake investment promotion, Telegram invite links, and suspicious URLs
- detects sexual, adult, and abuse-related text in English, Chinese, and Khmer
- detects similar promotional sentences even when words, spaces, or punctuation are slightly changed
- deletes forwarded messages from channels and bots
- bans spam bots automatically by default
- mutes non-admin spam users by default
- ignores group admins, channel broadcast posts, admin-style comments, and whitelisted users
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

export ADMIN_WHITELIST_IDS="123456789,987654321"
export WHITELIST_IDS="123456789,987654321"
export ADMIN_IDS="123456789,987654321"
export WHITELIST_USERNAMES="trusteduser,anothertrusteduser"
export BOT_SPAM_ACTION="ban"
export USER_SPAM_ACTION="mute"
export ALLOW_CHANNEL_POSTS="true"
export ALLOW_ANONYMOUS_ADMIN_COMMENTS="true"
export ALLOW_CHANNEL_IDENTITY_COMMENTS="true"
export ALLOW_LINKED_CHANNEL_FORWARDS="true"
export ALLOW_CHANNEL_MEDIA_WITH_LINKS="true"
export TRUSTED_CHANNEL_IDS="-1001234567890"
export ADMIN_CACHE_TTL="300"
export FLOOD_WINDOW_SECONDS="10"
export FLOOD_MESSAGE_LIMIT="8"
export SIMILAR_WINDOW_SECONDS="300"
export SIMILAR_MESSAGE_LIMIT="3"
export SIMILARITY_THRESHOLD="0.72"
export MUTE_SECONDS="86400"
export LOG_LEVEL="INFO"

The bot automatically checks Telegram permissions before running spam filters.
Group owners, admins, anonymous admins, and linked channel posts can post hidden
links, embedded links, button links, URL links, and promotional text without
deletion. Admin status is cached for ADMIN_CACHE_TTL seconds, then refreshed.
ADMIN_WHITELIST_IDS is optional and can be used as a manual emergency bypass
list if Telegram cannot resolve an admin identity. ADMIN_IDS still works as an
old alias.

STEP 5 - Start the bot

python3 bot.py

DEPLOYMENT NOTES
- For Railway, set API_ID, API_HASH, and BOT_TOKEN in Variables.
- Start command: python bot.py
- Do not create a web domain. This is a worker bot, not a website.
- Keep BOT_TOKEN and API_HASH private.

TUNING FOR LARGE GROUPS
- Lower FLOOD_MESSAGE_LIMIT to catch floods faster.
- Lower SIMILARITY_THRESHOLD to catch more changed promotional text.
- Raise SIMILARITY_THRESHOLD if it deletes too aggressively.
- Raise DELETE_WORKERS if your group receives very heavy spam.
- Keep DELETE_BATCH_SIZE at 100 or lower.
- If Telegram sends FloodWait, the bot will wait and continue automatically.

DEFAULT ACTIONS
- Bots that send spam: banned.
- Normal users that send spam: muted.
- Admins, channel posts, linked-channel discussion posts, anonymous admin posts, channel identity posts, and whitelist users: always ignored before filtering.

Logs are written to:
anti_spam.log
