import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect("history.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            url TEXT,
            platform TEXT,
            content_type TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_downloads INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()

def save_download(user_id, username, url, platform, content_type="video"):
    conn = sqlite3.connect("history.db")
    c = conn.cursor()
    
    # Guardar descarga
    c.execute(
        "INSERT INTO downloads (user_id, username, url, platform, content_type) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, url, platform, content_type)
    )
    
    # Actualizar estadísticas del usuario
    c.execute(
        "INSERT OR REPLACE INTO users (user_id, username, last_seen, total_downloads) "
        "VALUES (?, ?, ?, COALESCE((SELECT total_downloads FROM users WHERE user_id = ?) + 1, 1))",
        (user_id, username, datetime.now(), user_id)
    )
    
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = sqlite3.connect("history.db")
    c = conn.cursor()
    
    c.execute("SELECT total_downloads FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    conn.close()
    
    return result[0] if result else 0