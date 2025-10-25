import discord
from discord.ext import commands
import traceback

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Global error handler untuk semua command"""
        
        # Ignore command not found
        if isinstance(error, commands.CommandNotFound):
            return
        
        # Missing required argument
        if isinstance(error, commands.MissingRequiredArgument):
            command_name = ctx.command.name
            
            # Custom messages per command
            messages = {
                "cheatxp": (
                    "❓ **Format salah!**\n"
                    "✅ Gunakan: `mochi!cheatxp <jumlah> [@user]`\n"
                    "📌 Contoh: `mochi!cheatxp 100` atau `mochi!cheatxp 500 @user`"
                ),
                "cheatrp": (
                    "❓ **Format salah!**\n"
                    "✅ Gunakan: `mochi!cheatrp <jumlah> [@user]`\n"
                    "📌 Contoh: `mochi!cheatrp 50000` atau `mochi!cheatrp 100000 @user`"
                ),
                "tradeitem": (
                    "❓ **Format salah!**\n"
                    "✅ Gunakan: `mochi!tradeitem @user <item> <jumlah> <harga>`\n"
                    "📌 Contoh: `mochi!tradeitem @teman 2x 1 50000`\n"
                    "🎁 Item: `2x`, `4x`, `8x`, `10x`, `20x`"
                ),
                "use": (
                    "❓ **Format salah!**\n"
                    "✅ Gunakan: `mochi!use <item>`\n"
                    "📌 Contoh: `mochi!use 2x` atau `mochi!use 10x`\n"
                    "🎁 Item: `2x`, `4x`, `8x`, `10x`, `20x`"
                ),
            }
            
            if command_name in messages:
                await ctx.send(messages[command_name])
            else:
                await ctx.send(f"❌ Parameter tidak lengkap! Cek `mochi!help` untuk info lebih lanjut.")
            return
        
        # Bad argument (misal ketik huruf padahal butuh angka)
        if isinstance(error, commands.BadArgument):
            if "int" in str(error):
                await ctx.send(
                    "❌ **Input salah!**\n"
                    "Kamu harus memasukkan **angka**, bukan huruf!\n"
                    f"📌 Ketik `mochi!help` untuk melihat format yang benar."
                )
            elif "Member" in str(error):
                await ctx.send(
                    "❌ **User tidak ditemukan!**\n"
                    "Pastikan kamu mention user dengan benar: `@username`"
                )
            else:
                await ctx.send(f"❌ Parameter tidak valid! Cek `mochi!help` untuk info.")
            return
        
        # User sedang cooldown
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Tunggu **{error.retry_after:.1f} detik** sebelum pakai command ini lagi!")
            return
        
        # Missing permissions
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Kamu tidak punya izin untuk menggunakan command ini!")
            return
        
        # Bot missing permissions
        if isinstance(error, commands.BotMissingPermissions):
            missing = ", ".join(error.missing_permissions)
            await ctx.send(f"❌ Bot tidak punya permission: `{missing}`")
            return
        
        # Command disabled
        if isinstance(error, commands.DisabledCommand):
            await ctx.send("❌ Command ini sedang dinonaktifkan!")
            return
        
        # No private message (command hanya bisa di server)
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ Command ini hanya bisa dipakai di server, bukan DM!")
            return
        
        # Check failure (misal bukan owner)
        if isinstance(error, commands.CheckFailure):
            # Sudah dihandle di masing-masing command
            return
        
        # Unknown error - log ke console
        print(f"❌ ERROR di command {ctx.command}:")
        print(f"User: {ctx.author} ({ctx.author.id})")
        print(f"Channel: {ctx.channel}")
        print(f"Error: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)
        
        # Kirim error ke user
        await ctx.send(
            "❌ **Terjadi error yang tidak terduga!**\n"
            f"Command: `{ctx.command}`\n"
            f"Error: `{str(error)[:100]}`\n\n"
            "Coba lagi atau hubungi admin jika masalah berlanjut."
        )

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))