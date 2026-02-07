from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import os
from config import TOKEN
from downloader import download
from database import init_db, save_download, get_user_stats

init_db()

# ---------- COMANDOS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    stats = get_user_stats(user.id)
    
    welcome_text = (
        f"👋 ¡Hola {user.first_name}!\n\n"
        "📥 *Descargador Multimedia Bot*\n\n"
        "🎵 *TikTok*\n"
        "   • Videos sin marca de agua\n"
        "   • Álbumes de fotos completos\n"
        "   • Fotos animadas\n\n"
        "📸 *Instagram*\n"
        "   • Posts y álbumes\n"
        "   • Reels en HD\n"
        "   • Sin marca de agua\n\n"
        "▶️ *YouTube*\n"
        "   • Videos en alta calidad\n"
        "   • Shorts\n"
        "   • Múltiples calidades\n\n"
        f"📊 Has descargado *{stats}* archivos\n\n"
        "💡 *Envíame un link para empezar*"
    )
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    total = get_user_stats(user.id)
    
    await update.message.reply_text(
        f"📊 *Tus Estadísticas*\n\n"
        f"Total de descargas: *{total}*\n"
        f"Usuario: @{user.username or 'Sin username'}\n\n"
        "¡Gracias por usar el bot! 🎉",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "❓ *Ayuda - Cómo usar el bot*\n\n"
        "*Plataformas soportadas:*\n"
        "• TikTok (videos y álbumes)\n"
        "• Instagram (posts y reels)\n"
        "• YouTube (videos y shorts)\n\n"
        "*Comandos disponibles:*\n"
        "/start - Iniciar el bot\n"
        "/stats - Ver tus estadísticas\n"
        "/help - Ver esta ayuda\n\n"
        "*¿Cómo funciona?*\n"
        "1️⃣ Copia el link del video/foto\n"
        "2️⃣ Envíamelo por aquí\n"
        "3️⃣ Elige la calidad (si es video)\n"
        "4️⃣ ¡Descarga lista!\n\n"
        "✨ Todo sin marcas de agua"
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ---------- MANEJO DE LINKS ----------

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    # Validar URL
    supported_domains = ["tiktok.com", "instagram.com", "youtube.com", "youtu.be"]
    if not any(domain in url for domain in supported_domains):
        await update.message.reply_text(
            "❌ *URL no soportada*\n\n"
            "Plataformas válidas:\n"
            "• TikTok\n"
            "• Instagram\n"
            "• YouTube\n\n"
            "Envía /help para más información",
            parse_mode="Markdown"
        )
        return
    
    context.user_data["url"] = url

    # 🟣 TikTok álbum (photo/slideshow)
    if "tiktok.com" in url and "/photo/" in url:
        msg = await update.message.reply_text(
            "📸 *Álbum de TikTok detectado*\n\n"
            "⏳ Descargando imágenes...\n"
            "Esto puede tardar unos segundos",
            parse_mode="Markdown"
        )
        context.user_data["status_msg"] = msg
        await process_album(update, context)
        return
    
    # 🟠 Instagram posts/álbumes
    if "instagram.com" in url and ("/p/" in url or "/reel/" in url):
        msg = await update.message.reply_text(
            "📸 *Instagram detectado*\n\n"
            "⏳ Procesando contenido...",
            parse_mode="Markdown"
        )
        context.user_data["status_msg"] = msg
        await process_instagram(update, context)
        return

    # 🟢 Videos (TikTok video / YouTube)
    keyboard = [
        [
            InlineKeyboardButton("🎥 Alta Calidad (HD)", callback_data="best"),
            InlineKeyboardButton("📱 Calidad Media", callback_data="medium")
        ],
        [
            InlineKeyboardButton("❌ Cancelar", callback_data="cancel")
        ]
    ]

    await update.message.reply_text(
        "🎬 *Elige la calidad del video:*\n\n"
        "🎥 *Alta:* Mejor calidad, archivo más pesado\n"
        "📱 *Media:* Buena calidad, archivo ligero",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ---------- DESCARGA DE VIDEOS ----------

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.message.edit_text("❌ Descarga cancelada")
        return

    url = context.user_data.get("url")
    quality = query.data

    status_msg = await query.message.edit_text(
        "⏳ *Descargando video...*\n\n"
        "Por favor espera, esto puede tardar un momento",
        parse_mode="Markdown"
    )

    try:
        # QUITADO el await - download() NO es async
        files, platform = await download(url, quality)

        if not files:
            await status_msg.edit_text("❌ No se pudo descargar el contenido")
            return

        await status_msg.edit_text("📤 *Enviando archivo(s)...*", parse_mode="Markdown")

        # Enviar archivo(s)
        for idx, file in enumerate(files):
            try:
                if file.endswith((".mp4", ".webm", ".mov")):
                    with open(file, "rb") as video:
                        caption = f"✅ Descargado de *{platform}*" if idx == 0 else None
                        await query.message.reply_video(
                            video=video,
                            caption=caption,
                            parse_mode="Markdown",
                            supports_streaming=True
                        )
                elif file.endswith((".jpg", ".jpeg", ".png", ".webp")):
                    with open(file, "rb") as photo:
                        await query.message.reply_photo(photo=photo)
                
                # Limpiar archivo
                if os.path.exists(file):
                    os.remove(file)
            except Exception as e:
                print(f"Error enviando archivo {file}: {e}")
                continue

        # Eliminar mensaje de estado
        await status_msg.delete()

        # Guardar estadísticas
        user = query.from_user
        save_download(user.id, user.username or "Sin username", url, platform, "video")
        
        # Mostrar stats
        stats = get_user_stats(user.id)
        await query.message.reply_text(
            f"✅ *Descarga completada*\n\n"
            f"📊 Total de descargas: *{stats}*",
            parse_mode="Markdown"
        )

    except Exception as e:
        await status_msg.edit_text(
            f"❌ *Error al descargar*\n\n"
            f"Intenta con otro link o contacta al administrador\n\n"
            f"Error: `{str(e)}`",
            parse_mode="Markdown"
        )
        print(f"Error en download_video: {e}")


# ---------- DESCARGA DE ÁLBUMES ----------

async def process_album(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = context.user_data.get("url")
    status_msg = context.user_data.get("status_msg")

    try:
        # QUITADO el await - download() NO es async
        files, platform = await download(url, quality=None)

        if not files:
            await status_msg.edit_text("❌ No se encontraron imágenes en el álbum")
            return

        # Filtrar solo imágenes
        image_files = [f for f in files if f.endswith((".jpg", ".jpeg", ".png", ".webp"))]
        
        if not image_files:
            await status_msg.edit_text("❌ No se encontraron imágenes válidas")
            return

        await status_msg.edit_text(
            f"📤 *Enviando {len(image_files)} imágenes...*",
            parse_mode="Markdown"
        )

        # Enviar en grupos de 10 (límite de Telegram)
        for i in range(0, len(image_files), 10):
            batch = image_files[i:i+10]
            media_group = []
            
            for img in batch:
                with open(img, "rb") as photo:
                    media_group.append(InputMediaPhoto(media=photo.read()))

            await update.message.reply_media_group(media_group)
        
        # Eliminar mensaje de estado
        await status_msg.delete()
        
        # Mensaje final
        user = update.message.from_user
        save_download(user.id, user.username or "Sin username", url, platform, "album")
        
        stats = get_user_stats(user.id)
        await update.message.reply_text(
            f"✅ *Álbum descargado*\n\n"
            f"📸 {len(image_files)} imágenes de *{platform}*\n"
            f"📊 Total de descargas: *{stats}*",
            parse_mode="Markdown"
        )

        # Limpiar archivos
        for f in files:
            if os.path.exists(f):
                os.remove(f)

    except Exception as e:
        await status_msg.edit_text(
            f"❌ *Error al descargar álbum*\n\n"
            f"Error: `{str(e)}`",
            parse_mode="Markdown"
        )
        print(f"Error en process_album: {e}")


# ---------- DESCARGA INSTAGRAM ----------

async def process_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = context.user_data.get("url")
    status_msg = context.user_data.get("status_msg")

    try:
        # QUITADO el await - download() NO es async
        files, platform = await download(url, quality="best")

        if not files:
            await status_msg.edit_text("❌ No se pudo descargar el contenido")
            return

        # Separar videos e imágenes
        videos = [f for f in files if f.endswith((".mp4", ".webm", ".mov"))]
        images = [f for f in files if f.endswith((".jpg", ".jpeg", ".png", ".webp"))]

        await status_msg.edit_text("📤 *Enviando contenido...*", parse_mode="Markdown")

        # Enviar videos
        for video in videos:
            with open(video, "rb") as vid:
                await update.message.reply_video(
                    video=vid,
                    caption=f"✅ De *{platform}*",
                    parse_mode="Markdown",
                    supports_streaming=True
                )
        
        # Enviar imágenes como media group
        if images:
            for i in range(0, len(images), 10):
                batch = images[i:i+10]
                media_group = []
                
                for img in batch:
                    with open(img, "rb") as photo:
                        media_group.append(InputMediaPhoto(media=photo.read()))
                
                await update.message.reply_media_group(media_group)
        
        # Eliminar mensaje de estado
        await status_msg.delete()
        
        # Guardar stats
        user = update.message.from_user
        content_type = "video" if videos else "images"
        save_download(user.id, user.username or "Sin username", url, platform, content_type)
        
        stats = get_user_stats(user.id)
        await update.message.reply_text(
            f"✅ *Descarga completada*\n\n"
            f"📊 Total de descargas: *{stats}*",
            parse_mode="Markdown"
        )

        # Limpiar archivos
        for f in files:
            if os.path.exists(f):
                os.remove(f)

    except Exception as e:
        await status_msg.edit_text(
            f"❌ *Error al descargar*\n\n"
            f"Error: `{str(e)}`",
            parse_mode="Markdown"
        )
        print(f"Error en process_instagram: {e}")


# ---------- APP ----------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(download_video))

    print("🤖 Bot iniciado correctamente")
    print("📥 Esperando mensajes...")
    
    app.run_polling()


if __name__ == "__main__":
    main()