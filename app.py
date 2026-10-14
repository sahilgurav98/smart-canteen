
import os
import sqlite3
import csv
import io
from contextlib import contextmanager
from datetime import datetime
from functools import wraps

from flask import (
    Flask, jsonify, render_template, request, session,
    redirect, url_for, flash, Response
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-before-deploy")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(BASE_DIR, "data", "canteen.db")
)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-this-demo-password")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

STATUSES = [
    "Pending", "Preparing", "Ready for Pickup", "Completed", "Cancelled"
]

SEED = [
    ("meal1", "Paneer Tikka Wrap", "Meals", 90,
     "Grilled paneer, crunchy vegetables and mint chutney.",
     "🌯", "#f8e8d7", 1),
    ("meal2", "Veg Rice Bowl", "Meals", 110,
     "Rice bowl with seasonal vegetables.",
     "🍛", "#e9edcf", 1),
    ("snack1", "Masala Sandwich", "Snacks", 55,
     "Toasted sandwich with spicy potato filling.",
     "🥪", "#f3e4c7", 1),
    ("snack2", "Samosa (2 pcs)", "Snacks", 30,
     "Crispy samosas with green chutney.",
     "🥟", "#f5dfbf", 1),
    ("drink1", "Cold Coffee", "Drinks", 60,
     "Chilled coffee for your afternoon break.",
     "🥤", "#e4e8f5", 1),
    ("drink2", "Fresh Lime Soda", "Drinks", 35,
     "Refreshing lime soda served cold.",
     "🍋", "#e5efc9", 1),
]


