import os
import sqlite3
import sys
import webbrowser
from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, url_for

# Use the executable location when packaged; otherwise use current working directory.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.getcwd()

DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "charting.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = "patient-charting-local"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visit_date TEXT NOT NULL,
                subjective TEXT NOT NULL,
                treatment_details TEXT NOT NULL,
                client_feedback TEXT NOT NULL,
                home_care TEXT NOT NULL,
                recommended_treatment_plan TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def fetch_entries(search_query: str) -> list[sqlite3.Row]:
    with get_connection() as conn:
        if search_query:
            like = f"%{search_query}%"
            return conn.execute(
                """
                SELECT *
                FROM entries
                WHERE visit_date LIKE ?
                   OR subjective LIKE ?
                   OR treatment_details LIKE ?
                   OR client_feedback LIKE ?
                   OR home_care LIKE ?
                   OR recommended_treatment_plan LIKE ?
                ORDER BY created_at DESC, id DESC
                """,
                (like, like, like, like, like, like),
            ).fetchall()

        return conn.execute(
            """
            SELECT *
            FROM entries
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action", "save")

        if action == "delete":
            entry_id = request.form.get("entry_id", "").strip()
            search_query = request.form.get("q", "").strip()

            if entry_id.isdigit():
                with get_connection() as conn:
                    conn.execute("DELETE FROM entries WHERE id = ?", (int(entry_id),))
                flash("Entry deleted.", "success")
            else:
                flash("Could not delete entry.", "error")

            return redirect(url_for("index", q=search_query))

        visit_date = request.form.get("visit_date", date.today().isoformat()).strip()
        subjective = request.form.get("subjective", "").strip()
        treatment_details = request.form.get("treatment_details", "").strip()
        client_feedback = request.form.get("client_feedback", "").strip()
        home_care = request.form.get("home_care", "").strip()
        recommended_treatment_plan = request.form.get("recommended_treatment_plan", "").strip()

        if not subjective or not treatment_details:
            flash("Subjective and Treatment Details are required.", "error")
            return redirect(url_for("index"))

        created_at = datetime.now().isoformat(timespec="seconds")
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO entries (
                    visit_date,
                    subjective,
                    treatment_details,
                    client_feedback,
                    home_care,
                    recommended_treatment_plan,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    visit_date,
                    subjective,
                    treatment_details,
                    client_feedback,
                    home_care,
                    recommended_treatment_plan,
                    created_at,
                ),
            )

        flash("Entry saved.", "success")
        return redirect(url_for("index"))

    search_query = request.args.get("q", "").strip()
    entries = fetch_entries(search_query)
    return render_template(
        "form.html",
        entries=entries,
        search_query=search_query,
        today=date.today().isoformat(),
    )


if __name__ == "__main__":
    init_db()
    port = 5000
    webbrowser.open(f"http://127.0.0.1:{port}/")
    app.run(debug=True, port=port)
else:
    init_db()
