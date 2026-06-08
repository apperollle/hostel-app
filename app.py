from datetime import datetime

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database import db_session, init_db, refresh_hostel_rating

app = Flask(__name__)
app.secret_key = "hostel-app-dev-change-in-production"


@app.before_request
def ensure_db():
    if not getattr(app, "_db_ready", False):
        init_db()
        app._db_ready = True


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with db_session() as conn:
        row = conn.execute(
            "SELECT id, email, name, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def require_login():
    user = current_user()
    if not user:
        return None, (jsonify({"error": "Требуется вход в систему"}), 401)
    return user, None


def require_user():
    user, err = require_login()
    if err:
        return None, err
    if user["role"] != "user":
        return None, (jsonify({"error": "Доступно только для пользователей"}), 403)
    return user, None


def require_admin():
    user, err = require_login()
    if err:
        return None, err
    if user["role"] != "admin":
        return None, (jsonify({"error": "Доступ только для администратора"}), 403)
    return user, None


def redirect_if_logged_in():
    user = current_user()
    if not user:
        return None
    if user["role"] == "admin":
        return redirect(url_for("admin_page"))
    return redirect(url_for("index"))


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def nights_between(check_in, check_out):
    return (check_out - check_in).days


def room_available(conn, room_id, check_in, check_out, exclude_booking_id=None):
    room = conn.execute(
        "SELECT total_beds FROM rooms WHERE id = ?",
        (room_id,),
    ).fetchone()
    if not room:
        return False, "Номер не найден"

    query = """
        SELECT COALESCE(SUM(guests), 0) AS booked
        FROM bookings
        WHERE room_id = ?
          AND status = 'confirmed'
          AND check_in < ?
          AND check_out > ?
    """
    params = [room_id, check_out.isoformat(), check_in.isoformat()]
    if exclude_booking_id:
        query += " AND id != ?"
        params.append(exclude_booking_id)

    booked = conn.execute(query, params).fetchone()["booked"]
    if booked >= room["total_beds"]:
        return False, "Нет свободных мест на выбранные даты"
    return True, None


# --- Pages ---


@app.route("/")
def index():
    return render_template("index.html", user=current_user())


@app.route("/hostel/<int:hostel_id>")
def hostel_page(hostel_id):
    return render_template("hostel.html", user=current_user(), hostel_id=hostel_id)


@app.route("/login")
def login_page():
    redir = redirect_if_logged_in()
    if redir:
        return redir
    return render_template("login.html")


@app.route("/admin/login")
def admin_login_page():
    user = current_user()
    if user:
        if user["role"] == "admin":
            return redirect(url_for("admin_page"))
        return redirect(url_for("index"))
    return render_template("admin_login.html")


@app.route("/register")
def register_page():
    redir = redirect_if_logged_in()
    if redir:
        return redir
    return render_template("register.html")


@app.route("/bookings")
def bookings_page():
    user = current_user()
    if not user:
        return redirect(url_for("login_page"))
    if user["role"] == "admin":
        return redirect(url_for("admin_page"))
    return render_template("bookings.html", user=user)


@app.route("/admin")
def admin_page():
    user = current_user()
    if not user:
        return redirect(url_for("admin_login_page"))
    if user["role"] != "admin":
        return redirect(url_for("index"))
    return render_template("admin.html", user=user)


# --- API: Auth ---


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()

    if not email or not password or not name:
        return jsonify({"error": "Заполните имя, email и пароль"}), 400
    if len(password) < 6:
        return jsonify({"error": "Пароль должен быть не короче 6 символов"}), 400

    with db_session() as conn:
        exists = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if exists:
            return jsonify({"error": "Email уже зарегистрирован"}), 409

        cur = conn.execute(
            """
            INSERT INTO users (email, password_hash, name)
            VALUES (?, ?, ?)
            """,
            (email, generate_password_hash(password), name),
        )
        user_id = cur.lastrowid

    session["user_id"] = user_id
    return jsonify({"message": "Регистрация успешна", "user": current_user()})


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    with db_session() as conn:
        row = conn.execute(
            "SELECT id, password_hash, role FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "Неверный email или пароль"}), 401
    if row["role"] == "admin":
        return jsonify(
            {"error": "Это учётная запись администратора. Войдите через страницу администратора."}
        ), 403

    session["user_id"] = row["id"]
    return jsonify({"message": "Вход выполнен", "user": current_user()})


@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    with db_session() as conn:
        row = conn.execute(
            "SELECT id, password_hash, role FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "Неверный email или пароль"}), 401
    if row["role"] != "admin":
        return jsonify(
            {"error": "Нет прав администратора. Войдите как обычный пользователь."}
        ), 403

    session["user_id"] = row["id"]
    return jsonify({"message": "Вход администратора выполнен", "user": current_user()})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"message": "Вы вышли из аккаунта"})


@app.route("/api/me")
def api_me():
    user = current_user()
    if not user:
        return jsonify({"user": None})
    return jsonify({"user": user})


# --- API: Hostels ---


@app.route("/api/cities")
def api_cities():
    with db_session() as conn:
        rows = conn.execute(
            "SELECT DISTINCT city FROM hostels ORDER BY city"
        ).fetchall()
    return jsonify({"cities": [r["city"] for r in rows]})


@app.route("/api/hostels")
def api_hostels():
    city = (request.args.get("city") or "").strip()
    check_in = parse_date(request.args.get("check_in"))
    check_out = parse_date(request.args.get("check_out"))
    guests = request.args.get("guests", type=int) or 1
    query_text = (request.args.get("q") or "").strip()

    if check_in and check_out and check_out <= check_in:
        return jsonify({"error": "Дата выезда должна быть позже заезда"}), 400

    with db_session() as conn:
        sql = """
            SELECT h.id, h.name, h.city, h.address, h.description,
                   h.image_url, h.rating, h.review_count,
                   MIN(r.price_per_night) AS min_price
            FROM hostels h
            JOIN rooms r ON r.hostel_id = h.id
            WHERE 1=1
        """
        params = []

        if city:
            sql += " AND h.city = ?"
            params.append(city)
        if query_text:
            sql += " AND (h.name LIKE ? OR h.city LIKE ? OR h.description LIKE ?)"
            like = f"%{query_text}%"
            params.extend([like, like, like])

        sql += " GROUP BY h.id ORDER BY h.rating DESC, h.name"

        hostels = [dict(row) for row in conn.execute(sql, params).fetchall()]

        if check_in and check_out:
            available = []
            for hostel in hostels:
                rooms = conn.execute(
    "SELECT id, total_beds FROM rooms WHERE hostel_id = ?",
    (hostel["id"],),
).fetchall()
                has_room = False
                for room in rooms:
                    ok, _ = room_available(
                        conn, room["id"], check_in, check_out
                    )
                    if ok:
                        booked = conn.execute(
                            """
                            SELECT COALESCE(SUM(guests), 0) AS booked
                            FROM bookings
                            WHERE room_id = ? AND status = 'confirmed'
                              AND check_in < ? AND check_out > ?
                            """,
                            (
                                room["id"],
                                check_out.isoformat(),
                                check_in.isoformat(),
                            ),
                        ).fetchone()["booked"]
                        free = room["total_beds"] - booked
                        if free >= guests:
                            has_room = True
                            break
                if has_room:
                    available.append(hostel)
            hostels = available

    return jsonify({"hostels": hostels})


@app.route("/api/hostels/<int:hostel_id>")
def api_hostel_detail(hostel_id):
    check_in = parse_date(request.args.get("check_in"))
    check_out = parse_date(request.args.get("check_out"))
    guests = request.args.get("guests", type=int) or 1

    with db_session() as conn:
        hostel = conn.execute(
            "SELECT * FROM hostels WHERE id = ?",
            (hostel_id,),
        ).fetchone()
        if not hostel:
            return jsonify({"error": "Хостел не найден"}), 404

        rooms_raw = conn.execute(
            """
            SELECT id, name, room_type, price_per_night, total_beds
            FROM rooms WHERE hostel_id = ? ORDER BY price_per_night
            """,
            (hostel_id,),
        ).fetchall()

        rooms = []
        for room in rooms_raw:
            item = dict(room)
            item["available"] = True
            item["free_beds"] = room["total_beds"]

            if check_in and check_out:
                ok, msg = room_available(
                    conn, room["id"], check_in, check_out
                )
                booked = conn.execute(
                    """
                    SELECT COALESCE(SUM(guests), 0) AS booked
                    FROM bookings
                    WHERE room_id = ? AND status = 'confirmed'
                      AND check_in < ? AND check_out > ?
                    """,
                    (
                        room["id"],
                        check_out.isoformat(),
                        check_in.isoformat(),
                    ),
                ).fetchone()["booked"]
                item["free_beds"] = max(0, room["total_beds"] - booked)
                item["available"] = ok and item["free_beds"] >= guests
                if not item["available"]:
                    item["unavailable_reason"] = msg or "Недостаточно мест"

            if check_in and check_out and nights_between(check_in, check_out) > 0:
                nights = nights_between(check_in, check_out)
                item["total_price"] = round(room["price_per_night"] * nights, 2)
            rooms.append(item)

        reviews = conn.execute(
            """
            SELECT r.id, r.rating, r.comment, r.created_at, u.name AS user_name
            FROM reviews r
            JOIN users u ON u.id = r.user_id
            WHERE r.hostel_id = ?
            ORDER BY r.created_at DESC
            """,
            (hostel_id,),
        ).fetchall()

    return jsonify(
        {
            "hostel": dict(hostel),
            "rooms": rooms,
            "reviews": [dict(r) for r in reviews],
        }
    )


@app.route("/api/hostels/<int:hostel_id>/reviews", methods=["POST"])
def api_add_review(hostel_id):
    user, err = require_user()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    comment = (data.get("comment") or "").strip()

    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": "Оценка от 1 до 5"}), 400
    if len(comment) < 10:
        return jsonify({"error": "Комментарий не короче 10 символов"}), 400

    with db_session() as conn:
        hostel = conn.execute(
            "SELECT id FROM hostels WHERE id = ?",
            (hostel_id,),
        ).fetchone()
        if not hostel:
            return jsonify({"error": "Хостел не найден"}), 404

        try:
            conn.execute(
                """
                INSERT INTO reviews (hostel_id, user_id, rating, comment)
                VALUES (?, ?, ?, ?)
                """,
                (hostel_id, user["id"], rating, comment),
            )
        except Exception:
            return jsonify({"error": "Вы уже оставляли отзыв на этот хостел"}), 409

        refresh_hostel_rating(conn, hostel_id)

    return jsonify({"message": "Отзыв добавлен"})


# --- API: Bookings ---


@app.route("/api/bookings", methods=["GET"])
def api_list_bookings():
    user, err = require_user()
    if err:
        return err

    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT b.id, b.check_in, b.check_out, b.guests, b.total_price,
                   b.status, b.created_at,
                   h.name AS hostel_name, h.city, h.image_url,
                   r.name AS room_name
            FROM bookings b
            JOIN rooms r ON r.id = b.room_id
            JOIN hostels h ON h.id = r.hostel_id
            WHERE b.user_id = ?
            ORDER BY b.check_in DESC
            """,
            (user["id"],),
        ).fetchall()

    return jsonify({"bookings": [dict(r) for r in rows]})


@app.route("/api/bookings", methods=["POST"])
def api_create_booking():
    user, err = require_user()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    room_id = data.get("room_id")
    check_in = parse_date(data.get("check_in"))
    check_out = parse_date(data.get("check_out"))
    guests = data.get("guests", 1)

    if not room_id or not check_in or not check_out:
        return jsonify({"error": "Укажите номер и даты"}), 400
    if check_out <= check_in:
        return jsonify({"error": "Дата выезда должна быть позже заезда"}), 400
    if guests < 1:
        return jsonify({"error": "Укажите число гостей"}), 400

    nights = nights_between(check_in, check_out)
    if nights < 1:
        return jsonify({"error": "Минимум одна ночь"}), 400

    with db_session() as conn:
        room = conn.execute(
            """
            SELECT r.id, r.price_per_night, r.total_beds, h.name AS hostel_name
            FROM rooms r
            JOIN hostels h ON h.id = r.hostel_id
            WHERE r.id = ?
            """,
            (room_id,),
        ).fetchone()
        if not room:
            return jsonify({"error": "Номер не найден"}), 404

        ok, msg = room_available(conn, room_id, check_in, check_out)
        if not ok:
            return jsonify({"error": msg}), 409

        booked = conn.execute(
            """
            SELECT COALESCE(SUM(guests), 0) AS booked
            FROM bookings
            WHERE room_id = ? AND status = 'confirmed'
              AND check_in < ? AND check_out > ?
            """,
            (room_id, check_out.isoformat(), check_in.isoformat()),
        ).fetchone()["booked"]
        if booked + guests > room["total_beds"]:
            return jsonify({"error": "Недостаточно свободных мест"}), 409

        total_price = round(room["price_per_night"] * nights * guests, 2)
        cur = conn.execute(
            """
            INSERT INTO bookings (user_id, room_id, check_in, check_out, guests, total_price)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                room_id,
                check_in.isoformat(),
                check_out.isoformat(),
                guests,
                total_price,
            ),
        )

    return jsonify(
        {
            "message": "Бронирование подтверждено",
            "booking_id": cur.lastrowid,
            "total_price": total_price,
            "hostel_name": room["hostel_name"],
        }
    )


