import discord
from discord.ext import commands
import aiohttp
import asyncio
from datetime import datetime

from database import get_user, create_user, update_user

class Trading(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        self.cache_time = {}
        
        self.available_crypto = {
            "btc": {"name": "Bitcoin", "symbol": "BTC", "coingecko_id": "bitcoin"},
            "eth": {"name": "Ethereum", "symbol": "ETH", "coingecko_id": "ethereum"},
            "bnb": {"name": "BNB", "symbol": "BNB", "coingecko_id": "binancecoin"},
            "sol": {"name": "Solana", "symbol": "SOL", "coingecko_id": "solana"},
            "xrp": {"name": "XRP", "symbol": "XRP", "coingecko_id": "ripple"},
            "gold": {"name": "Gold", "symbol": "GOLD", "coingecko_id": "pax-gold"},
            "silver": {"name": "Silver", "symbol": "SILVER", "coingecko_id": "silver-tokenized-stock-defichain"}
        }

    async def get_crypto_price(self, crypto_id: str):
        """Ambil harga crypto dari CoinGecko API dengan caching"""
        now = datetime.utcnow()
        
        if crypto_id in self.cache and crypto_id in self.cache_time:
            if (now - self.cache_time[crypto_id]).seconds < 30:
                return self.cache[crypto_id]
        
        try:
            coingecko_id = self.available_crypto[crypto_id]["coingecko_id"]
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=idr&include_24hr_change=true"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price_data = data[coingecko_id]
                        
                        result = {
                            "price": price_data["idr"],
                            "change_24h": price_data.get("idr_24h_change", 0)
                        }
                        
                        self.cache[crypto_id] = result
                        self.cache_time[crypto_id] = now
                        
                        return result
                    else:
                        return None
        except Exception as e:
            print(f"Error fetching price for {crypto_id}: {e}")
            return None

    async def get_user_portfolio(self, user_id: int):
        """Ambil portfolio crypto user dari database"""
        import aiosqlite
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT crypto_symbol, amount, avg_buy_price 
                FROM crypto_portfolio 
                WHERE user_id = ?
            """, (user_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_user_holdings(self, user_id: int, crypto_symbol: str):
        """Ambil holdings spesifik crypto user"""
        import aiosqlite
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT crypto_symbol, amount, avg_buy_price 
                FROM crypto_portfolio 
                WHERE user_id = ? AND crypto_symbol = ?
            """, (user_id, crypto_symbol))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_portfolio(self, user_id: int, crypto_symbol: str, amount: float, avg_price: float):
        """Update portfolio user"""
        import aiosqlite
        try:
            async with aiosqlite.connect("mochi.db") as db:
                cursor = await db.execute("""
                    SELECT amount, avg_buy_price FROM crypto_portfolio 
                    WHERE user_id = ? AND crypto_symbol = ?
                """, (user_id, crypto_symbol))
                existing = await cursor.fetchone()
                
                if existing:
                    old_amount, old_avg = existing
                    new_amount = round(old_amount + amount, 8)
                    
                    if new_amount <= 0.00000001:
                        await db.execute("""
                            DELETE FROM crypto_portfolio 
                            WHERE user_id = ? AND crypto_symbol = ?
                        """, (user_id, crypto_symbol))
                    else:
                        if amount > 0:
                            new_avg = ((old_amount * old_avg) + (amount * avg_price)) / new_amount
                        else:
                            new_avg = old_avg
                        
                        await db.execute("""
                            UPDATE crypto_portfolio 
                            SET amount = ?, avg_buy_price = ?
                            WHERE user_id = ? AND crypto_symbol = ?
                        """, (new_amount, new_avg, user_id, crypto_symbol))
                else:
                    if amount > 0:
                        await db.execute("""
                            INSERT INTO crypto_portfolio (user_id, crypto_symbol, amount, avg_buy_price)
                            VALUES (?, ?, ?, ?)
                        """, (user_id, crypto_symbol, amount, avg_price))
                
                await db.commit()
        except Exception as e:
            print(f"❌ Error updating portfolio: {e}")
            raise

    @commands.command(name="market")
    async def market(self, ctx):
        """Lihat harga crypto real-time"""
        embed = discord.Embed(
            title="📊 Market Crypto - Mochi Exchange",
            description="Harga dalam Rupiah (IDR)",
            color=0x00ff00
        )
        
        loading_msg = await ctx.send("⏳ Mengambil data market...")
        
        market_text = ""
        for crypto_id, info in self.available_crypto.items():
            price_data = await self.get_crypto_price(crypto_id)
            
            if price_data:
                price = price_data["price"]
                change = price_data["change_24h"]
                
                emoji = "📈" if change >= 0 else "📉"
                change_text = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
                
                market_text += f"{emoji} **{info['symbol']}** | Rp {price:,.0f}\n"
                market_text += f"     └─ 24h: {change_text}\n\n"
            else:
                market_text += f"⚠️ **{info['symbol']}** | Error fetching price\n\n"
        
        embed.description = market_text
        embed.set_footer(text="Ketik mochi!buy atau mochi!sell untuk trading • Data dari CoinGecko")
        
        await loading_msg.edit(content=None, embed=embed)

    @commands.command(name="buy")
    async def buy_crypto(self, ctx, crypto: str = None, amount_str: str = None):
        """Beli crypto dengan Rupiah. Contoh: mochi!buy btc 1000000 atau mochi!buy btc all"""
        if crypto is None or amount_str is None:
            await ctx.send(
                "❌ **Format salah!**\n"
                "✅ Gunakan: `mochi!buy <crypto> <jumlah_rupiah>`\n"
                "📌 Contoh:\n"
                "• `mochi!buy btc 1000000` - Beli BTC senilai Rp 1 juta\n"
                "• `mochi!buy eth all` - Beli ETH dengan semua saldo\n\n"
                "💎 Crypto tersedia: btc, eth, bnb, sol, xrp, gold, silver"
            )
            return
        
        crypto = crypto.lower()
        
        if crypto not in self.available_crypto:
            await ctx.send(f"❌ Crypto `{crypto}` tidak tersedia! Cek `mochi!market` untuk daftar crypto.")
            return
        
        # Get user data
        user_data = await get_user(ctx.author.id)
        if not user_data:
            await create_user(ctx.author.id)
            user_data = await get_user(ctx.author.id)
        
        # Parse amount
        if amount_str.lower() == "all":
            idr_amount = user_data["currency"]
        else:
            try:
                idr_amount = int(amount_str)
            except ValueError:
                await ctx.send("❌ Jumlah harus berupa angka atau `all`!")
                return
        
        if idr_amount <= 0:
            await ctx.send("❌ Jumlah harus lebih dari 0!")
            return
        
        if user_data["currency"] < idr_amount:
            await ctx.send(f"❌ Saldo tidak cukup! Kamu punya: Rp {user_data['currency']:,}")
            return
        
        # Get price
        price_data = await self.get_crypto_price(crypto)
        if not price_data:
            await ctx.send("❌ Gagal mengambil harga! Coba lagi nanti.")
            return
        
        current_price = price_data["price"]
        
        # ========================================
        # ✅ FIXED TAX LOGIC
        # ========================================
        # Tax dipotong DARI uang yang dipakai, bukan ditambah ke cost
        # Jadi: Total cost = idr_amount (sesuai saldo)
        #       Tax = 0.1% dari idr_amount
        #       Net untuk beli crypto = idr_amount - tax
        
        tax_cog = self.bot.get_cog('TaxSystem')
        tax_amount = 0
        
        if tax_cog:
            # Check if tax exempt (level 20+)
            is_exempt = await tax_cog.is_tax_exempt(ctx.author.id, user_data["level"])
            
            if not is_exempt:
                # Tax rate: 0.1% dari total amount
                tax_amount = int(idr_amount * tax_cog.TAX_RATES["trading_buy_tax"])
        
        # Net amount untuk beli crypto (setelah dipotong tax)
        net_for_crypto = idr_amount - tax_amount
        
        # Calculate crypto amount
        crypto_amount = net_for_crypto / current_price
        
        # ========================================
        # PROCESS PURCHASE
        # ========================================
        # Deduct TOTAL dari saldo (idr_amount aja, bukan + tax)
        await update_user(ctx.author.id, currency=-idr_amount)
        
        # Add crypto ke portfolio
        await self.update_portfolio(ctx.author.id, crypto.upper(), crypto_amount, current_price)
        
        # Log tax
        if tax_cog and tax_amount > 0:
            await tax_cog.log_transaction_tax(ctx.author.id, "trading_buy_tax", tax_amount)
        
        info = self.available_crypto[crypto]
        
        embed = discord.Embed(
            title="✅ Pembelian Berhasil!",
            color=0x00ff00
        )
        embed.add_field(name="Crypto", value=f"{info['symbol']} ({info['name']})", inline=True)
        embed.add_field(name="Harga/unit", value=f"Rp {current_price:,.0f}", inline=True)
        embed.add_field(name="Jumlah Crypto", value=f"{crypto_amount:,.8f}", inline=True)
        
        embed.add_field(name="💵 Total Bayar", value=f"Rp {idr_amount:,}", inline=True)
        
        if tax_amount > 0:
            embed.add_field(name="�️ Pajak (0.1%)", value=f"Rp {tax_amount:,}", inline=True)
            embed.add_field(name="💎 Net untuk Crypto", value=f"Rp {net_for_crypto:,}", inline=True)
        else:
            embed.add_field(name="🏛️ Tax Status", value="**BEBAS PAJAK**", inline=True)
            embed.add_field(name="💎 Net untuk Crypto", value=f"Rp {net_for_crypto:,}", inline=True)
        
        embed.set_footer(text="Gunakan mochi!portfolio untuk lihat aset kamu")
        
        await ctx.send(embed=embed)

    @commands.command(name="sell")
    async def sell_crypto(self, ctx, crypto: str = None, amount_str: str = None):
        """Jual crypto. Contoh: mochi!sell btc 0.001 atau mochi!sell btc all"""
        if crypto is None or amount_str is None:
            await ctx.send(
                "❌ **Format salah!**\n"
                "✅ Gunakan: `mochi!sell <crypto> <jumlah>`\n"
                "📌 Contoh:\n"
                "• `mochi!sell btc 0.001` - Jual 0.001 BTC\n"
                "• `mochi!sell eth all` - Jual semua ETH\n\n"
                "💎 Crypto tersedia: btc, eth, bnb, sol, xrp, gold, silver"
            )
            return
        
        crypto = crypto.lower()
        
        if crypto not in self.available_crypto:
            await ctx.send(f"❌ Crypto `{crypto}` tidak tersedia! Cek `mochi!market`")
            return
        
        # Get user data
        user_data = await get_user(ctx.author.id)
        if not user_data:
            await ctx.send("❌ Kamu belum punya data! Gunakan command lain dulu.")
            return
        
        # Get holdings
        holdings = await self.get_user_holdings(ctx.author.id, crypto.upper())
        
        if not holdings:
            await ctx.send(f"❌ Kamu tidak punya {crypto.upper()}!")
            return
        
        # Parse amount
        if amount_str.lower() == "all":
            amount = holdings["amount"]
        else:
            try:
                amount = float(amount_str)
            except ValueError:
                await ctx.send("❌ Jumlah harus berupa angka atau `all`!")
                return
        
        if amount <= 0:
            await ctx.send("❌ Jumlah harus lebih dari 0!")
            return
        
        if amount > holdings["amount"]:
            await ctx.send(
                f"❌ Jumlah tidak cukup!\n"
                f"Kamu punya: {holdings['amount']:,.8f} {crypto.upper()}"
            )
            return
        
        # Get price
        price_data = await self.get_crypto_price(crypto)
        if not price_data:
            await ctx.send("❌ Gagal mengambil harga! Coba lagi nanti.")
            return
        
        current_price = price_data["price"]
        gross_receive = int(current_price * amount)
        
        # ========================================
        # ✅ FIXED TAX LOGIC
        # ========================================
        # Tax dipotong DARI hasil jual
        tax_cog = self.bot.get_cog('TaxSystem')
        tax_amount = 0
        
        if tax_cog:
            # Check if tax exempt
            is_exempt = await tax_cog.is_tax_exempt(ctx.author.id, user_data["level"])
            
            if not is_exempt:
                # Tax 0.1% dari gross
                tax_amount = int(gross_receive * tax_cog.TAX_RATES["trading_sell_tax"])
        
        net_receive = gross_receive - tax_amount
        
        # Calculate profit/loss
        avg_buy = holdings["avg_buy_price"]
        profit_loss = int((current_price - avg_buy) * amount)
        profit_pct = ((current_price - avg_buy) / avg_buy) * 100
        
        # ========================================
        # PROCESS SALE
        # ========================================
        # Add net receive (setelah dipotong tax)
        await update_user(ctx.author.id, currency=net_receive)
        
        # Update quest progress (hanya jika profit)
        quest_cog = self.bot.get_cog('Quests')
        if quest_cog and profit_loss > 0:
            await quest_cog.update_quest_progress(ctx.author.id, "trade_profit", profit_loss)

        # Remove crypto dari portfolio
        await self.update_portfolio(ctx.author.id, crypto.upper(), -amount, current_price)
        
        # Log tax
        if tax_cog and tax_amount > 0:
            await tax_cog.log_transaction_tax(ctx.author.id, "trading_sell_tax", tax_amount)
        
        info = self.available_crypto[crypto]
        color = 0x00ff00 if profit_loss >= 0 else 0xff0000
        
        embed = discord.Embed(
            title="✅ Penjualan Berhasil!",
            color=color
        )
        embed.add_field(name="Crypto", value=f"{info['symbol']} ({info['name']})", inline=True)
        embed.add_field(name="Jumlah", value=f"{amount:,.8f}", inline=True)
        embed.add_field(name="Harga/unit", value=f"Rp {current_price:,.0f}", inline=True)
        
        embed.add_field(name="💵 Gross", value=f"Rp {gross_receive:,}", inline=True)
        
        if tax_amount > 0:
            embed.add_field(name="�️ Pajak (0.1%)", value=f"Rp {tax_amount:,}", inline=True)
            embed.add_field(name="💰 Net Terima", value=f"Rp {net_receive:,}", inline=True)
        else:
            embed.add_field(name="💰 Net Terima", value=f"Rp {net_receive:,}", inline=True)
            embed.add_field(name="🏛️ Tax Status", value="**BEBAS PAJAK**", inline=True)
        
        embed.add_field(
            name="📊 Profit/Loss",
            value=f"**{profit_loss:+,} Rp** ({profit_pct:+.2f}%)",
            inline=False
        )
        embed.set_footer(text="Gunakan mochi!portfolio untuk lihat aset kamu")
        
        await ctx.send(embed=embed)

    @commands.command(name="portfolio")
    async def portfolio_command(self, ctx, member: discord.Member = None):
        """Lihat portfolio crypto"""
        user = member or ctx.author
        user_data = await get_user(user.id)
        
        if not user_data:
            await ctx.send(f"{user.mention} belum punya data!")
            return
        
        portfolio = await self.get_user_portfolio(user.id)
        
        if not portfolio:
            embed = discord.Embed(
                title=f"💼 Portfolio {user.display_name}",
                description="Portfolio crypto kosong. Mulai trading dengan `mochi!buy`!",
                color=0xff6b6b
            )
            embed.add_field(name="💰 Cash", value=f"Rp {user_data['currency']:,}", inline=False)
            await ctx.send(embed=embed)
            return
        
        total_value = 0
        total_invested = 0
        portfolio_text = ""
        
        for holding in portfolio:
            crypto_id = holding["crypto_symbol"].lower()
            
            crypto_info = None
            for cid, info in self.available_crypto.items():
                if info["symbol"] == holding["crypto_symbol"]:
                    crypto_id = cid
                    crypto_info = info
                    break
            
            if not crypto_info:
                continue
            
            price_data = await self.get_crypto_price(crypto_id)
            
            if price_data:
                current_price = price_data["price"]
                current_value = current_price * holding["amount"]
                invested = holding["avg_buy_price"] * holding["amount"]
                profit_loss = current_value - invested
                profit_pct = ((current_price - holding["avg_buy_price"]) / holding["avg_buy_price"]) * 100
                
                total_value += current_value
                total_invested += invested
                
                pl_emoji = "📈" if profit_loss >= 0 else "📉"
                
                portfolio_text += f"\n**{crypto_info['symbol']}** ({crypto_info['name']})\n"
                portfolio_text += f"├─ Jumlah: `{holding['amount']:,.8f}`\n"
                portfolio_text += f"├─ Harga Beli: `Rp {holding['avg_buy_price']:,.0f}`\n"
                portfolio_text += f"├─ Harga Sekarang: `Rp {current_price:,.0f}`\n"
                portfolio_text += f"├─ Nilai: `Rp {current_value:,.0f}`\n"
                portfolio_text += f"└─ {pl_emoji} P/L: `{'+'if profit_loss >= 0 else ''}{profit_loss:,.0f}` ({profit_pct:+.2f}%)\n"
        
        total_pl = total_value - total_invested
        total_pl_pct = (total_pl / total_invested * 100) if total_invested > 0 else 0
        
        color = 0x00ff00 if total_pl >= 0 else 0xff0000
        
        embed = discord.Embed(
            title=f"💼 Portfolio {user.display_name}",
            description=portfolio_text,
            color=color
        )
        
        embed.add_field(
            name="📊 Summary",
            value=(
                f"💰 **Cash**: Rp {user_data['currency']:,}\n"
                f"💎 **Total Aset**: Rp {total_value:,.0f}\n"
                f"🎯 **Total Invested**: Rp {total_invested:,.0f}\n"
                f"{'📈' if total_pl >= 0 else '📉'} **Total P/L**: {'+'if total_pl >= 0 else ''}{total_pl:,.0f} ({total_pl_pct:+.2f}%)\n"
                f"💵 **Net Worth**: Rp {user_data['currency'] + int(total_value):,}"
            ),
            inline=False
        )
        
        embed.set_footer(text="Gunakan mochi!market untuk lihat harga • Data real-time dari CoinGecko")
        await ctx.send(embed=embed)

    @commands.command(name="chart")
    async def crypto_chart(self, ctx, crypto: str = None, days: str = "7"):
        """Lihat chart harga crypto"""
        if crypto is None:
            await ctx.send(
                "❌ **Format salah!**\n"
                "✅ Gunakan: `mochi!chart <crypto> [hari]`\n"
                "📌 Contoh:\n"
                "• `mochi!chart btc` - Chart 7 hari\n"
                "• `mochi!chart eth 30` - Chart 30 hari\n\n"
                "💎 Crypto tersedia: btc, eth, bnb, sol, xrp, gold, silver"
            )
            return
        
        crypto = crypto.lower()
        
        if crypto not in self.available_crypto:
            await ctx.send(f"❌ Crypto `{crypto}` tidak tersedia! Cek `mochi!market`")
            return
        
        try:
            days_int = int(days)
            if days_int not in [1, 7, 30, 90]:
                await ctx.send("❌ Pilih periode: `1`, `7`, `30`, atau `90` hari")
                return
        except:
            await ctx.send("❌ Periode harus angka! (1/7/30/90)")
            return
        
        loading_msg = await ctx.send(f"⏳ Mengambil data chart {crypto.upper()} untuk {days_int} hari...")
        
        try:
            coingecko_id = self.available_crypto[crypto]["coingecko_id"]
            url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart?vs_currency=idr&days={days_int}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        prices = data["prices"]
                        
                        if not prices:
                            await loading_msg.edit(content="❌ Data chart tidak tersedia!")
                            return
                        
                        timestamps = [p[0] for p in prices]
                        price_values = [p[1] for p in prices]
                        
                        current_price = price_values[-1]
                        start_price = price_values[0]
                        min_price = min(price_values)
                        max_price = max(price_values)
                        change = ((current_price - start_price) / start_price) * 100
                        
                        chart_height = 12
                        chart_width = 35
                        
                        price_range = max_price - min_price
                        if price_range == 0:
                            normalized = [chart_height // 2] * len(price_values)
                        else:
                            normalized = [
                                int(((p - min_price) / price_range) * (chart_height - 1))
                                for p in price_values
                            ]
                        
                        if len(normalized) > chart_width:
                            step = len(normalized) // chart_width
                            normalized = [normalized[i * step] for i in range(chart_width)]
                        
                        chart_lines = []
                        for y in range(chart_height - 1, -1, -1):
                            line = ""
                            for x in range(len(normalized)):
                                if normalized[x] == y:
                                    line += "●"
                                elif normalized[x] > y:
                                    line += "│"
                                else:
                                    line += " "
                            chart_lines.append(line)
                        
                        chart_text = "\n".join(chart_lines)
                        
                        trend_emoji = "📈" if change >= 0 else "📉"
                        
                        info = self.available_crypto[crypto]
                        embed = discord.Embed(
                            title=f"{trend_emoji} {info['symbol']} Chart - {days_int} Hari",
                            description=f"```\n{chart_text}\n```",
                            color=0x00ff00 if change >= 0 else 0xff0000
                        )
                        
                        embed.add_field(
                            name="📊 Statistics",
                            value=(
                                f"**Current**: Rp {current_price:,.0f}\n"
                                f"**Change**: {change:+.2f}%\n"
                                f"**High**: Rp {max_price:,.0f}\n"
                                f"**Low**: Rp {min_price:,.0f}"
                            ),
                            inline=False
                        )
                        
                        embed.set_footer(text=f"Data dari CoinGecko • {days_int} hari terakhir")
                        
                        await loading_msg.edit(content=None, embed=embed)
                    else:
                        await loading_msg.edit(content="❌ Gagal mengambil data chart! Coba lagi nanti.")
        except Exception as e:
            print(f"Error fetching chart: {e}")
            await loading_msg.edit(content="❌ Terjadi error saat mengambil chart! Coba lagi.")
    
    @commands.command(name="thelp", aliases=["tradinghelp", "helptrade", "help_trade"])
    async def trading_help(self, ctx):
        """📖 Panduan trading system"""
        user_data = await get_user(ctx.author.id)
        is_tax_exempt = user_data and user_data["level"] >= 20
        
        embed = discord.Embed(
            title="📈 Crypto Trading System - Help",
            description="Trading crypto real-time dengan harga dari CoinGecko!",
            color=0x2ecc71 if is_tax_exempt else 0x3498db
        )
        
        embed.add_field(
            name="💰 Basic Commands",
            value=(
                "`mochi!market` - Lihat harga crypto real-time\n"
                "`mochi!buy <crypto> <amount>` - Beli crypto\n"
                "`mochi!sell <crypto> <amount>` - Jual crypto\n"
                "`mochi!portfolio [@user]` - Lihat portfolio\n"
                "`mochi!chart <crypto> [days]` - Lihat chart harga"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💎 Available Crypto",
            value=(
                "• **BTC** (Bitcoin)\n"
                "• **ETH** (Ethereum)\n"
                "• **BNB** (Binance Coin)\n"
                "• **SOL** (Solana)\n"
                "• **XRP** (Ripple)\n"
                "• **GOLD** (Gold)\n"
                "• **SILVER** (Silver)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🏛️ Pajak Trading",
            value=(
                f"**Buy Tax**: 0.1% dari pembelian\n"
                f"**Sell Tax**: 0.1% dari penjualan\n"
                f"**Status Kamu**: {'👑 BEBAS PAJAK (Adipati/Raja)' if is_tax_exempt else '⚠️ Kena Pajak'}\n"
                f"{'Naik ke Level 20+ untuk bebas pajak!' if not is_tax_exempt else 'Semua transaksi tanpa potongan!'}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Pro Tips",
            value=(
                "📊 Cek `mochi!market` sebelum buy/sell\n"
                "📈 Gunakan `mochi!chart` untuk analisa trend\n"
                "💰 Crypto **tidak kena weekly tax** (berbeda dengan cash)\n"
                "🎯 Hold jangka panjang untuk profit maksimal\n"
                "⚡ Harga update setiap 30 detik\n"
                "👑 Naik Level 20+ untuk trading bebas pajak!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📌 Contoh Penggunaan",
            value=(
                "`mochi!buy btc 1000000` - Beli BTC Rp 1jt\n"
                "`mochi!buy eth all` - Beli ETH semua saldo\n"
                "`mochi!sell btc 0.001` - Jual 0.001 BTC\n"
                "`mochi!sell sol all` - Jual semua SOL\n"
                "`mochi!chart btc 30` - Chart BTC 30 hari"
            ),
            inline=False
        )
        
        embed.set_footer(text="Data real-time dari CoinGecko API")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Trading(bot))