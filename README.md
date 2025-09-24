# Discord Chatbot

A minimal Discord bot built with `discord.py`.

## Prerequisites
- Python 3.10+ recommended
- A Discord bot token stored in `.env`

## Setup
1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Add your token to `.env`:
   ```env
   DISCORD_TOKEN=your-token-here
   ```

## Run the bot
```bash
python bot.py
```

The console will print a message once the bot is online. Invite the bot to your server and try `!hello` to confirm it responds: `Hey Steven! I'm alive 👋`.

## Keep your token safe
Never commit or share the `.env` file or your bot token publicly.
