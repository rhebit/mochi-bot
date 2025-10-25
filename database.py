# database.py
import aiosqlite
from datetime import datetime, timedelta

async def init_db():
    """Initialize all database tables"""
    async with aiosqlite.connect("mochi.db") as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                currency INTEGER DEFAULT 0,
                gacha_rolls INTEGER DEFAULT 0,
                xp_2x INTEGER DEFAULT 0,
                xp_4x INTEGER DEFAULT 0,
                xp_8x INTEGER DEFAULT 0,
                xp_10x INTEGER DEFAULT 0,
                xp_20x INTEGER DEFAULT 0,
                next_xp_mult REAL DEFAULT 1.0,
                luck INTEGER DEFAULT 0,
                last_weekly_claim TEXT DEFAULT NULL,
                last_kumpul_time TEXT DEFAULT NULL
            )
        """)

        # Jade Gacha Stats table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jade_stats (
                user_id INTEGER PRIMARY KEY,
                total_spent INTEGER DEFAULT 0,
                total_won INTEGER DEFAULT 0,
                total_cuts INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                total_jackpots INTEGER DEFAULT 0,
                last_cut_time TEXT
            )
        """)
        
        # Fishing Stats table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS fishing_stats (
                user_id INTEGER PRIMARY KEY,
                total_fish_caught INTEGER DEFAULT 0,
                last_fish_time TIMESTAMP,
                last_daily_claim TIMESTAMP
            )
        """)
        
        # Fishing Inventory table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS fishing_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                fish_name TEXT NOT NULL,
                amount INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, fish_name)
            )
        """)
        
        # Fishing Upgrades table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS fishing_upgrades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                upgrade_type TEXT NOT NULL,
                level INTEGER DEFAULT 0,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, upgrade_type)
            )
        """)
        
        # Crypto Portfolio table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS crypto_portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                crypto_symbol TEXT NOT NULL,
                amount REAL NOT NULL,
                avg_buy_price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, crypto_symbol)
            )
        """)

        # Kumpul Tracking table (BARU)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS kumpul_tracking (
                message_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                max_reactions INTEGER DEFAULT 0, -- Reaksi tertinggi yang pernah tercatat
                status TEXT DEFAULT 'active',
                last_xp_check_time TEXT DEFAULT NULL
            )
        """)

        # ====== TABEL TAX HISTORY BARU ======
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tax_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tax_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better performance
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_fishing_inventory_user 
            ON fishing_inventory(user_id)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_fishing_upgrades_user 
            ON fishing_upgrades(user_id)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_crypto 
            ON crypto_portfolio(user_id, crypto_symbol)
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS tax_system_stats (
                id INTEGER PRIMARY KEY DEFAULT 1,
                last_forced_tax TEXT DEFAULT NULL
            )
        """)
        
        # Memastikan selalu ada satu row untuk diupdate
        await db.execute("INSERT OR IGNORE INTO tax_system_stats (id) VALUES (1)")
        
        await db.commit()
        print("✅ All database tables created/verified!")

