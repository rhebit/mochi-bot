import discord
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime

class TradingAdvanced(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.price_alerts = {}  # {user_id: [{crypto, target_price, condition}]}
    
    @commands.command(name="history")
    async def trade_history(self, ctx, limit: int = 10):
        """Lihat riwayat trading (buy/sell terakhir)"""
        if limit > 50:
            limit = 50
        
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM trade_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (ctx.author.id, limit))
            rows = await cursor.fetchall()
        
        if not rows:
            await ctx.send("📭 Belum ada riwayat trading!")
            return
        
        embed = discord.Embed(
            title=f"📜 Trading History - {ctx.author.display_name}",
            color=0x3498db
        )
        
        history_text = ""
        for row in rows:
            trade_type = "🟢 BUY" if row["trade_type"] == "buy" else "🔴 SELL"
            emoji = "💰" if row["profit_loss"] is None else ("📈" if row["profit_loss"] >= 0 else "📉")
            
            history_text += f"\n{trade_type} **{row['crypto_symbol']}**\n"
            history_text += f"├─ Jumlah: `{row['amount']:,.6f}`\n"
            history_text += f"├─ Harga: `Rp {row['price']:,.0f}`\n"
            
            if row["profit_loss"] is not None:
                history_text += f"└─ {emoji} P/L: `{row['profit_loss']:+,.0f}`\n"
            else:
                history_text += f"└─ Total: `Rp {row['total']:,.0f}`\n"
        
        embed.description = history_text
        embed.set_footer(text=f"Showing last {len(rows)} trades")
        await ctx.send(embed=embed)
    
    @commands.command(name="alert")
    async def price_alert(self, ctx, crypto: str = None, condition: str = None, price: float = None):
        """Set price alert. Contoh: mochi!alert btc above 1000000000"""
        if crypto is None or condition is None or price is None:
            await ctx.send(
                "❌ **Format salah!**\n"
                "✅ Gunakan: `mochi!alert <crypto> <above/below> <harga>`\n"
                "📌 Contoh:\n"
                "• `mochi!alert btc above 1500000000` - Notif jika BTC > 1.5M\n"
                "• `mochi!alert eth below 30000000` - Notif jika ETH < 30M"
            )
            return
        
        crypto = crypto.lower()
        condition = condition.lower()
        
        if condition not in ["above", "below"]:
            await ctx.send("❌ Condition harus `above` atau `below`!")
            return
        
        # Simpan alert (in-memory untuk simple version)
        if ctx.author.id not in self.price_alerts:
            self.price_alerts[ctx.author.id] = []
        
        self.price_alerts[ctx.author.id].append({
            "crypto": crypto,
            "condition": condition,
            "target_price": price,
            "created_at": datetime.utcnow()
        })
        
        await ctx.send(
            f"✅ Alert diset!\n"
            f"📊 **{crypto.upper()}** {condition} Rp {price:,.0f}\n"
            f"Kamu akan dapat DM jika kondisi terpenuhi!"
        )
    
    @commands.command(name="alerts")
    async def view_alerts(self, ctx):
        """Lihat semua price alerts aktif"""
        if ctx.author.id not in self.price_alerts or not self.price_alerts[ctx.author.id]:
            await ctx.send("📭 Kamu belum set alert apapun!")
            return
        
        embed = discord.Embed(
            title="🔔 Price Alerts Aktif",
            color=0xf39c12
        )
        
        alerts_text = ""
        for i, alert in enumerate(self.price_alerts[ctx.author.id], 1):
            alerts_text += (
                f"`{i}.` **{alert['crypto'].upper()}** "
                f"{alert['condition']} Rp {alert['target_price']:,.0f}\n"
            )
        
        embed.description = alerts_text
        embed.set_footer(text="Gunakan mochi!delalert <nomor> untuk hapus")
        await ctx.send(embed=embed)
    
    @commands.command(name="delalert")
    async def delete_alert(self, ctx, index: int):
        """Hapus price alert berdasarkan nomor"""
        if ctx.author.id not in self.price_alerts or not self.price_alerts[ctx.author.id]:
            await ctx.send("📭 Kamu tidak punya alert!")
            return
        
        if index < 1 or index > len(self.price_alerts[ctx.author.id]):
            await ctx.send(f"❌ Alert nomor {index} tidak ada!")
            return
        
        deleted = self.price_alerts[ctx.author.id].pop(index - 1)
        await ctx.send(
            f"✅ Alert dihapus!\n"
            f"📊 **{deleted['crypto'].upper()}** {deleted['condition']} "
            f"Rp {deleted['target_price']:,.0f}"
        )
    
    @commands.command(name="networth")
    async def net_worth_leaderboard(self, ctx):
        """Leaderboard berdasarkan net worth (cash + crypto assets)"""
        # Get trading cog untuk akses harga
        trading_cog = self.bot.get_cog('Trading')
        if not trading_cog:
            await ctx.send("❌ Trading system tidak aktif!")
            return
        
        from database import get_user
        
        # Get all users with crypto portfolio
        async with aiosqlite.connect("mochi.db") as db:
            cursor = await db.execute("""
                SELECT DISTINCT user_id FROM crypto_portfolio
            """)
            user_ids = [row[0] for row in await cursor.fetchall()]
        
        # Calculate net worth for each user
        net_worths = []
        for user_id in user_ids:
            user_data = await get_user(user_id)
            if not user_data:
                continue
            
            cash = user_data["currency"]
            portfolio = await trading_cog.get_user_portfolio(user_id)
            
            total_assets = 0
            for holding in portfolio:
                crypto_id = holding["crypto_symbol"].lower()
                
                # Find crypto info
                for cid, info in trading_cog.available_crypto.items():
                    if info["symbol"] == holding["crypto_symbol"]:
                        crypto_id = cid
                        break
                
                price_data = await trading_cog.get_crypto_price(crypto_id)
                if price_data:
                    total_assets += price_data["price"] * holding["amount"]
            
            net_worth = cash + int(total_assets)
            net_worths.append((user_id, net_worth, cash, int(total_assets)))
        
        # Sort by net worth
        net_worths.sort(key=lambda x: x[1], reverse=True)
        
        if not net_worths:
            await ctx.send("📭 Belum ada yang punya crypto!")
            return
        
        embed = discord.Embed(
            title="💎 Net Worth Leaderboard",
            description="Top traders berdasarkan total aset (Cash + Crypto)",
            color=0x2ecc71
        )
        
        leaderboard_text = ""
        for i, (user_id, net_worth, cash, assets) in enumerate(net_worths[:10], 1):
            user = self.bot.get_user(user_id)
            username = user.display_name if user else f"User {user_id}"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"`{i}.`"
            
            leaderboard_text += (
                f"{medal} **{username}**\n"
                f"├─ Net Worth: `Rp {net_worth:,}`\n"
                f"├─ Cash: `Rp {cash:,}`\n"
                f"└─ Crypto: `Rp {assets:,}`\n\n"
            )
        
        embed.description = leaderboard_text
        embed.set_footer(text="Trade smart, get rich! 💰")
        await ctx.send(embed=embed)
    
    @commands.command(name="convert")
    async def convert_crypto(self, ctx, amount: float = None, from_crypto: str = None, to_crypto: str = None):
        """Konversi nilai crypto. Contoh: mochi!convert 1 btc eth"""
        if amount is None or from_crypto is None or to_crypto is None:
            await ctx.send(
                "❌ **Format salah!**\n"
                "✅ Gunakan: `mochi!convert <jumlah> <dari> <ke>`\n"
                "📌 Contoh: `mochi!convert 1 btc eth`"
            )
            return
        
        from_crypto = from_crypto.lower()
        to_crypto = to_crypto.lower()
        
        trading_cog = self.bot.get_cog('Trading')
        if not trading_cog:
            await ctx.send("❌ Trading system tidak aktif!")
            return
        
        if from_crypto not in trading_cog.available_crypto:
            await ctx.send(f"❌ Crypto `{from_crypto}` tidak tersedia!")
            return
        
        if to_crypto not in trading_cog.available_crypto:
            await ctx.send(f"❌ Crypto `{to_crypto}` tidak tersedia!")
            return
        
        # Get prices
        from_price_data = await trading_cog.get_crypto_price(from_crypto)
        to_price_data = await trading_cog.get_crypto_price(to_crypto)
        
        if not from_price_data or not to_price_data:
            await ctx.send("❌ Gagal mengambil harga! Coba lagi.")
            return
        
        from_price = from_price_data["price"]
        to_price = to_price_data["price"]
        
        # Calculate conversion
        from_value_idr = amount * from_price
        to_amount = from_value_idr / to_price
        
        from_info = trading_cog.available_crypto[from_crypto]
        to_info = trading_cog.available_crypto[to_crypto]
        
        embed = discord.Embed(
            title="💱 Crypto Converter",
            color=0x9b59b6
        )
        embed.add_field(
            name="From",
            value=f"`{amount:,.6f}` {from_info['symbol']}\n= Rp {from_value_idr:,.0f}",
            inline=True
        )
        embed.add_field(
            name="To",
            value=f"`{to_amount:,.6f}` {to_info['symbol']}\n= Rp {from_value_idr:,.0f}",
            inline=True
        )
        embed.set_footer(text="Harga real-time dari CoinGecko")
        
        await ctx.send(embed=embed)

# Database migration untuk fitur advanced (optional)
async def create_history_table():
    """Tambahkan tabel trade_history untuk tracking"""
    import aiosqlite
    async with aiosqlite.connect("mochi.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                trade_type TEXT NOT NULL,
                crypto_symbol TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                total REAL NOT NULL,
                profit_loss REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def setup(bot):
    await bot.add_cog(TradingAdvanced(bot))