@app.route("/api/bookings/<int:booking_id>", methods=["DELETE"])
def api_cancel_booking(booking_id):
    user, err = require_user()
    if err:
        return err

    with db_session() as conn:
        row = conn.execute(
            "SELECT id, user_id FROM bookings WHERE id = ?",
            (booking_id,),
        ).fetchone()
        if not row:
            return jsonify({"error": "Бронирование не найдено"}), 404
        if row["user_id"] != user["id"]:
            return jsonify({"error": "Нет доступа"}), 403

        conn.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ?",
            (booking_id,),
        )

    return jsonify({"message": "Бронирование отменено"})


# --- API: Admin CRUD ---


def _hostel_payload(data, partial=False):
    fields = {
        "name": (data.get("name") or "").strip(),
        "city": (data.get("city") or "").strip(),
        "address": (data.get("address") or "").strip(),
        "description": (data.get("description") or "").strip(),
        "image_url": (data.get("image_url") or "").strip(),
    }
    if not partial:
        missing = [k for k, v in fields.items() if k != "image_url" and not v]
        if missing:
            return None, "Заполните название, город, адрес и описание"
    return fields, None


@app.route("/api/admin/hostels", methods=["GET"])
def api_admin_list_hostels():
    _, err = require_admin()
    if err:
        return err

    with db_session() as conn:
        hostels = conn.execute(
            "SELECT * FROM hostels ORDER BY city, name"
        ).fetchall()
        result = []
        for h in hostels:
            item = dict(h)
            rooms = conn.execute(
                """
                SELECT id, name, room_type, price_per_night, total_beds
                FROM rooms WHERE hostel_id = ? ORDER BY price_per_night
                """,
                (h["id"],),
            ).fetchall()
            item["rooms"] = [dict(r) for r in rooms]
            result.append(item)

    return jsonify({"hostels": result})


