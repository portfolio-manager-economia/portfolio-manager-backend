"""Capa de persistencia de datos (SQLite local / Supabase)."""

from datetime import date
from typing import Dict, List, Optional
import os
import sqlite3
import uuid

DB_PATH = os.path.join(os.path.dirname(__file__), "portfolio.db")


def init_db():
    """Inicializa la base de datos SQLite para persistencia local de posiciones."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                user_id TEXT DEFAULT 'default_user',
                ticker TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                buy_price REAL NOT NULL,
                buy_date TEXT NOT NULL
            )
        """)
        conn.commit()


def save_position(
    ticker: str,
    asset_type: str,
    quantity: float,
    buy_price: float,
    buy_date: date,
    user_id: str = "default_user",
) -> Dict:
    """Guarda una nueva posición en la base de datos."""
    init_db()
    pos_id = str(uuid.uuid4())
    date_str = buy_date.isoformat() if hasattr(buy_date, "isoformat") else str(buy_date)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO positions (id, user_id, ticker, asset_type, quantity, buy_price, buy_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (pos_id, user_id, ticker.upper(), asset_type, quantity, buy_price, date_str))
        conn.commit()

    return {
        "id": pos_id,
        "user_id": user_id,
        "ticker": ticker.upper(),
        "asset_type": asset_type,
        "quantity": quantity,
        "buy_price": buy_price,
        "buy_date": buy_date,
    }


def list_positions(user_id: str = "default_user") -> List[Dict]:
    """Recupera todas las posiciones activas de un usuario."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM positions WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()

    return [
        {
            "id": row["id"],
            "ticker": row["ticker"],
            "asset_type": row["asset_type"],
            "quantity": float(row["quantity"]),
            "buy_price": float(row["buy_price"]),
            "buy_date": row["buy_date"],
        }
        for row in rows
    ]


def delete_position(position_id: str) -> bool:
    """Elimina una posición por su ID."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM positions WHERE id = ?", (position_id,))
        conn.commit()
        return cursor.rowcount > 0

