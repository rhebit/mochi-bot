import discord
from discord.ext import commands
import asyncio

from database import get_user, update_user

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="tradeitem")
    async def trade_item(self, ctx, member: discord.Member = None, item_code: str = None, amount: int = None, price: int = None):
        """Jual item ke orang lain dengan konfirmasi. 
        
        Contoh: `mochi!tradeitem @teman 2x 1 50000`
        """
        
        # Validasi input
        if member is None or item_code is None or amount is None or price is None:
            await ctx.send(
                "❌ **Format salah!**\n"
                "✅ Gunakan: `mochi!tradeitem @user <item> <jumlah> <harga>`\n"
                "📌 Contoh:\n"
                "• `mochi!tradeitem @teman 2x 1 50000`\n"
                "• `mochi!tradeitem @user 4x 2 100000`\n\n"
                "🎁 Item tersedia: `2x`, `4x`, `8x`, `10x`, `20x`"
            )
            return
        
        if ctx.author.id == member.id:
            await ctx.send("Kamu tidak bisa trade dengan diri sendiri!")
            return

        seller = ctx.author
        buyer = member
        seller_data = await get_user(seller.id)
        buyer_data = await get_user(buyer.id)

        if not seller_data or not buyer_data:
            await ctx.send("Salah satu pihak belum punya data!")
            return

        if buyer_data["currency"] < price:
            await ctx.send(f"{buyer.mention} tidak punya cukup uang! Butuh Rp {price:,}")
            return

        item_map = {
            "2x": "xp_2x",
            "4x": "xp_4x",
            "8x": "xp_8x",
            "10x": "xp_10x",
            "20x": "xp_20x"
        }

        if item_code not in item_map:
            await ctx.send("Item tidak valid! Gunakan: `2x`, `4x`, `8x`, `10x`, atau `20x`")
            return

        db_column = item_map[item_code]
        seller_stock = seller_data[db_column]

        if seller_stock < amount:
            await ctx.send(f"Kamu hanya punya `{seller_stock}` item `{item_code}`!")
            return

        # === KONFIRMASI DARI PEMBELI ===
        confirm_msg = await ctx.send(
            f"{buyer.mention}, ketik `y` atau `n` dalam 30 detik untuk konfirmasi pembelian:\n"
            f"**{amount}x {item_code}** seharga **Rp {price:,}** dari {seller.mention}"
        )

        def check(m):
            return m.author == buyer and m.channel == ctx.channel and m.content.lower() in ['y', 'n']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            if msg.content.lower() == 'y':
                # Seller: kurangi item, tambah currency
                await update_user(
                    seller.id,
                    **{f"set_{db_column}": seller_stock - amount},
                    currency=price
                )
                # Buyer: tambah item, kurangi currency
                await update_user(
                    buyer.id,
                    **{db_column: amount},
                    currency=-price
                )
                await ctx.send(f"✅ Transaksi berhasil! {buyer.mention} membeli {amount}x {item_code} dari {seller.mention}")
            else:
                await ctx.send("❌ Transaksi dibatalkan oleh pembeli.")
        except asyncio.TimeoutError:
            await ctx.send("⏰ Waktu konfirmasi habis! Transaksi dibatalkan.")
        finally:
            try:
                await confirm_msg.delete()
            except:
                pass
    
    @commands.command(name="ehelp", aliases=["economyhelp", "help_economy"])
    async def economy_help(self, ctx):
        """💰 Panduan Economy & Tax System"""
        user_data = await get_user(ctx.author.id)
        is_tax_exempt = user_data and user_data["level"] >= 20
        
        embed = discord.Embed(
            title="💰 Economy & Tax System - Help",
            description="Sistem ekonomi lengkap dengan pajak real-life Indonesia!",
            color=0x2ecc71 if is_tax_exempt else 0xe74c3c
        )
        
        # Basic Economy Commands
        embed.add_field(
            name="💳 Economy Commands",
            value=(
                "`mochi!tradeitem @user <item> <jumlah> <harga>` - Jual item\n"
                "`mochi!profile [@user]` - Lihat saldo & aset\n"
                "`mochi!top` - Leaderboard kaya\n"
                "`mochi!weekly` - [Bangsawan+] Free 2x XP weekly"
            ),
            inline=False
        )
        
        # Tax System
        embed.add_field(
            name="🏛️ Sistem Pajak",
            value=(
                "**📅 Weekly Income Tax**\n"
                "• 5% dari cash (Senin pagi)\n"
                "• Cash di profile saja\n"
                "• Crypto & ikan AMAN\n\n"
                "**💳 Transaction Taxes**\n"
                "• Buy Crypto: 0.1%\n"
                "• Sell Crypto: 0.1%\n"
                "• Sell Fish: 1%\n"
                "• Jade Cut: 2%\n"
                "• Item Trade: 10%"
            ),
            inline=False
        )
        
        # Tax Commands
        embed.add_field(
            name="📋 Tax Commands",
            value=(
                "`mochi!taxinfo` - Info lengkap pajak\n"
                "`mochi!taxhistory` - Riwayat pajak kamu\n"
                "`mochi!taxstats` - Statistik pajak server"
            ),
            inline=False
        )
        
        # User Tax Status
        if is_tax_exempt:
            embed.add_field(
                name="👑 Status Kamu",
                value="✅ **BEBAS SEMUA PAJAK** (Adipati/Raja)\nSemua transaksi tanpa potongan!",
                inline=False
            )
        else:
            level_needed = 20 - user_data["level"] if user_data else 20
            embed.add_field(
                name="⚠️ Status Kamu",
                value=f"**Kena Pajak**\nNaik {level_needed} level lagi untuk bebas pajak!",
                inline=False
            )
        
        # Tips Hemat Pajak
        embed.add_field(
            name="💡 Tips Hemat Pajak",
            value=(
                "🔹 **Invest ke Crypto** - Tidak kena weekly tax!\n"
                "🔹 **Simpan di Ikan** - Inventory aman dari pajak\n"
                "🔹 **Naik Level 20+** - Bebas SEMUA pajak\n"
                "🔹 **Trade Weekend** - Hindari weekly tax Senin\n"
                "🔹 **Hold Assets** - Bukan cash = no weekly tax\n"
                "🔹 **Smart Trading** - Profit lebih besar dari pajak"
            ),
            inline=False
        )
        
        # Asset Protection
        embed.add_field(
            name="🛡️ Aset yang Bebas Weekly Tax",
            value=(
                "✅ **Crypto Portfolio** - BTC, ETH, SOL, dll\n"
                "✅ **Fish Inventory** - Semua ikan tersimpan\n"
                "✅ **XP Items** - 2x, 4x, 8x, 10x, 20x\n"
                "✅ **Gacha Rolls** - Roll tersimpan\n"
                "❌ **Cash** - Kena 5% setiap Senin (kecuali Adipati/Raja)"
            ),
            inline=False
        )
        
        # Economy Tips
        embed.add_field(
            name="📊 Pro Economy Tips",
            value=(
                "💎 Diversifikasi: Jangan simpan semua di cash\n"
                "📈 Trading aktif bisa cover pajak transaksi\n"
                "🎣 Fishing passive income tanpa pajak weekly\n"
                "🏆 Achievement unlock = luck = profit\n"
                "👑 Target Level 20+ untuk maximize profit\n"
                "💰 Monitor `mochi!taxhistory` untuk tracking"
            ),
            inline=False
        )
        
        embed.set_footer(text="Gunakan mochi!taxinfo untuk detail lengkap sistem pajak")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))