@app.route("/api/admin/hostels", methods=["POST"])
def api_admin_create_hostel():
    _, err = require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    fields, err_msg = _hostel_payload(data)
    if err_msg:
        return jsonify({"error": err_msg}), 400

    with db_session() as conn:
        cur = conn.execute(
            """
            INSERT INTO hostels (name, city, address, description, image_url)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                fields["name"],
                fields["city"],
                fields["address"],
                fields["description"],
                fields["image_url"] or None,
            ),
        )
        hostel_id = cur.lastrowid

    return jsonify({"message": "Хостел добавлен", "hostel_id": hostel_id}), 201


@app.route("/api/admin/hostels/<int:hostel_id>", methods=["PUT"])
def api_admin_update_hostel(hostel_id):
    _, err = require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    fields, err_msg = _hostel_payload(data, partial=True)
    if err_msg:
        return jsonify({"error": err_msg}), 400

    with db_session() as conn:
        exists = conn.execute(
            "SELECT id FROM hostels WHERE id = ?",
            (hostel_id,),
        ).fetchone()
        if not exists:
            return jsonify({"error": "Хостел не найден"}), 404

        conn.execute(
            """
            UPDATE hostels
            SET name = ?, city = ?, address = ?, description = ?, image_url = ?
            WHERE id = ?
            """,
            (
                fields["name"],
                fields["city"],
                fields["address"],
                fields["description"],
                fields["image_url"] or None,
                hostel_id,
            ),
        )

    return jsonify({"message": "Хостел обновлён"})


@app.route("/api/admin/hostels/<int:hostel_id>", methods=["DELETE"])
def api_admin_delete_hostel(hostel_id):
    _, err = require_admin()
    if err:
        return err

    with db_session() as conn:
        exists = conn.execute(
            "SELECT id FROM hostels WHERE id = ?",
            (hostel_id,),
        ).fetchone()
        if not exists:
            return jsonify({"error": "Хостел не найден"}), 404
        conn.execute("DELETE FROM hostels WHERE id = ?", (hostel_id,))

    return jsonify({"message": "Хостел удалён"})


@app.route("/api/admin/hostels/<int:hostel_id>/rooms", methods=["POST"])
def api_admin_create_room(hostel_id):
    _, err = require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    room_type = (data.get("room_type") or "dorm").strip()
    price = data.get("price_per_night")
    total_beds = data.get("total_beds")

    if not name or price is None or total_beds is None:
        return jsonify({"error": "Заполните название, цену и число мест"}), 400
    if room_type not in ("dorm", "private"):
        return jsonify({"error": "Тип номера: dorm или private"}), 400
    try:
        price = float(price)
        total_beds = int(total_beds)
    except (TypeError, ValueError):
        return jsonify({"error": "Некорректная цена или число мест"}), 400
    if price <= 0 or total_beds < 1:
        return jsonify({"error": "Цена и число мест должны быть положительными"}), 400

    with db_session() as conn:
        hostel = conn.execute(
            "SELECT id FROM hostels WHERE id = ?",
            (hostel_id,),
        ).fetchone()
        if not hostel:
            return jsonify({"error": "Хостел не найден"}), 404

        cur = conn.execute(
            """
            INSERT INTO rooms (hostel_id, name, room_type, price_per_night, total_beds)
            VALUES (?, ?, ?, ?, ?)
            """,
            (hostel_id, name, room_type, price, total_beds),
        )

    return jsonify({"message": "Номер добавлен", "room_id": cur.lastrowid}), 201


@app.route("/api/admin/rooms/<int:room_id>", methods=["PUT"])
def api_admin_update_room(room_id):
    _, err = require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    room_type = (data.get("room_type") or "dorm").strip()
    price = data.get("price_per_night")
    total_beds = data.get("total_beds")

    if not name or price is None or total_beds is None:
        return jsonify({"error": "Заполните все поля номера"}), 400
    if room_type not in ("dorm", "private"):
        return jsonify({"error": "Тип номера: dorm или private"}), 400
    try:
        price = float(price)
        total_beds = int(total_beds)
    except (TypeError, ValueError):
        return jsonify({"error": "Некорректная цена или число мест"}), 400

    with db_session() as conn:
        exists = conn.execute(
            "SELECT id FROM rooms WHERE id = ?",
            (room_id,),
        ).fetchone()
        if not exists:
            return jsonify({"error": "Номер не найден"}), 404

        conn.execute(
            """
            UPDATE rooms
            SET name = ?, room_type = ?, price_per_night = ?, total_beds = ?
            WHERE id = ?
            """,
            (name, room_type, price, total_beds, room_id),
        )

    return jsonify({"message": "Номер обновлён"})


@app.route("/api/admin/rooms/<int:room_id>", methods=["DELETE"])
def api_admin_delete_room(room_id):
    _, err = require_admin()
    if err:
        return err

    with db_session() as conn:
        exists = conn.execute(
            "SELECT id FROM rooms WHERE id = ?",
            (room_id,),
        ).fetchone()
        if not exists:
            return jsonify({"error": "Номер не найден"}), 404
        conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))

    return jsonify({"message": "Номер удалён"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
