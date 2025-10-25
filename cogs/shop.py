import discord
from discord.ext import commands, tasks
import aiosqlite
import random
from datetime import datetime, timedelta
import pytz
from database import get_user, update_user
from utils.config_secrets import QUEST_CHANNEL_ID as SHOP_CHANNEL_ID

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Item catalog (pool untuk random selection)
        self.item_catalog = {
            # XP Boosters
            "xp_2x": {
                "name": "2x XP Booster",
                "emoji": "✨",
                "description": "Double XP untuk 1 portfolio berikutnya",
                "base_price": 25000,
                "max_stock": 10,
                "category": "booster"
            },
            "xp_4x": {
                "name": "4x XP Booster",
                "emoji": "🌟",
                "description": "4x XP untuk 1 portfolio berikutnya",
                "base_price": 75000,
                "max_stock": 5,
                "category": "booster"
            },
            "xp_8x": {
                "name": "8x XP Booster",
                "emoji": "🌈",
                "description": "8x XP untuk 1 portfolio berikutnya",
                "base_price": 200000,
                "max_stock": 3,
                "category": "booster"
            },
            
            # Gacha Rolls
            "gacha_roll_1": {
                "name": "1 Gacha Roll",
                "emoji": "🎰",
                "description": "1 kesempatan gacha",
                "base_price": 50000,
                "max_stock": 8,
                "category": "gacha"
            },
            "gacha_roll_3": {
                "name": "3 Gacha Rolls",
                "emoji": "🎲",
                "description": "3 kesempatan gacha",
                "base_price": 120000,
                "max_stock": 5,
                "category": "gacha"
            },
            "gacha_roll_5": {
                "name": "5 Gacha Rolls",
                "emoji": "🎪",
                "description": "5 kesempatan gacha",
                "base_price": 180000,
                "max_stock": 3,
                "category": "gacha"
            },
            
            # Luck Boosters (PERMANENT)
            "luck_boost_small": {
                "name": "Lucky Charm",
                "emoji": "🍀",
                "description": "+5 Luck (PERMANENT!)",
                "base_price": 150000,
                "max_stock": 5,
                "category": "luck"
            },
            "luck_boost_medium": {
                "name": "Fortune Talisman",
                "emoji": "🔮",
                "description": "+10 Luck (PERMANENT!)",
                "base_price": 300000,
                "max_stock": 3,
                "category": "luck"
            },
            "luck_boost_large": {
                "name": "Divine Blessing",
                "emoji": "✨",
                "description": "+25 Luck (PERMANENT!)",
                "base_price": 1000000,
                "max_stock": 1,
                "category": "luck"
            },
            
            # Currency Packages
            "money_small": {
                "name": "Money Pouch",
                "emoji": "💰",
                "description": "+100,000 Rupiah",
                "base_price": 80000,
                "max_stock": 10,
                "category": "currency"
            },
            "money_medium": {
                "name": "Money Bag",
                "emoji": "💵",
                "description": "+500,000 Rupiah",
                "base_price": 350000,
                "max_stock": 5,
                "category": "currency"
            },
            "money_large": {
                "name": "Treasure Chest",
                "emoji": "💎",
                "description": "+2,000,000 Rupiah",
                "base_price": 1200000,
                "max_stock": 2,
                "category": "currency"
            },
            
            # Special Items
            "mystery_box": {
                "name": "Mystery Box",
                "emoji": "🎁",
                "description": "Random reward (2x-10x XP atau 50k-500k Rp)",
                "base_price": 100000,
                "max_stock": 5,
                "category": "special"
            },
            "double_daily_xp": {
                "name": "Double Daily XP",
                "emoji": "⚡",
                "description": "2x XP untuk SEMUA portfolio hari ini",
                "base_price": 200000,
                "max_stock": 3,
                "category": "special"
            }
        }
        
        # Start daily shop reset
        self.daily_shop_reset.start()
    
    def cog_unload(self):
        self.daily_shop_reset.cancel()
    
    @tasks.loop(hours=1)
    async def daily_shop_reset(self):
        """Reset shop setiap hari jam 00:00 WIB"""
        wib = pytz.timezone('Asia/Jakarta')
        now_wib = datetime.now(wib)
        
        # Check if it's 00:00 WIB
        if now_wib.hour == 0 and now_wib.minute < 5:
            print("🛒 Daily shop reset starting (00:00 WIB)...")
            await self.generate_daily_shop()
    
    @daily_shop_reset.before_loop
    async def before_daily_reset(self):
        await self.bot.wait_until_ready()
        # Generate shop saat bot start jika belum ada
        await self.generate_daily_shop()
    
    async def generate_daily_shop(self):
        """Generate random shop items untuk hari ini"""
        wib = pytz.timezone('Asia/Jakarta')
        now_wib = datetime.now(wib)
        shop_id = now_wib.strftime('%Y%m%d')
        
        # Check if shop already exists for today
        async with aiosqlite.connect("mochi.db") as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM daily_shop WHERE shop_id = ?
            """, (shop_id,))
            exists = (await cursor.fetchone())[0] > 0
            
            if exists:
                print(f"✅ Shop already exists for {shop_id}")
                return
        
        # Select random items (8-12 items)
        num_items = random.randint(8, 12)
        selected_items = random.sample(list(self.item_catalog.keys()), num_items)
        
        # Pick 1-2 special deals (20-50% discount)
        num_deals = random.randint(1, 2)
        special_deals = random.sample(selected_items, num_deals)
        
        async with aiosqlite.connect("mochi.db") as db:
            # Clear old shop data (older than 7 days)
            seven_days_ago = (now_wib - timedelta(days=7)).strftime('%Y%m%d')
            await db.execute("""
                DELETE FROM daily_shop WHERE shop_id < ?
            """, (seven_days_ago,))
            
            # Insert new shop items
            for item_key in selected_items:
                item = self.item_catalog[item_key]
                
                is_special = item_key in special_deals
                discount = random.uniform(0.2, 0.5) if is_special else 0
                
                price = int(item["base_price"] * (1 - discount))
                stock = random.randint(
                    max(1, item["max_stock"] // 2),
                    item["max_stock"]
                )
                
                await db.execute("""
                    INSERT INTO daily_shop (shop_id, item_key, price, stock, original_price, is_special)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (shop_id, item_key, price, stock, item["base_price"], 1 if is_special else 0))
            
            await db.commit()
        
        # Send announcement
        shop_channel = self.bot.get_channel(SHOP_CHANNEL_ID)
        if shop_channel:
            await self.send_shop_announcement(shop_channel, shop_id)
        
        print(f"✅ Daily shop generated: {shop_id} ({num_items} items, {num_deals} special deals)")
    
    async def send_shop_announcement(self, channel, shop_id):
        """Send shop announcement dengan preview"""
        embed = discord.Embed(
            title="🛒 DAILY SHOP OPENED!",
            description=(
                "**Shop baru telah dibuka!**\n\n"
                "🎉 Special deals tersedia!\n"
                "⏰ Reset besok jam **00:00 WIB**\n"
                "📦 Stock terbatas!"
            ),
            color=0xf39c12
        )
        
        # Get shop items (limit preview)
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM daily_shop WHERE shop_id = ? AND stock > 0
                ORDER BY is_special DESC, price ASC
                LIMIT 6
            """, (shop_id,))
            items = await cursor.fetchall()
        
        if items:
            preview_text = ""
            for item_row in items:
                item = self.item_catalog.get(item_row["item_key"])
                if not item:
                    continue
                
                price_text = f"Rp {item_row['price']:,}"
                if item_row["is_special"]:
                    discount = int((1 - item_row["price"] / item_row["original_price"]) * 100)
                    price_text = f"~~Rp {item_row['original_price']:,}~~ **Rp {item_row['price']:,}** 🔥"
                
                preview_text += f"{item['emoji']} {item['name']} - {price_text}\n"
            
            embed.add_field(name="📋 Preview (Top 6)", value=preview_text, inline=False)
        
        embed.add_field(
            name="🛍️ Commands",
            value=(
                "`mochi!shop` - Lihat semua item\n"
                "`mochi!shopbuy <item>` - Beli item\n"
                "`mochi!shopinfo` - Info shop system"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Shop ID: {shop_id} • Reset besok 00:00 WIB")
        await channel.send("@everyone", embed=embed)
    
    async def get_current_shop(self):
        """Ambil shop items hari ini"""
        wib = pytz.timezone('Asia/Jakarta')
        now_wib = datetime.now(wib)
        shop_id = now_wib.strftime('%Y%m%d')
        
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM daily_shop WHERE shop_id = ? AND stock > 0
                ORDER BY is_special DESC, price ASC
            """, (shop_id,))
            return await cursor.fetchall()
    
    @commands.command(name="shop", aliases=["store", "dailyshop"])
    async def shop_command(self, ctx):
        """🛒 Lihat shop items hari ini"""
        items = await self.get_current_shop()
        
        if not items:
            wib = pytz.timezone('Asia/Jakarta')
            tomorrow = (datetime.now(wib) + timedelta(days=1)).replace(hour=0, minute=0)
            
            embed = discord.Embed(
                title="🛒 Daily Shop",
                description="❌ Shop hari ini sudah habis atau belum dibuka!",
                color=0xff9900
            )
            embed.add_field(
                name="⏰ Shop Reset",
                value=f"<t:{int(tomorrow.timestamp())}:R>",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🛒 Daily Shop - Today's Deals",
            description="📦 Stock terbatas! Buruan beli sebelum habis!",
            color=0x3498db
        )
        
        # Group by category
        categories = {}
        for item_row in items:
            item_key = item_row["item_key"]
            item = self.item_catalog.get(item_key)
            if not item:
                continue
            
            category = item["category"]
            if category not in categories:
                categories[category] = []
            
            categories[category].append((item_row, item))
        
        # Display items
        category_names = {
            "booster": "✨ XP Boosters",
            "gacha": "🎰 Gacha Rolls",
            "luck": "🍀 Luck Boosters",
            "currency": "💰 Currency Packages",
            "special": "🎁 Special Items"
        }
        
        for category, items_list in categories.items():
            category_text = ""
            for idx, (item_row, item) in enumerate(items_list, 1):
                price_text = f"Rp {item_row['price']:,}"
                
                if item_row["is_special"]:
                    discount = int((1 - item_row["price"] / item_row["original_price"]) * 100)
                    price_text = f"~~Rp {item_row['original_price']:,}~~ **Rp {item_row['price']:,}** 🔥"
                    special_tag = f" **DEAL (-{discount}%)**"
                else:
                    special_tag = ""
                
                category_text += (
                    f"`{idx}.` {item['emoji']} **{item['name']}**{special_tag}\n"
                    f"     💵 {price_text} | 📦 Stock: **{item_row['stock']}**\n\n"
                )
            
            if category_text:
                embed.add_field(
                    name=category_names.get(category, category.upper()),
                    value=category_text,
                    inline=False
                )
        
        # User balance
        user_data = await get_user(ctx.author.id)
        if user_data:
            embed.add_field(
                name="💳 Saldo Kamu",
                value=f"Rp {user_data['currency']:,}",
                inline=False
            )
        
        embed.add_field(
            name="🛍️ Cara Beli",
            value=(
                "Gunakan: `mochi!shopbuy <nama_item>`\n"
                "Contoh: `mochi!shopbuy 2x xp booster`\n"
                "Contoh: `mochi!shopbuy lucky charm`"
            ),
            inline=False
        )
        
        wib = pytz.timezone('Asia/Jakarta')
        tomorrow = (datetime.now(wib) + timedelta(days=1)).replace(hour=0, minute=0)
        embed.set_footer(text=f"Reset: <t:{int(tomorrow.timestamp())}:R> • Limited stock!")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="shopbuy", aliases=["sbuy"])
    async def shopbuy_command(self, ctx, *, item_name: str = None):
        """🛍️ Beli item dari shop"""
        if not item_name:
            await ctx.send(
                "❌ **Format salah!**\n"
                "✅ Gunakan: `mochi!shopbuy <nama_item>`\n"
                "📋 Lihat shop: `mochi!shop`"
            )
            return
        
        # Normalize item name
        item_name_lower = item_name.lower().strip()
        
        # Find matching item
        items = await self.get_current_shop()
        matched_item = None
        matched_item_key = None
        
        for item_row in items:
            item_key = item_row["item_key"]
            item = self.item_catalog.get(item_key)
            if not item:
                continue
            
            # Match by name or key
            if (item_name_lower in item["name"].lower() or 
                item_name_lower in item_key.lower()):
                matched_item = item_row
                matched_item_key = item_key
                break
        
        if not matched_item:
            await ctx.send(
                "❌ Item tidak ditemukan atau sudah habis!\n"
                "📋 Gunakan `mochi!shop` untuk lihat item tersedia."
            )
            return
        
        item_data = self.item_catalog[matched_item_key]
        
        # Check user balance
        user_data = await get_user(ctx.author.id)
        if not user_data:
            await ctx.send("❌ Kamu belum terdaftar!")
            return
        
        if user_data["currency"] < matched_item["price"]:
            await ctx.send(
                f"❌ **Saldo tidak cukup!**\n"
                f"💰 Butuh: Rp {matched_item['price']:,}\n"
                f"💳 Saldo: Rp {user_data['currency']:,}"
            )
            return
        
        # Check stock
        if matched_item["stock"] <= 0:
            await ctx.send("❌ Item sudah **SOLD OUT**!")
            return
        
        # Confirm purchase
        discount_text = ""
        if matched_item["is_special"]:
            discount = int((1 - matched_item["price"] / matched_item["original_price"]) * 100)
            discount_text = f"\n🔥 **SPECIAL DEAL: -{discount}%**"
        
        confirm_embed = discord.Embed(
            title="🛍️ Konfirmasi Pembelian",
            description=f"Apa kamu yakin ingin membeli item ini?{discount_text}",
            color=0x3498db
        )
        confirm_embed.add_field(
            name=f"{item_data['emoji']} {item_data['name']}",
            value=item_data['description'],
            inline=False
        )
        confirm_embed.add_field(name="💵 Harga", value=f"Rp {matched_item['price']:,}", inline=True)
        confirm_embed.add_field(name="💳 Saldo", value=f"Rp {user_data['currency']:,}", inline=True)
        confirm_embed.add_field(name="📦 Stock", value=f"{matched_item['stock']}", inline=True)
        confirm_embed.set_footer(text="React ✅ untuk konfirmasi atau ❌ untuk cancel (30 detik)")
        
        confirm_msg = await ctx.send(embed=confirm_embed)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return (user == ctx.author and 
                    str(reaction.emoji) in ["✅", "❌"] and 
                    reaction.message.id == confirm_msg.id)
        
        try:
            import asyncio
            reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await confirm_msg.edit(embed=discord.Embed(
                    title="❌ Pembelian Dibatalkan",
                    color=0xff0000
                ))
                await confirm_msg.clear_reactions()
                return
            
            # Process purchase
            await self.process_purchase(ctx, matched_item, matched_item_key, item_data)
            await confirm_msg.clear_reactions()
            
        except asyncio.TimeoutError:
            await confirm_msg.edit(content="⏰ Timeout! Pembelian dibatalkan.")
            await confirm_msg.clear_reactions()
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
            await confirm_msg.clear_reactions()
    
    async def process_purchase(self, ctx, item_row, item_key, item_data):
        """Process the actual purchase"""
        wib = pytz.timezone('Asia/Jakarta')
        shop_id = datetime.now(wib).strftime('%Y%m%d')
        
        async with aiosqlite.connect("mochi.db") as db:
            # Double check stock
            cursor = await db.execute("""
                SELECT stock FROM daily_shop 
                WHERE shop_id = ? AND item_key = ?
            """, (shop_id, item_key))
            result = await cursor.fetchone()
            
            if not result or result[0] <= 0:
                await ctx.send("❌ Item sudah **SOLD OUT**!")
                return
            
            current_stock = result[0]
            
            # Deduct stock
            await db.execute("""
                UPDATE daily_shop 
                SET stock = stock - 1 
                WHERE shop_id = ? AND item_key = ?
            """, (shop_id, item_key))
            
            # Log purchase
            await db.execute("""
                INSERT INTO shop_purchases (user_id, shop_id, item_key, price, purchased_at)
                VALUES (?, ?, ?, ?, ?)
            """, (ctx.author.id, shop_id, item_key, item_row["price"], datetime.utcnow().isoformat()))
            
            await db.commit()
        
        # Deduct currency
        await update_user(ctx.author.id, currency=-item_row["price"])
        
        # Give item
        reward_text = await self.give_item_to_user(ctx.author.id, item_key, item_data)
        
        # Success message
        embed = discord.Embed(
            title="✅ Pembelian Berhasil!",
            description=f"Kamu berhasil membeli **{item_data['name']}**!",
            color=0x00ff00
        )
        embed.add_field(name="📦 Item", value=f"{item_data['emoji']} {item_data['name']}", inline=True)
        embed.add_field(name="💵 Harga", value=f"Rp {item_row['price']:,}", inline=True)
        embed.add_field(name="📦 Stock Tersisa", value=f"{current_stock - 1}", inline=True)
        
        if reward_text:
            embed.add_field(name="🎁 Reward", value=reward_text, inline=False)
        
        embed.set_footer(text="Terima kasih sudah berbelanja!")
        await ctx.send(embed=embed)
    
    async def give_item_to_user(self, user_id: int, item_key: str, item_data: dict):
        """Give purchased item to user"""
        category = item_data["category"]
        reward_text = None
        
        if category == "booster":
            if "2x" in item_key:
                await update_user(user_id, xp_2x=1)
            elif "4x" in item_key:
                await update_user(user_id, xp_4x=1)
            elif "8x" in item_key:
                await update_user(user_id, xp_8x=1)
            reward_text = "Item sudah masuk inventory!"
        
        elif category == "gacha":
            if "roll_1" in item_key:
                await update_user(user_id, gacha_rolls=1)
            elif "roll_3" in item_key:
                await update_user(user_id, gacha_rolls=3)
            elif "roll_5" in item_key:
                await update_user(user_id, gacha_rolls=5)
            reward_text = "Gacha rolls sudah ditambahkan!"
        
        elif category == "luck":
            if "small" in item_key:
                await update_user(user_id, luck=5)
                reward_text = "+5 Luck (PERMANENT!)"
            elif "medium" in item_key:
                await update_user(user_id, luck=10)
                reward_text = "+10 Luck (PERMANENT!)"
            elif "large" in item_key:
                await update_user(user_id, luck=25)
                reward_text = "+25 Luck (PERMANENT!)"
        
        elif category == "currency":
            if "small" in item_key:
                await update_user(user_id, currency=100000)
                reward_text = "+Rp 100,000"
            elif "medium" in item_key:
                await update_user(user_id, currency=500000)
                reward_text = "+Rp 500,000"
            elif "large" in item_key:
                await update_user(user_id, currency=2000000)
                reward_text = "+Rp 2,000,000"
        
        elif category == "special":
            if item_key == "mystery_box":
                roll = random.random()
                if roll < 0.4:
                    xp_type = random.choice(["xp_2x", "xp_4x", "xp_8x", "xp_10x"])
                    if xp_type == "xp_2x":
                        await update_user(user_id, xp_2x=1)
                        reward_text = "🎁 Mystery Box: 2x XP!"
                    elif xp_type == "xp_4x":
                        await update_user(user_id, xp_4x=1)
                        reward_text = "🎁 Mystery Box: 4x XP!"
                    elif xp_type == "xp_8x":
                        await update_user(user_id, xp_8x=1)
                        reward_text = "🎁 Mystery Box: 8x XP!"
                    else:
                        await update_user(user_id, xp_10x=1)
                        reward_text = "🎁 Mystery Box: 10x XP! JACKPOT!"
                else:
                    amount = random.randint(50000, 500000)
                    await update_user(user_id, currency=amount)
                    reward_text = f"🎁 Mystery Box: +Rp {amount:,}!"
            
            elif item_key == "double_daily_xp":
                async with aiosqlite.connect("mochi.db") as db:
                    today = datetime.utcnow().date().isoformat()
                    await db.execute("""
                        INSERT OR REPLACE INTO active_buffs (user_id, buff_type, expires_at)
                        VALUES (?, 'double_daily_xp', ?)
                    """, (user_id, today))
                    await db.commit()
                reward_text = "⚡ 2x XP aktif untuk hari ini!"
        
        return reward_text
    
    @commands.command(name="shopinfo")
    async def shop_info(self, ctx):
        """📋 Info tentang shop system"""
        embed = discord.Embed(
            title="🛒 Daily Shop System - Info",
            description="Shop dengan item limited dan special deals!",
            color=0xf39c12
        )
        
        embed.add_field(
            name="🎯 Cara Kerja",
            value=(
                "1️⃣ Shop reset **setiap hari jam 00:00 WIB**\n"
                "2️⃣ **8-12 item random** dari catalog\n"
                "3️⃣ **Stock terbatas** per item\n"
                "4️⃣ **1-2 special deals** dengan diskon 20-50%\n"
                "5️⃣ **First come first served**!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🛍️ Commands",
            value=(
                "`mochi!shop` - Lihat semua item\n"
                "`mochi!shopbuy <item>` - Beli item\n"
                "`mochi!shophistory` - Riwayat pembelian\n"
                "`mochi!shopinfo` - Info ini"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Tips",
            value=(
                "⏰ Cek shop **pagi hari**\n"
                "🔥 Prioritaskan **special deals**\n"
                "📦 **Stock terbatas** - jangan tunda\n"
                "🍀 **Luck boosters** = permanent investment\n"
                "🎁 **Mystery box** = high risk high reward"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="shophistory", aliases=["shoph"])
    async def shop_history(self, ctx, limit: int = 10):
        """📜 Riwayat pembelian shop"""
        if limit > 50:
            limit = 50
        
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM shop_purchases 
                WHERE user_id = ?
                ORDER BY purchased_at DESC
                LIMIT ?
            """, (ctx.author.id, limit))
            purchases = await cursor.fetchall()
        
        if not purchases:
            await ctx.send("📜 Kamu belum pernah berbelanja!")
            return
        
        total_spent = sum(p["price"] for p in purchases)
        
        embed = discord.Embed(
            title=f"📜 Shop History - {ctx.author.display_name}",
            color=0x3498db
        )
        
        history_text = ""
        for purchase in purchases[:10]:
            item = self.item_catalog.get(purchase["item_key"])
            if not item:
                continue
            
            date = datetime.fromisoformat(purchase["purchased_at"]).strftime("%d/%m/%Y")
            history_text += f"{item['emoji']} {item['name']} - Rp {purchase['price']:,} ({date})\n"
        
        embed.description = history_text + f"\n**Total Spent**: Rp {total_spent:,}"
        embed.set_footer(text=f"Last {len(purchases)} purchases")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="forceshopgen")
    @commands.is_owner()
    async def force_shop_gen(self, ctx):
        """🔧 [OWNER] Force generate daily shop"""
        await ctx.send("🛒 Generating daily shop...")
        await self.generate_daily_shop()
        await ctx.send("✅ Daily shop generated!")

async def init_shop_tables():
    """Initialize shop tables"""
    async with aiosqlite.connect("mochi.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_shop (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id TEXT NOT NULL,
                item_key TEXT NOT NULL,
                price INTEGER NOT NULL,
                stock INTEGER NOT NULL,
                original_price INTEGER NOT NULL,
                is_special INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(shop_id, item_key)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shop_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                shop_id TEXT NOT NULL,
                item_key TEXT NOT NULL,
                price INTEGER NOT NULL,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS active_buffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                buff_type TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                UNIQUE(user_id, buff_type)
            )
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_shop_id 
            ON daily_shop(shop_id, stock)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_shop_purchases_user 
            ON shop_purchases(user_id, purchased_at DESC)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_active_buffs_user 
            ON active_buffs(user_id, expires_at)
        """)
        
        await db.commit()
        print("✅ Shop tables created!")

async def setup(bot):
    await init_shop_tables()
    await bot.add_cog(Shop(bot))