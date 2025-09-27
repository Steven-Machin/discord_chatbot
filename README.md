# Discord Chatbot

A production-ready Discord bot demonstrating clean architecture, async workflows, API integrations, and persistent state management.

## Features
- Config-driven startup with dotenv-based secrets management
- Modular cog system for commands, events, and background tasks
- SQLite persistence for user points and per-guild configuration (prefix, welcome channel, role gating)
- Scheduled maintenance task plus rich logging to `logs/`
- Role-aware moderation commands with configurable moderator/administrator roles
- Live data commands: OpenWeather forecasts and CoinGecko cryptocurrency prices
- Slash command support (`/hello`) alongside classic prefix commands
- Automatic welcome embeds and message edit auditing to `logs/activity.log`

## Requirements
- Python 3.11+
- Discord bot token with the required gateway intents (Message Content + Server Members)
- OpenWeather API key if you plan to use the `!weather` command

## Project Structure
```
bot.py                 # Entry point; wires config, logging, database, and cogs
core/
  config.py            # Loads DISCORD_TOKEN, BOT_PREFIX, DB_PATH, and API keys from .env
  database.py          # Async helpers for points, guild settings, and metadata
cogs/
  api.py               # Weather and cryptocurrency commands backed by HTTP APIs
  general.py           # General utility commands and /hello slash command
  moderation.py        # Moderation actions with role-based authorization
  system.py            # Welcome events, message audit logging, and background save
  *.py                 # Additional feature cogs (fun, points, etc.)
scripts/
  migrate.py           # Lightweight migration runner that bootstraps the database
tests/
  test_database.py     # Pytest coverage for guild settings persistence
.github/workflows/
  ci.yml               # GitHub Actions workflow (flake8 + pytest)
Dockerfile             # Container image definition
docker-compose.yml     # Orchestrates the bot with volume mounts for data/logs
```

## Setup
1. **Clone the repository**
   ```bash
   git clone <your_repo_url> discord-chatbot
   cd discord-chatbot
   ```
2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```
3. **Activate the environment**
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. **Install dependencies inside the venv**
   ```bash
   pip install -r requirements.txt
   ```
5. **Configure environment variables**
   ```bash
   cp .env.example .env  # use `copy .env.example .env` on Windows PowerShell
   ```
   Edit `.env` and provide values for `DISCORD_TOKEN`, `OPENWEATHER_KEY`, and `DB_PATH`.
6. **Run the bot**
   ```bash
   python bot.py
   ```
   *(Optional)* Initialise the database ahead of time with `python scripts/migrate.py`.

## Command Reference
- `!hello`, `/hello` - Friendly greeting embeds
- `!ping` - Round-trip latency check
- `!setprefix <prefix>` - Update the guild prefix (aliases: `!prefix`)
- `!setwelcome [#channel]` - Choose which channel receives welcome embeds
- `!setmodrole [@role]` / `!setadminrole [@role]` - Configure moderation role requirements (omit the role to clear)
- `!weather <city>` - Fetch current conditions via OpenWeather
- `!crypto <symbol>` - Fetch USD pricing and 24h delta via CoinGecko (e.g. `!crypto btc`)
- `!points`, `!addpoints @user <amount>`, `!leaderboard` - Points economy commands
- `!lastsave` - Report when the scheduled background save last executed
- Standard moderation commands: `!kick`, `!ban`, `!unban`

### API command examples
```text
!weather London
!crypto btc
```

## Server Configuration & Permissions
- Prefixes, welcome channels, and moderation role requirements are stored per guild in SQLite (`guild_settings` table).
- When a moderator role is configured, users must hold that role (in addition to Discord permissions) to use `!kick`.
- When an administrator role is configured, users must hold it to use `!ban` and `!unban`.

## API Integrations
- **OpenWeather**: Supply `OPENWEATHER_KEY` in `.env`. The bot requests metric units; feel free to customise the cog for imperial conversions.
- **CoinGecko**: No API key required. The bot caches symbol-to-coin ID mappings on first use to keep lookups snappy.

## Event Automation
- New members trigger a welcome embed in the configured channel (or fall back to `#general` / the guild system channel).
- Edited messages are appended to `logs/activity.log` with before/after content for moderation review.

## Testing
Run the automated test suite (requires `pytest` and `pytest-asyncio`, already listed in `requirements.txt`):
```bash
python -m pytest
```
Tests cover the database manager's guild configuration workflow.

## Docker
Build and run the bot in a containerised environment:
```bash
docker compose build
docker compose up -d
```
Volumes map `./data` and `./logs` so state persists across restarts. Environment variables are sourced from `.env`.

## CI/CD
`.github/workflows/ci.yml` runs on every push and pull request:
1. Installs dependencies with pip caching.
2. Runs `flake8` for static analysis.
3. Executes the pytest suite.

## Persistence Workflow
- `core.database.DatabaseManager` wraps `sqlite3` calls with `asyncio.to_thread` for non-blocking access.
- Tables:
  - `points` (`user_id`, `balance`) - per-user currency balances
  - `metadata` (`key`, `value`) - background job timestamps (e.g. `last_save`)
  - `guild_settings` (`guild_id`, `prefix`, `welcome_channel_id`, `mod_role_id`, `admin_role_id`)
- Running `python scripts/migrate.py` is idempotent and safe to repeat.

## Coding Skills Demonstrated
- Asynchronous Discord bot architecture with cog-based modularity
- External API consumption with aiohttp and proper error handling
- Role-based authorization layered atop Discord permissions
- Containerisation (Docker) and automated CI (GitHub Actions)
- Robust persistence patterns with SQLite plus async-friendly coordination
