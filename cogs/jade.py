import discord
from discord.ext import commands
import aiosqlite
import random
import asyncio
from datetime import datetime, timedelta
from database import get_user, create_user, update_user

class JadeGacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Tipe batu jade dengan tier dan multiplier
        self.jade_types = {
            "common": {
                "name": "Batu Lumpur",
                "emoji": "🪨",
                "price": 100,
                "color": 0x8B4513,
                "min_multi": 0,
                "max_multi": 2,
                "jackpot_chance": 0.0005,  # 0.05%
                "jackpot_multi": 10,
                "loss_chance": 0.60  # 60% 
            },
            "uncommon": {
                "name": "Batu Pasir",
                "emoji": "🗿",
                "price": 1000,
                "color": 0xD2691E,
                "min_multi": 0,
                "max_multi": 2.5,
                "jackpot_chance": 0.0005,  # 0.05%
                "jackpot_multi": 15,
                "loss_chance": 0.65  # 65%
            },
            "rare": {
                "name": "Batu Giok",
                "emoji": "💎",
                "price": 10000,
                "color": 0x50C878,
                "min_multi": 0,
                "max_multi": 3,
                "jackpot_chance": 0.0005,  # 0.05%
                "jackpot_multi": 25,
                "loss_chance": 0.70  # 70%
            },
            "epic": {
                "name": "Batu Jade",
                "emoji": "💠",
                "price": 100000,
                "color": 0x00CED1,
                "min_multi": 0,
                "max_multi": 4,
                "jackpot_chance": 0.0005,  # 0.05%
                "jackpot_multi": 50,
                "loss_chance": 0.80  # 80% 
            },
            "legendary": {
                "name": "Batu Imperial",
                "emoji": "🔮",
                "price": 1000000,
                "color": 0xFF1493,
                "min_multi": 0,
                "max_multi": 5,
                "jackpot_chance": 0.0005,  # 0.05%
                "jackpot_multi": 100,
                "loss_chance": 0.90  # 90% 
            }
        }
        
        # Active cutting sessions
        self.active_sessions = {}
    
    async def save_jade_stats(self, user_id: int, jade_type: str, spent: int, won: int, is_win: bool, is_jackpot: bool):
        """Simpan statistik jade gacha ke database"""
        async with aiosqlite.connect("mochi.db") as db:
            # Check if user stats exist
            cursor = await db.execute("""
                SELECT * FROM jade_stats WHERE user_id = ?
            """, (user_id,))
            existing = await cursor.fetchone()
            
            win_increment = 1 if is_win else 0
            loss_increment = 0 if is_win else 1
            jackpot_increment = 1 if is_jackpot else 0
            
            if existing:
                await db.execute("""
                    UPDATE jade_stats 
                    SET total_spent = total_spent + ?,
                        total_won = total_won + ?,
                        total_cuts = total_cuts + 1,
                        total_wins = total_wins + ?,
                        total_losses = total_losses + ?,
                        total_jackpots = total_jackpots + ?,
                        last_cut_time = ?
                    WHERE user_id = ?
                """, (spent, won, win_increment, loss_increment, jackpot_increment, datetime.utcnow(), user_id))
            else:
                await db.execute("""
                    INSERT INTO jade_stats (user_id, total_spent, total_won, total_cuts, total_wins, total_losses, total_jackpots, last_cut_time)
                    VALUES (?, ?, ?, 1, ?, ?, ?, ?)
                """, (user_id, spent, won, win_increment, loss_increment, jackpot_increment, datetime.utcnow()))
            
            await db.commit()
    
    async def get_jade_stats(self, user_id: int):
        """Ambil statistik jade gacha user"""
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM jade_stats WHERE user_id = ?
            """, (user_id,))
            stats = await cursor.fetchone()
            
            if stats:
                return dict(stats)
            return {
                "total_spent": 0,
                "total_won": 0,
                "total_cuts": 0,
                "total_wins": 0,
                "total_losses": 0,
                "total_jackpots": 0,
                "last_cut_time": None
            }
    
    async def get_user_luck(self, user_id: int):
        """Ambil luck multiplier user dari achievement/items"""
        # TODO: Implementasi sistem achievement/items untuk luck bonus
        # Untuk sekarang return base luck (0%)
        user_data = await get_user(user_id)
        
        # Contoh: Bisa ambil dari achievement, items, atau special rewards
        base_luck = 0.0
        
        # Placeholder untuk future implementation
        # if user has certain achievements:
        #     base_luck += 0.05  # +5% luck
        # if user has lucky charm item:
        #     base_luck += 0.10  # +10% luck
        
        return base_luck
    
    def calculate_reward(self, jade_type_key: str, luck_bonus: float = 0.0):
        """Hitung reward berdasarkan RNG dengan luck modifier"""
        jade = self.jade_types[jade_type_key]
        
        # Apply luck bonus (reduces loss chance, increases win chance)
        adjusted_jackpot = jade["jackpot_chance"] + (luck_bonus * 0.5)  # Luck affects jackpot less
        adjusted_loss = max(0.1, jade["loss_chance"] - luck_bonus)  # Min 10% loss chance
        
        # Random roll untuk menentukan outcome
        roll = random.random()
        
        # Check jackpot
        if roll < adjusted_jackpot:
            multiplier = jade["jackpot_multi"]
            is_jackpot = True
        # Check loss
        elif roll < adjusted_jackpot + adjusted_loss:
            # Loss: 0x hingga 0.95x (tidak dapat balik modal)
            multiplier = random.uniform(0, 0.95)
            is_jackpot = False
        # Sisanya untung
        else:
            # Win: 1.05x hingga max_multi
            multiplier = random.uniform(1.05, jade["max_multi"])
            is_jackpot = False
        
        reward = int(jade["price"] * multiplier)
        profit = reward - jade["price"]
        
        return {
            "reward": reward,
            "profit": profit,
            "multiplier": multiplier,
            "is_jackpot": is_jackpot,
            "is_win": profit > 0
        }
    
    @commands.command(name="jadeshop", aliases=["jshop"])
    async def jade_shop_command(self, ctx):
        """🪨 Lihat daftar batu jade yang bisa dibeli"""
        embed = discord.Embed(
            title="🪨 Jade Stone Shop",
            description="**Potong batu jade dan temukan harta karun!**\n⚠️ High Risk, High Reward!",
            color=0x50C878
        )
        
        for tier, jade in self.jade_types.items():
            win_chance = round((1 - jade["loss_chance"] - jade["jackpot_chance"]) * 100, 1)
            value_text = (
                f"💰 **Harga**: Rp {jade['price']:,}\n"
                f"📊 **Max Return**: {jade['max_multi']}x\n"
                f"🎰 **Jackpot**: 0.05% ({jade['jackpot_multi']}x)\n"
                f"📈 **Win Rate**: {win_chance}%\n"
                f"📉 **Loss Rate**: {jade['loss_chance']*100:.0f}%\n"
                f"💎 **Max Win**: Rp {int(jade['price'] * jade['jackpot_multi']):,}"
            )
            
            # Risk indicator
            if jade["loss_chance"] >= 0.85:
                risk = "🔴 EXTREME RISK"
            elif jade["loss_chance"] >= 0.75:
                risk = "🟠 VERY HIGH RISK"
            elif jade["loss_chance"] >= 0.65:
                risk = "🟡 HIGH RISK"
            else:
                risk = "🟢 MODERATE RISK"
            
            embed.add_field(
                name=f"{jade['emoji']} {jade['name']} - {risk}",
                value=value_text,
                inline=False
            )
        
        embed.add_field(
            name="📌 Cara Main",
            value=(
                "1️⃣ Pilih batu: `mochi!buyjade <tipe>`\n"
                "2️⃣ Konfirmasi pembelian (30 detik)\n"
                "3️⃣ Klik 🔨 untuk memotong batu!\n"
                "4️⃣ Lihat hasilnya! 🎉\n\n"
                "💡 **Luck bonus** dari achievement mengurangi loss rate!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎮 Commands",
            value=(
                "`mochi!buyjade lumpur` - Beli Batu Lumpur\n"
                "`mochi!buyjade pasir` - Beli Batu Pasir\n"
                "`mochi!buyjade giok` - Beli Batu Giok\n"
                "`mochi!buyjade jade` - Beli Batu Jade\n"
                "`mochi!buyjade imperial` - Beli Batu Imperial\n"
                "`mochi!jadestats` - Lihat statistik & luck\n"
                "`mochi!jhelp` - Panduan lengkap"
            ),
            inline=False
        )
        
        embed.set_footer(text="⚠️ Batu mahal = High Risk, High Reward!")
        await ctx.send(embed=embed)
    
    @commands.command(name="buyjade", aliases=["bjade"])
    async def buy_jade_command(self, ctx, jade_type: str = None):
        """🪨 Beli batu jade untuk dipotong"""
        if not jade_type:
            await ctx.send("❌ Pilih tipe batu! Contoh: `mochi!buyjade giok`\nLihat daftar: `mochi!jadeshop`")
            return
        
        # Check if user already has active session
        if ctx.author.id in self.active_sessions:
            await ctx.send("⚠️ Kamu masih punya batu yang belum dipotong! Selesaikan dulu atau tunggu timeout.")
            return
        
        # Parse jade type
        jade_type_lower = jade_type.lower()
        selected_jade = None
        jade_key = None
        
        for key, jade in self.jade_types.items():
            if (jade_type_lower in jade["name"].lower() or 
                jade_type_lower in key.lower()):
                selected_jade = jade
                jade_key = key
                break
        
        if not selected_jade:
            await ctx.send("❌ Batu tidak ditemukan! Gunakan `mochi!jadeshop` untuk lihat daftar.")
            return
        
        # Check user balance
        user_data = await get_user(ctx.author.id)
        if not user_data:
            await create_user(ctx.author.id)
            user_data = await get_user(ctx.author.id)
        
        if user_data["currency"] < selected_jade["price"]:
            await ctx.send(
                f"❌ Saldo tidak cukup!\n"
                f"💰 Butuh: Rp {selected_jade['price']:,}\n"
                f"💳 Saldo: Rp {user_data['currency']:,}"
            )
            return
        
        # Get user luck
        luck_bonus = await self.get_user_luck(ctx.author.id)
        adjusted_loss = max(0.1, selected_jade["loss_chance"] - luck_bonus)
        win_chance = round((1 - adjusted_loss - selected_jade["jackpot_chance"]) * 100, 1)
        
        # Risk indicator
        if adjusted_loss >= 0.85:
            risk = "🔴 EXTREME"
        elif adjusted_loss >= 0.75:
            risk = "🟠 VERY HIGH"
        elif adjusted_loss >= 0.65:
            risk = "🟡 HIGH"
        else:
            risk = "🟢 MODERATE"
        
        # Confirmation embed
        confirm_embed = discord.Embed(
            title=f"🪨 Konfirmasi Pembelian",
            description=f"Apa kamu yakin ingin membeli **{selected_jade['name']}**?",
            color=selected_jade["color"]
        )
        confirm_embed.add_field(name="💰 Harga", value=f"Rp {selected_jade['price']:,}", inline=True)
        confirm_embed.add_field(name="💳 Saldo", value=f"Rp {user_data['currency']:,}", inline=True)
        confirm_embed.add_field(name="⚠️ Risk Level", value=risk, inline=True)
        confirm_embed.add_field(
            name="🎰 Peluang",
            value=(
                f"🎰 Jackpot: 0.05% ({selected_jade['jackpot_multi']}x)\n"
                f"📈 Untung: {win_chance}%\n"
                f"📉 Rugi: {adjusted_loss*100:.0f}%"
            ),
            inline=False
        )
        
        if luck_bonus > 0:
            confirm_embed.add_field(
                name="🍀 Luck Bonus",
                value=f"+{luck_bonus*100:.1f}% (Mengurangi loss rate!)",
                inline=False
            )
        
        confirm_embed.set_footer(text="Klik ✅ untuk konfirmasi atau ❌ untuk batalkan (30 detik)")
        
        confirm_msg = await ctx.send(embed=confirm_embed)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return (user == ctx.author and 
                    str(reaction.emoji) in ["✅", "❌"] and 
                    reaction.message.id == confirm_msg.id)
        
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await confirm_msg.edit(embed=discord.Embed(
                    title="❌ Pembelian Dibatalkan",
                    description="Pembelian batu jade dibatalkan.",
                    color=0xff0000
                ))
                await confirm_msg.clear_reactions()
                return
            
            # Process purchase (✅ clicked)
            await update_user(ctx.author.id, currency=-selected_jade["price"])
            
            # Create cutting session
            cutting_embed = discord.Embed(
                title=f"🪨 {selected_jade['name']} Siap Dipotong!",
                description=(
                    f"{selected_jade['emoji']} **Batu kamu sudah siap!**\n\n"
                    f"Klik 🔨 untuk memotong batu dan lihat isinya!\n\n"
                    f"*Apakah ada harta karun di dalamnya?*"
                ),
                color=selected_jade["color"]
            )
            cutting_embed.add_field(name="💰 Investasi", value=f"Rp {selected_jade['price']:,}", inline=True)
            cutting_embed.add_field(name="🎰 Win Rate", value=f"{win_chance}%", inline=True)
            cutting_embed.add_field(name="📉 Loss Rate", value=f"{adjusted_loss*100:.0f}%", inline=True)
            cutting_embed.set_footer(text="Klik 🔨 untuk memotong! (60 detik)")
            
            await confirm_msg.clear_reactions()
            await confirm_msg.edit(embed=cutting_embed)
            await confirm_msg.add_reaction("🔨")
            
            # Store session with luck bonus
            self.active_sessions[ctx.author.id] = {
                "message": confirm_msg,
                "jade_key": jade_key,
                "jade_data": selected_jade,
                "luck_bonus": luck_bonus,
                "time": datetime.utcnow()
            }
            
            # Wait for cutting reaction
            def cut_check(reaction, user):
                return (user == ctx.author and 
                        str(reaction.emoji) == "🔨" and 
                        reaction.message.id == confirm_msg.id)
            
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=cut_check)
                
                # Process cutting
                await self.process_cutting(ctx, confirm_msg, jade_key, selected_jade, luck_bonus)
                
            except asyncio.TimeoutError:
                # Timeout - refund
                await update_user(ctx.author.id, currency=selected_jade["price"])
                
                timeout_embed = discord.Embed(
                    title="⏰ Waktu Habis!",
                    description=f"Batu tidak dipotong. Uang dikembalikan: Rp {selected_jade['price']:,}",
                    color=0xff9900
                )
                await confirm_msg.edit(embed=timeout_embed)
                await confirm_msg.clear_reactions()
                
                if ctx.author.id in self.active_sessions:
                    del self.active_sessions[ctx.author.id]
        
        except asyncio.TimeoutError:
            # Confirmation timeout
            timeout_embed = discord.Embed(
                title="⏰ Waktu Konfirmasi Habis",
                description="Pembelian dibatalkan karena tidak ada konfirmasi.",
                color=0xff9900
            )
            await confirm_msg.edit(embed=timeout_embed)
            await confirm_msg.clear_reactions()
    
    async def process_cutting(self, ctx, message, jade_key, jade_data, luck_bonus):
        """Process the jade cutting and reveal reward"""
        # Calculate reward
        result = self.calculate_reward(jade_key, luck_bonus)
        
        # Cutting animation
        cutting_embed = discord.Embed(
            title="🔨 Memotong Batu...",
            description=f"{jade_data['emoji']} *Tuk... tuk... tuk...*",
            color=jade_data["color"]
        )
        await message.edit(embed=cutting_embed)
        await message.clear_reactions()
        await asyncio.sleep(2)
        
        # Reveal result
        if result["is_jackpot"]:
            result_embed = discord.Embed(
                title="🎰 JACKPOT! 🎰",
                description=(
                    f"# {jade_data['emoji']} **LUAR BIASA!** {jade_data['emoji']}\n\n"
                    f"Kamu menemukan harta karun langka!\n"
                    f"**{result['multiplier']:.0f}x JACKPOT MULTIPLIER!**"
                ),
                color=0xFFD700  # Gold
            )
        elif result["profit"] > 0:
            result_embed = discord.Embed(
                title="✨ Untung!",
                description=f"{jade_data['emoji']} Kamu menemukan sesuatu berharga di dalam batu!",
                color=0x00ff00
            )
        elif result["profit"] == 0:
            result_embed = discord.Embed(
                title="😐 Break Even",
                description=f"{jade_data['emoji']} Modal kembali! Tidak untung, tidak rugi.",
                color=0xffff00
            )
        else:
            result_embed = discord.Embed(
                title="💔 Rugi",
                description=f"{jade_data['emoji']} Sayangnya batu ini tidak ada isinya...",
                color=0xff0000
            )
        
        result_embed.add_field(name="💰 Investasi", value=f"Rp {jade_data['price']:,}", inline=True)
        result_embed.add_field(name="💎 Hasil", value=f"Rp {result['reward']:,}", inline=True)
        result_embed.add_field(
            name="📊 Profit/Loss",
            value=f"**{result['profit']:+,} Rp** ({result['multiplier']:.2f}x)",
            inline=True
        )
        
        if result["is_jackpot"]:
            result_embed.add_field(
                name="🎉 Bonus Jackpot!",
                value=f"Kamu sangat beruntung! Peluang: 0.05%",
                inline=False
            )
        
        if luck_bonus > 0:
            result_embed.add_field(
                name="🍀 Luck Bonus Active",
                value=f"+{luck_bonus*100:.1f}% luck meningkatkan peluangmu!",
                inline=False
            )
        
        result_embed.set_footer(text="Gunakan mochi!jadeshop untuk membeli lagi!")
        
        await message.edit(embed=result_embed)
        
        # Update user currency
        await update_user(ctx.author.id, currency=result["reward"])
        
        
        # Save stats
        await self.save_jade_stats(
            ctx.author.id, 
            jade_key, 
            jade_data["price"], 
            result["reward"],
            result["is_win"],
            result["is_jackpot"]
        )
        
          # Update quest progress
        ach_cog = self.bot.get_cog('Achievements')
        if ach_cog:
            # Quest jade_cut hanya untuk rare+
            if jade_key in ["rare", "epic", "legendary"]:
                await ach_cog.update_quest_progress(ctx.author.id, "jade_cut", 1)

        # Remove session
        if ctx.author.id in self.active_sessions:
            del self.active_sessions[ctx.author.id]
        
        # Announcement for big wins
        if result["is_jackpot"] and jade_data["price"] >= 10000:
            announce_embed = discord.Embed(
                title="🎰 JACKPOT ANNOUNCEMENT! 🎰",
                description=(
                    f"**{ctx.author.display_name}** mendapat JACKPOT!\n"
                    f"{jade_data['emoji']} **{jade_data['name']}**\n"
                    f"💰 Menang: **Rp {result['reward']:,}**"
                ),
                color=0xFFD700
            )
            await ctx.send(embed=announce_embed)
    
    @commands.command(name="jadestats", aliases=["jstats"])
    async def jade_stats_command(self, ctx, member: discord.Member = None):
        """📊 Lihat statistik jade gacha"""
        user = member or ctx.author
        stats = await self.get_jade_stats(user.id)
        luck_bonus = await self.get_user_luck(user.id)
        
        embed = discord.Embed(
            title=f"📊 Jade Gacha Stats - {user.display_name}",
            color=0x50C878
        )
        
        # Financial stats
        embed.add_field(name="💰 Total Spent", value=f"Rp {stats['total_spent']:,}", inline=True)
        embed.add_field(name="💎 Total Won", value=f"Rp {stats['total_won']:,}", inline=True)
        embed.add_field(name="🪨 Total Cuts", value=f"{stats['total_cuts']:,}x", inline=True)
        
        # Win/Loss stats
        if stats["total_cuts"] > 0:
            win_rate = (stats["total_wins"] / stats["total_cuts"]) * 100
            loss_rate = (stats["total_losses"] / stats["total_cuts"]) * 100
        else:
            win_rate = 0
            loss_rate = 0
        
        embed.add_field(name="📈 Wins", value=f"{stats['total_wins']:,}x ({win_rate:.1f}%)", inline=True)
        embed.add_field(name="📉 Losses", value=f"{stats['total_losses']:,}x ({loss_rate:.1f}%)", inline=True)
        embed.add_field(name="🎰 Jackpots", value=f"{stats['total_jackpots']:,}x", inline=True)
        
        # Calculate profit/loss
        profit = stats["total_won"] - stats["total_spent"]
        profit_percent = ((profit / stats["total_spent"]) * 100) if stats["total_spent"] > 0 else 0
        
        if profit > 0:
            profit_text = f"🟢 +Rp {profit:,} ({profit_percent:+.1f}%)"
            profit_color = 0x00ff00
        elif profit < 0:
            profit_text = f"🔴 Rp {profit:,} ({profit_percent:.1f}%)"
            profit_color = 0xff0000
        else:
            profit_text = f"⚪ Break Even (0%)"
            profit_color = 0xffff00
        
        embed.add_field(name="📊 Net Profit/Loss", value=profit_text, inline=False)
        
        # Luck bonus info
        if luck_bonus > 0:
            luck_text = f"🍀 **+{luck_bonus*100:.1f}%** (Mengurangi loss rate!)"
            embed.add_field(name="🎲 Luck Bonus", value=luck_text, inline=False)
        else:
            embed.add_field(
                name="🎲 Luck Bonus", 
                value="🔒 **0%** (Unlock achievement untuk luck bonus!)", 
                inline=False
            )
        
        embed.color = profit_color
        
        if stats["last_cut_time"]:
            last_cut = datetime.fromisoformat(stats["last_cut_time"])
            embed.set_footer(text=f"Terakhir potong: {last_cut.strftime('%d/%m/%Y %H:%M')}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="jadeleaderboard", aliases=["jlb"])
    async def jade_leaderboard_command(self, ctx, sort_by: str = "profit"):
        """🏆 Leaderboard jade gacha"""
        valid_sorts = {
            "profit": ("profit DESC", "💰 Profit"),
            "spent": ("total_spent DESC", "💸 Total Spent"),
            "won": ("total_won DESC", "💎 Total Won"),
            "cuts": ("total_cuts DESC", "🪨 Total Cuts"),
            "jackpots": ("total_jackpots DESC", "🎰 Jackpots"),
            "winrate": ("win_rate DESC", "📈 Win Rate")
        }
        
        sort_key = sort_by.lower()
        if sort_key not in valid_sorts:
            sort_key = "profit"
        
        order_by, title_suffix = valid_sorts[sort_key]
        
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            
            # Special handling for win rate
            if sort_key == "winrate":
                cursor = await db.execute("""
                    SELECT user_id, total_spent, total_won, total_cuts, total_wins, total_losses, total_jackpots,
                           (total_won - total_spent) as profit,
                           CAST(total_wins AS FLOAT) / total_cuts * 100 as win_rate
                    FROM jade_stats
                    WHERE total_cuts > 0
                    ORDER BY win_rate DESC
                    LIMIT 10
                """)
            else:
                cursor = await db.execute(f"""
                    SELECT user_id, total_spent, total_won, total_cuts, total_wins, total_losses, total_jackpots,
                           (total_won - total_spent) as profit,
                           CAST(total_wins AS FLOAT) / total_cuts * 100 as win_rate
                    FROM jade_stats
                    ORDER BY {order_by}
                    LIMIT 10
                """)
            rows = await cursor.fetchall()
        
        if not rows:
            await ctx.send("📊 Belum ada data leaderboard!")
            return
        
        embed = discord.Embed(
            title=f"🏆 Jade Gacha Leaderboard - {title_suffix}",
            color=0xFFD700
        )
        
        leaderboard_text = ""
        for i, row in enumerate(rows, 1):
            user = self.bot.get_user(row["user_id"])
            username = user.display_name if user else f"User#{row['user_id']}"
            
            profit = row["profit"]
            profit_emoji = "🟢" if profit > 0 else "🔴" if profit < 0 else "⚪"
            
            leaderboard_text += (
                f"**{i}.** {username}\n"
                f"   {profit_emoji} Profit: Rp {profit:+,}\n"
                f"   💰 Spent: Rp {row['total_spent']:,} | 💎 Won: Rp {row['total_won']:,}\n"
                f"   📊 W/L: {row['total_wins']}/{row['total_losses']} ({row['win_rate']:.1f}%) | 🎰 {row['total_jackpots']}x\n\n"
            )
        
        embed.description = leaderboard_text
        embed.add_field(
            name="📋 Sort Options",
            value=(
                "`profit` • `spent` • `won` • `cuts` • `jackpots` • `winrate`\n"
                f"Contoh: `mochi!jlb winrate`"
            ),
            inline=False
        )
        embed.set_footer(text="Gunakan mochi!jadestats untuk lihat stats kamu")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="jrate", aliases=["jaderate"])
    async def jade_rate_command(self, ctx):
        """📊 Lihat rate jade gacha untuk semua tier"""
        user_luck = await self.get_user_luck(ctx.author.id)
        
        embed = discord.Embed(
            title="📊 Jade Gacha - Win/Loss Rates",
            description=f"Rate untuk semua tier batu jade\n🍀 **Your Luck Bonus**: {user_luck*100:.1f}%",
            color=0x50C878
        )
        
        for tier, jade in self.jade_types.items():
            # Calculate adjusted rates with luck
            adjusted_jackpot = jade["jackpot_chance"] + (user_luck * 0.5)
            adjusted_loss = max(0.1, jade["loss_chance"] - user_luck)
            adjusted_win = 1 - adjusted_jackpot - adjusted_loss
            
            # Risk indicator
            if adjusted_loss >= 0.85:
                risk = "🔴 EXTREME"
            elif adjusted_loss >= 0.75:
                risk = "🟠 VERY HIGH"
            elif adjusted_loss >= 0.65:
                risk = "🟡 HIGH"
            else:
                risk = "🟢 MODERATE"
            
            rate_text = (
                f"**Price**: Rp {jade['price']:,}\n"
                f"🎰 Jackpot: {adjusted_jackpot*100:.2f}% ({jade['jackpot_multi']}x)\n"
                f"📈 Win: {adjusted_win*100:.1f}% (1.05x - {jade['max_multi']}x)\n"
                f"📉 Loss: {adjusted_loss*100:.1f}% (0x - 0.95x)"
            )
            
            embed.add_field(
                name=f"{jade['emoji']} {jade['name']} - {risk}",
                value=rate_text,
                inline=False
            )
        
        embed.add_field(
            name="💡 Info",
            value=(
                "• Luck bonus mengurangi loss rate!\n"
                "• Min loss rate: 10% (dengan luck tinggi)\n"
                "• Jackpot rate: 0.05% untuk semua tier\n"
                "• Unlock achievement untuk luck bonus"
            ),
            inline=False
        )
        
        embed.set_footer(text="Gunakan mochi!jadeshop untuk lihat daftar batu")
        await ctx.send(embed=embed)
    
    @commands.command(name="jhelp", aliases=["jadehelp"])
    async def jade_help_command(self, ctx):
        """📖 Panduan jade gacha system"""
        embed = discord.Embed(
            title="📖 Jade Stone Gacha - Help",
            description="Sistem gacha memotong batu jade! Temukan harta karun!",
            color=0x50C878
        )
        
        embed.add_field(
            name="🎮 Cara Bermain",
            value=(
                "1️⃣ Lihat daftar batu: `mochi!jadeshop`\n"
                "2️⃣ Beli batu: `mochi!buyjade <tipe>`\n"
                "3️⃣ Konfirmasi pembelian (30 detik)\n"
                "4️⃣ Klik 🔨 untuk potong (60 detik)\n"
                "5️⃣ Lihat hasilmu! 🎉"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Risk Levels",
            value=(
                "🟢 **Common (60% loss)** - Moderate risk\n"
                "🟡 **Uncommon (65% loss)** - Moderate risk\n"
                "🟠 **Rare (70% loss)** - High risk\n"
                "🔴 **Epic (80% loss)** - Very high risk\n"
                "⚫ **Legendary (90% loss)** - EXTREME risk!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Tips & Trik",
            value=(
                "🪨 Batu murah = safer, reward kecil\n"
                "💎 Batu mahal = HIGH RISK, HIGH REWARD!\n"
                "🎰 Jackpot: 0.05% untuk semua tier\n"
                "🍀 Unlock achievement untuk luck bonus\n"
                "📊 Luck bonus mengurangi loss rate!\n"
                "⏰ Jangan lupa potong sebelum timeout!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📋 Commands",
            value=(
                "`mochi!jadeshop` - Lihat daftar batu\n"
                "`mochi!buyjade <tipe>` - Beli batu\n"
                "`mochi!jadestats [@user]` - Stats & luck\n"
                "`mochi!jlb [sort]` - Leaderboard\n"
                "`mochi!jrate` - Lihat win/loss rates\n"
                "`mochi!jhelp` - Panduan ini\n\n"
                "**Sort options**: profit, spent, won, cuts, jackpots, winrate"
            ),
            inline=False
        )
        
        embed.set_footer(text="Good luck! 🍀 High risk, high reward!")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(JadeGacha(bot))