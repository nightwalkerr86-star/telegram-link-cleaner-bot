TELEGRAM LINK CLEANER BOT — RENDER VERSION

This version is prepared for Render.com hosting.

WHAT YOU NEED
1) A Telegram bot token from @BotFather
2) Your bot added as Admin in your Telegram channel
3) A GitHub account
4) A Render account

BEFORE DEPLOYING
1) In Telegram, create your bot with @BotFather using /newbot
2) Copy the bot token
3) Add the bot to your channel as Admin
4) Give it these permissions:
   - Post Messages
   - Delete Messages

DEPLOY ON RENDER
1) Create a new GitHub repository
2) Upload all files from this folder into that repository
3) Log in to Render
4) Click New +
5) Choose Blueprint
6) Connect your GitHub repository
7) Render will detect render.yaml automatically
8) When asked for BOT_TOKEN, paste your BotFather token
9) Start the deploy

AFTER DEPLOYMENT
1) Wait for the worker to become Live
2) Forward a message into your Telegram channel
3) The bot should remove the forwarded source link and repost the content cleanly

IF IT DOESN'T WORK
- Check that the bot is Admin in the channel
- Check Post Messages permission is ON
- Check Delete Messages permission is ON
- Check BOT_TOKEN is correct in Render environment settings
- Check the deploy logs in Render
