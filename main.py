# main.py - UPDATED WITH TAX SYSTEM
import discord
from discord.ext import commands
import asyncio

from database import init_db, migrate_jade_stats
from utils.config_secrets import TOKEN

# Setup bot
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="mochi!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    # Initialize database with auto migration
    await init_db()
    print("✅ Database initialized!")
    
    # Auto migration for jade stats
    await migrate_jade_stats()
    print("✅ Jade stats migration complete!")
    
    print(f"✅ {bot.user} sudah online!")
    print("🚀 Mochi siap mengumpulkan portfolio!")
    
    # Load all cogs
    cogs_to_load = [
        'cogs.leveling',
        'cogs.gacha',
        'cogs.economy',
        'cogs.inventory',
        'cogs.admin',
        'cogs.error_handler',
        'cogs.trading',
        'cogs.fishing',
        'cogs.jade',
        'cogs.achievements',
        'cogs.quests',
        'cogs.tax',
        'cogs.shop'    # NEW TAX SYSTEM!
    ]
    
    for cog in cogs_to_load:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded: {cog}")
        except Exception as e:
            print(f"❌ Failed to load {cog}: {e}")
    
    print("📦 Semua cogs berhasil dimuat!")
    print("="*50)
    
# Jalankan bot
if __name__ == "__main__":
    bot.run(TOKEN)