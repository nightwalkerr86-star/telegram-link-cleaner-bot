RAILWAY HOSTING STEPS

1. Create your bot with @BotFather in Telegram.
   - Send: /newbot
   - Save the BOT TOKEN.

2. Add your bot to your Telegram channel as Admin.
   Turn ON:
   - Post Messages
   - Delete Messages

3. Make a new GitHub repository.

4. Upload these files to the main folder of the repo:
   - bot.py
   - requirements.txt
   - README.txt
   - railway.json
   - README_RAILWAY.txt

5. Go to Railway and sign in.

6. Click New Project.

7. Choose Deploy from GitHub Repo.

8. Select your repository.

9. In Railway, open your service Variables tab.
   Add:
   - BOT_TOKEN = your BotFather token

10. Railway should read railway.json automatically.
    If it asks for a start command, use:
    python bot.py

11. Deploy.

12. Test by forwarding a post into your channel.
    The bot should delete the forwarded post and repost it without the source link.

IMPORTANT
- Do not generate a domain. This bot is not a website.
- Keep BOT_TOKEN only in Railway Variables, not inside bot.py.
