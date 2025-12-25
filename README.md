Persiapan Folder: Buat folder baru bernama prizm_bot. Di dalamnya, buat 4 file sesuai nama di atas (requirements.txt, .env, browser_automation.py, main.py) dan tempelkan (copy-paste) kode yang sesuai.

Instalasi Environment: Buka terminal/CMD di dalam folder prizm_bot, lalu jalankan:

Bash
pip install -r requirements.txt
Konfigurasi: Edit file .env, masukkan Token Bot Telegram Anda dan API Key 2Captcha Anda.

Menjalankan Bot: Jalankan perintah:

Bash
python main.py
Penggunaan di Telegram:

Buka bot Anda di Telegram.

Ketik /start untuk melihat menu.

Ketik /vote untuk memulai proses input (Email -> OTP -> 2FA).

Bot akan mengirim screenshot bukti setelah sukses memvoting Hearts2Hearts.