@contextmanager
def db():
    """Open a SQLite connection and always close it."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    with db() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS menu_items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price INTEGER NOT NULL CHECK(price >= 0),
                description TEXT NOT NULL,
                emoji TEXT NOT NULL,
                color TEXT NOT NULL,
                available INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pickup_time TEXT NOT NULL,
                status TEXT NOT NULL,
                total INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL
                    REFERENCES orders(id) ON DELETE CASCADE,
                menu_item_id TEXT,
                item_name TEXT NOT NULL,
                unit_price INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0)
            );
        """)

        if c.execute("SELECT COUNT(*) FROM menu_items").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO menu_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                SEED
            )


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            if request.path.startswith("/api/"):
                return jsonify(error="Admin login required"), 401
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def order_json(c, row):
    items = c.execute(
        """SELECT item_name, unit_price, quantity
           FROM order_items WHERE order_id=? ORDER BY id""",
        (row["id"],)
    ).fetchall()

    return {
        "id": row["id"],
        "pickup_time": row["pickup_time"],
        "status": row["status"],
        "total": row["total"],
        "created_at": row["created_at"],
        "items": [
            {
                "name": item["item_name"],
                "price": item["unit_price"],
                "quantity": item["quantity"],
            }
            for item in items
        ],
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    try:
        with db() as c:
            c.execute("SELECT 1")
        return jsonify(status="ok", service="smart-canteen")
    except sqlite3.Error:
        return jsonify(status="error"), 500


@app.get("/api/menu")
def menu():
    category = request.args.get("category")

    with db() as c:
        if category and category != "All":
            rows = c.execute(
                """SELECT * FROM menu_items
                   WHERE available=1 AND category=?
                   ORDER BY name""",
                (category,)
            ).fetchall()
        else:
            rows = c.execute(
                """SELECT * FROM menu_items
                   WHERE available=1 ORDER BY category, name"""
            ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.post("/api/orders")
def create_order():
    data = request.get_json(silent=True) or {}
    pickup = data.get("pickup_time", "As soon as possible")

    allowed_pickup = {
        "As soon as possible", "In 15 minutes",
        "In 30 minutes", "In 45 minutes"
    }

    if pickup not in allowed_pickup:
        return jsonify(error="Invalid pickup time"), 400

    raw_items = data.get("items")

    if not isinstance(raw_items, list) or not raw_items:
        return jsonify(error="Your cart is empty"), 400

    quantities = {}

    for item in raw_items:
        if not isinstance(item, dict):
            return jsonify(error="Invalid cart item"), 400

        item_id = str(item.get("id", ""))
        quantity = item.get("quantity")

        if (
            not item_id
            or not isinstance(quantity, int)
            or isinstance(quantity, bool)
            or quantity < 1
            or quantity > 20
        ):
            return jsonify(error="Quantity must be between 1 and 20"), 400

        quantities[item_id] = quantities.get(item_id, 0) + quantity

        if quantities[item_id] > 20:
            return jsonify(error="Maximum quantity per item is 20"), 400

    with db() as c:
        lines = []
        total = 0

        for item_id, quantity in quantities.items():
            item = c.execute(
                """SELECT id, name, price FROM menu_items
                   WHERE id=? AND available=1""",
                (item_id,)
            ).fetchone()

            if not item:
                return jsonify(error="Menu item unavailable"), 400

            total += item["price"] * quantity
            lines.append((
                item["id"], item["name"], item["price"], quantity
            ))

        created = datetime.now().astimezone().strftime(
            "%Y-%m-%d %H:%M:%S %Z"
        )

        cursor = c.execute(
            """INSERT INTO orders
               (pickup_time, status, total, created_at)
               VALUES (?, ?, ?, ?)""",
            (pickup, "Pending", total, created)
        )

        order_id = cursor.lastrowid

        c.executemany(
            """INSERT INTO order_items
               (order_id, menu_item_id, item_name, unit_price, quantity)
               VALUES (?, ?, ?, ?, ?)""",
            [(order_id, *line) for line in lines]
        )

        row = c.execute(
            "SELECT * FROM orders WHERE id=?", (order_id,)
        ).fetchone()

        result = order_json(c, row)

    return jsonify(result), 201


@app.get("/api/orders/<int:oid>")
def track_order(oid):
    with db() as c:
        row = c.execute(
            "SELECT * FROM orders WHERE id=?", (oid,)
        ).fetchone()

        if not row:
            return jsonify(error="Order not found"), 404

        return jsonify(order_json(c, row))


@app.get("/api/admin/orders")
@admin_required
def admin_orders():
    with db() as c:
        rows = c.execute(
            "SELECT * FROM orders ORDER BY id DESC"
        ).fetchall()

        return jsonify([order_json(c, row) for row in rows])


@app.patch("/api/admin/orders/<int:oid>")
@admin_required
def update_status(oid):
    status = (request.get_json(silent=True) or {}).get("status")

    if status not in STATUSES:
        return jsonify(error="Invalid order status"), 400

    with db() as c:
        row = c.execute(
            "SELECT * FROM orders WHERE id=?", (oid,)
        ).fetchone()

        if not row:
            return jsonify(error="Order not found"), 404

        c.execute(
            "UPDATE orders SET status=? WHERE id=?",
            (status, oid)
        )

        updated = c.execute(
            "SELECT * FROM orders WHERE id=?", (oid,)
        ).fetchone()

        return jsonify(order_json(c, updated))


@app.get("/api/admin/summary")
@admin_required
def summary():
    with db() as c:
        return jsonify(
            total_orders=c.execute(
                "SELECT COUNT(*) FROM orders"
            ).fetchone()[0],
            preparing=c.execute(
                "SELECT COUNT(*) FROM orders WHERE status='Preparing'"
            ).fetchone()[0],
            ready=c.execute(
                "SELECT COUNT(*) FROM orders WHERE status='Ready for Pickup'"
            ).fetchone()[0],
            sales=c.execute(
                """SELECT COALESCE(SUM(total), 0) FROM orders
                   WHERE status != 'Cancelled'"""
            ).fetchone()[0],
        )


@app.get("/admin/login")
def login():
    return render_template("admin_login.html")


@app.post("/admin/login")
def login_post():
    if request.form.get("password") == ADMIN_PASSWORD:
        session["admin"] = True
        return redirect(url_for("dashboard"))

    flash("Incorrect password", "error")
    return redirect(url_for("login"))


@app.get("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.get("/admin")
@admin_required
def dashboard():
    return render_template("admin.html")


@app.post("/admin/menu/<item_id>/availability")
@admin_required
def availability(item_id):
    with db() as c:
        row = c.execute(
            "SELECT available FROM menu_items WHERE id=?", (item_id,)
        ).fetchone()

        if row:
            c.execute(
                "UPDATE menu_items SET available=? WHERE id=?",
                (0 if row["available"] else 1, item_id)
            )
        else:
            flash("Menu item not found", "error")

    return redirect(url_for("dashboard"))


@app.get("/admin/report.csv")
@admin_required
def report():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Order ID", "Created at", "Pickup",
        "Status", "Items", "Total INR"
    ])

    with db() as c:
        rows = c.execute(
            "SELECT * FROM orders ORDER BY id DESC"
        ).fetchall()

        for row in rows:
            order = order_json(c, row)
            items = "; ".join(
                f'{item["quantity"]} x {item["name"]}'
                for item in order["items"]
            )

            writer.writerow([
                order["id"], order["created_at"],
                order["pickup_time"], order["status"],
                items, order["total"]
            ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=smart-canteen-report.csv"
        },
    )


@app.errorhandler(404)
def not_found(err):
    if request.path.startswith("/api/"):
        return jsonify(error="Not found"), 404

    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG") == "1"
    )
    print("Implemented Order Tracking")
