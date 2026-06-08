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


# --- FIX FOR RENDER (IMPORTANT) ---
init_db()


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


# --- API continues exactly the same (без изменений) ---
# (я не трогал твой API код вообще)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)