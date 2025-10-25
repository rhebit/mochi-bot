import discord
from discord.ext import commands, tasks
import aiosqlite
import random
from datetime import datetime, timedelta
import pytz
from database import get_user, update_user
from utils.config_secrets import QUEST_CHANNEL_ID #

class Quests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Quest templates - DAILY GLOBAL QUEST
        self.quest_templates = [
            {
                "type": "fish_rare",
                "title": "🟠 Tangkap Ikan Langka",
                "description": "Tangkap {amount} ikan Rare atau lebih tinggi",
                "emoji": "🟠",
                "reward_currency": 50000,
                "reward_luck": 2,
                "amounts": [3, 5, 7, 10]
            },
            {
                "type": "fish_any",
                "title": "🎣 Memancing Produktif",
                "description": "Tangkap {amount} ikan (apapun)",
                "emoji": "🎣",
                "reward_currency": 30000,
                "reward_luck": 1,
                "amounts": [20, 30, 50, 75, 100]
            },
            {
                "type": "trade_profit",
                "title": "📈 Profit Trading",
                "description": "Dapatkan profit Rp {amount:,} dari trading crypto",
                "emoji": "📈",
                "reward_currency": 100000,
                "reward_luck": 3,
                "amounts": [100000, 500000, 1000000]
            },
            {
                "type": "jade_cut",
                "title": "💎 Potong Batu Jade",
                "description": "Potong {amount} batu jade (Rare atau lebih tinggi)",
                "emoji": "💎",
                "reward_currency": 75000,
                "reward_luck": 2,
                "amounts": [1, 3, 5, 10]
            },
            {
                "type": "gacha_roll",
                "title": "🎰 Gacha Streak",
                "description": "Roll gacha {amount} kali",
                "emoji": "🎰",
                "reward_currency": 50000,
                "reward_luck": 2,
                "amounts": [2, 3, 4, 5]
            },
        ]
        
        # Start daily quest reset at 07:00 WIB
        self.daily_quest_reset.start()
        self.check_quest_completion.start()
    
    def cog_unload(self):
        self.daily_quest_reset.cancel()
        self.check_quest_completion.cancel()
    
    @tasks.loop(hours=1)
    async def daily_quest_reset(self):
        """Reset quest setiap hari jam 07:00 WIB"""
        wib = pytz.timezone('Asia/Jakarta')
        now_wib = datetime.now(wib)
        
        # Check if it's 07:00 WIB (dengan toleransi 5 menit)
        if now_wib.hour == 7 and now_wib.minute < 5:
            print("🎯 Daily quest reset starting (07:00 WIB)...")
            await self.generate_daily_quest()
    
    @daily_quest_reset.before_loop
    async def before_daily_reset(self):
        await self.bot.wait_until_ready()
    
    @tasks.loop(seconds=10)
    async def check_quest_completion(self):
        """Check quest completion setiap 10 detik dan auto-reward"""
        async with aiosqlite.connect("mochi.db") as db:
            # Get current active quest
            cursor = await db.execute("""
                SELECT quest_id, type, target_amount, reward_currency, 
                    reward_luck, title, emoji
                FROM global_quests 
                WHERE active = 1 AND expires_at > ?
                LIMIT 1
            """, (datetime.utcnow().isoformat(),))
            quest = await cursor.fetchone()
            
            if not quest:
                return
            
            quest_id, quest_type, target, reward_currency, reward_luck, title, emoji = quest
            
            # Check all users who completed quest but not claimed
            cursor = await db.execute("""
                SELECT user_id, current_progress 
                FROM quest_progress 
                WHERE quest_id = ? AND completed = 0 AND current_progress >= ?
            """, (quest_id, target))
            completed_users = await cursor.fetchall()
            
            quest_channel = self.bot.get_channel(QUEST_CHANNEL_ID)
            
            for user_id, progress in completed_users:
                # Mark as completed
                await db.execute("""
                    UPDATE quest_progress 
                    SET completed = 1, completed_at = ?
                    WHERE quest_id = ? AND user_id = ?
                """, (datetime.utcnow().isoformat(), quest_id, user_id))
                
                # Give reward - PERBAIKAN DI SINI
                # Jangan gunakan update_user() yang membuat koneksi database baru
                # Gunakan execute langsung dengan koneksi yang sama
                cursor = await db.execute("""
                    SELECT currency, luck FROM users WHERE user_id = ?
                """, (user_id,))
                user_data = await cursor.fetchone()
                
                if user_data:
                    new_currency = user_data[0] + reward_currency
                    new_luck = user_data[1] + reward_luck
                    
                    await db.execute("""
                        UPDATE users 
                        SET currency = ?, luck = ?
                        WHERE user_id = ?
                    """, (new_currency, new_luck, user_id))
                
                await db.commit()  # Commit untuk setiap user
                
                # Update quest completed count
                await db.execute("""
                    INSERT OR REPLACE INTO quest_stats (user_id, total_completed, last_completed_at)
                    VALUES (
                        ?,
                        COALESCE((SELECT total_completed FROM quest_stats WHERE user_id = ?), 0) + 1,
                        ?
                    )
                """, (user_id, user_id, datetime.utcnow().isoformat()))
                await db.commit()  # Commit lagi
                
                # Send completion message
                if quest_channel:
                    try:
                        user = self.bot.get_user(user_id)
                        user_mention = user.mention if user else f"<@{user_id}>"
                        
                        embed = discord.Embed(
                            title="✅ QUEST COMPLETED!",
                            description=f"{user_mention} telah menyelesaikan daily quest!",
                            color=0x00ff00
                        )
                        embed.add_field(name="📋 Quest", value=f"{emoji} {title}", inline=False)
                        embed.add_field(name="✅ Progress", value=f"{progress}/{target}", inline=True)
                        embed.add_field(name="💰 Reward", value=f"Rp {reward_currency:,}", inline=True)
                        embed.add_field(name="🍀  Luck Bonus", value=f"+{reward_luck}", inline=True)
                        embed.set_footer(text="Selamat! Daily quest baru besok jam 07:00 WIB")
                        
                        await quest_channel.send(embed=embed)
                    except Exception as e:
                        print(f"Error sending completed quest message: {e}")
                
                # Check quest achievement progress (untuk achievement system)
                ach_cog = self.bot.get_cog('Achievements')
                if ach_cog:
                    cursor = await db.execute("""
                        SELECT total_completed FROM quest_stats 
                        WHERE user_id = ?
                    """, (user_id,))
                    row = await cursor.fetchone()
                    total_completed = row[0] if row else 0
                    
                    await ach_cog.check_achievement_progress(user_id, "quests_completed", total_completed)
    
    @check_quest_completion.before_loop
    async def before_check_completion(self):
        await self.bot.wait_until_ready()
    
    async def generate_daily_quest(self):
        """Generate 1 GLOBAL quest untuk SEMUA user"""
        print("🎯 Generating daily global quest...")
        
        quest_channel = self.bot.get_channel(QUEST_CHANNEL_ID)
        if not quest_channel:
            print(f"❌ Quest channel {QUEST_CHANNEL_ID} not found!")
            return
        
        # Random quest template
        template = random.choice(self.quest_templates)
        amount = random.choice(template["amounts"])
        
        wib = pytz.timezone('Asia/Jakarta')
        now_wib = datetime.now(wib)
        
        # Quest ID dengan tanggal WIB
        quest_id = f"global_{now_wib.strftime('%Y%m%d')}"
        
        # ========================================
        # ✅ PERBAIKAN: Cek dulu apakah quest hari ini sudah ada
        # ========================================
        async with aiosqlite.connect("mochi.db") as db:
            cursor = await db.execute("""
                SELECT quest_id FROM global_quests 
                WHERE quest_id = ? AND active = 1
            """, (quest_id,))
            existing_quest = await cursor.fetchone()
            
            if existing_quest:
                print(f"⚠️ Quest hari ini ({quest_id}) sudah ada! Tidak perlu generate baru.")
                
                # Kirim pesan ke channel bahwa quest sudah ada
                embed = discord.Embed(
                    title="⚠️ Quest Hari Ini Sudah Ada!",
                    description=f"Daily quest untuk hari ini sudah aktif.\nGunakan `mochi!quest` untuk melihat quest yang sedang berjalan.",
                    color=0xff9900
                )
                
                # Cari info quest yang sedang aktif
                cursor = await db.execute("""
                    SELECT title, description, target_amount, expires_at 
                    FROM global_quests 
                    WHERE quest_id = ? AND active = 1
                """, (quest_id,))
                active_quest = await cursor.fetchone()
                
                if active_quest:
                    title, description, target, expires_at = active_quest
                    embed.add_field(
                        name="📋 Quest Aktif",
                        value=f"**{title}**\n{description}",
                        inline=False
                    )
                    
                    try:
                        if isinstance(expires_at, str):
                            expire_time = datetime.fromisoformat(expires_at.replace('Z', '').replace('+00:00', ''))
                        else:
                            expire_time = expires_at
                        expire_timestamp = int(expire_time.timestamp())
                        embed.add_field(
                            name="⏰ Expires",
                            value=f"<t:{expire_timestamp}:R>",
                            inline=True
                        )
                    except:
                        pass
                
                embed.set_footer(text="Quest baru akan dibuat besok jam 07:00 WIB")
                await quest_channel.send(embed=embed)
                return
        
        # ========================================
        # LANJUTKAN DENGAN GENERATE QUEST BARU
        # ========================================
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        async with aiosqlite.connect("mochi.db") as db:
            # Deactivate old quests
            await db.execute("UPDATE global_quests SET active = 0")
            
            # Create new global quest
            await db.execute("""
                INSERT INTO global_quests (quest_id, type, title, description, 
                                        emoji, target_amount, reward_currency, 
                                        reward_luck, created_at, expires_at, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                quest_id, 
                template["type"],
                template["title"],
                template["description"].format(amount=amount),
                template["emoji"],
                amount,
                template["reward_currency"],
                template["reward_luck"],
                datetime.utcnow().isoformat(),
                expires_at.isoformat()
            ))
            await db.commit()
        
        # Send announcement (kode yang sama seperti sebelumnya)
        expire_wib = expires_at.replace(tzinfo=pytz.utc).astimezone(wib)
        
        embed = discord.Embed(
            title="🌅 DAILY QUEST BARU!",
            description=f"**Quest hari ini untuk SEMUA PLAYER!**\n\n{template['emoji']} **{template['title']}**\n{template['description'].format(amount=amount)}",
            color=0xf39c12
        )
        
        # Progress bar (empty at start)
        progress_bar = "⬜" * 15
        embed.add_field(
            name="📊 Target",
            value=f"{progress_bar}\n`0/{amount}` completed",
            inline=False
        )
        
        embed.add_field(
            name="💰 Reward",
            value=f"**Currency:** Rp {template['reward_currency']:,}\n**Luck Bonus:** +{template['reward_luck']}",
            inline=True
        )
        
        embed.add_field(
            name="⏰ Deadline",
            value=f"Expire: <t:{int(expires_at.timestamp())}:R>\nReset: Besok jam **07:00 WIB**",
            inline=True
        )
        
        embed.add_field(
            name="💡 Info",
            value=(
                "✅ **Quest langsung aktif!** Tidak perlu accept\n"
                "📊 Progress auto-update setiap 10 detik\n"
                "🏆 **Semua player dapat quest yang sama**\n"
                "🎯 Gunakan `mochi!quest` untuk cek progress\n"
                "⚡ Quest selesai? Auto dapat reward!"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Quest ID: {quest_id} • Daily reset 07:00 WIB")
        
        await quest_channel.send("@everyone", embed=embed)
        print(f"✅ Global daily quest created: {template['title']}")
    
    async def update_quest_progress(self, user_id: int, quest_type: str, amount: int = 1):
        """Update progress quest user untuk GLOBAL quest"""
        async with aiosqlite.connect("mochi.db") as db:
            # Get current active quest
            cursor = await db.execute("""
                SELECT quest_id, target_amount FROM global_quests
                WHERE type = ? AND active = 1 AND expires_at > ?
                LIMIT 1
            """, (quest_type, datetime.utcnow().isoformat()))
            quest = await cursor.fetchone()
            
            if not quest:
                return
            
            quest_id, target_amount = quest
            
            # Update or insert progress
            cursor = await db.execute("""
                SELECT current_progress FROM quest_progress 
                WHERE quest_id = ? AND user_id = ?
            """, (quest_id, user_id))
            existing = await cursor.fetchone()
            
            if existing:
                new_progress = min(existing[0] + amount, target_amount)
                await db.execute("""
                    UPDATE quest_progress 
                    SET current_progress = ?, last_updated = ?
                    WHERE quest_id = ? AND user_id = ?
                """, (new_progress, datetime.utcnow().isoformat(), quest_id, user_id))
            else:
                await db.execute("""
                    INSERT INTO quest_progress (quest_id, user_id, current_progress, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (quest_id, user_id, min(amount, target_amount), datetime.utcnow().isoformat()))
            
            await db.commit()
    
    @commands.command(name="quest", aliases=["q", "dailyquest"])
    async def view_quest(self, ctx):
        """📋 Lihat daily quest dengan progress bar"""
        async with aiosqlite.connect("mochi.db") as db:
            # Get current active quest
            cursor = await db.execute("""
                SELECT quest_id, title, description, emoji, target_amount,
                       reward_currency, reward_luck, expires_at, created_at
                FROM global_quests 
                WHERE active = 1 AND expires_at > ?
                LIMIT 1
            """, (datetime.utcnow().isoformat(),))
            quest = await cursor.fetchone()
            
            if not quest:
                wib = pytz.timezone('Asia/Jakarta')
                tomorrow_7am = (datetime.now(wib).replace(hour=7, minute=0, second=0) + timedelta(days=1))
                
                embed = discord.Embed(
                    title="📋 Daily Quest",
                    description="Tidak ada quest aktif!\n\n✨ **Daily quest baru** akan spawn besok jam **07:00 WIB**",
                    color=0xff9900
                )
                embed.add_field(
                    name="⏰ Reset Time",
                    value=f"<t:{int(tomorrow_7am.timestamp())}:R>",
                    inline=False
                )
                embed.set_footer(text="Daily quest system • Reset setiap 07:00 WIB")
                await ctx.send(embed=embed)
                return
            
            quest_id, title, description, emoji, target, reward_currency, reward_luck, expires_at, created_at = quest
            
            # Get user progress
            cursor = await db.execute("""
                SELECT current_progress, completed FROM quest_progress 
                WHERE quest_id = ? AND user_id = ?
            """, (quest_id, ctx.author.id))
            progress_row = await cursor.fetchone()
            
            if progress_row:
                progress, completed = progress_row
            else:
                progress, completed = 0, 0
            
            # Get leaderboard (top 10)
            cursor = await db.execute("""
                SELECT user_id, current_progress, completed
                FROM quest_progress 
                WHERE quest_id = ? AND current_progress > 0
                ORDER BY completed DESC, current_progress DESC, last_updated ASC
                LIMIT 10
            """, (quest_id,))
            leaderboard = await cursor.fetchall()
        
        # Calculate percentage
        percentage = int((progress / target) * 100) if target > 0 else 0
        
        # Create progress bar
        progress_bar = self.create_progress_bar(progress, target, length=15)
        
        # Parse expires_at
        try:
            if isinstance(expires_at, str):
                expires_at_clean = expires_at.replace('Z', '').replace('+00:00', '')
                expire_time = datetime.fromisoformat(expires_at_clean)
            else:
                expire_time = expires_at
            expire_timestamp = int(expire_time.timestamp())
        except Exception:
            expire_timestamp = int((datetime.utcnow() + timedelta(hours=24)).timestamp())
        
        quest_emoji = emoji if emoji else "📋"
        status = "✅ COMPLETED!" if completed else "🔄 IN PROGRESS"
        
        embed = discord.Embed(
            title=f"📋 Daily Quest - {status}",
            description=f"**Quest Global Hari Ini** (Sama untuk semua player)",
            color=0x00ff00 if completed else 0xf39c12
        )
        
        embed.add_field(
            name=f"{quest_emoji} {title}",
            value=description,
            inline=False
        )
        
        embed.add_field(
            name="📊 Progress Kamu",
            value=(
                f"**{percentage}%** completed\n"
                f"{progress_bar}\n"
                f"`{progress}/{target}` {quest_emoji}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💰 Reward",
            value=f"Rp {reward_currency:,}",
            inline=True
        )
        embed.add_field(
            name="🍀  Luck Bonus",
            value=f"+{reward_luck}",
            inline=True
        )
        embed.add_field(
            name="⏰ Deadline",
            value=f"<t:{expire_timestamp}:R>",
            inline=True
        )
        
        # Leaderboard
        if leaderboard:
            leaderboard_text = ""
            for idx, (user_id, user_progress, user_completed) in enumerate(leaderboard, 1):
                user = self.bot.get_user(user_id)
                username = user.name if user else f"User {user_id}"
                
                # Highlight completed users
                if user_completed:
                    medal = "✅"
                    username = f"~~{username}~~"
                else:
                    medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][idx-1] if idx <= 10 else f"`{idx}.`"
                
                bar = self.create_progress_bar(user_progress, target, length=8)
                leaderboard_text += f"{medal} **{username}**: {bar} `{user_progress}/{target}`\n"
            
            embed.add_field(
                name="🏆 Leaderboard Top 10",
                value=leaderboard_text,
                inline=False
            )
        
        embed.add_field(
            name="💡 Info",
            value=(
                "• Progress update otomatis setiap **10 detik**\n"
                "• Quest selesai? Auto dapat reward!\n"
                "• Daily quest reset setiap **07:00 WIB**\n"
                "• **Semua player dapat quest yang sama!**"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Quest ID: {quest_id} • Reset besok 07:00 WIB")
        await ctx.send(embed=embed)
    
    def create_progress_bar(self, current: int, target: int, length: int = 10):
        """Buat visual progress bar dengan emoji warna"""
        if target == 0:
            percent = 0
        else:
            percent = min(current / target, 1.0)
        
        filled = int(length * percent)
        empty = length - filled
        
        # Color-coded progress
        if percent >= 1.0:
            bar = "🟩" * length
        elif percent >= 0.75:
            bar = "🟨" * filled + "⬜" * empty
        elif percent >= 0.5:
            bar = "🟨" * filled + "⬜" * empty
        elif percent >= 0.25:
            bar = "🟧" * filled + "⬜" * empty
        else:
            bar = "🟥" * filled + "⬜" * empty
        
        return bar
    
    @commands.command(name="queststats", aliases=["qstats"])
    async def quest_stats_command(self, ctx, member: discord.Member = None):
        """📊 Lihat statistik quest kamu"""
        user = member or ctx.author
        
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            
            # Get quest stats
            cursor = await db.execute("""
                SELECT total_completed, last_completed_at
                FROM quest_stats
                WHERE user_id = ?
            """, (user.id,))
            stats = await cursor.fetchone()
            
            # Get current active quest progress
            cursor = await db.execute("""
                SELECT gq.title, gq.emoji, qp.current_progress, gq.target_amount, qp.completed
                FROM quest_progress qp
                JOIN global_quests gq ON qp.quest_id = gq.quest_id
                WHERE qp.user_id = ? AND gq.active = 1
            """, (user.id,))
            current_quest = await cursor.fetchone()
        
        embed = discord.Embed(
            title=f"📊 Quest Stats - {user.display_name}",
            color=0x3498db
        )
        
        total_completed = stats["total_completed"] if stats else 0
        embed.add_field(
            name="🏆 Total Quest Completed",
            value=f"**{total_completed}** quests",
            inline=True
        )
        
        if stats and stats["last_completed_at"]:
            last_time = datetime.fromisoformat(stats["last_completed_at"])
            embed.add_field(
                name="⏰ Last Completed",
                value=f"<t:{int(last_time.timestamp())}:R>",
                inline=True
            )
        
        if current_quest:
            progress = current_quest["current_progress"]
            target = current_quest["target_amount"]
            percentage = int((progress / target) * 100) if target > 0 else 0
            
            bar = self.create_progress_bar(progress, target, 12)
            
            status = "✅ COMPLETED" if current_quest["completed"] else "🔄 IN PROGRESS"
            
            embed.add_field(
                name=f"{current_quest['emoji']} Current Quest - {status}",
                value=(
                    f"**{current_quest['title']}**\n"
                    f"{bar}\n"
                    f"`{progress}/{target}` ({percentage}%)"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="📋 Current Quest",
                value="Belum ada progress untuk quest hari ini",
                inline=False
            )
        
        embed.set_footer(text="Gunakan mochi!quest untuk lihat quest detail")
        await ctx.send(embed=embed)
    
    @commands.command(name="qhelp", aliases=["questhelp"])
    async def quest_help_command(self, ctx):
        """📖 Panduan Quest System"""
        embed = discord.Embed(
            title="📖 Daily Quest System - Help",
            description="Sistem quest harian dengan reward menarik!",
            color=0xf39c12
        )
        
        embed.add_field(
            name="🎯 Cara Kerja",
            value=(
                "1️⃣ Quest baru spawn **setiap hari jam 07:00 WIB**\n"
                "2️⃣ Quest **sama untuk semua player**\n"
                "3️⃣ Progress di-track otomatis saat aktivitas\n"
                "4️⃣ Reward otomatis saat quest selesai\n"
                "5️⃣ Quest expire dalam **24 jam**"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📋 Quest Commands",
            value=(
                "`mochi!quest` - Lihat quest aktif & progress\n"
                "`mochi!q` - Alias\n"
                "`mochi!queststats [@user]` - Lihat statistik quest\n"
                "`mochi!qstats` - Alias\n"
                "`mochi!qhelp` - Panduan ini"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎲 Tipe Quest",
            value=(
                "**🟠 Fish Rare** - Tangkap ikan langka\n"
                "**🎣 Fish Any** - Tangkap ikan apapun\n"
                "**📈 Trade Profit** - Profit dari trading\n"
                "**💎 Jade Cut** - Potong batu jade rare+\n"
                "**🎰 Gacha Roll** - Roll gacha\n"
                "**📚 Kumpul XP** - Kumpul portfolio"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🏆 Rewards",
            value=(
                "💰 **Currency**: 30,000 - 100,000 Rp\n"
                "🍀  **Luck Bonus**: +1 sampai +3 permanent\n"
                "⭐ **Achievement Progress**: Quest completed count"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Progress Tracking",
            value=(
                "✅ Progress update **setiap 10 detik**\n"
                "📈 Lihat real-time di `mochi!quest`\n"
                "🏅 Leaderboard top 10 ditampilkan\n"
                "🎯 Indikator warna progress bar:\n"
                "   • 🟥 0-25% (Merah)\n"
                "   • 🟧 25-50% (Orange)\n"
                "   • 🟨 50-100% (Kuning)\n"
                "   • 🟩 100% (Hijau - Complete!)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Tips",
            value=(
                "⏰ Cek quest pagi hari jam 07:00 WIB\n"
                "🎯 Fokus selesaikan quest sebelum expire\n"
                "🏆 Quest completed = achievement progress\n"
                "📊 Track progress di `mochi!quest`\n"
                "✨ Luck bonus dari quest = permanent!"
            ),
            inline=False
        )
        
        embed.set_footer(text="Quest spawn otomatis jam 07:00 WIB setiap hari!")
        await ctx.send(embed=embed)

async def init_quest_tables():
    """Initialize quest tables"""
    async with aiosqlite.connect("mochi.db") as db:
        # Global quests table (1 quest for all users)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS global_quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quest_id TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                emoji TEXT DEFAULT '📋',
                target_amount INTEGER NOT NULL,
                reward_currency INTEGER NOT NULL,
                reward_luck INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)
        
        # Quest progress per user
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quest_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quest_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                current_progress INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                completed_at TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(quest_id, user_id)
            )
        """)
        
        # Quest stats per user
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quest_stats (
                user_id INTEGER PRIMARY KEY,
                total_completed INTEGER DEFAULT 0,
                last_completed_at TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_quest_progress_user 
            ON quest_progress(user_id, quest_id)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_global_quest_active 
            ON global_quests(active, expires_at)
        """)
        
        await db.commit()
        print("✅ Quest tables created!")

async def setup(bot):
    await init_quest_tables()
    await bot.add_cog(Quests(bot))