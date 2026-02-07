import yt_dlp
import os
import glob
import asyncio
from TikTokApi import TikTokApi
from playwright.async_api import async_playwright
import requests
import re

# Variable global para TikTok API
tiktok_api = None

async def init_tiktok_api():
    """Inicializa la API de TikTok con manejo de errores"""
    global tiktok_api
    if tiktok_api is None:
        try:
            tiktok_api = TikTokApi()
            await tiktok_api.create_sessions(num_sessions=1, sleep_after=3, headless=True)
        except Exception as e:
            print(f"Error al inicializar TikTokApi: {e}")
            return None
    return tiktok_api

async def download_tiktok_album_api(url):
    """
    Descarga álbumes de TikTok usando TikTokApi oficial corrigiendo el error de URL
    """
    try:
        # Extraer ID del post para nombres de archivo
        match = re.search(r'/photo/(\d+)', url)
        post_id = match.group(1) if match else "tiktok_post"
        
        api = await init_tiktok_api()
        if not api:
            return await download_tiktok_album_fallback(url)
        
        # CORRECCIÓN: Usar url=url en lugar de id=post_id para evitar el error de video.info()
        video = api.video(url=url)
        video_data = await video.info()
        
        downloaded_files = []
        os.makedirs("media", exist_ok=True)
        
        # Estructura de datos de TikTok para álbumes (imagePost)
        if 'imagePost' in video_data and 'images' in video_data['imagePost']:
            images = video_data['imagePost']['images']
            
            for idx, img in enumerate(images):
                # Obtener la URL (usualmente la última de la lista es mejor calidad)
                img_url = img['imageURL']['urlList'][-1]
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.tiktok.com/'
                }
                
                response = requests.get(img_url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    filename = f"media/tiktok_album_{post_id}_{idx}.jpg"
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    downloaded_files.append(filename)
        
        # Si no se bajó nada, intentar fallback
        if not downloaded_files:
            return await download_tiktok_album_fallback(url)
            
        return downloaded_files, "TikTok"
    
    except Exception as e:
        print(f"Error con TikTokApi ({e}), intentando método alternativo...")
        return await download_tiktok_album_fallback(url)

async def download_tiktok_album_fallback(url):
    """
    Método alternativo usando Playwright para scraping directo (más lento pero seguro)
    """
    try:
        match = re.search(r'/photo/(\d+)', url)
        post_id = match.group(1) if match else "fb"
        downloaded_files = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000) # Esperar renderizado
            
            # Selector mejorado para imágenes de álbum
            img_urls = await page.evaluate("""
                () => {
                    const images = Array.from(document.querySelectorAll('img'));
                    return images
                        .map(img => img.src)
                        .filter(src => src.includes('photomode') || (src.includes('tos-alisg') && !src.includes('avatar')));
                }
            """)
            
            await browser.close()
            
            os.makedirs("media", exist_ok=True)
            headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.tiktok.com/'}
            
            # Limitar a 20 imágenes para evitar spam y asegurar unicidad
            unique_urls = list(set(img_urls))
            for idx, img_url in enumerate(unique_urls[:20]):
                try:
                    res = requests.get(img_url, headers=headers, timeout=10)
                    if res.status_code == 200 and len(res.content) > 10000: # Ignorar iconos pequeños
                        fn = f"media/tiktok_fb_{post_id}_{idx}.jpg"
                        with open(fn, 'wb') as f:
                            f.write(res.content)
                        downloaded_files.append(fn)
                except:
                    continue
        
        return downloaded_files, "TikTok"
    except Exception as e:
        print(f"Error en método fallback: {e}")
        return [], "TikTok"

def download_sync(url, quality="best"):
    """Versión síncrona para yt-dlp (Instagram/YouTube/TikTok Video)"""
    os.makedirs("media", exist_ok=True)
    downloaded_files = []
    platform = ""
    
    ydl_opts = {
        "outtmpl": "media/%(id)s_%(autonumber)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
    }
    
    if "tiktok.com" in url:
        platform = "TikTok"
        ydl_opts["format"] = "best"
    elif "instagram.com" in url:
        platform = "Instagram"
        ydl_opts["format"] = "best"
    elif "youtube.com" in url or "youtu.be" in url:
        platform = "YouTube"
        if quality == "best":
            ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        else:
            ydl_opts["format"] = "worst[ext=mp4]/worst"
        ydl_opts["merge_output_format"] = "mp4"

    def progress_hook(d):
        if d["status"] == "finished":
            file = d.get("filename")
            if file and file not in downloaded_files:
                downloaded_files.append(file)
    
    ydl_opts["progress_hooks"] = [progress_hook]
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not downloaded_files:
                # Caso especial: algunos archivos cambian de nombre al finalizar
                pattern = f"media/{info.get('id', '*')}*"
                downloaded_files = glob.glob(pattern)
            if not platform:
                platform = info.get("extractor_key", "Video")
    except Exception as e:
        print(f"Error en yt-dlp: {e}")
        return [], "Error"
    
    return downloaded_files, platform

async def download(url, quality="best"):
    """Función principal de entrada"""
    # Detectar si es álbum de fotos de TikTok
    if "tiktok.com" in url and "/photo/" in url:
        return await download_tiktok_album_api(url)
    
    # Para todo lo demás usar yt-dlp en un hilo separado
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, download_sync, url, quality)