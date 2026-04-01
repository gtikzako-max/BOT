import sqlite3
import os

DB_PATH = "game.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT UNIQUE NOT NULL,
            nickname TEXT UNIQUE NOT NULL,
            kingdom TEXT,
            coins INTEGER DEFAULT 0,
            hp INTEGER DEFAULT 200,
            status TEXT DEFAULT 'pending',
            step TEXT DEFAULT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_player(sender):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE sender = ?", (sender,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def nickname_exists(nickname):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM players WHERE LOWER(nickname) = LOWER(?)", (nickname,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def create_player(sender, nickname):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO players (sender, nickname, status, step) VALUES (?, ?, 'pending', 'awaiting_kingdom')",
        (sender, nickname)
    )
    conn.commit()
    conn.close()

def update_player(sender, **kwargs):
    conn = get_connection()
    c = conn.cursor()
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [sender]
    c.execute(f"UPDATE players SET {fields} WHERE sender = ?", values)
    conn.commit()
    conn.close()

def delete_player(sender):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM players WHERE sender = ?", (sender,))
    conn.commit()
    conn.close()
