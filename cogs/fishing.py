import discord
from discord.ext import commands, tasks
import aiosqlite
import random
import asyncio
from datetime import datetime, timedelta
from database import get_user, create_user, update_user

class Fishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fish_market_prices = {}
        self.last_price_update = None
        
        # Tracking auto fishing
        self.auto_fishing_tasks = {}
        self.auto_fishing_end_time = {}
        
        # Data ikan dengan rarity dan base price
        self.fish_types = {
            "common": [
                {"name": "Ikan Teri", "emoji": "🐟", "base_price": 50, "weight": 40},
                {"name": "Ikan Bandeng", "emoji": "🐠", "base_price": 100, "weight": 30},
                {"name": "Ikan Nila", "emoji": "🐡", "base_price": 150, "weight": 20},
                {"name": "Ikan Lele", "emoji": "🎣", "base_price": 120, "weight": 25}
            ],
            "uncommon": [
                {"name": "Ikan Kakap", "emoji": "🐟", "base_price": 300, "weight": 15},
                {"name": "Ikan Tongkol", "emoji": "🐠", "base_price": 400, "weight": 12},
                {"name": "Ikan Kembung", "emoji": "🐡", "base_price": 350, "weight": 13}
            ],
            "rare": [
                {"name": "Ikan Tuna", "emoji": "🐟", "base_price": 800, "weight": 7},
                {"name": "Ikan Salmon", "emoji": "🐠", "base_price": 1000, "weight": 5},
                {"name": "Ikan Barakuda", "emoji": "🦈", "base_price": 900, "weight": 6}
            ],
            "epic": [
                {"name": "Ikan Marlin", "emoji": "🐟", "base_price": 2000, "weight": 3},
                {"name": "Ikan Hiu", "emoji": "🦈", "base_price": 3000, "weight": 2}
            ],
            "legendary": [
                {"name": "Ikan Paus", "emoji": "🐋", "base_price": 10000, "weight": 0.5},
                {"name": "Ikan Naga", "emoji": "🐉", "base_price": 50000, "weight": 0.1}
            ]
        }
        
        # Upgrades yang bisa dibeli
        self.upgrades = {
            "fishing_rod": {
                "name": "Fishing Rod",
                "emoji": "🎣",
                "description": "Raises collected fish per message",
                "max_level": 100,
                "base_cost": 200,
                "multiplier": 1.18,
                "bonus_per_level": 0.5
            },
            "fishing_robot": {
                "name": "Fishing Robot",
                "emoji": "🤖",
                "description": "Raises daily fish (passive income)",
                "max_level": 50,
                "base_cost": 5000,
                "multiplier": 1.20,
                "bonus_per_level": 10
            },
            "fishing_net": {
                "name": "Fishing Net",
                "emoji": "🕸️",
                "description": "Raises fish per minute in Voice Channel",
                "max_level": 150,
                "base_cost": 15000,
                "multiplier": 1.15,
                "bonus_per_level": 5
            }
        }
        
        # Tax rate untuk penjualan ikan
        self.sell_tax_rate = 0.25  # 25% pajak
        
        # Start background task
        self.update_market_prices.start()
    
    def cog_unload(self):
        self.update_market_prices.cancel()
        for task in self.auto_fishing_tasks.values():
            task.cancel()
    
    @tasks.loop(minutes=15)
    async def update_market_prices(self):
        """Update harga pasar ikan secara dinamis"""
        for rarity, fish_list in self.fish_types.items():
            for fish in fish_list:
                fluctuation = random.uniform(0.8, 1.2)
                self.fish_market_prices[fish["name"]] = int(fish["base_price"] * fluctuation)
        
        self.last_price_update = datetime.utcnow()
        print("🐟 Market prices updated!")
    
    @update_market_prices.before_loop
    async def before_price_update(self):
        await self.bot.wait_until_ready()
        for rarity, fish_list in self.fish_types.items():
            for fish in fish_list:
                self.fish_market_prices[fish["name"]] = fish["base_price"]
    
    def get_fish_price(self, fish_name: str) -> int:
        """Ambil harga ikan saat ini"""
        return self.fish_market_prices.get(fish_name, 0)
    
    async def get_user_fishing_data(self, user_id: int):
        """Ambil data fishing user dari database"""
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            
            cursor = await db.execute("""
                SELECT * FROM fishing_stats WHERE user_id = ?
            """, (user_id,))
            stats = await cursor.fetchone()
            
            if not stats:
                await db.execute("""
                    INSERT INTO fishing_stats (user_id, total_fish_caught, last_fish_time)
                    VALUES (?, 0, ?)
                """, (user_id, datetime.utcnow()))
                await db.commit()
                stats = {"total_fish_caught": 0, "last_fish_time": datetime.utcnow()}
            
            cursor = await db.execute("""
                SELECT upgrade_type, level FROM fishing_upgrades WHERE user_id = ?
            """, (user_id,))
            upgrades_rows = await cursor.fetchall()
            upgrades_dict = {row["upgrade_type"]: row["level"] for row in upgrades_rows}
            
            cursor = await db.execute("""
                SELECT fish_name, amount FROM fishing_inventory WHERE user_id = ?
            """, (user_id,))
            inventory_rows = await cursor.fetchall()
            inventory_dict = {row["fish_name"]: row["amount"] for row in inventory_rows}
            
            return {
                "stats": dict(stats) if stats else {},
                "upgrades": upgrades_dict,
                "inventory": inventory_dict
            }
    
    def calculate_upgrade_cost(self, upgrade_key: str, current_level: int) -> int:
        """Hitung harga upgrade berikutnya"""
        upgrade = self.upgrades[upgrade_key]
        cost = upgrade["base_cost"] * (upgrade["multiplier"] ** current_level)
        return int(cost)
    
    def get_random_fish(self, rod_level: int = 0):
        """Ambil ikan random berdasarkan weight dan rod level"""
        luck_bonus = rod_level * 0.5
        
        all_fish = []
        for rarity, fish_list in self.fish_types.items():
            for fish in fish_list:
                adjusted_weight = fish["weight"]
                if rarity in ["rare", "epic", "legendary"]:
                    adjusted_weight += luck_bonus
                
                all_fish.append((fish, adjusted_weight))
        
        total_weight = sum(w for _, w in all_fish)
        rand = random.uniform(0, total_weight)
        
        current = 0
        for fish, weight in all_fish:
            current += weight
            if rand <= current:
                return fish
        
        return all_fish[0][0]
    
    async def perform_fishing(self, user_id: int, channel_id: int, guild_id: int, is_auto: bool = False):
        """Core fishing logic"""
        user_data = await get_user(user_id)
        if not user_data:
            await create_user(user_id)
        
        fishing_data = await self.get_user_fishing_data(user_id)
        
        # Check voice channel
        voice_bonus = 1.0
        in_voice = False
        
        guild = self.bot.get_guild(guild_id)
        if guild:
            member = guild.get_member(user_id)
            if member and member.voice and member.voice.channel:
                voice_bonus = 2.5
                in_voice = True
        
        # Formula tier-based berdasarkan rod level
        rod_level = fishing_data["upgrades"].get("fishing_rod", 0)
        
        if rod_level == 0:
            base_catch_count = random.randint(1, 2)
            fish_amount_min = 1
            fish_amount_max = 1
        elif rod_level < 10:
            base_catch_count = random.randint(1, 2)
            fish_amount_min = 1
            fish_amount_max = 2
        elif rod_level < 25:
            base_catch_count = random.randint(2, 3)
            fish_amount_min = 1
            fish_amount_max = 2
        elif rod_level < 50:
            base_catch_count = random.randint(2, 4)
            fish_amount_min = 1
            fish_amount_max = 3
        else:
            base_catch_count = random.randint(3, 5)
            fish_amount_min = 2
            fish_amount_max = 4
        
        # Apply voice bonus
        if in_voice:
            base_catch_count = int(base_catch_count * voice_bonus)
        
        # Catch fish
        caught_fish = []
        for _ in range(base_catch_count):
            fish = self.get_random_fish(rod_level)
            amount = random.randint(fish_amount_min, fish_amount_max)
            
            if in_voice:
                amount = int(amount * 1.5)
            
            caught_fish.append((fish, amount))
        
        # Update database
        async with aiosqlite.connect("mochi.db") as db:
            await db.execute("""
                UPDATE fishing_stats 
                SET total_fish_caught = total_fish_caught + ?, 
                    last_fish_time = ?
                WHERE user_id = ?
            """, (sum(amt for _, amt in caught_fish), datetime.utcnow(), user_id))
            
            for fish, amount in caught_fish:
                cursor = await db.execute("""
                    SELECT amount FROM fishing_inventory 
                    WHERE user_id = ? AND fish_name = ?
                """, (user_id, fish["name"]))
                existing = await cursor.fetchone()
                
                if existing:
                    await db.execute("""
                        UPDATE fishing_inventory 
                        SET amount = amount + ? 
                        WHERE user_id = ? AND fish_name = ?
                    """, (amount, user_id, fish["name"]))
                else:
                    await db.execute("""
                        INSERT INTO fishing_inventory (user_id, fish_name, amount)
                        VALUES (?, ?, ?)
                    """, (user_id, fish["name"], amount))
            
            await db.commit()
        
        # Build response
        catch_text = ""
        total_value = 0
        
        for fish, amount in caught_fish:
            price = self.get_fish_price(fish["name"])
            value = price * amount
            total_value += value
            catch_text += f"{fish['emoji']} **{fish['name']}** x{amount} (Rp {value:,})\n"
        
        embed = discord.Embed(
            title=f"{'🤖 Auto-Fishing' if is_auto else '🎣 Hasil Memancing'}!",
            description=catch_text,
            color=0x3498db
        )
        
        if in_voice:
            embed.add_field(
                name="🎤 Voice Bonus",
                value="**+150%** ikan! (2.5x multiplier)",
                inline=False
            )
        
        embed.add_field(name="💰 Total Nilai", value=f"Rp {total_value:,}", inline=True)
        embed.add_field(name="🎒 Inventory", value="Gunakan `mochi!inventory`", inline=True)
        
        footer_text = "Jual: mochi!sellfish • Harga berubah tiap 15 menit!"
        if not in_voice:
            footer_text = "💡 Join VC untuk +150% ikan! • " + footer_text
    
        embed.set_footer(text=footer_text)
    
        # ========================================
        # ✅ UPDATE QUEST PROGRESS
        # ========================================
        quest_cog = self.bot.get_cog('Quests')
        if quest_cog:
            # Quest: fish_any (tangkap ikan apapun)
            total_fish_caught_quest = sum(amt for _, amt in caught_fish)
            await quest_cog.update_quest_progress(user_id, "fish_any", total_fish_caught_quest)
            
            # Quest: fish_rare (tangkap ikan rare+)
            rare_count = 0
            for fish, amount in caught_fish:
                for rarity, fish_list in self.fish_types.items():
                    if rarity in ["rare", "epic", "legendary"]:
                        if fish in fish_list:
                            rare_count += amount
                            break
            
            if rare_count > 0:
                await quest_cog.update_quest_progress(user_id, "fish_rare", rare_count)
        
        # ========================================
        # ✅ UPDATE ACHIEVEMENT PROGRESS
        # ========================================
        ach_cog = self.bot.get_cog('Achievements')
        if ach_cog:
            # Achievement: total fish caught
            fishing_stats = await self.get_user_fishing_data(user_id)
            total_caught = fishing_stats["stats"].get("total_fish_caught", 0)
            await ach_cog.check_achievement_progress(user_id, "fish_caught", total_caught)
            
            # Achievement: legendary fish
            for fish, amount in caught_fish:
                for rarity, fish_list in self.fish_types.items():
                    if rarity == "legendary" and fish in fish_list:
                        await ach_cog.check_achievement_progress(user_id, "legendary_fish", 1)
                        break
        
        # ========================================
        # KIRIM EMBED
        # ========================================
        channel = self.bot.get_channel(channel_id)
        if channel:
            await channel.send(f"<@{user_id}>", embed=embed)
        
        return True
    
    async def auto_fishing_loop(self, user_id: int, channel_id: int, guild_id: int, duration_hours: int):
        """Loop auto fishing setiap 1 menit"""
        import time
        end_time = datetime.utcnow() + timedelta(hours=duration_hours)
        self.auto_fishing_end_time[user_id] = end_time
        
        try:
            while datetime.utcnow() < end_time:
                await self.perform_fishing(user_id, channel_id, guild_id, is_auto=True)
                await asyncio.sleep(60)
            
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(
                    f"<@{user_id}> ⏰ **Auto-fishing selesai!** ({duration_hours} jam)\n"
                    f"Gunakan `mochi!autofish` lagi untuk melanjutkan."
                )
        except asyncio.CancelledError:
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(f"<@{user_id}> 🛑 **Auto-fishing dihentikan!**")
        finally:
            if user_id in self.auto_fishing_tasks:
                del self.auto_fishing_tasks[user_id]
            if user_id in self.auto_fishing_end_time:
                del self.auto_fishing_end_time[user_id]
    
    @commands.command(name="autofish", aliases=["af"])
    async def autofish_command(self, ctx, duration: int = 2):
        """🤖 Auto-fishing setiap 1 menit"""
        import time
        
        if duration < 1 or duration > 12:
            await ctx.send("⏰ Durasi harus antara 1-12 jam!")
            return
        
        if ctx.author.id in self.auto_fishing_tasks:
            await ctx.send("⚠️ Auto-fishing sudah berjalan! Gunakan `mochi!stopautofish`")
            return
        
        task = asyncio.create_task(
            self.auto_fishing_loop(ctx.author.id, ctx.channel.id, ctx.guild.id, duration)
        )
        self.auto_fishing_tasks[ctx.author.id] = task
        
        end_timestamp = int(time.time()) + (duration * 3600)
        
        embed = discord.Embed(
            title="🤖 Auto-Fishing Dimulai!",
            description=f"Fishing otomatis setiap **1 menit** selama **{duration} jam**",
            color=0x00ff00
        )
        embed.add_field(
            name="⏰ Selesai pada",
            value=f"<t:{end_timestamp}:F>\n(<t:{end_timestamp}:R>)",
            inline=False
        )
        embed.add_field(name="💡 Tips", value="Join VC untuk +150% bonus!", inline=False)
        embed.set_footer(text="mochi!stopautofish untuk stop • mochi!afstatus untuk status")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="stopautofish", aliases=["stopaf"])
    async def stop_autofish_command(self, ctx):
        """🛑 Stop auto-fishing"""
        if ctx.author.id not in self.auto_fishing_tasks:
            await ctx.send("❌ Auto-fishing tidak aktif!")
            return
        
        self.auto_fishing_tasks[ctx.author.id].cancel()
        await ctx.send("🛑 **Auto-fishing dihentikan!**")
    
    @commands.command(name="afstatus", aliases=["autofishstatus"])
    async def autofish_status_command(self, ctx):
        """📊 Cek status auto-fishing"""
        if ctx.author.id not in self.auto_fishing_tasks:
            await ctx.send("❌ Auto-fishing tidak aktif!\nGunakan `mochi!autofish`")
            return
        
        end_time = self.auto_fishing_end_time.get(ctx.author.id)
        if not end_time:
            await ctx.send("❌ Data tidak ditemukan!")
            return
        
        remaining = end_time - datetime.utcnow()
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        
        embed = discord.Embed(title="📊 Status Auto-Fishing", color=0x3498db)
        embed.add_field(name="⏰ Sisa Waktu", value=f"**{hours} jam {minutes} menit**", inline=False)
        embed.add_field(name="🏁 Selesai", value=f"<t:{int(end_time.timestamp())}:F>", inline=False)
        embed.set_footer(text="mochi!stopautofish untuk menghentikan")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="fish")
    async def fish_command(self, ctx):
        """🎣 Memancing ikan! Cooldown 1 menit"""
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        
        # 1. Check if Auto-fishing is running
        if user_id in self.auto_fishing_tasks:
            end_time = self.auto_fishing_end_time.get(user_id)
            if end_time and datetime.utcnow() < end_time:
                 remaining_time = end_time - datetime.utcnow()
                 hours = int(remaining_time.total_seconds() // 3600)
                 minutes = int((remaining_time.total_seconds() % 3600) // 60)
                 
                 await ctx.send(
                     f"🤖 **Auto-fishing sedang aktif!** Kamu akan menerima ikan otomatis.\n"
                     f"Sisa waktu: **{hours} jam {minutes} menit**."
                 )
                 return

        user_data = await get_user(user_id)
        if not user_data:
            await create_user(user_id)
        
        # 2. Check Cooldown 1 Menit (Universal Cooldown)
        fishing_data = await self.get_user_fishing_data(user_id)
        last_fish_time_str = fishing_data["stats"].get("last_fish_time")
        
        cooldown_duration = timedelta(minutes=1)
        
        if last_fish_time_str:
            # Menggunakan datetime.fromisoformat untuk string dari database
            last_time = datetime.fromisoformat(last_fish_time_str)
            
            if datetime.utcnow() - last_time < cooldown_duration:
                remaining = cooldown_duration - (datetime.utcnow() - last_time)
                # Tampilkan sisa waktu cooldown
                await ctx.send(f"⏳ Tunggu **{remaining.seconds}s** lagi untuk `mochi!fish`.")
                return
        
        # 3. Panggil CORE LOGIC (perform_fishing menangani penangkapan dan DB update)
        await self.perform_fishing(user_id, channel_id, guild_id, is_auto=False)
        # Check voice bonus
        voice_bonus = 1.0
        in_voice = False
        if ctx.author.voice and ctx.author.voice.channel:
            voice_bonus = 2.5
            in_voice = True
        
        # Tier-based catch system
        rod_level = fishing_data["upgrades"].get("fishing_rod", 0)
        
        if rod_level == 0:
            base_catch_count = random.randint(1, 2)
            fish_amount_min = 1
            fish_amount_max = 1
        elif rod_level < 10:
            base_catch_count = random.randint(1, 2)
            fish_amount_min = 1
            fish_amount_max = 2
        elif rod_level < 25:
            base_catch_count = random.randint(2, 3)
            fish_amount_min = 1
            fish_amount_max = 2
        elif rod_level < 50:
            base_catch_count = random.randint(2, 4)
            fish_amount_min = 1
            fish_amount_max = 3
        else:
            base_catch_count = random.randint(3, 5)
            fish_amount_min = 2
            fish_amount_max = 4
        
        if in_voice:
            base_catch_count = int(base_catch_count * voice_bonus)
        
        # Catch fish
        caught_fish = []
        for _ in range(base_catch_count):
            fish = self.get_random_fish(rod_level)
            amount = random.randint(fish_amount_min, fish_amount_max)
            
            if in_voice:
                amount = int(amount * 1.5)
            
            caught_fish.append((fish, amount))
        
        # Update database
        async with aiosqlite.connect("mochi.db") as db:
            await db.execute("""
                UPDATE fishing_stats 
                SET total_fish_caught = total_fish_caught + ?, 
                    last_fish_time = ?
                WHERE user_id = ?
            """, (sum(amt for _, amt in caught_fish), datetime.utcnow(), ctx.author.id))
            
            for fish, amount in caught_fish:
                cursor = await db.execute("""
                    SELECT amount FROM fishing_inventory 
                    WHERE user_id = ? AND fish_name = ?
                """, (ctx.author.id, fish["name"]))
                existing = await cursor.fetchone()
                
                if existing:
                    await db.execute("""
                        UPDATE fishing_inventory 
                        SET amount = amount + ? 
                        WHERE user_id = ? AND fish_name = ?
                    """, (amount, ctx.author.id, fish["name"]))
                else:
                    await db.execute("""
                        INSERT INTO fishing_inventory (user_id, fish_name, amount)
                        VALUES (?, ?, ?)
                    """, (ctx.author.id, fish["name"], amount))
            
            await db.commit()
        
        # Build response
        catch_text = ""
        total_value = 0
        
        for fish, amount in caught_fish:
            price = self.get_fish_price(fish["name"])
            value = price * amount
            total_value += value
            catch_text += f"{fish['emoji']} **{fish['name']}** x{amount} (Rp {value:,})\n"
        
        embed = discord.Embed(title="🎣 Hasil Memancing!", description=catch_text, color=0x3498db)
        
        if in_voice:
            embed.add_field(name="🎤 Voice Bonus", value="**+150%** ikan! (2.5x)", inline=False)
        
        embed.add_field(name="💰 Total Nilai", value=f"Rp {total_value:,}", inline=True)
        embed.add_field(name="🎒 Inventory", value="Gunakan `mochi!inventory`", inline=True)
        
        footer_text = "Jual: mochi!sellfish • Harga update tiap 15 menit!"
        if not in_voice:
            footer_text = "💡 Join VC untuk +150% ikan! • " + footer_text
        
        embed.set_footer(text=footer_text)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="inventory", aliases=["inv"])
    async def inventory_command(self, ctx, member: discord.Member = None):
        """🎒 Lihat inventory ikan"""
        user = member or ctx.author
        fishing_data = await self.get_user_fishing_data(user.id)
        
        if not fishing_data["inventory"]:
            await ctx.send(f"🎒 {user.mention} belum punya ikan! Gunakan `mochi!fish`")
            return
        
        inventory_by_rarity = {
            "legendary": [],
            "epic": [],
            "rare": [],
            "uncommon": [],
            "common": []
        }
        
        total_value = 0
        
        for fish_name, amount in fishing_data["inventory"].items():
            for rarity, fish_list in self.fish_types.items():
                for fish in fish_list:
                    if fish["name"] == fish_name:
                        price = self.get_fish_price(fish_name)
                        value = price * amount
                        total_value += value
                        
                        inventory_by_rarity[rarity].append({
                            "fish": fish,
                            "amount": amount,
                            "price": price,
                            "value": value
                        })
                        break
        
        embed = discord.Embed(
            title=f"🎒 Inventory Ikan - {user.display_name}",
            color=0x3498db
        )
        
        rarity_colors = {
            "legendary": "🟡",
            "epic": "🟣",
            "rare": "🔵",
            "uncommon": "🟢",
            "common": "⚪"
        }
        
        for rarity in ["legendary", "epic", "rare", "uncommon", "common"]:
            if inventory_by_rarity[rarity]:
                text = ""
                for item in inventory_by_rarity[rarity]:
                    fish = item["fish"]
                    text += f"{fish['emoji']} **{fish['name']}** x{item['amount']}\n"
                    text += f"   └─ @Rp {item['price']:,} = Rp {item['value']:,}\n"
                
                embed.add_field(
                    name=f"{rarity_colors[rarity]} {rarity.upper()}",
                    value=text,
                    inline=False
                )
        
        embed.add_field(name="💰 Total Nilai", value=f"Rp {total_value:,}", inline=False)
        embed.set_footer(text="mochi!sellfish <ikan> <jumlah> • Pajak 25% saat jual")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="sellfish")
    async def sell_fish_command(self, ctx, *, fish_query: str = None):
        """💰 Jual ikan"""
        if not fish_query:
            await ctx.send(
                "❌ **Format salah!**\n"
                "✅ Gunakan: `mochi!sellfish <nama_ikan> <jumlah>`\n"
                "📌 Contoh:\n"
                "• `mochi!sellfish teri 10`\n"
                "• `mochi!sellfish tuna all`\n"
                "• `mochi!sellfish all` - Jual semua"
            )
            return
        
        fishing_data = await self.get_user_fishing_data(ctx.author.id)
        
        if not fishing_data["inventory"]:
            await ctx.send("❌ Inventory kosong! Gunakan `mochi!fish`")
            return
        
        # Handle "sell all"
        if fish_query.lower() == "all":
            total_money_before_tax = 0
            sold_items = []
            
            async with aiosqlite.connect("mochi.db") as db:
                for fish_name, amount in fishing_data["inventory"].items():
                    price = self.get_fish_price(fish_name)
                    money = price * amount
                    total_money_before_tax += money
                    sold_items.append((fish_name, amount, money))
                
                await db.execute("""
                    DELETE FROM fishing_inventory WHERE user_id = ?
                """, (ctx.author.id,))
                await db.commit()
            
            # Apply tax
            tax_amount = int(total_money_before_tax * self.sell_tax_rate)
            total_money = total_money_before_tax - tax_amount
            
            await update_user(ctx.author.id, currency=total_money)
            
            sold_text = "\n".join([f"• **{name}** x{amt} = Rp {val:,}" for name, amt, val in sold_items[:10]])
            if len(sold_items) > 10:
                sold_text += f"\n... dan {len(sold_items) - 10} item lainnya"
            
            embed = discord.Embed(title="✅ Jual Semua Ikan Berhasil!", description=sold_text, color=0x00ff00)
            embed.add_field(name="💵 Nilai Kotor", value=f"Rp {total_money_before_tax:,}", inline=True)
            embed.add_field(name="📉 Pajak (25%)", value=f"-Rp {tax_amount:,}", inline=True)
            embed.add_field(name="💰 Total Bersih", value=f"**Rp {total_money:,}**", inline=True)
            embed.set_footer(text="Pajak 25% untuk stabilitas ekonomi")
            await ctx.send(embed=embed)
            return
        
        # Parse query
        parts = fish_query.lower().split()
        if len(parts) < 2:
            await ctx.send("❌ Format salah! Contoh: `mochi!sellfish teri 10`")
            return
        
        amount_str = parts[-1]
        fish_query_name = " ".join(parts[:-1])
        
        # Cari ikan
        found_fish = None
        found_fish_name = None
        
        for fish_name in fishing_data["inventory"].keys():
            if fish_query_name in fish_name.lower():
                found_fish_name = fish_name
                for rarity, fish_list in self.fish_types.items():
                    for fish in fish_list:
                        if fish["name"] == fish_name:
                            found_fish = fish
                            break
                    if found_fish:
                        break
                break
        
        if not found_fish:
            await ctx.send(f"❌ Ikan `{fish_query_name}` tidak ada di inventory!")
            return
        
        current_amount = fishing_data["inventory"][found_fish_name]
        
        # Parse amount
        if amount_str == "all":
            sell_amount = current_amount
        else:
            try:
                sell_amount = int(amount_str)
            except ValueError:
                await ctx.send("❌ Jumlah tidak valid! Gunakan angka atau 'all'")
                return
        
        if sell_amount <= 0 or sell_amount > current_amount:
            await ctx.send(f"❌ Kamu hanya punya {current_amount} {found_fish_name}!")
            return
        
        # Hitung harga dengan pajak
        price = self.get_fish_price(found_fish_name)
        total_money_before_tax = price * sell_amount
        tax_amount = int(total_money_before_tax * self.sell_tax_rate)
        total_money = total_money_before_tax - tax_amount
        
        # Update database
        async with aiosqlite.connect("mochi.db") as db:
            new_amount = current_amount - sell_amount
            
            if new_amount <= 0:
                await db.execute("""
                    DELETE FROM fishing_inventory 
                    WHERE user_id = ? AND fish_name = ?
                """, (ctx.author.id, found_fish_name))
            else:
                await db.execute("""
                    UPDATE fishing_inventory 
                    SET amount = ? 
                    WHERE user_id = ? AND fish_name = ?
                """, (new_amount, ctx.author.id, found_fish_name))
            
            await db.commit()
        
        await update_user(ctx.author.id, currency=total_money)
        
        embed = discord.Embed(title="✅ Penjualan Berhasil!", color=0x00ff00)
        embed.add_field(name="Ikan", value=f"{found_fish['emoji']} {found_fish_name}", inline=True)
        embed.add_field(name="Jumlah", value=f"x{sell_amount}", inline=True)
        embed.add_field(name="Harga/unit", value=f"Rp {price:,}", inline=True)
        embed.add_field(name="💵 Nilai Kotor", value=f"Rp {total_money_before_tax:,}", inline=True)
        embed.add_field(name="📉 Pajak (25%)", value=f"-Rp {tax_amount:,}", inline=True)
        embed.add_field(name="💰 Total Bersih", value=f"**Rp {total_money:,}**", inline=True)
        embed.set_footer(text="Harga update tiap 15 menit! • Pajak 25% untuk stabilitas ekonomi")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="fishmarket", aliases=["fmarket"])
    async def fish_market_command(self, ctx):
        """📊 Lihat harga pasar ikan saat ini"""
        embed = discord.Embed(
            title="📊 Fish Market - Harga Ikan Hari Ini",
            description="Harga berubah setiap 15 menit",
            color=0x3498db
        )
        
        for rarity, fish_list in self.fish_types.items():
            text = ""
            for fish in fish_list:
                price = self.get_fish_price(fish["name"])
                base_price = fish["base_price"]
                change = ((price - base_price) / base_price) * 100
                
                emoji = "📈" if change >= 0 else "📉"
                text += f"{fish['emoji']} **{fish['name']}**: Rp {price:,} {emoji} {change:+.1f}%\n"
            
            embed.add_field(name=f"{rarity.upper()}", value=text, inline=False)
        
        if self.last_price_update:
            next_update = self.last_price_update + timedelta(minutes=15)
            remaining = (next_update - datetime.utcnow()).seconds // 60
            embed.set_footer(text=f"Update berikutnya ~{remaining} menit • Pajak jual: 25%")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="fishupgrade", aliases=["fupgrade", "fishup"])
    async def fish_upgrade_command(self, ctx, upgrade_name: str = None):
        """🛒 Beli upgrade fishing"""
        if not upgrade_name:
            fishing_data = await self.get_user_fishing_data(ctx.author.id)
            user_data = await get_user(ctx.author.id)
            
            embed = discord.Embed(
                title="🛒 Fishing Upgrade Shop",
                description="Tingkatkan kemampuan memancing!",
                color=0xf39c12
            )
            
            for key, upgrade in self.upgrades.items():
                current_level = fishing_data["upgrades"].get(key, 0)
                next_cost = self.calculate_upgrade_cost(key, current_level)
                
                if current_level >= upgrade["max_level"]:
                    status = "✅ MAX LEVEL"
                    cost_text = "—"
                else:
                    status = f"Level {current_level}/{upgrade['max_level']}"
                    cost_text = f"Rp {next_cost:,}"
                
                # Info bonus
                if key == "fishing_rod":
                    bonus_info = f"Better catch rate & rarer fish"
                elif key == "fishing_robot":
                    bonus = self.upgrades[key]["bonus_per_level"] * (current_level + 1)
                    bonus_info = f"+{bonus} fish per day (passive)"
                else:  # fishing_net
                    bonus = self.upgrades[key]["bonus_per_level"] * (current_level + 1)
                    bonus_info = f"+{bonus} fish/min in VC"
                
                embed.add_field(
                    name=f"{upgrade['emoji']} {upgrade['name']} ({status})",
                    value=(
                        f"{upgrade['description']}\n"
                        f"**Next Level**: {bonus_info}\n"
                        f"**Cost**: {cost_text}"
                    ),
                    inline=False
                )
            
            embed.add_field(name="💰 Saldo Kamu", value=f"Rp {user_data['currency']:,}", inline=False)
            embed.set_footer(text="Gunakan: mochi!fishupgrade <rod/robot/net>")
            await ctx.send(embed=embed)
            return
        
        # Process upgrade
        upgrade_key = None
        if "rod" in upgrade_name.lower():
            upgrade_key = "fishing_rod"
        elif "robot" in upgrade_name.lower() or "bot" in upgrade_name.lower():
            upgrade_key = "fishing_robot"
        elif "net" in upgrade_name.lower():
            upgrade_key = "fishing_net"
        else:
            await ctx.send("❌ Upgrade tidak valid! Pilih: `rod`, `robot`, atau `net`")
            return
        
        fishing_data = await self.get_user_fishing_data(ctx.author.id)
        user_data = await get_user(ctx.author.id)
        
        current_level = fishing_data["upgrades"].get(upgrade_key, 0)
        upgrade_info = self.upgrades[upgrade_key]
        
        if current_level >= upgrade_info["max_level"]:
            await ctx.send(f"✅ {upgrade_info['name']} sudah MAX LEVEL!")
            return
        
        cost = self.calculate_upgrade_cost(upgrade_key, current_level)
        
        if user_data["currency"] < cost:
            await ctx.send(
                f"❌ Saldo tidak cukup!\n"
                f"💰 Butuh: Rp {cost:,}\n"
                f"💳 Saldo: Rp {user_data['currency']:,}"
            )
            return
        
        # Proses upgrade
        await update_user(ctx.author.id, currency=-cost)
        
        async with aiosqlite.connect("mochi.db") as db:
            cursor = await db.execute("""
                SELECT level FROM fishing_upgrades 
                WHERE user_id = ? AND upgrade_type = ?
            """, (ctx.author.id, upgrade_key))
            existing = await cursor.fetchone()
            
            if existing:
                await db.execute("""
                    UPDATE fishing_upgrades 
                    SET level = level + 1 
                    WHERE user_id = ? AND upgrade_type = ?
                """, (ctx.author.id, upgrade_key))
            else:
                await db.execute("""
                    INSERT INTO fishing_upgrades (user_id, upgrade_type, level)
                    VALUES (?, ?, 1)
                """, (ctx.author.id, upgrade_key))
            
            await db.commit()
        
        new_level = current_level + 1
        new_bonus = upgrade_info["bonus_per_level"] * new_level
        
        embed = discord.Embed(title="✅ Upgrade Berhasil!", color=0x00ff00)
        embed.add_field(
            name=f"{upgrade_info['emoji']} {upgrade_info['name']}",
            value=f"Level {current_level} → **Level {new_level}**",
            inline=False
        )
        embed.add_field(name="Bonus Sekarang", value=f"+{new_bonus}", inline=True)
        embed.add_field(name="Biaya", value=f"Rp {cost:,}", inline=True)
        embed.add_field(name="Sisa Saldo", value=f"Rp {user_data['currency'] - cost:,}", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="fishstats", aliases=["fstats"])
    async def fish_stats_command(self, ctx, member: discord.Member = None):
        """📊 Lihat statistik fishing"""
        user = member or ctx.author
        fishing_data = await self.get_user_fishing_data(user.id)
        
        embed = discord.Embed(
            title=f"📊 Fishing Stats - {user.display_name}",
            color=0x3498db
        )
        
        total_caught = fishing_data["stats"].get("total_fish_caught", 0)
        embed.add_field(name="🎣 Total Ikan Ditangkap", value=f"{total_caught:,}", inline=True)
        
        total_inventory = sum(fishing_data["inventory"].values())
        embed.add_field(name="🎒 Ikan di Inventory", value=f"{total_inventory:,}", inline=True)
        
        upgrade_text = ""
        for key, upgrade_info in self.upgrades.items():
            level = fishing_data["upgrades"].get(key, 0)
            upgrade_text += f"{upgrade_info['emoji']} **{upgrade_info['name']}**: Lv.{level}\n"
        
        embed.add_field(name="⚙️ Upgrades", value=upgrade_text or "Belum ada", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="fhelp", aliases=["fishhelp"])
    async def fishing_help_command(self, ctx):
        """📖 Panduan lengkap fishing system"""
        embed = discord.Embed(
            title="🎣 Mochi Fishing System - Help",
            description="Panduan lengkap sistem fishing!",
            color=0x3498db
        )
        
        embed.add_field(
            name="🎣 Basic Commands",
            value=(
                "`mochi!fish` - Memancing (cooldown 1 menit)\n"
                "`mochi!autofish [jam]` - Auto-fishing (1-12 jam)\n"
                "`mochi!stopautofish` - Stop auto-fishing\n"
                "`mochi!afstatus` - Cek status auto-fishing\n"
                "`mochi!inv [@user]` - Lihat inventory ikan\n"
                "`mochi!fstats [@user]` - Lihat statistik fishing"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💰 Trading Commands",
            value=(
                "`mochi!sellfish <ikan> <jumlah>` - Jual ikan\n"
                "`mochi!sellfish all` - Jual semua ikan\n"
                "`mochi!fmarket` - Lihat harga pasar"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Upgrade Commands",
            value=(
                "`mochi!fishupgrade` - Lihat shop upgrade\n"
                "`mochi!fishupgrade rod` - Upgrade Fishing Rod\n"
                "`mochi!fishupgrade robot` - Upgrade Fishing Robot\n"
                "`mochi!fishupgrade net` - Upgrade Fishing Net"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Pro Tips",
            value=(
                "🎤 Join **Voice Channel** untuk +150% ikan!\n"
                "🤖 Gunakan **Auto-Fishing** untuk farming otomatis\n"
                "📊 Cek **Market** sebelum jual untuk profit max\n"
                "⚙️ Upgrade **Fishing Rod** dulu untuk hasil lebih\n"
                "💎 Simpan ikan **Rare/Legendary** saat harga turun\n"
                "📉 Ingat ada **pajak 25%** saat jual ikan!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🟦 Fish Rarity",
            value=(
                "⚪ Common (40%+) - Rp 50-150\n"
                "🟢 Uncommon (15%) - Rp 300-400\n"
                "🔵 Rare (7%) - Rp 800-1,000\n"
                "🟣 Epic (3%) - Rp 2,000-3,000\n"
                "🟡 Legendary (0.5%) - Rp 10,000-50,000"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🤖 Auto-Fishing",
            value=(
                "• Fish otomatis setiap **1 menit**\n"
                "• Durasi: **1-12 jam**\n"
                "• Default: **2 jam**\n"
                "• Contoh: `mochi!autofish 5` (5 jam)\n"
                "• Tetap dapat **Voice Bonus** jika di VC!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📈 Level Progression (Rod)",
            value=(
                "**Lv 0**: 1-2 ikan (sulit, untuk pemula)\n"
                "**Lv 10**: 2-4 ikan (menengah)\n"
                "**Lv 25**: 3-6 ikan (advanced)\n"
                "**Lv 50+**: 6-20 ikan (expert)"
            ),
            inline=False
        )
        
        embed.set_footer(text="Gunakan mochi!fhelp untuk melihat help ini lagi")
        
        await ctx.send(embed=embed)

# ============================================
# COPY & PASTE KE cogs/fishing.py
# Tambahkan sebelum: async def setup(bot)
# ============================================

    @commands.command(name="frate", aliases=["fishrate"])
    async def fish_rate_command(self, ctx):
        """📊 Lihat rate drop ikan untuk semua rarity"""
        embed = discord.Embed(
            title="📊 Fish Drop Rates",
            description="Peluang mendapatkan ikan berdasarkan rarity",
            color=0x3498db
        )
        
        for rarity, fish_list in self.fish_types.items():
            rate_text = ""
            for fish in fish_list:
                drop_chance = fish["weight"]  # Weight is already percentage
                rate_text += f"{fish['emoji']} **{fish['name']}**: {drop_chance}%\n"
                rate_text += f"   └─ Base Price: Rp {fish['base_price']:,}\n"
            
            # Color based on rarity
            if rarity == "legendary":
                color_emoji = "🟡"
            elif rarity == "epic":
                color_emoji = "🟣"
            elif rarity == "rare":
                color_emoji = "🔵"
            elif rarity == "uncommon":
                color_emoji = "🟢"
            else:
                color_emoji = "⚪"
            
            embed.add_field(
                name=f"{color_emoji} {rarity.upper()}",
                value=rate_text,
                inline=False
            )
        
        embed.add_field(
            name="💡 Fishing Tips",
            value=(
                "🎣 **Rod Level** meningkatkan chance rare fish!\n"
                "🎤 **Voice Channel** = +150% fish bonus!\n"
                "📊 Harga pasar berubah tiap **15 menit**\n"
                "⬆️ Higher rod = more fish per catch\n"
                "🐟 Rare fish = lebih profit!"
            ),
            inline=False
        )
        
        embed.set_footer(text="Upgrade rod: mochi!fishupgrade rod")
        await ctx.send(embed=embed)
    
    @commands.command(name="flb", aliases=["fishleaderboard", "fishlb"])
    async def fish_leaderboard_command(self, ctx, sort_by: str = "caught"):
        """🏆 Leaderboard fishing"""
        valid_sorts = {
            "caught": ("total_fish_caught DESC", "🎣 Total Fish Caught"),
            "value": ("portfolio_value DESC", "💰 Portfolio Value"),
            "unique": ("unique_fish DESC", "🐟 Unique Species")
        }
        
        sort_key = sort_by.lower()
        if sort_key not in valid_sorts:
            sort_key = "caught"
        
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            
            if sort_key == "value":
                # Calculate portfolio value for each user
                cursor = await db.execute("""
                    SELECT 
                        fs.user_id,
                        fs.total_fish_caught,
                        COUNT(DISTINCT fi.fish_name) as unique_fish
                    FROM fishing_stats fs
                    LEFT JOIN fishing_inventory fi ON fs.user_id = fi.user_id
                    GROUP BY fs.user_id
                    ORDER BY fs.total_fish_caught DESC
                    LIMIT 10
                """)
                rows = await cursor.fetchall()
                
                # Calculate portfolio value manually
                leaderboard_data = []
                for row in rows:
                    user_id = row["user_id"]
                    
                    # Get user inventory
                    cursor2 = await db.execute("""
                        SELECT fish_name, amount FROM fishing_inventory 
                        WHERE user_id = ?
                    """, (user_id,))
                    inventory = await cursor2.fetchall()
                    
                    total_value = 0
                    for item in inventory:
                        price = self.get_fish_price(item["fish_name"])
                        total_value += price * item["amount"]
                    
                    leaderboard_data.append({
                        "user_id": user_id,
                        "total_fish_caught": row["total_fish_caught"],
                        "unique_fish": row["unique_fish"],
                        "portfolio_value": total_value
                    })
                
                # Sort by portfolio value
                leaderboard_data.sort(key=lambda x: x["portfolio_value"], reverse=True)
                rows = leaderboard_data[:10]
                
            elif sort_key == "unique":
                cursor = await db.execute("""
                    SELECT 
                        fs.user_id,
                        fs.total_fish_caught,
                        COUNT(DISTINCT fi.fish_name) as unique_fish
                    FROM fishing_stats fs
                    LEFT JOIN fishing_inventory fi ON fs.user_id = fi.user_id
                    GROUP BY fs.user_id
                    ORDER BY unique_fish DESC
                    LIMIT 10
                """)
                rows = await cursor.fetchall()
                rows = [dict(row) for row in rows]
                
            else:  # caught
                cursor = await db.execute("""
                    SELECT 
                        fs.user_id,
                        fs.total_fish_caught,
                        COUNT(DISTINCT fi.fish_name) as unique_fish
                    FROM fishing_stats fs
                    LEFT JOIN fishing_inventory fi ON fs.user_id = fi.user_id
                    GROUP BY fs.user_id
                    ORDER BY fs.total_fish_caught DESC
                    LIMIT 10
                """)
                rows = await cursor.fetchall()
                rows = [dict(row) for row in rows]
        
        if not rows:
            await ctx.send("📊 Belum ada data leaderboard fishing!")
            return
        
        order_by, title_suffix = valid_sorts[sort_key]
        
        embed = discord.Embed(
            title=f"🏆 Fishing Leaderboard - {title_suffix}",
            color=0x3498db
        )
        
        leaderboard_text = ""
        for i, row in enumerate(rows, 1):
            user = self.bot.get_user(row["user_id"])
            username = user.display_name if user else f"User#{row['user_id']}"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"`{i}.`"
            
            if sort_key == "value":
                main_stat = f"💰 Rp {row['portfolio_value']:,}"
                sub_stat = f"🎣 {row['total_fish_caught']:,} caught"
            elif sort_key == "unique":
                main_stat = f"🐟 {row['unique_fish']} species"
                sub_stat = f"🎣 {row['total_fish_caught']:,} caught"
            else:
                main_stat = f"🎣 {row['total_fish_caught']:,} fish"
                sub_stat = f"🐟 {row['unique_fish']} species"
            
            leaderboard_text += (
                f"{medal} **{username}**\n"
                f"   ├─ {main_stat}\n"
                f"   └─ {sub_stat}\n\n"
            )
        
        embed.description = leaderboard_text
        embed.add_field(
            name="📋 Sort Options",
            value=(
                "`caught` • `value` • `unique`\n"
                f"Example: `mochi!flb value`"
            ),
            inline=False
        )
        embed.set_footer(text="Gunakan mochi!fstats untuk lihat stats kamu")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="fcompare", aliases=["fishcompare", "fc"])
    async def fish_compare_command(self, ctx, member1: discord.Member = None, member2: discord.Member = None):
        """⚖️ Bandingkan stats fishing 2 user"""
        user1 = member1 or ctx.author
        user2 = member2 or ctx.author
        
        if user1 == user2:
            await ctx.send("❌ Pilih 2 user berbeda untuk compare!\nContoh: `mochi!fcompare @user1 @user2`")
            return
        
        # Get stats for both users
        stats1 = await self.get_user_fishing_data(user1.id)
        stats2 = await self.get_user_fishing_data(user2.id)
        
        embed = discord.Embed(
            title="⚖️ Fishing Stats Comparison",
            color=0x3498db
        )
        
        # Total fish caught
        caught1 = stats1["stats"].get("total_fish_caught", 0)
        caught2 = stats2["stats"].get("total_fish_caught", 0)
        
        embed.add_field(
            name="🎣 Total Fish Caught",
            value=(
                f"{user1.mention}: **{caught1:,}** {'🥇' if caught1 > caught2 else '🥈' if caught1 < caught2 else '🤝'}\n"
                f"{user2.mention}: **{caught2:,}** {'🥇' if caught2 > caught1 else '🥈' if caught2 < caught1 else '🤝'}"
            ),
            inline=False
        )
        
        # Inventory count
        inv1_count = sum(stats1["inventory"].values())
        inv2_count = sum(stats2["inventory"].values())
        
        embed.add_field(
            name="🎒 Current Inventory",
            value=(
                f"{user1.mention}: **{inv1_count:,}** fish {'🥇' if inv1_count > inv2_count else '🥈' if inv1_count < inv2_count else '🤝'}\n"
                f"{user2.mention}: **{inv2_count:,}** fish {'🥇' if inv2_count > inv1_count else '🥈' if inv2_count < inv1_count else '🤝'}"
            ),
            inline=False
        )
        
        # Upgrades comparison
        rod1 = stats1["upgrades"].get("fishing_rod", 0)
        rod2 = stats2["upgrades"].get("fishing_rod", 0)
        
        embed.add_field(
            name="🎣 Fishing Rod Level",
            value=(
                f"{user1.mention}: **Lv.{rod1}** {'🥇' if rod1 > rod2 else '🥈' if rod1 < rod2 else '🤝'}\n"
                f"{user2.mention}: **Lv.{rod2}** {'🥇' if rod2 > rod1 else '🥈' if rod2 < rod1 else '🤝'}"
            ),
            inline=False
        )
        
        # Overall winner
        points1 = (1 if caught1 > caught2 else 0.5 if caught1 == caught2 else 0) + \
                  (1 if inv1_count > inv2_count else 0.5 if inv1_count == inv2_count else 0) + \
                  (1 if rod1 > rod2 else 0.5 if rod1 == rod2 else 0)
        points2 = 3 - points1
        
        if points1 > points2:
            overall_winner = f"🏆 **Overall Winner**: {user1.mention}"
            embed.color = 0x2ecc71
        elif points2 > points1:
            overall_winner = f"🏆 **Overall Winner**: {user2.mention}"
            embed.color = 0x2ecc71
        else:
            overall_winner = "🤝 **It's a tie!**"
            embed.color = 0xf39c12
        
        embed.add_field(name="🏆 Result", value=overall_winner, inline=False)
        embed.set_footer(text="Keep fishing to improve your stats! 🎣")
        
        await ctx.send(embed=embed)

# ============================================
# END OF FISHING ADDON COMMANDS
# Pastikan ada async def setup(bot) setelah ini!
# ============================================

async def setup(bot):
    await bot.add_cog(Fishing(bot))