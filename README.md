# ✨ Mochi Bot - Discord Portfolio & Economy Bot

Selamat datang di Mochi Bot! Bot Discord interaktif yang dirancang untuk server komunitas (khususnya yang berfokus pada seni/desain) untuk melacak portofolio anggota, memberikan XP, dan menjalankan sistem ekonomi yang kaya fitur. Bot ini dibangun menggunakan `discord.py`.

## 📜 Deskripsi

Mochi Bot memungkinkan anggota server untuk "mengumpulkan" (`mochi!kumpul`) portofolio mereka di channel yang ditentukan. Pengumpulan ini tidak hanya mencatat aktivitas tetapi juga memberikan XP berdasarkan dukungan (reaksi 🔥) dari anggota lain dalam sistem *real-time* yang unik. Seiring bertambahnya level, pengguna membuka hadiah, rank baru, dan benefit ekonomi.

Bot ini dilengkapi dengan berbagai modul ekonomi termasuk gacha, sistem memancing, trading crypto *real-time*, daily shop, quest harian global, sistem achievement, dan sistem pajak.

## 🚀 Fitur Utama

* **🆙 Sistem Leveling & Portofolio:**
    * `mochi!kumpul`: Memulai sesi pengumpulan XP *real-time* selama 7 hari berdasarkan reaksi 🔥.
    * XP diberikan secara instan saat jumlah reaksi meningkat.
    * Akumulasi XP di-*reset* per jam (setelah jam pertama).
    * Sistem Rank (Warga, Prajurit, ..., Raja) dengan benefit berbeda.
    * Pemberian *role* Discord otomatis berdasarkan rank.
* **💰 Ekonomi & Item:**
    * Mata uang dalam bot (Rupiah/Rp).
    * Item XP Multiplier (2x, 4x, 8x, 10x, 20x) yang didapat dari Gacha atau Shop.
    * `mochi!use <item>`: Mengaktifkan *multiplier* untuk sesi `kumpul` berikutnya.
    * `mochi!weekly`: Klaim bonus 2x XP mingguan untuk rank Bangsawan+.
    * `mochi!tradeitem`: Jual-beli item XP antar pengguna dengan konfirmasi.
    * `mochi!giverp`: Transfer Rupiah antar pengguna.
* **🎰 Gacha:**
    * `mochi!gacha`: Menggunakan *roll* (didapat dari naik level) untuk mendapatkan item XP atau currency.
    * Rate dipengaruhi oleh *Luck* pengguna.
    * `mochi!rate`: Melihat *drop rate* gacha saat ini.
* **🎣 Sistem Memancing:**
    * `mochi!fish`: Memancing ikan (cooldown 1 menit).
    * `mochi!autofish`: Memancing otomatis selama durasi tertentu.
    * `mochi!fmarket`: Pasar ikan dinamis dengan harga yang berubah setiap 15 menit.
    * `mochi!inv`: Melihat inventaris ikan.
    * `mochi!sellfish`: Menjual ikan (kena pajak 25%).
    * `mochi!fishupgrade`: Meningkatkan *equipment* memancing (Rod, Robot, Net).
    * Bonus +150% ikan jika berada di *Voice Channel*.
* **💎 Jade Gacha:**
    * `mochi!jadeshop`: Melihat jenis batu Jade yang bisa dibeli.
    * `mochi!buyjade <tipe>`: Membeli batu Jade (Lumpur, Pasir, Giok, Jade, Imperial).
    * Memotong batu untuk mendapatkan *multiplier* hadiah (atau rugi!).
    * Peluang Jackpot dengan *multiplier* besar.
    * *Luck* pengguna mengurangi peluang rugi.
    * `mochi!jadestats`: Melihat statistik Gacha Jade.
* **📈 Trading Crypto:**
    * `mochi!market`: Melihat harga *real-time* BTC, ETH, BNB, SOL, XRP, GOLD, SILVER dalam IDR (dari CoinGecko).
    * `mochi!buy <crypto> <jumlah_rp>`: Membeli crypto.
    * `mochi!sell <crypto> <jumlah_crypto>`: Menjual crypto.
    * `mochi!portfolio`: Melihat aset crypto, P/L, dan *net worth*.
    * `mochi!chart <crypto> [hari]`: Melihat chart harga sederhana.
    * *(Advanced)* `mochi!history`, `mochi!alert`, `mochi!networth`.
* **🛒 Daily Shop:**
    * `mochi!shop`: Menampilkan item yang dijual hari ini (reset setiap 00:00 WIB).
    * Item acak dengan stok terbatas, termasuk *special deals* (diskon).
    * Menjual XP Boosters, Gacha Rolls, Currency, dan **Luck Boosters permanen**.
    * `mochi!shopbuy <item>`: Membeli item dari shop.
* **🎯 Daily Quest Global:**
    * `mochi!quest`: Melihat quest harian yang sama untuk semua pemain (reset 07:00 WIB).
    * Progress di-*track* otomatis berdasarkan aktivitas (memancing, gacha, dll.).
    * Reward (Currency + Luck Permanen) diberikan otomatis saat selesai.
    * `mochi!queststats`: Melihat statistik penyelesaian quest.
* **🏆 Achievements:**
    * `mochi!achievements`: Melihat daftar *achievement* yang sudah atau belum terbuka.
    * Melacak *milestones* di berbagai sistem (Portfolio, Fishing, Trading, Jade, Quest, Level).
    * Membuka *achievement* memberikan Currency dan **Luck permanen**.
    * Total *Luck* ditampilkan di `mochi!profile`.
