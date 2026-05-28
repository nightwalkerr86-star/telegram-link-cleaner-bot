RAILWAY HOSTING STEPS

1. Create your Telegram bot with BotFather and copy BOT_TOKEN.

2. Get API_ID and API_HASH:
   - Go to https://my.telegram.org
   - Open API development tools
   - Create an app
   - Copy API_ID and API_HASH

3. Add the bot to your Telegram group as admin.
   Enable:
   - Delete Messages
   - Ban Users / Restrict Members

4. Upload this folder to GitHub:
   - bot.py
   - requirements.txt
   - railway.json
   - README.txt
   - README_RAILWAY.txt

5. In Railway, create a new project from your GitHub repo.

6. In Railway Variables, add:
   - API_ID = your Telegram API ID
   - API_HASH = your Telegram API hash
   - BOT_TOKEN = your BotFather token

7. Optional Railway Variables:
   - WHITELIST_IDS = comma-separated Telegram user IDs
   - ADMIN_IDS = comma-separated admin Telegram user IDs
   - WHITELIST_USERNAMES = comma-separated usernames without @
   - BOT_SPAM_ACTION = ban
   - USER_SPAM_ACTION = mute
   - ALLOW_CHANNEL_POSTS = true
   - ALLOW_ANONYMOUS_ADMIN_COMMENTS = true
   - ALLOW_CHANNEL_IDENTITY_COMMENTS = true
   - ALLOW_LINKED_CHANNEL_FORWARDS = true
   - ALLOW_CHANNEL_MEDIA_WITH_LINKS = true
   - TRUSTED_CHANNEL_IDS = comma-separated channel IDs, optional
   - FLOOD_MESSAGE_LIMIT = 8
   - SIMILAR_MESSAGE_LIMIT = 3
   - SIMILARITY_THRESHOLD = 0.72
   - LOG_LEVEL = INFO

8. Start command:
   python bot.py

IMPORTANT
- Do not generate a domain. This is a worker bot, not a website.
- Keep BOT_TOKEN and API_HASH private.
- If spam still appears, confirm the bot has Delete Messages and Ban Users permission.
