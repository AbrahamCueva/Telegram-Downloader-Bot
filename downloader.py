import yt_dlp

def download(url, quality="best"):
    ydl_opts = {
        "outtmpl": "video.%(ext)s",
        "format": "bestvideo+bestaudio/best" if quality == "best" else "mp4",
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "extractor_args": {
            "tiktok": {"webpage_download": True}
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename, info.get("extractor")
