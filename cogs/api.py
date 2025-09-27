from __future__ import annotations

from typing import Dict, Optional, Tuple

import aiohttp
import discord
from discord.ext import commands


COINGECKO_API = "https://api.coingecko.com/api/v3"
OPENWEATHER_API = "https://api.openweathermap.org/data/2.5/weather"


class Api(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._session: Optional[aiohttp.ClientSession] = None
        self._coin_map: Optional[Dict[str, Tuple[str, str]]] = None

    async def cog_load(self) -> None:
        self._session = aiohttp.ClientSession()

    async def cog_unload(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise RuntimeError("HTTP session is not initialised yet.")
        return self._session

    async def _ensure_coin_map(self) -> None:
        if self._coin_map is not None:
            return

        url = f"{COINGECKO_API}/coins/list"
        try:
            async with self.session.get(
                url, timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                response.raise_for_status()
                payload = await response.json()
        except aiohttp.ClientError:
            self._coin_map = {}
            raise

        mapping: Dict[str, Tuple[str, str]] = {}
        for entry in payload:
            symbol = entry.get("symbol")
            coin_id = entry.get("id")
            name = entry.get("name")
            if not symbol or not coin_id:
                continue
            display_name = name.strip() if isinstance(name, str) else symbol.upper()
            mapping.setdefault(symbol.lower(), (coin_id, display_name))
        self._coin_map = mapping

    @commands.command(name="weather")
    async def weather(self, ctx: commands.Context, *, city: str) -> None:
        api_key = self.bot.config.openweather_api_key  # type: ignore[attr-defined]
        if not api_key:
            await ctx.send(
                "Set OPENWEATHER_KEY in your environment to enable weather lookups."
            )
            return

        params = {"q": city, "appid": api_key, "units": "metric"}
        try:
            async with self.session.get(
                OPENWEATHER_API, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 404:
                    await ctx.send("I couldn't find that city.")
                    return
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientError as exc:
            await ctx.send(
                "I couldn't reach the weather service. Please try again later."
            )
            self.bot.logger.exception("Weather lookup failed", exc_info=exc)  # type: ignore[attr-defined]
            return

        main = data.get("main", {})
        weather_info = data.get("weather", [{}])[0]
        wind = data.get("wind", {})

        embed = discord.Embed(
            title=f"Weather in {data.get('name', city).title()}",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Condition",
            value=weather_info.get("description", "Unknown").title(),
            inline=False,
        )
        embed.add_field(
            name="Temperature", value=f"{main.get('temp', '?')} C", inline=True
        )
        embed.add_field(
            name="Feels Like", value=f"{main.get('feels_like', '?')} C", inline=True
        )
        embed.add_field(
            name="Humidity", value=f"{main.get('humidity', '?')}%", inline=True
        )
        embed.add_field(name="Wind", value=f"{wind.get('speed', '?')} m/s", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="crypto")
    async def crypto(self, ctx: commands.Context, symbol: str) -> None:
        try:
            await self._ensure_coin_map()
        except aiohttp.ClientError as exc:
            await ctx.send(
                "I couldn't reach the crypto service. Please try again later."
            )
            self.bot.logger.exception("CoinGecko listing fetch failed", exc_info=exc)  # type: ignore[attr-defined]
            return

        if self._coin_map is None:
            await ctx.send("CoinGecko data is unavailable right now.")
            return

        mapping = self._coin_map.get(symbol.lower())
        if not mapping:
            await ctx.send("I don't recognise that cryptocurrency symbol.")
            return

        coin_id, coin_name = mapping

        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        }
        url = f"{COINGECKO_API}/simple/price"
        try:
            async with self.session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientError as exc:
            await ctx.send(
                "I couldn't reach the crypto service. Please try again later."
            )
            self.bot.logger.exception("Crypto lookup failed", exc_info=exc)  # type: ignore[attr-defined]
            return

        prices = data.get(coin_id)
        if not prices:
            await ctx.send("I couldn't find pricing data right now.")
            return

        price = prices.get("usd")
        change = prices.get("usd_24h_change")
        change_text = f"{change:+.2f}%" if isinstance(change, (int, float)) else "?"

        embed = discord.Embed(title=f"{coin_name}", color=discord.Color.gold())
        embed.add_field(name="Symbol", value=symbol.upper(), inline=True)
        embed.add_field(
            name="Price (USD)",
            value=f"${price:,.2f}" if isinstance(price, (int, float)) else "?",
            inline=True,
        )
        embed.add_field(name="24h Change", value=change_text, inline=True)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Api(bot))
