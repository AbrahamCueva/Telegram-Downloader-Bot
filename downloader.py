import yt_dlp
import os
import re

def normalize_tiktok_photo(url):
    """
    Convierte links /photo/ de TikTok a formato usable por yt-dlp
    """
    match = re.search(r'/photo/(\d+)', url)
    if match:
        post_id = match.group(1)
        return f"https://www.tiktok.com/@tiktok/video/{post_id}"
    return url

def download(url, quality="best"):
    os.makedirs("media", exist_ok=True)

    # Fix TikTok álbum
    if "tiktok.com" in url and "/photo/" in url:
        url = normalize_tiktok_photo(url)

    downloaded_files = []

    ydl_opts = {
        "outtmpl": "media/%(id)s_%(autonumber)s.%(ext)s",
        "quiet": True,
        "noplaylist": False,
        "skip_download": False,
        "extractor_args": {
            "tiktok": {"webpage_download": True}
        }
    }

    if quality:
        ydl_opts["format"] = (
            "bestvideo+bestaudio/best"
            if quality == "best"
            else "mp4"
        )
        ydl_opts["merge_output_format"] = "mp4"

    def hook(d):
        if d["status"] == "finished":
            downloaded_files.append(d["filename"])

    ydl_opts["progress_hooks"] = [hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    return downloaded_files, info.get("extractor")
