from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import os
from config import TOKEN
from downloader import download
from database import init_db, save_download

init_db()

# ---------- COMANDOS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 Envíame un link de TikTok, Instagram o YouTube\n"
        "Soporto videos y álbumes 📸🎬"
    )

# ---------- MANEJO DE LINKS ----------

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data["url"] = url

    # 🟣 TikTok álbum (photo)
    if "tiktok.com" in url and "/photo/" in url:
        await update.message.reply_text("📸 Álbum detectado, descargando… ⏳")
        await process_album(update, context)
        return

    # 🟢 Videos (TikTok / IG / YouTube)
    keyboard = [
        [
            InlineKeyboardButton("🎥 Alta", callback_data="best"),
            InlineKeyboardButton("📱 Media", callback_data="medium")
        ]
    ]

    await update.message.reply_text(
        "Elige la calidad del video:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- DESCARGA DE VIDEOS ----------

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = context.user_data.get("url")
    quality = query.data

    await query.message.edit_text("Descargando… ⏳")

    try:
        files, platform = download(url, quality)

        if not files:
            await query.message.reply_text("❌ No se encontró contenido")
            return

        # Un solo archivo
        if len(files) == 1:
            file = files[0]

            if file.endswith((".mp4", ".webm", ".mov")):
                await query.message.reply_video(video=open(file, "rb"))
            else:
                await query.message.reply_photo(photo=open(file, "rb"))

        # Varios archivos (álbum / carrusel)
        else:
            media_group = []

            for f in files[:10]:  # límite Telegram
                if f.endswith((".jpg", ".jpeg", ".png", ".webp")):
                    media_group.append(InputMediaPhoto(open(f, "rb")))
                elif f.endswith(".mp4"):
                    media_group.append(InputMediaVideo(open(f, "rb")))

            if media_group:
                await query.message.reply_media_group(media_group)

        save_download(query.from_user.id, url, platform)

        for f in files:
            os.remove(f)

    except Exception as e:
        await query.message.reply_text("❌ Error al descargar el video")

# ---------- DESCARGA DE ÁLBUMES ----------

async def process_album(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = context.user_data.get("url")

    try:
        files, platform = download(url, quality=None)

        if not files:
            await update.message.reply_text("❌ No se encontraron imágenes")
            return

        media_group = []

        for f in files[:10]:
            media_group.append(InputMediaPhoto(open(f, "rb")))

        await update.message.reply_media_group(media_group)

        save_download(update.message.from_user.id, url, platform)

        for f in files:
            os.remove(f)

    except Exception as e:
        await update.message.reply_text("❌ Error al descargar el álbum")

# ---------- APP ----------

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(download_video))

app.run_polling()
