# utils/embeds.py
import discord
from utils.helpers import get_rank_title, total_xp_needed_for_level

def create_profile_embed(user: discord.Member, user_data: dict) -> discord.Embed:
    """Buat embed profil user"""
    current_xp = user_data["xp"]
    current_level = user_data["level"]
    xp_for_next = total_xp_needed_for_level(current_level + 1)
    xp_to_next = xp_for_next - current_xp
    currency = user_data["currency"]
    rolls = user_data["gacha_rolls"]
    mult = user_data["next_xp_mult"]

    # Warna berdasarkan level
    color = 0xffb6c1
    if current_level >= 10:
        color = 0xffd700  # emas
    elif current_level >= 5:
        color = 0x9370db  # ungu

    embed = discord.Embed(
        title=f"📊 Profil {user.display_name}",
        color=color
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    # Bagian Utama
    embed.add_field(
        name="🏅 Level & XP",
        value=f"**Level**: `{current_level}`\n"
              f"**XP**: `{current_xp} / {xp_for_next}`\n"
              f"**Butuh**: `{xp_to_next} XP` untuk naik level",
        inline=False
    )
    embed.add_field(
        name="💰 Currency",
        value=f"Rp {currency:,}",
        inline=False
    )

    # Inventory Gacha
    embed.add_field(
        name="🎁 Inventory",
        value=(
            f"• **Rolls**: `{rolls}`\n"
            f"• **2x XP**: `{user_data['xp_2x']}`\n"
            f"• **4x XP**: `{user_data['xp_4x']}`\n"
            f"• **8x XP**: `{user_data['xp_8x']}`\n"
            f"• **10x XP**: `{user_data['xp_10x']}`\n"
            f"• **20x XP**: `{user_data['xp_20x']}`"
        ),
        inline=False
    )

    # Status Aktif
    status = "Tidak ada"
    if mult > 1.0:
        status = f"`{mult}x XP` aktif untuk portofolio berikutnya!"
    embed.add_field(
        name="🚀 Status Aktif",
        value=status,
        inline=False
    )

    # Rank Medival
    rank_title = get_rank_title(current_level)
    embed.add_field(name="Rank", value=rank_title, inline=False)

    embed.set_footer(text="Mochi Bot • Naikkan levelmu dengan portofolio!")
    return embed

def create_help_embed(porto_mention: str, is_owner: bool = False) -> discord.Embed:
    """Buat embed help"""
    embed = discord.Embed(
        title="✨ Bantuan Mochi Bot",
        description="Sistem portofolio interaktif dengan XP, level, currency, gacha, dan trading!",
        color=0xffb6c1
    )
    
    embed.add_field(
        name="📤 mochi!kumpul",
        value=f"Kumpulkan XP dari portofoliomu di {porto_mention}.\n"
              "Setelah kirim portofolio, ketik perintah ini → minta dukungan via reaksi 🔥.",
        inline=False
    )
    embed.add_field(
        name="👤 mochi!profile [@user]",
        value="Lihat profil XP, level, currency, gacha rolls, dan item-mu.",
        inline=False
    )
    embed.add_field(
        name="🏅 mochi!rank",
        value="Lihat daftar rank, syarat level, dan benefitnya.",
        inline=False
    )
    embed.add_field(
        name="🏆 mochi!top",
        value="Lihat leaderboard 10 besar berdasarkan level & currency.",
        inline=False
    )
    embed.add_field(
        name="🍀 Luck",
        value="Luck untuk meningkatkan rate saat gacha!",
        inline=False
    )
    embed.add_field(
        name="🎰 mochi!gacha",
        value="Buka 1 roll gacha (butuh roll dari naik level).",
        inline=False
    )
    embed.add_field(
        name="📊 mochi!rate",
        value="Lihat persentase peluang mendapatkan hadiah di gacha.",
        inline=False
    )
    embed.add_field(
        name="✨ mochi!use <2x/4x/8x/10x/20x>",
        value="Gunakan item XP multiplier.",
        inline=False
    )
    embed.add_field(
        name="🎁 mochi!weekly",
        value="[Bangsawan+] Claim 1x 2x XP gratis setiap minggu!",
        inline=False
    )
    embed.add_field(
        name="💱 mochi!tradeitem @user <item> <jumlah> <harga>",
        value="Jual item ke teman! Contoh:\n`mochi!tradeitem @teman 2x 1 50000`",
        inline=False
    )

    if is_owner:
        embed.add_field(
            name="🛠️ Owner Only",
            value="`mochi!setup` - Lihat Role IDs\n"
                  "`mochi!cheatxp <jumlah> [@user]`\n"
                  "`mochi!cheatrp <jumlah> [@user]`",
            inline=False
        )

    embed.set_footer(text="Mochi Bot • Ketik mochi!help kapan saja untuk bantuan")
    return embed