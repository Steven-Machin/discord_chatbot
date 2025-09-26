# Discord Chatbot

A production-ready Discord bot demonstrating clean architecture, async workflows, and persistent state management.

## Features
- Config-driven startup with dotenv-based secrets management
- Modular cog system for commands, events, and background jobs
- SQLite persistence with a reusable async database helper
- Scheduled maintenance task that records timestamps every six hours
- Friendly error embeds plus structured logging to `logs/bot.log` and `logs/errors.log`

## Requirements
- Python 3.10+ (recommended)
- Discord bot token with the required gateway intents

## Project Structure
```
bot.py                 # Entry point; wires config, logging, database, and cogs
core/
  config.py            # Loads BOT_PREFIX, TOKEN, DB_PATH from the .env file
  database.py          # Async helpers for points balance and metadata storage
cogs/
  error_handler.py     # Global command error handling and logging
  points.py            # Points economy commands and leaderboard embeds
  system.py            # Background save task and !lastsave command
  *.py                 # Additional feature cogs (general, fun, moderation, ...)
scripts/
  migrate.py           # Lightweight migration runner that bootstraps the database
logs/                  # Created at runtime for bot and error logs
```

## Setup
1. (Optional) create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env` and configure the following values:
   ```env
   BOT_PREFIX=!
   TOKEN=your-token-here
   DB_PATH=data/bot.db
   ```
4. Initialise the database (tables are created automatically):
   ```bash
   python scripts/migrate.py
   ```
5. Run the bot:
   ```bash
   python bot.py
   ```

## Command Reference
- `!hello`, `!ping` — General status and latency checks
- `!points` — Display the caller's current balance via embed
- `!addpoints @user <amount>` — Admin-only; increments a member's balance
- `!leaderboard` — Show the top five balances in a rich embed
- `!lastsave` — Report when the scheduled background save last executed

## Persistence Workflow
- `core.database.DatabaseManager` wraps `sqlite3` calls with `asyncio.to_thread` for non-blocking access.
- The `points` table stores `user_id` and `balance` aggregates.
- The `metadata` table tracks maintenance timestamps (`last_save`).
- Running `python scripts/migrate.py` is safe to repeat; it ensures tables exist.

## Error Handling & Logging
- `cogs.error_handler.ErrorHandler` catches command failures, replies with user-friendly embeds, and logs tracebacks.
- Standard logs go to the console and `logs/bot.log`; errors additionally land in `logs/errors.log` for auditing.

## Extending the Bot
1. Create a new cog module under `cogs/` and implement `async def setup(bot)`.
2. Use `bot.database`, `bot.config`, and `bot.logger` to access shared services.
3. Restart the bot; `bot.py` auto-discovers and loads all cogs in the folder.

## Coding Skills Demonstrated
- Asynchronous command handling and background scheduling with `discord.py`
- Separation of concerns between configuration, persistence, and bot features
- SQLite persistence, migrations, and leaderboard queries
- Robust error handling with structured logging and user-facing feedback
