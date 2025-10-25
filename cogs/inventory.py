import discord
from discord.ext import commands
from datetime import datetime, timedelta

from database import get_user, create_user, update_user
from utils.helpers import get_rank_title

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="use")
    async def use_item(self, ctx, item_code: str = None):
        """Gunakan item XP multiplier"""
        if item_code is None:
            await ctx.send(
                "❓ Gunakan: `mochi!use <kode>`\n"
                "Kode yang tersedia: `2x`, `4x`, `8x`, `10x`, `20x`"
            )
            return

        user_data = await get_user(ctx.author.id)
        if not user_data:
            await ctx.send("Kamu belum punya data!")
            return

        if user_data["next_xp_mult"] > 1.0:
            await ctx.send(f"⚠️ Kamu masih punya efek XP aktif (**{user_data['next_xp_mult']}x XP**)! Tunggu sampai habis.")
            return

        item_code = item_code.lower()
        if item_code == "2x" and user_data["xp_2x"] > 0:
            await update_user(ctx.author.id, next_xp_mult=2.0) 
            await ctx.send("✨ **2x XP** aktif untuk portofolio berikutnya! Item akan dikonsumsi saat berhasil `mochi!kumpul`.")

        elif item_code == "4x" and user_data["xp_4x"] > 0:
            await update_user(ctx.author.id, next_xp_mult=4.0) 
            await ctx.send("🌟 **4x XP** aktif untuk portofolio berikutnya! Item akan dikonsumsi saat berhasil `mochi!kumpul`.")

        elif item_code == "8x" and user_data["xp_8x"] > 0:
            await update_user(ctx.author.id, next_xp_mult=8.0) 
            await ctx.send("🌈 **8x XP** aktif untuk portofolio berikutnya! Item akan dikonsumsi saat berhasil `mochi!kumpul`.")

        elif item_code == "10x" and user_data["xp_10x"] > 0:
            await update_user(ctx.author.id, next_xp_mult=10.0) 
            await ctx.send("💫 **10x XP** aktif untuk portofolio berikutnya! Item akan dikonsumsi saat berhasil `mochi!kumpul`.")

        elif item_code == "20x" and user_data["xp_20x"] > 0:
            await update_user(ctx.author.id, next_xp_mult=20.0) 
            await ctx.send("🔥 **20x XP** aktif untuk portofolio berikutnya! Item akan dikonsumsi saat berhasil `mochi!kumpul`.")
        else:
            await ctx.send("Item tidak dikenali atau kamu tidak punya! Gunakan: `2x`, `4x`, `8x`, `10x`, atau `20x`")

    @commands.command(name="weekly")
    async def weekly_bonus(self, ctx):
        """Claim weekly 2x XP bonus untuk Bangsawan rank ke atas"""
        user_data = await get_user(ctx.author.id)
        if not user_data:
            await ctx.send("Kamu belum punya data!")
            return
        
        current_level = user_data["level"]
        
        # Cek rank minimal Bangsawan (level 15+)
        if current_level < 15:
            await ctx.send(
                f"⚠️ Weekly bonus hanya untuk rank **Bangsawan** (Level 15) ke atas!\n"
                f"Level kamu sekarang: **{current_level}** ({get_rank_title(current_level)})"
            )
            return
        
        # Cek apakah sudah claim minggu ini
        now = datetime.utcnow()
        
        last_claim_str = user_data.get("last_weekly_claim")
        if last_claim_str:
            last_claim = datetime.fromisoformat(last_claim_str)
            week_ago = now - timedelta(days=7)
            
            if last_claim > week_ago:
                # Hitung kapan bisa claim lagi
                next_claim = last_claim + timedelta(days=7)
                time_left = next_claim - now
                days_left = time_left.days
                hours_left = time_left.seconds // 3600
                
                await ctx.send(
                    f"⏰ Kamu sudah claim weekly bonus minggu ini!\n"
                    f"Bisa claim lagi dalam: **{days_left} hari {hours_left} jam**"
                )
                return
        
        # Berikan 1x 2x XP item
        await update_user(ctx.author.id, xp_2x=1, last_weekly_claim=now.isoformat())
        
        await ctx.send(
            f"🎁 **Weekly Bonus Claimed!**\n"
            f"{ctx.author.mention} mendapat **1x 2x XP item** sebagai benefit rank {get_rank_title(current_level)}!\n"
            f"Gunakan dengan: `mochi!use 2x`"
        )

async def setup(bot):
    await bot.add_cog(Inventory(bot))