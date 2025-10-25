import discord
from discord.ext import commands
import random

from database import get_user, update_user

class Gacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gacha")
    async def gacha(self, ctx):
        """Buka 1 roll gacha"""
        user_data = await get_user(ctx.author.id)
        if not user_data or user_data["gacha_rolls"] <= 0:
            await ctx.send("Kamu tidak punya roll gacha! Naik level untuk dapat roll.")
            return

        new_rolls = user_data["gacha_rolls"] - 1
        await update_user(ctx.author.id, set_gacha_rolls=new_rolls)

        # Base rates
        base_20x = 0.0001
        base_10x = 0.0004
        base_8x = 0.001
        base_100k = 0.005
        base_4x = 0.0145
        base_2x = 0.08
        base_common = 0.899

        total_rare = base_20x + base_10x + base_8x + base_100k + base_4x + base_2x
        luck_bonus = min(user_data["luck"] * 0.001, 0.1)

        # Hitung cumulative dengan bonus proporsional
        def add_bonus(base):
            return base + (luck_bonus * (base / total_rare)) if total_rare > 0 else base

        cumulative = 0
        rand = random.random()

        # Roll gacha
        cumulative += add_bonus(base_20x)
        if rand < cumulative:
            await update_user(ctx.author.id, xp_20x=user_data["xp_20x"] + 1)
            item_msg = "🔥 **DIVINE (20x XP)** — Hanya bisa dipakai sekali!"
        else:
            cumulative += add_bonus(base_10x)
            if rand < cumulative:
                await update_user(ctx.author.id, xp_10x=user_data["xp_10x"] + 1)
                item_msg = "💫 **MYTHIC (10x XP)** — Hanya bisa dipakai sekali!"
            else:
                cumulative += add_bonus(base_8x)
                if rand < cumulative:
                    await update_user(ctx.author.id, xp_8x=user_data["xp_8x"] + 1)
                    item_msg = "🌈 **EPIC (8x XP)** — Hanya bisa dipakai sekali!"
                else:
                    cumulative += add_bonus(base_100k)
                    if rand < cumulative:
                        await update_user(ctx.author.id, currency=user_data["currency"] + 100000)
                        item_msg = "🌟 **LEGENDARY**: +Rp 100.000!"
                    else:
                        cumulative += add_bonus(base_4x)
                        if rand < cumulative:
                            await update_user(ctx.author.id, xp_4x=user_data["xp_4x"] + 1)
                            item_msg = "💎 **SUPER LANGKA (4x XP)** — Hanya bisa dipakai sekali!"
                        else:
                            cumulative += add_bonus(base_2x)
                            if rand < cumulative:
                                await update_user(ctx.author.id, xp_2x=user_data["xp_2x"] + 1)
                                item_msg = "✨ **LANGKA (2x XP)** — Hanya bisa dipakai sekali!"
                            else:
                                await update_user(ctx.author.id, currency=user_data["currency"] + 10000)
                                item_msg = "🎁 **Biasa**: +Rp 10.000"

        # Update quest progress
        quest_cog = self.bot.get_cog('Quests') # <<< Ambil COG yang benar
        if quest_cog:
            await quest_cog.update_quest_progress(ctx.author.id, "gacha_roll", 1) 
            
        embed = discord.Embed(title="🎰 Gacha Mochi", description=item_msg, color=0xff69b4)
        embed.set_footer(text=f"Sisa roll: {new_rolls}")
        await ctx.send(embed=embed)

    @commands.command(name="rate")
    async def gacha_rate(self, ctx):
        """Lihat rate gacha berdasarkan luck"""
        user_data = await get_user(ctx.author.id)
        current_luck = user_data["luck"] if user_data else 0

        base_rates = {
            "🔥 20x XP (Divine)": 0.0001,
            "💫 10x XP (Mythic)": 0.0004,
            "🌈 8x XP (Epic)": 0.001,
            "🌟 Rp 100.000 (Legendary)": 0.005,
            "💎 4x XP (Super Langka)": 0.0145,
            "✨ 2x XP (Langka)": 0.08,
            "🎁 Rp 10.000 (Biasa)": 0.899
        }

        rare_tiers = list(base_rates.keys())[:-1]
        total_rare_base = sum(base_rates[tier] for tier in rare_tiers)
        luck_bonus = min(current_luck * 0.001, 0.1)

        adjusted_rates = {}
        for tier in rare_tiers:
            ratio = base_rates[tier] / total_rare_base if total_rare_base > 0 else 0
            adjusted_rates[tier] = (base_rates[tier] + luck_bonus * ratio) * 100

        total_rare_adjusted = sum(adjusted_rates[tier] for tier in rare_tiers)
        adjusted_rates["🎁 Rp 10.000 (Biasa)"] = max(0, 100 - total_rare_adjusted)

        embed = discord.Embed(
            title="📊 Gacha Rate Mochi",
            description=f"Rate berdasarkan **Luck kamu: `{current_luck}`**",
            color=0xff69b4
        )

        for tier in base_rates.keys():
            embed.add_field(name=tier, value=f"`{adjusted_rates[tier]:.3f}%`", inline=False)

        embed.add_field(
            name="ℹ️ Info",
            value="• Setiap **1 Luck = +0.1%** total chance untuk hadiah langka\n• **Divine tetap paling langka!**\n• Max bonus: +10% (Luck 100)",
            inline=False
        )
        embed.set_footer(text="Naikkan level untuk dapat lebih banyak Luck!")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Gacha(bot))