"""
File: main.py
Deskripsi: Controller Bot Telegram untuk input manual (Email -> OTP -> 2FA)
"""
import logging
import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, ForceReply
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)
# Import modul worker yang kita buat di browser_automation.py
from browser_automation import PrizmVotingBot 

# Setup Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# State Definitions
EMAIL_STATE, OTP_STATE, TWO_FA_STATE = range(3)
user_sessions = {} # Menyimpan sesi browser per user ID

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    await update.message.reply_html(
        f"👋 Halo {user.mention_html()}! \n\n"
        "<b>🤖 Prizm Voting Bot - Hearts2Hearts Edition</b>\n"
        "Sistem ini membantu login akun dengan 2FA untuk voting.\n\n"
        "Ketik /vote untuk memulai proses login & voting.\n"
        "Ketik /cancel untuk membatalkan kapan saja."
    )
    return ConversationHandler.END

async def start_voting_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🚀 <b>LANGKAH 1: Login Email</b>\n"
        "Silakan masukkan alamat email akun Prizm Anda:",
        parse_mode="HTML",
        reply_markup=ForceReply(selective=True)
    )
    return EMAIL_STATE

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    email = update.message.text.strip()
    
    msg = await update.message.reply_text("⏳ Membuka browser & bypass CAPTCHA (Estimasi: 30-60 detik)...")

    # Inisialisasi Browser di thread terpisah (agar bot tidak freeze)
    loop = asyncio.get_running_loop()
    try:
        bot_instance = PrizmVotingBot()
        user_sessions[user_id] = bot_instance
        
        result = await loop.run_in_executor(None, bot_instance.initiate_login_sequence, email)
        
        if result == "OTP_SENT":
            await msg.edit_text("✅ CAPTCHA Sukses. OTP terkirim ke email.")
            await update.message.reply_text(
                "📩 <b>LANGKAH 2: Verifikasi OTP</b>\n"
                "Cek email Anda, masukkan kode OTP di sini:",
                parse_mode="HTML",
                reply_markup=ForceReply(selective=True)
            )
            return OTP_STATE
        else:
            await msg.edit_text(f"❌ Gagal: {result}")
            bot_instance.close_browser()
            return ConversationHandler.END
    except Exception as e:
        await msg.edit_text(f"❌ Error Sistem: {e}")
        return ConversationHandler.END

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    otp = update.message.text.strip()
    bot_instance = user_sessions.get(user_id)
    
    if not bot_instance:
        await update.message.reply_text("⚠️ Sesi habis. Ulangi /vote")
        return ConversationHandler.END

    msg = await update.message.reply_text("⏳ Memverifikasi OTP...")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, bot_instance.submit_otp, otp)
    
    if result == "2FA_REQUIRED":
        await msg.edit_text("✅ OTP Valid.")
        await update.message.reply_text(
            "🔐 <b>LANGKAH 3: Google Authenticator (2FA)</b>\n"
            "Buka aplikasi Authenticator Anda, masukkan kode 6 digit:",
            parse_mode="HTML",
            reply_markup=ForceReply(selective=True)
        )
        return TWO_FA_STATE
    else:
        await msg.edit_text(f"❌ Gagal OTP: {result}")
        bot_instance.close_browser()
        return ConversationHandler.END

async def handle_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    code_2fa = update.message.text.strip()
    bot_instance = user_sessions.get(user_id)
    
    msg = await update.message.reply_text("⏳ Login final & Voting Hearts2Hearts...")
    loop = asyncio.get_running_loop()
    
    # Login Final
    login_success = await loop.run_in_executor(None, bot_instance.submit_2fa_and_login, code_2fa)
    
    if login_success:
        # Eksekusi Vote
        vote_result = await loop.run_in_executor(None, bot_instance.perform_voting_hearts2hearts)
        if vote_result['status']:
            await msg.edit_text("🎉 <b>VOTING SUKSES!</b>", parse_mode="HTML")
            if vote_result.get('screenshot'):
                await update.message.reply_photo(
                    vote_result['screenshot'], 
                    caption=f"Bukti Vote Hearts2Hearts\nWaktu: {vote_result['timestamp']}"
                )
        else:
            await msg.edit_text(f"⚠️ Login Sukses, tapi Vote Gagal: {vote_result['message']}")
    else:
        await msg.edit_text("❌ Login 2FA Gagal.")

    # Bersihkan sesi
    bot_instance.close_browser()
    del user_sessions[user_id]
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id in user_sessions:
        user_sessions[user_id].close_browser()
        del user_sessions[user_id]
    await update.message.reply_text("🚫 Operasi dibatalkan.")
    return ConversationHandler.END

def main():
    # Inisialisasi Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Conversation Handler untuk alur Login
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("vote", start_voting_flow)],
        states={
            EMAIL_STATE:,
            OTP_STATE:,
            TWO_FA_STATE:,
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(conv_handler)

    print("Bot Telegram Berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
