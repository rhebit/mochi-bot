import discord
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime, timedelta, timezone
from database import get_user, update_user, get_tax_system_state, update_tax_system_state, create_user 
from utils.helpers import get_rank_title, OWNER_ID 
from utils.config_secrets import QUEST_CHANNEL_ID # <<< IMPOR QUEST_CHANNEL_ID DARI SINI

def get_next_monday_1700_utc() -> datetime:
    """Menghitung waktu Hari Senin berikutnya pada pukul 17:00 UTC."""
    # 1. Dapatkan waktu UTC saat ini
    now_utc = datetime.now(timezone.utc)
    
    # 2. Hitung jumlah hari ke Hari Senin berikutnya
    # weekday() Senin=0, Minggu=6. Jika sekarang Senin (0), perlu 7 hari lagi.
    # (0 - 0) % 7 = 0. Jika sekarang Minggu (6), perlu (0 - 6) % 7 = 1 hari lagi.
    days_until_monday = (0 - now_utc.weekday()) % 7
    if days_until_monday == 0:
        # Jika sekarang Hari Senin, kita cari Senin di minggu depan (7 hari)
        days_until_monday = 7 
        
    # 3. Hitung tanggal Hari Senin berikutnya (tanpa memperhatikan jam)
    next_monday = now_utc + timedelta(days=days_until_monday)
    
    # 4. Set waktu ke 17:00:00 UTC
    # 17:00 UTC = 00:00 WIB (UTC+7)
    next_monday_1700_utc = next_monday.replace(hour=17, minute=0, second=0, microsecond=0)
    
    # 5. Cek jika waktu yang dihitung sudah terlewat HARI INI
    # Ini terjadi jika bot dinyalakan setelah 17:00 UTC pada Hari Senin
    if next_monday_1700_utc < now_utc:
        # Pindah ke Hari Senin berikutnya lagi
        next_monday_1700_utc += timedelta(weeks=1)

    return next_monday_1700_utc

class TaxSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.TAX_RATES = {
            "income_tax": 0.05, 
            "trading_buy_tax": 0.001, 
            "trading_sell_tax": 0.001, 
            "fishing_sell_tax": 0.01, 
            "jade_cut_tax": 0.02, 
            "item_trade_tax": 0.10, 
        }
        
        self.TAX_FREE_RANKS = ["Adipati", "Raja"]
        
        self.weekly_tax_collection.start()

    def cog_unload(self):
        self.weekly_tax_collection.cancel()

    # --- HELPER: LOG TAX HISTORY (Dipindahkan ke dalam class) ---
    async def record_tax_history(self, user_id: int, tax_type: str, amount: int):
        """Helper to log tax history."""
        async with aiosqlite.connect("mochi.db") as db:
            await db.execute("""
                INSERT INTO tax_history (user_id, tax_type, amount, collected_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, tax_type, amount, datetime.utcnow()))
            await db.commit()

    # --- HELPER: CHECK TAX EXEMPTION ---
    def is_tax_exempt_level(self, level: int):
        """Check apakah user bebas pajak berdasarkan level (Level 20+ / Adipati/Raja)"""
        return level >= 20
    
    # --- AUTOMATIC TASK LOOP SETUP ---
    @tasks.loop(hours=1)
    async def weekly_tax_collection(self):
        """Check setiap jam, collect pajak setiap Senin jam 00:00 UTC+7"""
        now = datetime.utcnow()
        # 17:00 UTC = 00:00 WIB
        if now.weekday() == 0 and now.hour == 17 and now.minute < 5: 
            await self.collect_weekly_taxes()
    
    @weekly_tax_collection.before_loop
    async def before_weekly_tax(self):
        await self.bot.wait_until_ready()

    # --- CORE LOGIC: COLLECT TAXES (Dipanggil oleh Task dan Forcetax) ---
    async def collect_weekly_taxes(self):
        """Collect pajak mingguan dari semua user dan kirim pengumuman."""
        print("💰 Starting weekly tax collection...")
        
        tax_channel = self.bot.get_channel(QUEST_CHANNEL_ID) 
        
        total_collected = 0
        taxed_users = 0
        exempt_users = 0
        
        async with aiosqlite.connect("mochi.db") as db:
            cursor = await db.execute("SELECT user_id, currency, level FROM users WHERE currency > 0")
            users = await cursor.fetchall()
            
            for user_id, currency, level in users:
                # Check if user is tax exempt (Logic baru)
                if self.is_tax_exempt_level(level):
                    exempt_users += 1
                    continue
                
                # Calculate tax (5% of cash)
                tax_amount = int(currency * self.TAX_RATES["income_tax"])
                
                if tax_amount > 0:
                    # Deduct tax
                    await update_user(user_id, currency=-tax_amount)
                    
                    # Log tax history
                    await self.record_tax_history(user_id, "income_tax", tax_amount)
                    
                    total_collected += tax_amount
                    taxed_users += 1
            
            await db.commit()
        
        # Send announcement (Logic pengumuman yang sudah ada)
        if tax_channel:
            embed = discord.Embed(
                title="🏛️ Weekly Tax Collection",
                description=f"Pajak mingguan telah dikumpulkan!\n**Periode**: {datetime.utcnow().strftime('%d/%m/%Y')}",
                color=0xe74c3c
            )
            embed.add_field(name="💰 Total Collected", value=f"Rp {total_collected:,}", inline=True)
            embed.add_field(name="👥 Taxed Users", value=f"{taxed_users}", inline=True)
            embed.add_field(name="👑 Tax Exempt", value=f"{exempt_users}", inline=True)
            embed.add_field(
                name="ℹ️ Info",
                value=(
                    "• **5%** dari cash kamu\n"
                    "• Tidak termasuk crypto/ikan\n"
                    "• **Adipati & Raja** bebas pajak\n"
                    "• Gunakan `mochi!taxinfo` untuk detail"
                ),
                inline=False
            )
            embed.set_footer(text="Tax dikumpulkan setiap Senin pagi • Invest di crypto untuk avoid tax!")
            await tax_channel.send(embed=embed)
        
        print(f"✅ Tax collection complete: Rp {total_collected:,} from {taxed_users} users")
        
        return total_collected, taxed_users, exempt_users # Return untuk forcetax

    # --- mochi!forcetax COMMAND (Logic Baru) ---
    @commands.command(name="forcetax")
    async def force_tax_collection_command(self, ctx):
        """🔧 [OWNER] Force trigger weekly tax collection (max 1x/minggu kalender)"""
        
        allowed_owners = OWNER_ID if isinstance(OWNER_ID, list) else [OWNER_ID]
        if ctx.author.id not in allowed_owners:
            await ctx.send("❌ Hanya owner yang bisa pakai command ini!")
            return
            
        now = datetime.utcnow()
        state = await get_tax_system_state()
        
        last_forced_str = state.get("last_forced_tax")
        
        # --- PERUBAHAN LOGIKA COOLDOWN MINGGUAN ---
        if last_forced_str:
            last_forced = datetime.fromisoformat(last_forced_str)
            
            # Cari Hari Senin dari tanggal terakhir forcetax
            last_monday = last_forced - timedelta(days=last_forced.weekday())
            # Cari Hari Senin dari tanggal saat ini
            current_monday = now - timedelta(days=now.weekday())
            
            # Jika Hari Senin (tanggal) sama, artinya masih dalam minggu yang sama.
            if last_monday.date() == current_monday.date():
                
                # Cooldown aktif: Hitung kapan Hari Senin berikutnya (waktu reset)
                next_monday_reset = current_monday + timedelta(days=7)
                time_left = next_monday_reset - now
                days_left = time_left.days
                hours_left = time_left.seconds // 3600
                
                await ctx.send(
                    f"⏰ **Manual tax collection sudah dilakukan untuk minggu ini**\n"
                    f"Terakhir dilakukan: {last_forced.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                    f"Bisa dilakukan lagi saat reset mingguan pada **Senin ({next_monday_reset.date()})**."
                )
                return

        # 3. State reason for collection (Dilanjutkan jika Cooldown telah di-reset)
        await ctx.send(
            f"💰 Starting manual weekly tax collection...\n"
            f"**Alasan:** Bot kemungkinan mati atau gagal menjalankan scheduled task pada jadwal seharusnya (Senin).\n"
            f"**Perhatian:** Fitur ini hanya bisa dipakai sekali per periode Senin-Minggu."
        )

        # 4. Perform collection dan update state
        total_collected, taxed_users, exempt_users = await self.collect_weekly_taxes()
        await update_tax_system_state(last_forced_tax=now.isoformat())
        
        await ctx.send("✅ **Manual tax collection complete!** Weekly income tax telah dikumpulkan dari semua user yang dikenakan pajak.")

    # --- is_tax_exempt (Helper untuk transaksi dan taxinfo) ---
    async def is_tax_exempt(self, user_id: int, level: int = None):
        """Check apakah user bebas pajak (Adipati/Raja)"""
        if level is None:
            user_data = await get_user(user_id)
            if not user_data:
                return False
            level = user_data["level"]
        return self.is_tax_exempt_level(level) # Panggil helper level

    # --- TRANSACTION TAX CALCULATIONS ---
    def calculate_transaction_tax(self, amount: int, tax_type: str, user_level: int = 0):
        # ... (logic tidak berubah, menggunakan self.is_tax_exempt_level)
        if user_level >= 20:
            return 0, amount
        tax_rate = self.TAX_RATES.get(tax_type, 0)
        tax_amount = int(amount * tax_rate)
        net_amount = amount - tax_amount
        return tax_amount, net_amount

    async def log_transaction_tax(self, user_id: int, tax_type: str, amount: int):
        # ... (logic tidak berubah, memanggil record_tax_history)
        await self.record_tax_history(user_id, tax_type, amount)

    @commands.command(name="taxinfo")
    async def tax_info(self, ctx):
        """Lihat info dan tarif pajak saat ini."""
        
        user_data = await get_user(ctx.author.id)
        current_level = user_data["level"] if user_data else 1
        is_exempt = self.is_tax_exempt_level(current_level)
        
        embed = discord.Embed(
            title="🏛️ Tax System Information",
            description="Informasi tarif pajak mingguan dan transaksi di Mochi.",
            color=0x3498db
        )

        embed.add_field(
            name="📉 Weekly Income Tax (Cash)",
            value=(
                f"**Tarif**: **{self.TAX_RATES['income_tax']*100:.0f}%** dari total Cash\n"
                f"**Jadwal**: Setiap hari Senin pukul 00:00 WIB (17:00 UTC)\n"
                f"**Status Kamu**: {'👑 BEBAS PAJAK (Level 20+)' if is_exempt else '⚠️ Kena Pajak'}"
            ),
            inline=False
        )
        
        tax_list = "\n".join([
            f"• **Trading (Buy/Sell)**: {self.TAX_RATES['trading_buy_tax']*100:.1f}% (Total 0.2%)",
            f"• **Fishing (Sell)**: {self.TAX_RATES['fishing_sell_tax']*100:.0f}%",
            f"• **Jade Cut**: {self.TAX_RATES['jade_cut_tax']*100:.0f}%",
            f"• **Item Trade (User)**: {self.TAX_RATES['item_trade_tax']*100:.0f}%"
        ])

        embed.add_field(
            name="📊 Transaction Taxes (Bebas jika Level 20+)",
            value=tax_list,
            inline=False
        )
        
        embed.set_footer(text="Aset selain cash (crypto/item) BEBAS dari Weekly Tax!")
        await ctx.send(embed=embed)
    
    # cogs/tax.py

    @commands.command(name="taxhistory", aliases=["taxh"])
    async def tax_history(self, ctx, limit: int = 10):
        """Lihat riwayat potongan pajak terakhir kamu (default 10 data)."""
        # Batas maksimum adalah 20, jika user input angka terlalu besar
        if limit > 20: 
            limit = 20 
            
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT tax_type, amount, collected_at FROM tax_history
                WHERE user_id = ?
                ORDER BY collected_at DESC
                LIMIT ?
            """, (ctx.author.id, limit))
            rows = await cursor.fetchall()
        
        if not rows:
            await ctx.send("📭 **Belum ada riwayat potongan pajak.**")
            return
            
        history_text = ""
        for row in rows:
            # Format: [YYYY-MM-DD HH:MM] [Tipe] Rp [Jumlah]
            tax_date = datetime.fromisoformat(row["collected_at"]).strftime('%Y-%m-%d %H:%M')
            tax_name = row['tax_type'].replace('_', ' ').title() # Untuk tampilan yang lebih rapi
            
            history_text += (
                f"`[{tax_date}]` **{tax_name}**: "
                f"Rp {row['amount']:,}\n"
            )

        embed = discord.Embed(
            title=f"📜 Tax History - {ctx.author.display_name}",
            description=history_text,
            color=0xf39c12
        )
        embed.set_footer(text=f"Menampilkan {len(rows)} data terakhir. Gunakan mochi!taxh <jumlah> untuk ganti batas.")
        await ctx.send(embed=embed)

    # cogs/tax.py

    @commands.command(name="taxstats")
    async def tax_stats(self, ctx):
        """Lihat total pajak yang terkumpul dan Top Taxpayers."""
        
        async with aiosqlite.connect("mochi.db") as db:
            db.row_factory = aiosqlite.Row
            
            # 1. Hitung Total Pajak Terkumpul
            total_cursor = await db.execute("SELECT SUM(amount) AS total FROM tax_history")
            total_collected = (await total_cursor.fetchone())["total"] or 0
            
            # 2. Top 10 Taxpayers (SUM dari semua tax_history)
            top_cursor = await db.execute("""
                SELECT user_id, SUM(amount) AS total_amount 
                FROM tax_history
                GROUP BY user_id
                ORDER BY total_amount DESC
                LIMIT 10
            """)
            top_taxpayers = await top_cursor.fetchall()

        embed = discord.Embed(
            title="📊 Mochi Tax System Stats",
            description="Statistik total pajak yang dikumpulkan oleh Mochi.",
            color=0xe74c3c
        )
        
        embed.add_field(
            name="💰 Total Pajak Terkumpul (Semua Tipe)",
            value=f"**Rp {total_collected:,}**",
            inline=False
        )

        top_text = ""
        # Dapatkan nama user untuk 10 besar
        for i, row in enumerate(top_taxpayers, 1):
            user = self.bot.get_user(row["user_id"])
            username = user.display_name if user else f"Unknown User ({row['user_id']})"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            top_text += f"{medal} **{username}**: Rp {row['total_amount']:,}\n"
        
        embed.add_field(name="🏆 Top Taxpayers", value=top_text or "No data", inline=False)
        embed.set_footer(text="Good taxpayers = good citizens! 👍")
        
        await ctx.send(embed=embed)


async def setup(bot):
    # Asumsi init_tax_tables ada di database.py
    # Jika tidak, Anda harus memindahkan init_tax_tables ke database.py
    await bot.add_cog(TaxSystem(bot))