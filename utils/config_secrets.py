import os
import json
from pathlib import Path
from dotenv import load_dotenv

print("Loading environment variables...")

# Define the project root directory
ROOT_DIR = Path(__file__).resolve().parent.parent
env_path = ROOT_DIR / '.env'

# Load environment variables from a .env file if it exists
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    print(f"Warning: .env file not found at {env_path}")

# --- DISCORD TOKEN ---
raw_token = os.getenv("TOKEN")
TOKEN = raw_token.strip().strip("'").strip('"') if raw_token else None

# --- OWNER ID ---
# Ganti dengan ID Discord Anda di .env (contoh: OWNER_ID=123456789)
raw_owner_id = os.getenv("OWNER_ID", "0")
try:
    OWNER_ID = int(raw_owner_id)
except ValueError:
    print(f"Warning: Invalid OWNER_ID '{raw_owner_id}'. Using 0.")
    OWNER_ID = 0

# --- CHANNEL ID UNTUK PENGUMUMAN (Quest, Shop, Pajak) ---
raw_quest_channel = os.getenv("QUEST_CHANNEL_ID", "0")
try:
    QUEST_CHANNEL_ID = int(raw_quest_channel)
except ValueError:
    print(f"Warning: Invalid QUEST_CHANNEL_ID '{raw_quest_channel}'. Using 0.")
    QUEST_CHANNEL_ID = 0

# --- ROLE IDS (Dapatkan ID dari mochi!setup di server Anda) ---
# Bisa diatur via .env sebagai JSON string: RANK_ROLE_IDS='{"Warga": 123, ...}'
# Berikan default 0 agar bot tidak error saat pertama kali jalan
DEFAULT_ROLES = {
    "Warga": 0,
    "Prajurit": 0,
    "Ksatria": 0,
    "Bangsawan": 0,
    "Adipati": 0,
    "Raja": 0
}

raw_role_ids = os.getenv("RANK_ROLE_IDS")
if raw_role_ids:
    try:
        raw_role_ids = raw_role_ids.strip("'").strip('"')
        RANK_ROLE_IDS = json.loads(raw_role_ids)
    except Exception as e:
        print(f"Warning: Failed to parse RANK_ROLE_IDS from .env: {e}")
        RANK_ROLE_IDS = DEFAULT_ROLES
else:
    RANK_ROLE_IDS = DEFAULT_ROLES

if not TOKEN:
    print("Warning: TOKEN not found in environment variables. Please ensure it is set in your .env file.")
