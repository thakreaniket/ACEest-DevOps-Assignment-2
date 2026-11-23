# ACEest_Fitness.py
import os
import random
import sqlite3
from datetime import date
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "aceest_secret_key_2026")
DB_NAME = os.environ.get("DB_NAME", "aceest_fitness.db")
APP_VERSION = os.environ.get("APP_VERSION", "v1.0.0")

PROGRAM_TEMPLATES = {
    "Fat Loss": ["Full Body HIIT", "Circuit Training", "Cardio + Weights"],
    "Muscle Gain": ["Push/Pull/Legs", "Upper/Lower Split", "Full Body Strength"],
    "Beginner": ["Full Body 3x/week", "Light Strength + Mobility"],
}


def get_db_connection(db_name=None):
    conn = sqlite3.connect(db_name or app.config.get("DB_NAME", DB_NAME))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_name=None):
    conn = get_db_connection(db_name)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        age INTEGER,
        height REAL,
        weight REAL,
        program TEXT,
        calories INTEGER,
        target_weight REAL,
        target_adherence INTEGER,
        membership_status TEXT,
        membership_end TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        week TEXT,
        adherence INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        date TEXT,
        workout_type TEXT,
        duration_min INTEGER,
        notes TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workout_id INTEGER,
        name TEXT,
        sets INTEGER,
        reps INTEGER,
        weight REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        date TEXT,
        weight REAL,
        waist REAL,
        bodyfat REAL
    )
    """)

    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users VALUES ('admin', 'admin', 'Admin')")

    conn.commit()
    conn.close()


# Simple embedded HTML UI so you don't need extra template folders yet
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ACEest Fitness & Gym ({{ version }})</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; margin: 0; padding: 20px; }
        .header { background: #d4af37; color: #000; padding: 15px; font-size: 22px; font-weight: bold; }
        .card { background: #262626; padding: 15px; margin-top: 15px; border-radius: 6px; }
        input, select, button { padding: 8px; margin: 5px 0; }
        button { background: #d4af37; border: none; font-weight: bold; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #444; padding: 8px; text-align: left; }
    </style>
</head>
<body>
    <div class="header">ACEest Fitness & Gym — Dashboard ({{ version }})</div>
    <div class="card">
        <h3>Add Client</h3>
        <form method="POST" action="/clients">
            <input type="text" name="name" placeholder="Client Name" required>
            <input type="number" name="age" placeholder="Age">
            <input type="number" step="0.1" name="weight" placeholder="Weight (kg)">
            <button type="submit">Add Client</button>
        </form>
    </div>

    <div class="card">
        <h3>Registered Clients</h3>
        <table>
            <tr><th>Name</th><th>Program</th><th>Membership</th><th>Actions</th></tr>
            {% for c in clients %}
            <tr>
                <td>{{ c['name'] }}</td>
                <td>{{ c['program'] or 'Not Assigned' }}</td>
                <td>{{ c['membership_status'] }}</td>
                <td>
                    <form method="POST" action="/clients/{{ c['name'] }}/generate-program" style="display:inline;">
                        <button type="submit">Generate AI Program</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "app": "ACEest Fitness", "version": APP_VERSION}), 200


@app.route("/", methods=["GET"])
def index():
    conn = get_db_connection()
    clients = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    conn.close()
    return render_template_string(DASHBOARD_HTML, clients=clients, version=APP_VERSION)


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or request.form
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = get_db_connection()
    user = conn.execute(
        "SELECT role FROM users WHERE username=? AND password=?", (username, password)
    ).fetchone()
    conn.close()

    if user:
        session["user"] = username
        session["role"] = user["role"]
        return jsonify({"message": "Login successful", "role": user["role"]}), 200
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/clients", methods=["GET", "POST"])
def manage_clients():
    conn = get_db_connection()
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        name = data.get("name", "").strip()
        if not name:
            conn.close()
            return jsonify({"error": "Client name is required"}), 400

        age = data.get("age")
        weight = data.get("weight")
        conn.execute(
            "INSERT OR IGNORE INTO clients (name, age, weight, membership_status) VALUES (?, ?, ?, ?)",
            (name, age, weight, "Active"),
        )
        conn.commit()
        conn.close()

        if request.is_json:
            return jsonify({"message": f"Client {name} saved", "name": name}), 201
        return redirect(url_for("index"))

    clients = [dict(row) for row in conn.execute("SELECT * FROM clients ORDER BY name").fetchall()]
    conn.close()
    return jsonify(clients), 200


@app.route("/clients/<name>/generate-program", methods=["POST"])
def generate_program(name):
    conn = get_db_connection()
    client = conn.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    if not client:
        conn.close()
        return jsonify({"error": "Client not found"}), 404

    program_type = random.choice(list(PROGRAM_TEMPLATES.keys()))
    program_detail = random.choice(PROGRAM_TEMPLATES[program_type])

    conn.execute("UPDATE clients SET program=? WHERE name=?", (program_detail, name))
    conn.commit()
    conn.close()

    if request.is_json:
        return jsonify({"client": name, "category": program_type, "program": program_detail}), 200
    return redirect(url_for("index"))


@app.route("/clients/<name>/workouts", methods=["GET", "POST"])
def manage_workouts(name):
    conn = get_db_connection()
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        workout_date = data.get("date", date.today().isoformat())
        workout_type = data.get("workout_type", "Strength")
        duration_min = int(data.get("duration_min", 60))
        notes = data.get("notes", "")

        conn.execute(
            "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) VALUES (?, ?, ?, ?, ?)",
            (name, workout_date, workout_type, duration_min, notes),
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Workout added", "client": name}), 201

    workouts = [
        dict(row)
        for row in conn.execute(
            "SELECT date, workout_type, duration_min, notes FROM workouts WHERE client_name=? ORDER BY date DESC",
            (name,),
        ).fetchall()
    ]
    conn.close()
    return jsonify(workouts), 200


@app.route("/clients/<name>/membership", methods=["GET"])
def check_membership(name):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT membership_status, membership_end FROM clients WHERE name=?", (name,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Client not found"}), 404
    return jsonify({
        "client": name,
        "membership_status": row["membership_status"],
        "renewal_date": row["membership_end"] or "N/A",
    }), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)