import discord
from discord.ext import commands
import aiosqlite
from datetime import datetime
from database import get_user, update_user

class Achievements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Achievement definitions
        self.achievements = {
            # Portfolio Achievements
            "porto_beginner": {
                "name": "Portfolio Beginner",
                "emoji": "📗",
                "description": "Kumpulkan 5 portfolio",
                "requirement": 5,
                "type": "portfolio_count",
                "luck_bonus": 1,
                "reward_currency": 10000
            },
            "porto_collector": {
                "name": "Portfolio Collector",
                "emoji": "📚",
                "description": "Kumpulkan 25 portfolio",
                "requirement": 25,
                "type": "portfolio_count",
                "luck_bonus": 3,
                "reward_currency": 50000
            },
            "porto_master": {
                "name": "Portfolio Master",
                "emoji": "🎓",
                "description": "Kumpulkan 100 portfolio",
                "requirement": 100,
                "type": "portfolio_count",
                "luck_bonus": 5,
                "reward_currency": 200000
            },
            "porto_legend": {
                "name": "Portfolio Legend",
                "emoji": "👑",
                "description": "Kumpulkan 500 portfolio",
                "requirement": 500,
                "type": "portfolio_count",
                "luck_bonus": 10,
                "reward_currency": 1000000
            },
            
            # Fishing Achievements
            "fisher_novice": {
                "name": "Novice Fisher",
                "emoji": "🎣",
                "description": "Tangkap 100 ikan",
                "requirement": 100,
                "type": "fish_caught",
                "luck_bonus": 2,
                "reward_currency": 25000
            },
            "fisher_pro": {
                "name": "Pro Fisher",
                "emoji": "🐟",
                "description": "Tangkap 1000 ikan",
                "requirement": 1000,
                "type": "fish_caught",
                "luck_bonus": 5,
                "reward_currency": 100000
            },
            "legendary_catch": {
                "name": "Legendary Catch",
                "emoji": "🐋",
                "description": "Tangkap ikan Legendary",
                "requirement": 1,
                "type": "legendary_fish",
                "luck_bonus": 8,
                "reward_currency": 500000
            },
            
            # Trading Achievements
            "crypto_trader": {
                "name": "Crypto Trader",
                "emoji": "📈",
                "description": "Profit Rp 1 juta dari trading",
                "requirement": 1000000,
                "type": "trading_profit",
                "luck_bonus": 5,
                "reward_currency": 100000
            },
            "crypto_whale": {
                "name": "Crypto Whale",
                "emoji": "🐋",
                "description": "Profit Rp 10 juta dari trading",
                "requirement": 10000000,
                "type": "trading_profit",
                "luck_bonus": 15,
                "reward_currency": 1000000
            },
            
            # Jade Achievements
            "jade_cutter": {
                "name": "Jade Cutter",
                "emoji": "💎",
                "description": "Potong 50 batu jade",
                "requirement": 50,
                "type": "jade_cuts",
                "luck_bonus": 3,
                "reward_currency": 50000
            },
            "jackpot_hunter": {
                "name": "Jackpot Hunter",
                "emoji": "🎰",
                "description": "Dapat 5 jackpot di Jade",
                "requirement": 5,
                "type": "jade_jackpots",
                "luck_bonus": 10,
                "reward_currency": 500000
            },
            
            # Quest Achievements
            "quest_beginner": {
                "name": "Quest Beginner",
                "emoji": "⭐",
                "description": "Selesaikan 10 quest",
                "requirement": 10,
                "type": "quests_completed",
                "luck_bonus": 2,
                "reward_currency": 50000
            },
            "quest_hunter": {
                "name": "Quest Hunter",
                "emoji": "🏹",
                "description": "Selesaikan 50 quest",
                "requirement": 50,
                "type": "quests_completed",
                "luck_bonus": 5,
                "reward_currency": 200000
            },
            "quest_legend": {
                "name": "Quest Legend",
                "emoji": "🌟",
                "description": "Selesaikan 200 quest",
                "requirement": 200,
                "type": "quests_completed",
                "luck_bonus": 15,
                "reward_currency": 1000000
            },
            
            # Level Achievements
            "level_10": {
                "name": "Ksatria",
                "emoji": "🏹",
                "description": "Capai Level 10",
                "requirement": 10,
                "type": "level",
                "luck_bonus": 3,
                "reward_currency": 50000
            },
            "level_25": {
                "name": "Raja",
                "emoji": "👑",
                "description": "Capai Level 25",
                "requirement": 25,
                "type": "level",
                "luck_bonus": 10,
                "reward_currency": 500000
            }
        }
    
    async def check_achievement_progress(self, user_id: int, achievement_type: str, current_value: int):
        """Cek progress achievement dan unlock jika sudah tercapai"""
        async with aiosqlite.connect("mochi.db") as db:
            cursor = await db.execute("""
                SELECT achievement_id FROM user_achievements 
                WHERE user_id = ? AND unlocked = 1
            """, (user_id,))
            unlocked = [row[0] for row in await cursor.fetchall()]
        
        newly_unlocked = []
        for ach_id, ach in self.achievements.items():
            if ach["type"] == achievement_type and ach_id not in unlocked:
                if current_value >= ach["requirement"]:
                    await self.unlock_achievement(user_id, ach_id)
                    newly_unlocked.append(ach)
        
        return newly_unlocked
    
    async def unlock_achievement(self, user_id: int, achievement_id: str):
        """Unlock achievement dan berikan reward"""
        ach = self.achievements[achievement_id]
        
        async with aiosqlite.connect("mochi.db") as db:
            await db.execute("""
                INSERT OR REPLACE INTO user_achievements 
                (user_id, achievement_id, unlocked_at, unlocked)
                VALUES (?, ?, ?, 1)
            """, (user_id, achievement_id, datetime.utcnow().isoformat()))
            await db.commit()
        
        await update_user(user_id, currency=ach["reward_currency"], luck=ach["luck_bonus"])
        
        print(f"✨ {user_id} unlocked: {ach['name']} (+{ach['luck_bonus']} luck)")
    
    async def get_user_achievements(self, user_id: int):
        """Ambil semua achievements user"""
        async with aiosqlite.connect("mochi.db") as db:
            cursor = await db.execute("""
                SELECT achievement_id, unlocked_at 
                FROM user_achievements 
                WHERE user_id = ? AND unlocked = 1
            """, (user_id,))
            rows = await cursor.fetchall()
            return [{"achievement_id": row[0], "unlocked_at": row[1]} for row in rows]
    
    async def calculate_total_luck_bonus(self, user_id: int):
        """Hitung total luck bonus dari achievements"""
        achievements = await self.get_user_achievements(user_id)
        total_luck = 0
        
        for ach in achievements:
            ach_id = ach["achievement_id"]
            if ach_id in self.achievements:
                total_luck += self.achievements[ach_id]["luck_bonus"]
        
        return total_luck
    
    @commands.command(name="achievements", aliases=["ach", "achieve"])
    async def view_achievements(self, ctx, member: discord.Member = None):
        """🏆 Lihat achievements dan luck bonus"""
        user = member or ctx.author
        
        achievements = await self.get_user_achievements(user.id)
        unlocked_ids = [a["achievement_id"] for a in achievements]
        
        total_luck = await self.calculate_total_luck_bonus(user.id)
        total_unlocked = len(achievements)
        total_achievements = len(self.achievements)
        completion_pct = (total_unlocked / total_achievements) * 100
        
        embed = discord.Embed(
            title=f"🏆 Achievements - {user.display_name}",
            description=f"**Progress**: {total_unlocked}/{total_achievements} ({completion_pct:.1f}%)\n**Total Luck Bonus**: 🤞 +{total_luck}",
            color=0xffd700
        )
        
        categories = {
            "📚 Portfolio": ["porto_beginner", "porto_collector", "porto_master", "porto_legend"],
            "🎣 Fishing": ["fisher_novice", "fisher_pro", "legendary_catch"],
            "📈 Trading": ["crypto_trader", "crypto_whale"],
            "💎 Jade": ["jade_cutter", "jackpot_hunter"],
            "🎯 Quest": ["quest_beginner", "quest_hunter", "quest_legend"],
            "⭐ Level": ["level_10", "level_25"]
        }
        
        for category, ach_ids in categories.items():
            text = ""
            for ach_id in ach_ids:
                if ach_id not in self.achievements:
                    continue
                
                ach = self.achievements[ach_id]
                if ach_id in unlocked_ids:
                    text += f"✅ {ach['emoji']} **{ach['name']}** (+{ach['luck_bonus']} luck)\n"
                else:
                    text += f"🔒 {ach['emoji']} {ach['name']} - {ach['description']}\n"
            
            if text:
                embed.add_field(name=category, value=text, inline=False)
        
        embed.set_footer(text="Unlock achievements untuk luck bonus permanent!")
        await ctx.send(embed=embed)
    
    @commands.command(name="achhelp", aliases=["achievementhelp"])
    async def achievement_help(self, ctx):
        """🏆 Panduan Achievement System"""
        embed = discord.Embed(
            title="🏆 Achievement System - Help",
            description="Sistem reward dengan permanent luck bonus!",
            color=0xffd700
        )
        
        embed.add_field(
            name="🏆 Achievement Commands",
            value=(
                "`mochi!achievements [@user]` - Lihat semua achievements\n"
                "`mochi!ach` - Alias\n"
                "`mochi!achieve` - Alias\n\n"
                "**Achievement memberikan:**\n"
                "🤞 Permanent luck bonus\n"
                "💰 Currency reward\n"
                "⭐ Unlock otomatis saat capai requirement"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📚 Achievement Categories",
            value=(
                "**📚 Portfolio** - Kumpul 5, 25, 100, 500 portfolio\n"
                "**🎣 Fishing** - Tangkap 100, 1000 ikan, legendary fish\n"
                "**📈 Trading** - Profit Rp 1M, 10M dari crypto\n"
                "**💎 Jade** - Potong 50 batu, 5 jackpot\n"
                "**🎯 Quest** - Selesaikan 10, 50, 200 quest\n"
                "**⭐ Level** - Capai Level 10, 25"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🤞 Luck System",
            value=(
                "**Base Luck**: Dari naik level\n"
                "**Achievement Luck**: Permanent dari achievements ⭐\n"
                "**Total Luck**: Base + Achievement\n\n"
                "💡 **Luck affects:**\n"
                "• Gacha rates (max +10% at 100 luck)\n"
                "• Jade gambling (max +20% at 200 luck)\n"
                "• Fishing rare fish rates"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Portfolio Tier System",
            value=(
                "Ditampilkan di `mochi!profile`:\n"
                "🥉 **Bronze**: 1-5 portfolio\n"
                "🥈 **Silver**: 6-10 portfolio\n"
                "🥇 **Gold**: 11-25 portfolio\n"
                "💎 **Platinum**: 26-50 portfolio\n"
                "💠 **Diamond**: 51-100 portfolio\n"
                "👑 **Master**: 100+ portfolio"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Pro Tips",
            value=(
                "✨ Unlock achievements ASAP untuk luck boost permanent\n"
                "📊 Check `mochi!achievements` untuk target berikutnya\n"
                "🤞 Total luck ditampilkan di `mochi!profile`\n"
                "⭐ Achievement progress auto-tracked\n"
                "🏆 Setiap achievement = currency + permanent luck!"
            ),
            inline=False
        )
        
        embed.set_footer(text="Gunakan mochi!help untuk kembali ke menu utama")
        await ctx.send(embed=embed)

async def init_achievement_tables():
    """Initialize achievement tables"""
    async with aiosqlite.connect("mochi.db") as db:
        # User achievements table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_id TEXT NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                unlocked INTEGER DEFAULT 0,
                UNIQUE(user_id, achievement_id)
            )
        """)
        
        # Portfolio tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                portfolio_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)
        
        await db.commit()
        print("✅ Achievement tables created!")

async def setup(bot):
    await init_achievement_tables()
    await bot.add_cog(Achievements(bot))