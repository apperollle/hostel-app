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


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


# --- Pages ---

@app.route("/")
def index():
    return render_template("index.html", user=current_user())


@app.route("/hostel/<int:hostel_id>")
def hostel_page(hostel_id):
    return render_template("hostel.html", user=current_user(), hostel_id=hostel_id)


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/admin")
def admin_page():
    user = current_user()
    if not user:
        return redirect(url_for("login_page"))
    return render_template("admin.html", user=user)


# --- API: HOSTELS (ВОССТАНОВЛЕНО) ---

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
    query_text = (request.args.get("q") or "").strip()

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

    return jsonify({"hostels": hostels})


@app.route("/api/hostels/<int:hostel_id>")
def api_hostel_detail(hostel_id):
    with db_session() as conn:
        hostel = conn.execute(
            "SELECT * FROM hostels WHERE id = ?",
            (hostel_id,),
        ).fetchone()

        if not hostel:
            return jsonify({"error": "Хостел не найден"}), 404

    return jsonify({"hostel": dict(hostel)})


# --- AUTH API (упрощённо, но рабочее) ---

@app.route("/api/me")
def api_me():
    return jsonify({"user": current_user()})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"message": "ok"})


# --- START ---

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
