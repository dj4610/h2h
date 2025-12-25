"""
File: main.py
Deskripsi: Controller Bot Telegram untuk Prizm Voting GDA 2025 (Hearts2Hearts)
Kompatibel dengan browser_automation.py berbasis Playwright async
"""
import logging
import os
import asyncio
import traceback
from dotenv import load_dotenv
from telegram import Update, ForceReply
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

from browser_automation import PrizmVotingBot 

# Setup Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# State Definitions
EMAIL_STATE, OTP_STATE, TWO_FA_STATE = range(3)

# Simpan instance bot per user (Playwright context)
user_sessions = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    await update.message.reply_html(
        f"👋 Halo {user.mention_html()}! \n\n"
        "<b>🤖 Prizm GDA Voting Bot - Hearts2Hearts Edition ❤️</b>\n\n"
        "Bot ini membantu vote otomatis untuk Hearts2Hearts di Golden Disc Awards 2025.\n"
        "Voting masih aktif sampai ~5 Januari 2026!\n\n"
        "Ketik /vote untuk mulai (Email → OTP → 2FA).\n"
        "Ketik /cancel kapan saja untuk batal."
    )
    return ConversationHandler.END

async def start_voting_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🚀 <b>LANGKAH 1: Masukkan Email</b>\n\n"
        "Kirim email akun Prizm kamu (yang sudah punya 2FA):",
        parse_mode="HTML",
        reply_markup=ForceReply(selective=True)
    )
    return EMAIL_STATE

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    email = update.message.text.strip()
    
    msg = await update.message.reply_text("⏳ Membuka Prizm & klik Vote Hearts2Hearts (30-90 detik)...\nMohon sabar, bypass reCAPTCHA sedang berjalan.")

    try:
        bot_instance = PrizmVotingBot()
        user_sessions[user_id] = bot_instance
        
        result = await bot_instance.initiate_login_sequence(email)
        
        if result == "OTP_SENT":
            await msg.edit_text("✅ Login modal sukses! OTP telah dikirim ke email kamu.")
            await update.message.reply_text(
                "📩 <b>LANGKAH 2: Masukkan Kode OTP</b>\n\n"
                "Cek email (termasuk spam), kirim kode 6 digit:",
                parse_mode="HTML",
                reply_markup=ForceReply(selective=True)
            )
            return OTP_STATE
        else:
            await msg.edit_text(f"❌ Gagal di langkah awal:\n{result}")
            await bot_instance.close_browser()
            del user_sessions[user_id]
            return ConversationHandler.END
            
    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"Error initiate_login: {error_detail}")
        await msg.edit_text(
            "❌ Error sistem (browser gagal).\n"
            "Kemungkinan: reCAPTCHA sulit, selector berubah, atau koneksi lambat.\n"
            "Coba lagi dalam 5-10 menit."
        )
        if user_id in user_sessions:
            await user_sessions[user_id].close_browser()
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

    try:
        # Kamu harus tambahkan method async submit_otp di browser_automation.py
        result = await bot_instance.submit_otp(otp)
        
        if result == "2FA_REQUIRED":
            await msg.edit_text("✅ OTP benar!")
            await update.message.reply_text(
                "🔐 <b>LANGKAH 3: Kode 2FA (Authenticator)</b>\n\n"
                "Buka Google Authenticator / Authy, kirim kode 6 digit:",
                parse_mode="HTML",
                reply_markup=ForceReply(selective=True)
            )
            return TWO_FA_STATE
        elif result == "LOGIN_SUCCESS":
            await msg.edit_text("✅ Login sukses tanpa 2FA!")
            return await finalize_voting(update, bot_instance, msg)
        else:
            await msg.edit_text(f"❌ OTP salah/gagal: {result}")
            await bot_instance.close_browser()
            del user_sessions[user_id]
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error OTP: {traceback.format_exc()}")
        await msg.edit_text("❌ Error verifikasi OTP.")
        await bot_instance.close_browser()
        del user_sessions[user_id]
        return ConversationHandler.END

async def handle_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    code_2fa = update.message.text.strip()
    bot_instance = user_sessions.get(user_id)
    
    if not bot_instance:
        await update.message.reply_text("⚠️ Sesi habis. Mulai ulang dengan /vote")
        return ConversationHandler.END
    
    msg = await update.message.reply_text("⏳ Submit 2FA & voting Hearts2Hearts...")

    try:
        success = await bot_instance.submit_2fa_and_login(code_2fa)
        if success:
            return await finalize_voting(update, bot_instance, msg)
        else:
            await msg.edit_text("❌ Kode 2FA salah.")
            await bot_instance.close_browser()
            del user_sessions[user_id]
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error 2FA: {traceback.format_exc()}")
        await msg.edit_text("❌ Error saat 2FA atau voting.")
        await bot_instance.close_browser()
        del user_sessions[user_id]
        return ConversationHandler.END

async def finalize_voting(update: Update, bot_instance: PrizmVotingBot, msg):
    try:
        vote_result = await bot_instance.perform_voting_hearts2hearts()
        
        if vote_result['status']:
            await msg.edit_text("🎉 <b>VOTING SUKSES!</b>\nHearts2Hearts tetap leading ~50%+ ❤️\nTerima kasih telah voting!", parse_mode="HTML")
            if vote_result.get('screenshot'):
                await update.message.reply_photo(
                    open(vote_result['screenshot'], 'rb'),
                    caption=f"📸 Bukti vote GDA\nWaktu: {vote_result['timestamp']}\n{vote_result.get('message', '')}"
                )
        else:
            await msg.edit_text(f"⚠️ Login sukses tapi vote gagal:\n{vote_result.get('message')}")
    except Exception as e:
        logger.error(f"Error finalize voting: {traceback.format_exc()}")
        await msg.edit_text("❌ Error saat voting final.")
    finally:
        await bot_instance.close_browser()
        del user_sessions[update.effective_user.id]
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id in user_sessions:
        await user_sessions[user_id].close_browser()
        del user_sessions[user_id]
    await update.message.reply_text("🚫 Proses voting dibatalkan. Ketik /vote untuk mulai lagi.")
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
        conversation_timeout=900,  # 15 menit
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(conv_handler)

    print("🤖 Prizm GDA Voting Bot (Hearts2Hearts) berjalan...")
    print("Voting aktif sampai ~5 Jan 2026. H2H leading solid!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