async def migrate_jade_stats():
    """Migrate jade_stats table to add new columns if they don't exist"""
    async with aiosqlite.connect("mochi.db") as db:
        try:
            # Check existing columns
            cursor = await db.execute("PRAGMA table_info(jade_stats)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            print(f"📊 Checking jade_stats columns: {column_names}")
            
            # Add missing columns
            columns_added = []
            
            if 'total_wins' not in column_names:
                await db.execute("ALTER TABLE jade_stats ADD COLUMN total_wins INTEGER DEFAULT 0")
                columns_added.append("total_wins")
            
            if 'total_losses' not in column_names:
                await db.execute("ALTER TABLE jade_stats ADD COLUMN total_losses INTEGER DEFAULT 0")
                columns_added.append("total_losses")
            
            if 'total_jackpots' not in column_names:
                await db.execute("ALTER TABLE jade_stats ADD COLUMN total_jackpots INTEGER DEFAULT 0")
                columns_added.append("total_jackpots")
            
            await db.commit()
            
            if columns_added:
                print(f"✅ Added jade_stats columns: {', '.join(columns_added)}")
            else:
                print("✅ Jade stats table already up to date!")
            
        except Exception as e:
            print(f"❌ Migration error: {e}")

async def get_user(user_id: int):
    async with aiosqlite.connect("mochi.db") as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def create_user(user_id: int):
    async with aiosqlite.connect("mochi.db") as db:
        await db.execute(
            "INSERT INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        await db.commit()

async def update_user(user_id: int, **kwargs):
    """
    Update user data dengan SMART LOGIC:
    
    SET (Replace nilai):
    - level, next_xp_mult, last_weekly_claim
    
    INCREMENT (Tambah dengan nilai lama):
    - xp, currency, luck, gacha_rolls, xp_2x, xp_4x, xp_8x, xp_10x, xp_20x
    
    DECREMENT (Kurangi dari nilai lama - untuk inventory yang dipakai):
    - Ditandai dengan key yang diawali "set_" (misal: set_gacha_rolls, set_xp_2x)
    
    Contoh:
    await update_user(user_id, xp=100)  -> xp += 100
    await update_user(user_id, level=5)  -> level = 5
    await update_user(user_id, gacha_rolls=5)  -> gacha_rolls += 5
    await update_user(user_id, set_gacha_rolls=3)  -> gacha_rolls = 3 (force set)
    """
    if not kwargs:
        return
    
    # Ambil data lama
    user_data = await get_user(user_id)
    if not user_data:
        await create_user(user_id)
        user_data = await get_user(user_id)
    
    # Field yang di-SET (replace, tidak ditambah)
    set_fields = ["level", "next_xp_mult", "last_weekly_claim"]
    
    # Field yang di-INCREMENT (tambah dengan nilai lama)
    increment_fields = ["xp", "currency", "luck", "gacha_rolls", "xp_2x", "xp_4x", "xp_8x", "xp_10x", "xp_20x"]
    
    # Process kwargs untuk handle set_ prefix
    processed_kwargs = {}
    values = []
    
    for key, value in kwargs.items():
        # Handle force set dengan prefix "set_"
        if key.startswith("set_"):
            actual_key = key[4:]  # Remove "set_" prefix
            processed_kwargs[actual_key] = value
            values.append(value)
        elif key in set_fields:
            processed_kwargs[key] = value
            values.append(value)
        elif key in increment_fields:
            processed_kwargs[key] = value
            values.append(user_data[key] + value)
        else:
            # Default: SET
            processed_kwargs[key] = value
            values.append(value)
    
    # Build query
    set_clause = ", ".join([f"{key} = ?" for key in processed_kwargs.keys()])
    values.append(user_id)
    
    async with aiosqlite.connect("mochi.db") as db:
        await db.execute(
            f"UPDATE users SET {set_clause} WHERE user_id = ?",
            values
        )
        await db.commit()
async def get_kumpul_tracking(message_id: int):
    """Ambil data tracking kumpul berdasarkan ID pesan."""
    async with aiosqlite.connect("mochi.db") as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM kumpul_tracking WHERE message_id = ?", (message_id,))
        return await cursor.fetchone()

async def update_kumpul_tracking(message_id: int, **kwargs):
    """Update status atau reaksi dari pesan kumpul."""
    updates = []
    values = []
    
    for key, value in kwargs.items():
        updates.append(f"{key} = ?")
        values.append(value)
        
    if not updates: return
        
    query = f"UPDATE kumpul_tracking SET {', '.join(updates)} WHERE message_id = ?"
    values.append(message_id)
    
    async with aiosqlite.connect("mochi.db") as db:
        await db.execute(query, tuple(values))
        await db.commit()

# PERBAIKAN: Tambahkan last_xp_check_time ke parameter
# database.py
async def insert_kumpul_tracking(message_id: int, user_id: int, channel_id: int, start_time: str, end_time: str, max_reactions: int, last_xp_check_time: str):
    """Masukkan pesan kumpul baru."""
    async with aiosqlite.connect("mochi.db") as db:
        await db.execute("""
            INSERT INTO kumpul_tracking 
            (message_id, user_id, channel_id, start_time, end_time, max_reactions, last_xp_check_time) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (message_id, user_id, channel_id, start_time, end_time, max_reactions, last_xp_check_time))
        await db.commit()
        
async def get_active_kumpul_messages():
    """Ambil semua pesan kumpul yang masih aktif."""
    async with aiosqlite.connect("mochi.db") as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM kumpul_tracking WHERE status = 'active' OR status = 'calculating'")
        return await cursor.fetchall()
    
async def get_tax_system_state():
    """Get the global tax system state."""
    async with aiosqlite.connect("mochi.db") as db:
        db.row_factory = aiosqlite.Row
        await db.execute("INSERT OR IGNORE INTO tax_system_stats (id) VALUES (1)")
        cursor = await db.execute("SELECT * FROM tax_system_stats WHERE id = 1")
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_tax_system_state(last_forced_tax: str = None):
    """Update the global tax system state."""
    async with aiosqlite.connect("mochi.db") as db:
        await db.execute("INSERT OR IGNORE INTO tax_system_stats (id) VALUES (1)")
        
        set_parts = []
        params = []
        
        if last_forced_tax:
            set_parts.append("last_forced_tax = ?")
            params.append(last_forced_tax)
            
        if set_parts:
            query = f"UPDATE tax_system_stats SET {', '.join(set_parts)} WHERE id = 1"
            await db.execute(query, params)
            await db.commit()
            return True
        return False
# ============================================
# HELPER FUNCTIONS (OPTIONAL)
# ============================================

async def verify_all_tables():
    """Verify all database tables structure"""
    async with aiosqlite.connect("mochi.db") as db:
        tables = ["users", "jade_stats", "fishing_stats", "fishing_inventory", "fishing_upgrades", "crypto_portfolio"]
        
        print("\n" + "="*60)
        print("📊 DATABASE STRUCTURE VERIFICATION")
        print("="*60)
        
        for table_name in tables:
            cursor = await db.execute(f"PRAGMA table_info({table_name})")
            columns = await cursor.fetchall()
            
            if columns:
                print(f"\n✅ Table: {table_name}")
                print("-" * 60)
                for col in columns:
                    print(f"  • {col[1]:25} | {col[2]:10} | Default: {col[4]}")
                
                # Count rows
                cursor = await db.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = await cursor.fetchone()
                print(f"  📈 Total records: {count[0]}")
            else:
                print(f"\n❌ Table: {table_name} - NOT FOUND")
        
        print("\n" + "="*60)


async def backup_database():
    """Backup database to JSON"""
    import json
    from datetime import datetime
    
    backup_data = {}
    
    async with aiosqlite.connect("mochi.db") as db:
        db.row_factory = aiosqlite.Row
        
        tables = ["users", "jade_stats", "fishing_stats", "fishing_inventory", "fishing_upgrades", "crypto_portfolio"]
        
        for table in tables:
            try:
                cursor = await db.execute(f"SELECT * FROM {table}")
                rows = await cursor.fetchall()
                backup_data[table] = [dict(row) for row in rows]
            except Exception as e:
                print(f"⚠️ Error backing up {table}: {e}")
                backup_data[table] = []
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mochi_backup_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Backup saved to: {filename}")
    
    # Calculate total records
    total_records = sum(len(data) for data in backup_data.values())
    print(f"📊 Total records backed up: {total_records}")
    
    return filename


async def reset_table(table_name: str):
    """Reset specific table (BE CAREFUL!)"""
    async with aiosqlite.connect("mochi.db") as db:
        response = input(f"⚠️ Are you sure you want to DELETE all data from '{table_name}'? (yes/no): ")
        if response.lower() == 'yes':
            await db.execute(f"DELETE FROM {table_name}")
            await db.commit()
            print(f"✅ Table '{table_name}' has been cleared!")
        else:
            print("❌ Operation cancelled.")


# ============================================
# STANDALONE SCRIPTS
# ============================================

if __name__ == "__main__":
    """
    Run this file directly for database maintenance:
    python database.py
    """
    import asyncio
    import sys
    
    async def main_menu():
        print("\n" + "="*60)
        print("🗄️  MOCHI DATABASE MAINTENANCE")
        print("="*60)
        print("1. Verify all tables")
        print("2. Backup database")
        print("3. Migrate jade_stats (add new columns)")
        print("4. Initialize/Reset database")
        print("5. Exit")
        print("="*60)
        
        choice = input("\nSelect option (1-5): ")
        
        if choice == "1":
            await verify_all_tables()
        elif choice == "2":
            await backup_database()
        elif choice == "3":
            await migrate_jade_stats()
        elif choice == "4":
            confirm = input("⚠️ This will recreate all tables. Continue? (yes/no): ")
            if confirm.lower() == "yes":
                await init_db()
            else:
                print("❌ Cancelled")
        elif choice == "5":
            print("👋 Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid option!")
        
        # Loop back to menu
        await main_menu()
    
    asyncio.run(main_menu())