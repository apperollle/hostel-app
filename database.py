import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).parent / "hostel_app.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS hostels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                address TEXT NOT NULL,
                description TEXT NOT NULL,
                image_url TEXT,
                rating REAL NOT NULL DEFAULT 0,
                review_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostel_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                room_type TEXT NOT NULL,
                price_per_night REAL NOT NULL,
                total_beds INTEGER NOT NULL,
                FOREIGN KEY (hostel_id) REFERENCES hostels(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                room_id INTEGER NOT NULL,
                check_in TEXT NOT NULL,
                check_out TEXT NOT NULL,
                guests INTEGER NOT NULL,
                total_price REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmed',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (hostel_id) REFERENCES hostels(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE (hostel_id, user_id)
            );
            """
        )

        count = conn.execute("SELECT COUNT(*) FROM hostels").fetchone()[0]
        if count == 0:
            seed_data(conn)


def seed_data(conn):
    hostels = [
        (
            "Сон на Невском",
            "Санкт-Петербург",
            "Невский проспект, 12",
            "Уютный хостел в центре Петербурга: общая кухня, Wi‑Fi, камера хранения.",
            "https://images.unsplash.com/photo-1520250497591-112f2f40a3d4?w=800",
        ),
        (
            "Красная площадь Stay",
            "Москва",
            "ул. Мясницкая, 24",
            "Современные капсульные и общие номера рядом с метро.",
            "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=800",
        ),
        (
            "Казанский дворик",
            "Казань",
            "ул. Баумана, 5",
            "Атмосферный хостел в историческом центре с террасой.",
            "https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=800",
        ),
        (
            "Байкал Base",
            "Иркутск",
            "ул. Ленина, 30",
            "Идеальная база перед поездкой на Байкал, завтрак включён.",
            "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=800",
        ),
    ]

    for name, city, address, description, image_url in hostels:
        cur = conn.execute(
            """
            INSERT INTO hostels (name, city, address, description, image_url, rating, review_count)
            VALUES (?, ?, ?, ?, ?, 4.2, 0)
            """,
            (name, city, address, description, image_url),
        )
        hostel_id = cur.lastrowid
        rooms = [
            ("Общий 8-местный", "dorm", 850, 8),
            ("Общий 4-местный", "dorm", 1200, 4),
            ("Двухместный", "private", 2800, 2),
        ]
        for room_name, room_type, price, beds in rooms:
            conn.execute(
                """
                INSERT INTO rooms (hostel_id, name, room_type, price_per_night, total_beds)
                VALUES (?, ?, ?, ?, ?)
                """,
                (hostel_id, room_name, room_type, price, beds),
            )

    conn.execute(
        """
        INSERT INTO users (email, password_hash, name, role)
        VALUES (?, ?, ?, 'admin')
        """,
        ("admin@hostel.app", generate_password_hash("admin123"), "Администратор"),
    )

    demo_user_id = conn.execute(
        """
        INSERT INTO users (email, password_hash, name, role)
        VALUES (?, ?, ?, 'user')
        """,
        ("demo@hostel.app", generate_password_hash("demo123"), "Демо Пользователь"),
    ).lastrowid

    today = date.today()
    check_in = (today + timedelta(days=7)).isoformat()
    check_out = (today + timedelta(days=10)).isoformat()
    room_id = conn.execute("SELECT id FROM rooms LIMIT 1").fetchone()[0]

    conn.execute(
        """
        INSERT INTO bookings (user_id, room_id, check_in, check_out, guests, total_price, status)
        VALUES (?, ?, ?, ?, 2, 2550, 'confirmed')
        """,
        (demo_user_id, room_id, check_in, check_out),
    )

    conn.execute(
        """
        INSERT INTO reviews (hostel_id, user_id, rating, comment)
        VALUES (1, ?, 5, 'Отличное расположение и чистые номера!')
        """,
        (demo_user_id,),
    )
    _refresh_hostel_rating(conn, 1)


def _refresh_hostel_rating(conn, hostel_id):
    row = conn.execute(
        """
        SELECT ROUND(AVG(rating), 1) AS avg_rating, COUNT(*) AS cnt
        FROM reviews WHERE hostel_id = ?
        """,
        (hostel_id,),
    ).fetchone()
    avg_rating = row["avg_rating"] or 0
    cnt = row["cnt"] or 0
    conn.execute(
        "UPDATE hostels SET rating = ?, review_count = ? WHERE id = ?",
        (avg_rating, cnt, hostel_id),
    )


def refresh_hostel_rating(conn, hostel_id):
    _refresh_hostel_rating(conn, hostel_id)
