import discord
from discord.ext import commands, tasks
import asyncio
import aiosqlite
from datetime import datetime, timedelta
import pytz # Import pytz untuk manajemen timezone

# Import semua utility, termasuk yang BARU dari database dan config
from config import (
    ALLOWED_PORTO_CHANNELS, MAIN_PORTO_CHANNEL_NAME, FIRE_EMOJI, 
    CANCEL_EMOJI, CONFIRM_EMOJI, DENY_EMOJI, KUMPUL_COOLDOWN_DAYS, 
    KUMPUL_DURATION_DAYS, KUMPUL_XP_PER_FIRE
)
from database import (
    get_user, create_user, update_user, 
    get_kumpul_tracking, update_kumpul_tracking, insert_kumpul_tracking, get_active_kumpul_messages 
)
from utils.helpers import (
    total_xp_needed_for_level, get_rank_title, get_rank_role_name,
    get_gacha_rolls_for_level, get_luck_gain_for_level, RANK_ROLE_IDS, OWNER_ID 
)
from utils.embeds import create_profile_embed

# Define time zone (contoh: WIB)
MY_TIMEZONE = pytz.timezone('Asia/Jakarta') 

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Start the background task
        # PERBAIKAN: Pastikan loop berjalan setiap menit
        if not self.kumpul_processor.is_running():
            self.kumpul_processor.change_interval(minutes=1) # Set interval ke 1 menit
            self.kumpul_processor.start()

    def cog_unload(self):
        self.kumpul_processor.cancel()
        
    # --- LOGIC LAMA: CHECK LEVEL UP dan APPLY RANK ROLE (Dipertahankan) ---
    async def check_level_up(self, user_id: int, current_xp: int, current_level: int):
        # ... (logic check_level_up tetap sama)
        level = current_level
        while current_xp >= total_xp_needed_for_level(level + 1):
            level += 1

        if level > current_level:
            levels_gained = level - current_level
            total_reward = sum(50000 * (current_level + i) for i in range(1, levels_gained + 1))
            total_rolls = 0
            for i in range(levels_gained):
                new_lvl = current_level + i + 1
                total_rolls += get_gacha_rolls_for_level(new_lvl)
            luck_per_level = get_luck_gain_for_level(level)
            total_luck_gain = luck_per_level * levels_gained

            await update_user(
                user_id, level=level, currency=total_reward, gacha_rolls=total_rolls, luck=total_luck_gain
            )
            ach_cog = self.bot.get_cog('Achievements')
            if ach_cog:
                await ach_cog.check_achievement_progress(user_id, "level", level)
            return level, total_reward, total_rolls
        return None, None, None

    async def apply_rank_role(self, ctx, member, new_level):
        # ... (logic apply_rank_role tetap sama)
        new_rank_name = get_rank_role_name(new_level)
        new_rank_id = RANK_ROLE_IDS.get(new_rank_name, 0)
        # ... (logic hapus/tambah role)
        pass # Placeholder untuk menyingkat

    # --- COMMAND BARU: KUMPUL (REAL-TIME TRIGGER) ---
    @commands.command(name="kumpul")
    async def kumpul(self, ctx):
        """Mulai sesi pengumpulan XP Real-Time selama 7 hari."""
        
        # 1. Pengecekan Channel & Pesan Portofolio
        if ctx.channel.name.lower() not in [name.lower() for name in ALLOWED_PORTO_CHANNELS]:
            main_channel = discord.utils.get(ctx.guild.channels, name=MAIN_PORTO_CHANNEL_NAME)
            await ctx.send(
                f"❌ Perintah ini hanya bisa dipakai di channel <#{main_channel.id}>" if main_channel 
                else f"❌ Perintah ini hanya bisa dipakai di channel `#{MAIN_PORTO_CHANNEL_NAME}`", 
                delete_after=5
            )
            return

        async for msg in ctx.channel.history(limit=5):
            if msg.author == ctx.author and not msg.content.startswith("mochi!"):
                break
        else:
            await ctx.send("❌ Kirim portofoliomu dulu, lalu ketik `mochi!kumpul`!", delete_after=10)
            return

        # 2. Ambil Data Pengguna (PERBAIKAN: Pindahkan ke atas)
        user_data = await get_user(ctx.author.id)
        if not user_data:
            await create_user(ctx.author.id)
            user_data = await get_user(ctx.author.id)
            
        now_utc = datetime.utcnow()

        # 3. Pengecekan Cooldown 7 Hari (Sekarang aman diakses)
        last_kumpul_str = user_data.get("last_kumpul_time")
        if last_kumpul_str:
            last_kumpul_time = datetime.fromisoformat(last_kumpul_str)
            cooldown_end = last_kumpul_time + timedelta(days=KUMPUL_COOLDOWN_DAYS)
            
            if now_utc < cooldown_end:
                time_left = cooldown_end - now_utc
                days = time_left.days
                hours = time_left.seconds // 3600
                await ctx.send(f"⏰ Kamu baru bisa `mochi!kumpul` lagi dalam **{days} hari {hours} jam**.")
                return

        # 4. Pengecekan Sesi Aktif (Mencegah duplikasi)
        active_sessions = await get_active_kumpul_messages() 
        active_session_data = next((s for s in active_sessions if s['user_id'] == ctx.author.id), None)

        if active_session_data:
            await ctx.send("⚠️ Kamu sudah punya sesi pengumpulan XP yang aktif! Selesaikan dulu sebelum memulai yang baru.")
            return

        # 5. Memulai Sesi Kumpul Baru
        end_time_utc = now_utc + timedelta(days=KUMPUL_DURATION_DAYS)

        embed = discord.Embed(
            title="🔥 Pengumpulan XP Real-Time Dimulai!",
            description=(
                f"**Sesi** oleh {ctx.author.mention} dimulai.\n"
                f"XP akan dikreditkan secara **Real-Time** saat reaksi **{FIRE_EMOJI}** bertambah.\n"
                f"**Durasi**: Sesi berlangsung **{KUMPUL_DURATION_DAYS} hari**.\n"
                f"**Reset Akumulasi**: Reaksi dihitung per menit (jam pertama) dan per jam (setelahnya)."
            ),
            color=0xff4500
        )
        
        kumpul_message = await ctx.send(embed=embed)
        await kumpul_message.add_reaction(FIRE_EMOJI) 
        await kumpul_message.add_reaction(CANCEL_EMOJI)

        # 6. Simpan data sesi baru ke database
        await insert_kumpul_tracking(
            kumpul_message.id,
            ctx.author.id,
            ctx.channel.id,
            now_utc.isoformat(),
            end_time_utc.isoformat(),
            0, # max_reactions awal
            now_utc.isoformat() # last_xp_check_time awal
        )
        
        # 7. Update Cooldown Timer Pengguna (KUNCI untuk mencegah spam setelah cancel)
        await update_user(ctx.author.id, last_kumpul_time=now_utc.isoformat())

    # --- LISTENER: UPDATE MAX REACTIONS & BERIKAN XP REAL-TIME ---
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        kumpul_data = await get_kumpul_tracking(payload.message_id)
        if not kumpul_data or kumpul_data['status'] != 'active': 
            return
            
        # --- LOGIC OWNER CANCELLATION (PERBAIKAN FOKUS DI SINI) ---
        allowed_owners = OWNER_ID if isinstance(OWNER_ID, list) else [OWNER_ID]
        
        if str(payload.emoji) == CANCEL_EMOJI and payload.user_id in allowed_owners:
            channel = self.bot.get_channel(payload.channel_id)
            if not channel: return
            
            try:
                message = await channel.fetch_message(payload.message_id)
            except discord.NotFound:
                return
            
            # PERBAIKAN: Panggil handler cancellation
            await self.handle_owner_cancellation(message, kumpul_data, payload.user_id) 
            return # Keluar setelah memanggil handler

        # --- XP Tracking dan Pemberian XP ---
        if str(payload.emoji) == FIRE_EMOJI:
            # ... (logic pemberian XP real-time tetap sama seperti yang Anda berikan)
            channel = self.bot.get_channel(payload.channel_id)
            if not channel: return
            
            try:
                message = await channel.fetch_message(payload.message_id)
            except discord.NotFound:
                return

            fire_count = 0
            for reaction in message.reactions:
                if str(reaction.emoji) == FIRE_EMOJI:
                    users = [user async for user in reaction.users() if user.id != self.bot.user.id]
                    fire_count = len(users)
                    break
            
            previous_max = kumpul_data['max_reactions']
            
            if fire_count > previous_max:
                new_max = fire_count
                xp_increase = (new_max - previous_max) * KUMPUL_XP_PER_FIRE
                
                user_id = kumpul_data['user_id']
                user = self.bot.get_user(user_id)
                user_data = await get_user(user_id)
                
                if not user_data: return

                xp_multiplier = user_data.get('next_xp_mult', 1.0)
                final_xp = int(xp_increase * xp_multiplier)
                
                await update_user(user_id, xp=final_xp) 
                await self.check_level_up(user_id, user_data['xp'] + final_xp, user_data['level'])
                await update_kumpul_tracking(payload.message_id, max_reactions=new_max)
                
                if channel:
                     await channel.send(
                        f"🎉 {user.mention} mendapatkan **{final_xp:,} XP**! (Reaksi naik menjadi {new_max} 🔥)", 
                        delete_after=10
                     )


    # --- BACKGROUND TASK: PROSES RESET AKUMULASI XP PER JAM/PERIODE END ---
    # PERBAIKAN: Ubah interval loop ke menit
    @tasks.loop(minutes=1) # <<< PASTIKAN INI minutes=1, BUKAN hours=1
    async def kumpul_processor(self):
        await self.bot.wait_until_ready()
        
        active_kumpul = await get_active_kumpul_messages()
        now_utc = datetime.utcnow()
        
        for kumpul_data in active_kumpul:
            if kumpul_data['status'] != 'active':
                continue
            
            start_time = datetime.fromisoformat(kumpul_data['start_time'])
            end_time = datetime.fromisoformat(kumpul_data['end_time'])
            
            # 1. LOGIKA SESI BERAKHIR (Setelah 7 hari)
            if now_utc >= end_time:
                # ... (logic sesi berakhir dan konsumsi item tetap sama)
                pass # Placeholder
                continue
            
            # 2. LOGIKA RESET AKUMULASI (Tetap sama)
            is_boost_hour = (now_utc - start_time) < timedelta(hours=1)
            last_check_time = datetime.fromisoformat(kumpul_data['last_xp_check_time'])
            
            if is_boost_hour:
                if now_utc >= (last_check_time + timedelta(minutes=1)):
                    await update_kumpul_tracking(kumpul_data['message_id'], last_xp_check_time=now_utc.isoformat())
            else:
                if now_utc >= (last_check_time + timedelta(hours=1)):
                    await update_kumpul_tracking(
                        kumpul_data['message_id'], 
                        max_reactions=0, 
                        last_xp_check_time=now_utc.isoformat()
                    )
                    channel = self.bot.get_channel(kumpul_data['channel_id'])
                    if channel:
                        await channel.send("🔔 Akumulasi XP (reaksi) di-reset per jam...", delete_after=60)
            
    # --- OWNER CANCELLATION HANDLER (Definisi Lengkap) ---
    async def handle_owner_cancellation(self, message, kumpul_data, reacting_owner_id: int): 
        """Proses pembatalan XP oleh owner dengan double verifikasi."""
        
        owner = self.bot.get_user(reacting_owner_id) 
        if not owner: 
             await message.channel.send("❌ Gagal menemukan user Owner. Pembatalan dibatalkan.")
             await update_kumpul_tracking(kumpul_data['message_id'], status='active')
             return
        
        kumpul_user = self.bot.get_user(kumpul_data['user_id'])
        if not kumpul_user: # Safety check
            await update_kumpul_tracking(kumpul_data['message_id'], status='canceled')
            return 
            
        await update_kumpul_tracking(kumpul_data['message_id'], status='calculating') 

        embed = discord.Embed(
            title="🚨 VERIFIKASI PEMBATALAN XP KUMPUL",
            description=(
                f"**User**: {kumpul_user.mention} (`{kumpul_user.id}`)\n"
                f"**Pesan**: [Link Pesan]({message.jump_url})\n"
                f"**Reaksi Saat Ini**: {kumpul_data['max_reactions']} {FIRE_EMOJI}\n\n"
                f"Owner `{owner.name}` bereaksi {CANCEL_EMOJI}. Batalkan sesi XP ini?\n"
                f"{CONFIRM_EMOJI} **YA, Batalkan** | {DENY_EMOJI} **TIDAK, Lanjutkan**."
            ),
            color=0xe74c3c
        )
        
        try:
            dm_message = await owner.send(embed=embed)
        except discord.Forbidden: # Handle jika DM ditutup
            await message.channel.send(f"❌ Gagal mengirim DM verifikasi ke Owner {owner.mention}. Pembatalan dibatalkan.")
            await update_kumpul_tracking(kumpul_data['message_id'], status='active')
            return

        await dm_message.add_reaction(CONFIRM_EMOJI)
        await dm_message.add_reaction(DENY_EMOJI)

        def check(reaction, user):
            # Cek hanya berlaku untuk Owner yang menerima DM dan reaksi yang valid
            return user.id == reacting_owner_id and str(reaction.emoji) in [CONFIRM_EMOJI, DENY_EMOJI] and reaction.message.id == dm_message.id

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=600.0, check=check)
            
            if str(reaction.emoji) == CONFIRM_EMOJI:
                await update_kumpul_tracking(kumpul_data['message_id'], status='canceled')
                await message.channel.send(f"✅ **Pembatalan Kumpul XP** untuk {kumpul_user.mention} dikonfirmasi oleh Owner.")
                await dm_message.edit(embed=discord.Embed(title="✅ PEMBATALAN DIKONFIRMASI", description=f"XP kumpul oleh {kumpul_user.mention} dibatalkan.", color=0x2ecc71))
            
            elif str(reaction.emoji) == DENY_EMOJI:
                await update_kumpul_tracking(kumpul_data['message_id'], status='active') 
                await message.channel.send(f"🚫 **Pembatalan Kumpul XP** untuk {kumpul_user.mention} ditolak oleh Owner. Proses kumpul dilanjutkan.")
                await dm_message.edit(embed=discord.Embed(title="🚫 PEMBATALAN DITOLAK", description=f"XP kumpul oleh {kumpul_user.mention} dilanjutkan.", color=0xf1c40f))

        except asyncio.TimeoutError:
            await update_kumpul_tracking(kumpul_data['message_id'], status='active') 
            await message.channel.send(f"⏰ Konfirmasi pembatalan XP kumpul untuk {kumpul_user.mention} **timeout**. Proses kumpul dilanjutkan.")
            await dm_message.edit(embed=discord.Embed(title="⏰ TIMEOUT", description="Konfirmasi pembatalan timeout.", color=0xf39c12))

    @kumpul_processor.before_loop
    async def before_kumpul_processor(self):
        await self.bot.wait_until_ready()


    # --- LOGIC LAMA: PROFILE, TOP, RANK ---
    @commands.command(name="profile")
    async def profile(self, ctx, member: discord.Member = None):
        # ... (logic lama profile)
        user = member or ctx.author
        user_data = await get_user(user.id)

        if not user_data:
            await ctx.send(f"{user.mention} belum pernah mengumpulkan portofolio!")
            return

        # Get portfolio count
        async with aiosqlite.connect("mochi.db") as db:
            cursor = await db.execute("""
                SELECT portfolio_count FROM portfolio_tracking WHERE user_id = ?
            """, (user.id,))
            row = await cursor.fetchone()
            portfolio_count = row[0] if row else 0
        
        # Get achievement luck bonus
        ach_cog = self.bot.get_cog('Achievements')
        achievement_luck = 0
        if ach_cog:
            achievement_luck = await ach_cog.calculate_total_luck_bonus(user.id)
        
        # Create custom profile embed dengan achievements
        embed = create_profile_embed(user, user_data)
        
        # Add portfolio tracking dengan tier
        if portfolio_count <= 5:
            tier = "🥉 Bronze"
        elif portfolio_count <= 10:
            tier = "🥈 Silver"
        elif portfolio_count <= 25:
            tier = "🥇 Gold"
        elif portfolio_count <= 50:
            tier = "💎 Platinum"
        elif portfolio_count <= 100:
            tier = "💠 Diamond"
        else:
            tier = "👑 Master"
        
        embed.add_field(
            name="📚 Portfolio Activity",
            value=f"**Count**: {portfolio_count}\n**Tier**: {tier}",
            inline=False
        )
        
        # Add achievement info
        if ach_cog:
            achievements = await ach_cog.get_user_achievements(user.id)
            total_achievements = len(ach_cog.achievements)
            unlocked_count = len(achievements)
            
            embed.add_field(
                name="🏆 Achievements",
                value=(
                    f"**Unlocked**: {unlocked_count}/{total_achievements}\n"
                    f"**Achievement Luck**: 🍀 +{achievement_luck}\n"
                    f"**Total Luck**: 🍀 {user_data['luck'] + achievement_luck}"
                ),
                inline=False
            )
        
        # Update footer
        embed.set_footer(text="mochi!achievements untuk detail • mochi!quests untuk quest aktif")
        
        await ctx.send(embed=embed)


    @commands.command(name="top")
    async def leaderboard(self, ctx):
        # ... (logic lama leaderboard)
        async with aiosqlite.connect("mochi.db") as db:
            cursor = await db.execute("""
                SELECT user_id, level, currency
                FROM users
                ORDER BY level DESC, currency DESC
                LIMIT 10
            """)
            rows = await cursor.fetchall()

        if not rows:
            await ctx.send("Belum ada data leaderboard!")
            return

        embed = discord.Embed(
            title="🏆 Leaderboard Mochi",
            description="Top 10 berdasarkan Level & Currency",
            color=0xffd700
        )

        leaderboard_text = ""
        for i, (user_id, level, currency) in enumerate(rows, start=1):
            user = self.bot.get_user(user_id)
            username = user.display_name if user else f"[User {user_id}]"
            leaderboard_text += f"`{i}.` **{username}** — Level {level} | Rp {currency:,}\n"

        embed.description = leaderboard_text
        embed.set_footer(text="Naikkan levelmu dengan kirim portofolio!")
        await ctx.send(embed=embed)

    @commands.command(name="rank")
    async def rank_info(self, ctx):
        # ... (logic lama rank_info)
        user_data = await get_user(ctx.author.id)
        current_level = user_data["level"] if user_data else 1
        current_rank = get_rank_title(current_level)

        embed = discord.Embed(
            title="🏅 Sistem Rank Mochi",
            description=f"**Rank-mu saat ini**: {current_rank}",
            color=0xffd700
        )

        rank_info_text = (
            "🧑‍🌾 **Warga** (Level 1–4)\n"
            "└─ Benefit: +1 Luck/level, +1 roll gacha/level\n\n"
            
            "🛡️ **Prajurit** (Level 5–9)\n"
            "└─ Benefit: +1 Luck/level, +1 roll gacha/level\n\n"
            
            "🏹 **Ksatria** (Level 10–14)\n"
            "└─ Benefit: +2 Luck/level, +2 roll gacha/level\n\n"
            
            "🎩 **Bangsawan** (Level 15–19)\n"
            "└─ Benefit: +3 Luck/level, +2 roll gacha/level, 1x free 2x XP/minggu\n\n"
            
            "👑 **Adipati** (Level 20–24)\n"
            "└─ Benefit: +5 Luck/level, +2 roll gacha/level, bebas pajak trading\n\n"
            
            "🌟 **Raja** (Level 25+)\n"
            "└─ Benefit: +10 Luck/level, +2 roll gacha/level, akses semua benefit"
        )

        embed.add_field(name="📜 Daftar Rank", value=rank_info_text, inline=False)
        embed.set_footer(text="Naikkan levelmu untuk naik rank!")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Leveling(bot))