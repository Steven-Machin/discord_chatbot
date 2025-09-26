# Discord Chatbot

A Discord bot showcasing clean architecture, persistence, and production-ready error handling.

## Getting Started
1. Create and activate a virtual environment (recommended).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables by copying `.env` and updating the values:
   ```env
   BOT_PREFIX=!
   TOKEN=your-token-here
   DB_PATH=data/bot.db
   ```
4. Apply database migrations (table creation is managed for you):
   ```bash
   python scripts/migrate.py
   ```
5. Launch the bot:
   ```bash
   python bot.py
   ```

## Working with Cogs
- Commands, events, and background tasks live in the `cogs/` package.
- Add a new feature by creating a `cogs/<feature>.py` file and exposing an `async def setup(bot)` function.
- The bot automatically discovers all cogs in the folder at startup.

## Persistence
- SQLite is used for state via the `core.database.DatabaseManager` helper.
- The `points` table tracks user balances for the `!points`, `!addpoints`, and `!leaderboard` commands.
- A background task records timestamps every six hours so `!lastsave` can report when maintenance last occurred.

## Error Handling & Logging
- A global error cog catches command failures, sends user-friendly embeds, and logs full tracebacks to `logs/errors.log`.
- Application logs stream to both the console and `logs/bot.log` for easy inspection.

## Coding Skills Demonstrated
- Asynchronous Discord command and task management using `discord.py`.
- Database persistence with SQLite, schema bootstrapping, and leaderboard queries.
- Clean project structure separating configuration, data access, and Discord cogs.
- Robust error handling with structured logging and graceful user messaging.
