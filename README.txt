TELEGRAM FORWARD LINK CLEANER BOT

What this bot does:
- watches your Telegram channel
- if someone forwards a post into your channel, the bot removes the forwarded version
- reposts it as a clean post without the forwarded-source link
- removes normal links from the text/caption too

Important:
- This only works if the bot is an ADMIN in your channel.
- Give the bot permission to Post Messages and Delete Messages.
- It cannot remove links that are drawn inside an image itself.

STEP 1 — Create the bot
1. Open Telegram
2. Search for BotFather
3. Send /newbot
4. Choose a bot name
5. Choose a bot username
6. Copy the token BotFather gives you

STEP 2 — Add bot to your channel
1. Open your Telegram channel
2. Go to Administrators
3. Add your bot
4. Enable:
   - Post Messages
   - Delete Messages

STEP 3 — Run the bot
Option A: ask a freelancer/friend to deploy this folder
- Send them this whole folder or zip file
- Tell them: “Please deploy this Python Telegram bot and set BOT_TOKEN as an environment variable.”

Option B: run it on your own computer
1. Install Python 3
2. Open Terminal in this folder
3. Run:
   pip install -r requirements.txt
4. Set your token:
   Mac/Linux:
   export BOT_TOKEN="YOUR_BOT_TOKEN"

   Windows PowerShell:
   setx BOT_TOKEN "YOUR_BOT_TOKEN"
5. Start it:
   python bot.py

How to test:
- Forward a message into your channel
- The bot should delete the forwarded post
- Then repost the same content without the source link

If it does not work:
- check the bot is admin
- check Post Messages and Delete Messages are enabled
- check the token is correct
- make sure the bot is running