* **🏛️ Sistem Pajak:**
    * Pajak Penghasilan Mingguan: 5% dari *cash* (Senin 00:00 WIB), aset (crypto, ikan) aman.
    * Pajak Transaksi: Trading (0.1%), Jual Ikan (1%), Potong Jade (2%), Trade Item (10%).
    * Bebas Pajak: Rank Adipati (Lv. 20+) dan Raja (Lv. 25+) bebas dari semua pajak.
    * `mochi!taxinfo`, `mochi!taxhistory`, `mochi!taxstats` untuk melihat info pajak.
    * `mochi!forcetax` (Owner): Memaksa pengumpulan pajak mingguan (cooldown per minggu kalender).
* **🛠️ Admin & Bantuan:**
    * `mochi!help`: Menampilkan menu bantuan utama.
    * `mochi!help <category>`: Bantuan spesifik per fitur (fish, jade, trade, dll.).
    * Perintah *owner-only* untuk *debugging* dan *testing* (`cheatxp`, `cheatrp`, `forcequestgen`, dll.).
    * *Error Handling* yang informatif.

---

## ⚙️ Instalasi & Setup

1.  **Clone Repositori:**
    ```bash
    git clone [https://github.com/rhebit/mochi-bot.git](https://github.com/rhebit/mochi-bot.git)
    cd mochi-bot
    ```
2.  **Buat Virtual Environment** (Direkomendasikan):
    ```bash
    python -m venv venv
    # Linux/macOS
    source venv/bin/activate
    # Windows
    .\venv\Scripts\activate
    ```
3.  **Install Dependencies:**
    * Pastikan Anda memiliki file `requirements.txt`. Jika belum, buat dengan:
        ```bash
        pip freeze > requirements.txt
        ```
    * Install library yang dibutuhkan:
        ```bash
        pip install -r requirements.txt
        ```
        (Library utama: `discord.py`, `aiosqlite`, `aiohttp`, `pytz`)
4.  **Konfigurasi:**
    * **File Konfigurasi Utama:** `config.py` berisi pengaturan non-sensitif seperti nama channel dan emoji. Anda mungkin perlu menyesuaikannya.
    * **File Rahasia:** Buat file `utils/config_secrets.py` (file ini **TIDAK BOLEH** di-commit ke Git!). Isi file ini dengan:
        ```python
        # utils/config_secrets.py
        
        # TOKEN DISCORD BOT (Dapatkan dari Discord Developer Portal)
        TOKEN = "TOKEN_BOT_ANDA_DISINI"
        
        # OWNER ID (List ID Discord Owner/Tester)
        OWNER_ID = 1234567891236785 # Ganti dengan ID Anda/Tester
        
        # ROLE IDS (Dapatkan ID dari mochi!setup di server Anda)
        RANK_ROLE_IDS = {
            "Warga": 0,
            "Prajurit": 0,
            "Ksatria": 0,
            "Bangsawan": 0,
            "Adipati": 0,
            "Raja": 0
        }
        
        # CHANNEL ID UNTUK PENGUMUMAN (Quest, Shop, Pajak)
        QUEST_CHANNEL_ID = 0 # Ganti dengan ID channel info Anda
        ```
    * **Penting:** Tambahkan `utils/config_secrets.py` ke file `.gitignore` Anda!
        ```
        # .gitignore
        venv/
        __pycache__/
        *.pyc
        mochi.db
        mochi.db-journal
        utils/config_secrets.py
        ```
5.  **Setup Role di Server:**
    * Pastikan Anda sudah membuat *role* Discord dengan nama: `Warga`, `Prajurit`, `Ksatria`, `Bangsawan`, `Adipati`, `Raja`.
    * Jalankan bot, lalu gunakan perintah `mochi!setup` (sebagai *owner*) di server untuk mendapatkan ID *role* tersebut.
    * Salin ID *role* ke `RANK_ROLE_IDS` di `utils/config_secrets.py`.

---

## ▶️ Menjalankan Bot

1.  Aktifkan *virtual environment* Anda (jika menggunakan).
2.  Jalankan file `main.py`:
    ```bash
    python main.py
    ```
3.  Bot akan *online*, menginisialisasi *database* (`mochi.db`), dan memuat semua *cogs*.

---

## 📋 Penggunaan Dasar

* **Prefix Default:** `mochi!`
* **Bantuan Utama:** `mochi!help`
* **Bantuan Spesifik:** `mochi!help <category>` (misal: `mochi!help fish`)
* **Perintah Utama:** `mochi!kumpul` (setelah mengirim portofolio)

---

## 📚 Dependencies Utama

* `discord.py` - Framework utama bot Discord.
* `aiosqlite` - Untuk interaksi database SQLite asinkron.
* `aiohttp` - Untuk permintaan HTTP asinkron (ke CoinGecko API).
* `pytz` - Untuk manajemen *timezone* (WIB).

*(Pastikan `requirements.txt` Anda mencakup semua dependensi ini)*

---

*(Opsional: Tambahkan bagian Contributing atau License jika perlu)*

---

##  Running with Docker

You can easily run Mochi Bot using Docker and Docker Compose. This ensures a consistent environment and easy deployment.

1.  **Install Docker:** Ensure you have Docker and Docker Compose installed on your system.

2.  **Configuration (.env):**
    *   Duplicate the .env.example file and rename it to .env.
    *   Open .env and fill in your Discord Bot Token:
        `env
        TOKEN=your_real_discord_token_here
        `

3.  **Run the Bot:**
    *   Build and start the container in the background:
        `ash
        docker-compose up -d
        `

4.  **Manage the Bot:**
    *   View logs: docker-compose logs -f
    *   Stop the bot: docker-compose down
    *   Restart: docker-compose restart
    *   Rebuild (after code changes): docker-compose up -d --build

**Note on Database Persistence:**
The docker-compose.yml is configured to map a local ./data folder to /app/data inside the container. Your mochi.db database will be stored in this local ./data folder, ensuring your data is safe even if the container is deleted.

