from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import os
from config import TOKEN
from downloader import download
from database import init_db, save_download

init_db()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 Envíame un link de TikTok, Instagram o Shorts"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    context.user_data["url"] = url

    keyboard = [
        [
            InlineKeyboardButton("🎥 Alta", callback_data="best"),
            InlineKeyboardButton("📱 Media", callback_data="medium")
        ]
    ]

    await update.message.reply_text(
        "Elige la calidad:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = context.user_data.get("url")
    quality = query.data

    msg = await query.message.edit_text("Descargando… ⏳")

    try:
        file, platform = download(url, quality)
        await query.message.reply_video(video=open(file, "rb"))
        save_download(query.from_user.id, url, platform)
        os.remove(file)

    except Exception as e:
        await query.message.reply_text("❌ Error al descargar")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(download_video))

app.run_polling()
