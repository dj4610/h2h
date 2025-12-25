"""
File: main.py
Deskripsi: Controller Bot Telegram untuk input manual (Email -> OTP -> 2FA) - Hearts2Hearts Voting Bot
"""
import logging
import os
import asyncio
import traceback  # Tambahan untuk logging error detail
from dotenv import load_dotenv
from telegram import Update, ForceReply
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

# Pastikan file browser_automation.py ada di folder yang sama
from browser_automation import PrizmVotingBot 

# Setup Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# State Definitions
EMAIL_STATE, OTP_STATE, TWO_FA_STATE = range(3)

# Menyimpan sesi browser per user ID
user_sessions = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    await update.message.reply_html(
        f"👋 Halo {user.mention_html()}! \n\n"
        "<b>🤖 Prizm Voting Bot - Hearts2Hearts Edition ❤️</b>\n\n"
        "Bot ini membantu login akun dengan OTP & 2FA untuk voting Hearts2Hearts.\n\n"
        "Ketik /vote untuk memulai.\n"
        "Ketik /cancel kapan saja untuk batal."
    )
    return ConversationHandler.END

async def start_voting_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🚀 <b>LANGKAH 1: Masukkan Email</b>\n\n"
        "Kirim alamat email akun voting kamu:",
        parse_mode="HTML",
        reply_markup=ForceReply(selective=True)
    )
    return EMAIL_STATE

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    email = update.message.text.strip()
    
    msg = await update.message.reply_text("⏳ Membuka browser & bypass CAPTCHA (30-60 detik)...")

    loop = asyncio.get_running_loop()
    try:
        bot_instance = PrizmVotingBot()
        user_sessions[user_id] = bot_instance
        
        result = await loop.run_in_executor(None, bot_instance.initiate_login_sequence, email)
        
        if result == "OTP_SENT":
            await msg.edit_text("✅ Bypass CAPTCHA sukses! OTP dikirim ke email.")
            await update.message.reply_text(
                "📩 <b>LANGKAH 2: Masukkan OTP</b>\n\n"
                "Cek email (termasuk spam), kirim kode OTP 6 digit:",
                parse_mode="HTML",
                reply_markup=ForceReply(selective=True)
            )
            return OTP_STATE
        else:
            await msg.edit_text(f"❌ Gagal langkah awal: {result}")
            bot_instance.close_browser()
            del user_sessions[user_id]
            return ConversationHandler.END
    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"Error di initiate_login_sequence: {error_detail}")
        await msg.edit_text(
            "❌ Error sistem (browser automation gagal).\n"
            "Kemungkinan selector di situs berubah atau CAPTCHA sulit.\n"
            "Coba lagi nanti atau hubungi admin."
        )
        if user_id in user_sessions:
            user_sessions[user_id].close_browser()
            del user_sessions[user_id]
        return ConversationHandler.END

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    otp = update.message.text.strip()
    bot_instance = user_sessions.get(user_id)
    
    if not bot_instance:
        await update.message.reply_text("⚠️ Sesi habis. Mulai ulang dengan /vote")
        return ConversationHandler.END

    msg = await update.message.reply_text("⏳ Verifikasi OTP...")

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, bot_instance.submit_otp, otp)
        
        if result == "2FA_REQUIRED":
            await msg.edit_text("✅ OTP benar!")
            await update.message.reply_text(
                "🔐 <b>LANGKAH 3: Masukkan Kode 2FA</b>\n\n"
                "Buka Google Authenticator/Authy, kirim kode 6 digit:",
                parse_mode="HTML",
                reply_markup=ForceReply(selective=True)
            )
            return TWO_FA_STATE
        else:
            await msg.edit_text(f"❌ OTP salah/gagal: {result}")
            bot_instance.close_browser()
            del user_sessions[user_id]
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error di submit_otp: {traceback.format_exc()}")
        await msg.edit_text("❌ Error verifikasi OTP.")
        bot_instance.close_browser()
        del user_sessions[user_id]
        return ConversationHandler.END

async def handle_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    code_2fa = update.message.text.strip()
    bot_instance = user_sessions.get(user_id)
    
    if not bot_instance:
        await update.message.reply_text("⚠️ Sesi habis. Mulai ulang dengan /vote")
        return ConversationHandler.END
    
    msg = await update.message.reply_text("⏳ Login final & voting Hearts2Hearts...")

    loop = asyncio.get_running_loop()
    
    try:
        login_success = await loop.run_in_executor(None, bot_instance.submit_2fa_and_login, code_2fa)
        
        if login_success:
            vote_result = await loop.run_in_executor(None, bot_instance.perform_voting_hearts2hearts)
            
            if vote_result['status']:
                await msg.edit_text("🎉 <b>VOTING SUKSES!</b>\nTerima kasih dukung Hearts2Hearts ❤️", parse_mode="HTML")
                if vote_result.get('screenshot') and os.path.exists(vote_result['screenshot']):
                    await update.message.reply_photo(
                        photo=open(vote_result['screenshot'], 'rb'),
                        caption=f"📸 Bukti voting berhasil!\nWaktu: {vote_result['timestamp']}"
                    )
            else:
                await msg.edit_text(f"✅ Login sukses, tapi voting gagal:\n{vote_result.get('message', 'Unknown error')}")
        else:
            await msg.edit_text("❌ Kode 2FA salah atau login gagal.")
    except Exception as e:
        logger.error(f"Error di 2FA/voting: {traceback.format_exc()}")
        await msg.edit_text("❌ Error saat login final atau voting.")

    # Bersihkan sesi
    bot_instance.close_browser()
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id in user_sessions:
        user_sessions[user_id].close_browser()
        del user_sessions[user_id]
    await update.message.reply_text("🚫 Proses dibatalkan. Ketik /vote untuk mulai lagi.")
    return ConversationHandler.END

def main():
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN tidak ada di .env")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("vote", start_voting_flow)],
        states={
            EMAIL_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
            OTP_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
            TWO_FA_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_2fa)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=600,  # 10 menit
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(conv_handler)

    print("🤖 Bot berjalan... Ctrl+C untuk stop")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
