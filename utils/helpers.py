from utils.config_secrets import OWNER_ID, RANK_ROLE_IDS

def total_xp_needed_for_level(level: int) -> int:
    """Total XP kumulatif yang dibutuhkan untuk mencapai level ini."""
    if level <= 1:
        return 0
    n = level - 1
    return n * (n + 2)

def get_rank_title(level: int) -> str:
    """Kembalikan gelar medival berdasarkan level."""
    if level >= 25:
        return "🌟 Raja"
    elif level >= 20:
        return "👑 Adipati"
    elif level >= 15:
        return "🎩 Bangsawan"
    elif level >= 10:
        return "🏹 Ksatria"
    elif level >= 5:
        return "🛡️ Prajurit"
    else:
        return "🧑‍🌾 Warga"

def get_rank_role_name(level: int) -> str:
    """Kembalikan nama role Discord (tanpa emoji)."""
    if level >= 25:
        return "Raja"
    elif level >= 20:
        return "Adipati"
    elif level >= 15:
        return "Bangsawan"
    elif level >= 10:
        return "Ksatria"
    elif level >= 5:
        return "Prajurit"
    else:
        return "Warga"

def get_gacha_rolls_for_level(level: int) -> int:
    """Hitung berapa gacha rolls yang didapat berdasarkan rank saat naik level."""
    if level >= 15:  # Bangsawan ke atas
        return 2
    elif level >= 10:  # Ksatria
        return 2
    else:
        return 1

def get_luck_gain_for_level(level: int) -> int:
    """Hitung berapa luck yang didapat berdasarkan rank."""
    if level >= 25:  # Raja
        return 10
    elif level >= 20:  # Adipati
        return 5
    elif level >= 15:  # Bangsawan
        return 3
    elif level >= 10:  # Ksatria
        return 2
    elif level >= 5:  # Prajurit
        return 1
    else:  # Warga
        return 1
    
# Achievement Luck Integration
async def get_total_luck(bot, user_id: int):
    """
    Hitung total luck dari:
    1. Base luck dari level (database)
    2. Achievement luck bonus
    
    Returns: (base_luck, achievement_luck, total_luck)
    """
    from database import get_user
    
    # Get base luck
    user_data = await get_user(user_id)
    base_luck = user_data["luck"] if user_data else 0
    
    # Get achievement luck
    achievement_luck = 0
    ach_cog = bot.get_cog('Achievements')
    if ach_cog:
        achievement_luck = await ach_cog.calculate_total_luck_bonus(user_id)
    
    total_luck = base_luck + achievement_luck
    
    return base_luck, achievement_luck, total_luck