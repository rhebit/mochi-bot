import discord
from discord.ext import commands
import asyncio
import aiosqlite

from database import get_user, create_user, update_user
from utils.helpers import OWNER_ID, RANK_ROLE_IDS, get_rank_role_name, get_rank_title
from config import MAIN_PORTO_CHANNEL_NAME

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup")
    async def setup_roles(self, ctx):
        # PERBAIKAN: Check in list untuk konsistensi/multi-owner masa depan
        allowed_owners = OWNER_ID if isinstance(OWNER_ID, list) else [OWNER_ID]
        if ctx.author.id not in allowed_owners:
            await ctx.send("❌ Hanya owner yang bisa pakai command ini!")
            return
        
        embed = discord.Embed(
            title="🔧 Setup Role IDs",
            description="Copy Role IDs ini ke variabel `RANK_ROLE_IDS` di utils/helpers.py:",
            color=0x00ff00
        )
        
        role_list = ""
        for rank_name in ["Warga", "Prajurit", "Ksatria", "Bangsawan", "Adipati", "Raja"]:
            role = discord.utils.get(ctx.guild.roles, name=rank_name)
            if role:
                role_list += f'"{rank_name}": {role.id},\n'
            else:
                role_list += f'"{rank_name}": 0,  # ⚠️ Role belum dibuat!\n'
        
        embed.add_field(
            name="📋 Role IDs",
            value=f"```python\nRANK_ROLE_IDS = {{\n{role_list}}}\n```",
            inline=False
        )
        
        embed.add_field(
            name="📌 Cara Pakai",
            value="1. Copy kode di atas\n2. Paste ke `utils/helpers.py` (ganti yang lama)\n3. Restart bot",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="cheatxp")
    async def cheat_xp(self, ctx, amount: int = None, member: discord.Member = None):
        """Cheat XP untuk testing"""
        if ctx.author.id != OWNER_ID:
            await ctx.send("❌ Hanya owner yang bisa pakai cheat ini!")
            return

        if amount is None:
            await ctx.send(
                "❓ **Format salah!**\n"
                "✅ Gunakan: `mochi!cheatxp <jumlah> [@user]`\n"
                "📌 Contoh:\n"
                "• `mochi!cheatxp 100` (untuk diri sendiri)\n"
                "• `mochi!cheatxp 500 @user` (untuk user lain)"
            )
            return

        target = member or ctx.author
        user_data = await get_user(target.id)
        if not user_data:
            await create_user(target.id)
            user_data = await get_user(target.id)

        await update_user(target.id, xp=amount)
        new_xp = user_data["xp"] + amount

        # Import check_level_up from leveling cog
        leveling_cog = self.bot.get_cog('Leveling')
        if leveling_cog:
            level_up, reward, rolls = await leveling_cog.check_level_up(target.id, new_xp, user_data["level"])
            
            if level_up:
                # Apply role dengan ID
                new_rank_name = get_rank_role_name(level_up)
                new_rank_id = RANK_ROLE_IDS.get(new_rank_name, 0)
                
                if new_rank_id != 0:
                    # Hapus role rank lama
                    roles_to_remove = []
                    for rank_name, role_id in RANK_ROLE_IDS.items():
                        if role_id != 0:
                            role = ctx.guild.get_role(role_id)
                            if role and role in target.roles:
                                roles_to_remove.append(role)
                    
                    if roles_to_remove:
                        try:
                            await target.remove_roles(*roles_to_remove, reason=f"Cheat XP level up ke {level_up}")
                        except Exception as e:
                            print(f"❌ Error hapus role: {e}")
                    
                    # Tambah role baru
                    new_role = ctx.guild.get_role(new_rank_id)
                    if new_role:
                        try:
                            await target.add_roles(new_role, reason=f"Cheat XP level up ke {level_up}")
                            await ctx.send(f"✅ Role `{new_rank_name}` ditambahkan!")
                        except Exception as e:
                            await ctx.send(f"❌ Error tambah role: {e}")
                
                await ctx.send(
                    f"✨ {target.mention} dapat **{amount} XP** → naik ke **Level {level_up}** ({get_rank_title(level_up)})! Hadiah: Rp {reward:,} + {rolls} roll gacha!"
                )
            else:
                await ctx.send(f"✨ {target.mention} dapat **{amount} XP**. Total XP: {new_xp}")
        else:
            await ctx.send(f"✨ {target.mention} dapat **{amount} XP**. Total XP: {new_xp}")
    
    @commands.command(name="cheatrp")
    async def cheat_rp(self, ctx, amount: int = None, member: discord.Member = None):
        """Cheat currency untuk testing"""
        if ctx.author.id != OWNER_ID:
            await ctx.send("❌ Hanya owner yang bisa pakai cheat ini!")
            return

        if amount is None:
            await ctx.send(
                "❓ **Format salah!**\n"
                "✅ Gunakan: `mochi!cheatrp <jumlah> [@user]`\n"
                "📌 Contoh:\n"
                "• `mochi!cheatrp 50000` (untuk diri sendiri)\n"
                "• `mochi!cheatrp 100000 @user` (untuk user lain)"
            )
            return

        target = member or ctx.author
        user_data = await get_user(target.id)
        if not user_data:
            await create_user(target.id)
            user_data = await get_user(target.id)

        new_currency = user_data["currency"] + amount
        await update_user(target.id, currency=amount)
        await ctx.send(f"💰 {target.mention} dapat **Rp {amount:,}**! Total: Rp {new_currency:,}")

    @commands.command(name="forcequestgen")
    @commands.is_owner()
    async def force_quest_gen(self, ctx):
        """🔧 [OWNER] Force generate daily quest sekarang"""
        quest_cog = self.bot.get_cog("Quests")
        
        if not quest_cog:
            await ctx.send("❌ Quest cog belum diload!")
            return
        
        await ctx.send("🎯 Generating daily quest...")
        await quest_cog.generate_daily_quest()
        await ctx.send("✅ Daily quest generated! Cek quest channel.")
    
    @commands.command(name="testquest")
    @commands.is_owner()
    async def test_quest(self, ctx, quest_type: str, amount: int = 1):
        """🧪 Test update quest progress"""
        quest_cog = self.bot.get_cog("Quests")
        if quest_cog:
            await quest_cog.update_quest_progress(ctx.author.id, quest_type, amount)
            await ctx.send(f"✅ Updated quest `{quest_type}` by {amount}")
        else:
            await ctx.send("❌ Quests cog not loaded")
    
    @commands.command(name="questdebug")
    @commands.is_owner()
    async def quest_debug(self, ctx):
        """🔍 Debug quest system"""
        async with aiosqlite.connect("mochi.db") as db:
            cursor = await db.execute("""
                SELECT quest_id, type, title, target_amount, active, expires_at
                FROM global_quests 
                WHERE active = 1
            """)
            quest = await cursor.fetchone()
            
            if not quest:
                await ctx.send("❌ No active quest found!")
                return
            
            quest_id, qtype, title, target, active, expires = quest
            
            cursor = await db.execute("""
                SELECT user_id, current_progress, completed 
                FROM quest_progress 
                WHERE quest_id = ?
                ORDER BY current_progress DESC
                LIMIT 10
            """, (quest_id,))
            progress_data = await cursor.fetchall()
        
        embed = discord.Embed(title="🔍 Quest Debug", color=0x00ff00)
        embed.add_field(name="Quest ID", value=quest_id, inline=False)
        embed.add_field(name="Type", value=qtype, inline=True)
        embed.add_field(name="Title", value=title, inline=True)
        embed.add_field(name="Target", value=target, inline=True)
        embed.add_field(name="Active", value=active, inline=True)
        embed.add_field(name="Expires", value=expires, inline=False)
        
        if progress_data:
            prog_text = "\n".join([
                f"<@{uid}>: {prog}/{target} {'✅' if completed else '🔄'}"
                for uid, prog, completed in progress_data
            ])
            embed.add_field(name="Progress (Top 10)", value=prog_text, inline=False)
        else:
            embed.add_field(name="Progress", value="No progress yet", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="giverp", aliases=["givecurrency", "pay"])
    async def give_rp_command(self, ctx, member: discord.Member = None, amount: int = None):
        """💰 Transfer Rupiah (Rp) ke user lain"""
        if member is None or amount is None or amount <= 0:
            await ctx.send(
                "❌ **Format salah!**\n"
                "✅ Gunakan: `mochi!giverp @user <jumlah>`\n"
                "📌 Contoh: `mochi!giverp @teman 50000`"
            )
            return

        if ctx.author.id == member.id:
            await ctx.send("❌ Kamu tidak bisa transfer ke diri sendiri!")
            return

        user_data = await get_user(ctx.author.id)
        if not user_data or user_data["currency"] < amount:
            await ctx.send(f"❌ Saldo tidak cukup! Kamu hanya punya Rp {user_data['currency']:,}")
            return
        
        receiver_data = await get_user(member.id)
        if not receiver_data:
            await create_user(member.id)

        # Proses transfer
        await update_user(ctx.author.id, currency=-amount)
        await update_user(member.id, currency=amount)
        
        await ctx.send(
            f"✅ **Transfer Berhasil!**\n"
            f"{ctx.author.mention} mentransfer **Rp {amount:,}** ke {member.mention}"
        )

    @commands.command(name="help", aliases=["h", "commands", "cmd"])
    async def help_command(self, ctx, category: str = None):
        """📚 Tampilkan bantuan bot - Gunakan mochi!help <category> untuk detail"""
        
        if category:
            category = category.lower()
            
            # Redirect ke help commands lain
            if category in ["fish", "fishing", "f"]:
                await ctx.invoke(self.bot.get_command("fhelp"))
                return
            elif category in ["jade", "j", "gacha"]:
                await ctx.invoke(self.bot.get_command("jhelp"))
                return
            elif category in ["trade", "trading", "t", "crypto"]:
                await ctx.invoke(self.bot.get_command("thelp"))
                return
            elif category in ["economy", "e", "eco"]:
                await ctx.invoke(self.bot.get_command("ehelp"))
                return
            elif category in ["achievement", "ach"]:
                await ctx.invoke(self.bot.get_command("achhelp"))
                return
            elif category in ["quest", "q"]:
                await ctx.invoke(self.bot.get_command("qhelp"))
                return
            elif category in ["shop", "store", "s"]:
                await ctx.invoke(self.bot.get_command("shopinfo"))
                return
        
        main_channel = discord.utils.get(ctx.guild.channels, name=MAIN_PORTO_CHANNEL_NAME)
        porto_mention = f"<#{main_channel.id}>" if main_channel else f"`#{MAIN_PORTO_CHANNEL_NAME}`"
        
        is_owner = ctx.author.id == OWNER_ID
        
        embed = discord.Embed(
            title="✨ Mochi Bot - Command List",
            description=(
                "**Sistem portofolio interaktif dengan XP, level, currency, gacha, dan trading!**\n\n"
                "💡 **Tip**: Gunakan `mochi!help <category>` untuk detail\n"
                "📋 Categories: `fish`, `jade`, `trade`, `economy`, `achievement`, `quest`, `shop`"
            ),
            color=0xffb6c1
        )
        
        # Basic Commands
        embed.add_field(
            name="🎯 Basic Commands",
            value=(
                f"`mochi!kumpul` - Kumpul XP di {porto_mention}\n"
                "`mochi!profile [@user]` - Lihat profil\n"
                "`mochi!rank` - Info sistem rank\n"
                "`mochi!top` - Leaderboard\n"
                "`mochi!help <category>` - Help detail"
            ),
            inline=False
        )
        
        # Gacha & Items
        embed.add_field(
            name="🎰 Gacha & Items",
            value=(
                "`mochi!gacha` - Roll gacha (butuh roll)\n"
                "`mochi!rate` - Lihat rate gacha\n"
                "`mochi!use <2x/4x/8x/10x/20x>` - Pakai item XP\n"
                "`mochi!weekly` - [Bangsawan+] Free 2x XP\n"
                "`mochi!tradeitem` - Jual item ke teman"
            ),
            inline=False
        )
        
        # Achievement (TERPISAH dari Quest)
        embed.add_field(
            name="🏆 Achievement System",
            value=(
                "`mochi!achievements [@user]` - Lihat achievements & luck bonus\n"
                "`mochi!achhelp` - Panduan achievement system\n"
                "🤞 **Unlock achievements untuk permanent luck boost!**"
            ),
            inline=False
        )
        
        # Quest System (TERPISAH!)
        embed.add_field(
            name="🎯 Daily Quest System",
            value=(
                "`mochi!quest` - Lihat quest aktif & progress\n"
                "`mochi!queststats [@user]` - Statistik quest kamu\n"
                "`mochi!qhelp` - Panduan quest system\n"
                "⏰ **Quest baru setiap hari jam 07:00 WIB!**"
            ),
            inline=False
        )
        
        # Shop System (BARU!)
        embed.add_field(
            name="🛒 Daily Shop System",
            value=(
                "`mochi!shop` - Lihat shop items hari ini\n"
                "`mochi!shopbuy <item>` - Beli item dari shop\n"
                "`mochi!shopinfo` - Panduan shop system\n"
                "🔥 **Special deals & limited stock!**"
            ),
            inline=False
        )
        
        # Quick Access
        embed.add_field(
            name="🎮 Quick Access (Detail: mochi!help <category>)",
            value=(
                "🎣 **Fishing**: `mochi!fhelp` atau `mochi!help fish`\n"
                "💎 **Jade Gacha**: `mochi!jhelp` atau `mochi!help jade`\n"
                "📈 **Trading**: `mochi!thelp` atau `mochi!help trade`\n"
                "💰 **Economy**: `mochi!ehelp` atau `mochi!help economy`\n"
                "🏆 **Achievements**: `mochi!achhelp` atau `mochi!help achievement`\n"
                "🎯 **Quest**: `mochi!qhelp` atau `mochi!help quest`\n"
                "🛒 **Shop**: `mochi!shopinfo` atau `mochi!help shop`"
            ),
            inline=False
        )

        if is_owner:
            embed.add_field(
                name="🛠️ Owner Only",
                value=(
                    "`mochi!setup` - Lihat Role IDs\n"
                    "`mochi!cheatxp <jumlah> [@user]`\n"
                    "`mochi!cheatrp <jumlah> [@user]`\n"
                    "`mochi!forcequestgen` - Force spawn quest\n"
                    "`mochi!forceshopgen` - Force spawn shop\n"
                    "`mochi!testquest <type> <amount>` - Test quest\n"
                    "`mochi!questdebug` - Debug quest system"
                ),
                inline=False
            )

        embed.set_footer(text="Mochi Bot • Ketik mochi!help <category> untuk detail lengkap")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Admin(bot))