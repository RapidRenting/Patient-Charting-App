import os
import sqlite3
import sys
import threading
import time
import webbrowser
from datetime import date, datetime
from typing import Final

from flask import Flask, flash, redirect, render_template, request, url_for

APP_NAME = "PatientCharting"
IS_FROZEN = getattr(sys, "frozen", False)
HEARTBEAT_TIMEOUT_SECONDS: Final[int] = 5
HEARTBEAT_CHECK_INTERVAL_SECONDS: Final[int] = 1
last_heartbeat_monotonic = time.monotonic()


def get_resource_dir() -> str:
    # PyInstaller one-file bundles unpack resources here at runtime.
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_data_dir() -> str:
    if IS_FROZEN and sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~/Library/Application Support"),
            APP_NAME,
            "data",
        )
    if IS_FROZEN:
        return os.path.join(os.path.dirname(sys.executable), "data")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


RESOURCE_DIR = get_resource_dir()
DATA_DIR = get_data_dir()
DB_PATH = os.path.join(DATA_DIR, "charting.db")

app = Flask(__name__, template_folder=os.path.join(RESOURCE_DIR, "templates"))
app.config["SECRET_KEY"] = "patient-charting-local"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def heartbeat_watchdog() -> None:
    while True:
        time.sleep(HEARTBEAT_CHECK_INTERVAL_SECONDS)
        elapsed = time.monotonic() - last_heartbeat_monotonic
        if elapsed >= HEARTBEAT_TIMEOUT_SECONDS:
            os._exit(0)


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


def format_saved_timestamp(timestamp: str) -> str:
    value = (timestamp or "").strip()
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        return f"{dt.date().isoformat()} {dt.strftime('%I:%M %p').lstrip('0')}"
    except ValueError:
        return value.replace("T", " ")


def normalize_date_part(value: str, width: int) -> str:
    text = (value or "").strip()
    if not text.isdigit():
        return ""
    return text.zfill(width)


def build_visit_date_pattern(year: str, month: str, day: str) -> str:
    y = normalize_date_part(year, 4)
    m = normalize_date_part(month, 2)
    d = normalize_date_part(day, 2)

    if y and m and d:
        return f"{y}-{m}-{d}"
    if y and m:
        return f"{y}-{m}-%"
    if y:
        return f"{y}-%"
    if m and d:
        return f"%-{m}-{d}"
    if m:
        return f"%-{m}-%"
    if d:
        return f"%-%-{d}"
    return ""


def fetch_entries(search_year: str, search_month: str, search_day: str, text_query: str) -> list[dict[str, str]]:
    rows: list[sqlite3.Row]
    text_query = (text_query or "").strip()
    date_pattern = build_visit_date_pattern(search_year, search_month, search_day)
    with get_connection() as conn:
        if date_pattern and text_query:
            like = f"%{text_query}%"
            rows = conn.execute(
                """
                SELECT *
                FROM entries
                WHERE visit_date LIKE ?
                  AND (
                    subjective LIKE ?
                    OR treatment_details LIKE ?
                    OR client_feedback LIKE ?
                    OR home_care LIKE ?
                    OR recommended_treatment_plan LIKE ?
                  )
                ORDER BY created_at DESC, id DESC
                """,
                (date_pattern, like, like, like, like, like),
            ).fetchall()
        elif date_pattern:
            rows = conn.execute(
                """
                SELECT *
                FROM entries
                WHERE visit_date LIKE ?
                ORDER BY created_at DESC, id DESC
                """,
                (date_pattern,),
            ).fetchall()
        elif text_query:
            like = f"%{text_query}%"
            rows = conn.execute(
                """
                SELECT *
                FROM entries
                WHERE subjective LIKE ?
                   OR treatment_details LIKE ?
                   OR client_feedback LIKE ?
                   OR home_care LIKE ?
                   OR recommended_treatment_plan LIKE ?
                ORDER BY created_at DESC, id DESC
                """,
                (like, like, like, like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT *
                FROM entries
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()

    results: list[dict[str, str]] = []
    for row in rows:
        item = dict(row)
        item["created_at_display"] = format_saved_timestamp(str(row["created_at"]))
        results.append(item)
    return results


def fetch_entry_stats() -> tuple[int, str, str]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS total_entries,
                   COALESCE(MIN(visit_date), '') AS earliest_visit_date,
                   COALESCE(MAX(visit_date), '') AS latest_visit_date
            FROM entries
            """
        ).fetchone()
    return (
        int(row["total_entries"]),
        str(row["earliest_visit_date"]),
        str(row["latest_visit_date"]),
    )


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

        visit_year = normalize_date_part(request.form.get("visit_year", ""), 4)
        visit_month = normalize_date_part(request.form.get("visit_month", ""), 2)
        visit_day = normalize_date_part(request.form.get("visit_day", ""), 2)
        visit_date = request.form.get("visit_date", date.today().isoformat()).strip()
        if visit_year and visit_month and visit_day:
            visit_date = f"{visit_year}-{visit_month}-{visit_day}"
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

    today = date.today()
    search_year = normalize_date_part(request.args.get("sy", ""), 4)
    search_month = normalize_date_part(request.args.get("sm", ""), 2)
    search_day = normalize_date_part(request.args.get("sd", ""), 2)
    text_query = request.args.get("t", "").strip()
    if not search_year and not search_month and not search_day and not text_query:
        search_year = str(today.year)
        search_month = f"{today.month:02d}"
        search_day = f"{today.day:02d}"

    entries = fetch_entries(search_year, search_month, search_day, text_query)
    total_entries, earliest_visit_date, latest_visit_date = fetch_entry_stats()
    start_year = today.year - 5
    if earliest_visit_date and len(earliest_visit_date) >= 4 and earliest_visit_date[:4].isdigit():
        start_year = min(start_year, int(earliest_visit_date[:4]))
    year_options = [str(year) for year in range(today.year + 1, start_year - 1, -1)]

    return render_template(
        "form.html",
        entries=entries,
        shown_count=len(entries),
        total_entries=total_entries,
        earliest_visit_date=earliest_visit_date,
        latest_visit_date=latest_visit_date,
        db_path=DB_PATH,
        search_year=search_year,
        search_month=search_month,
        search_day=search_day,
        text_query=text_query,
        visit_year=f"{today.year:04d}",
        visit_month=f"{today.month:02d}",
        visit_day=f"{today.day:02d}",
        year_options=year_options,
    )


@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    global last_heartbeat_monotonic
    last_heartbeat_monotonic = time.monotonic()
    return ("", 204)


if __name__ == "__main__":
    init_db()
    port = 5000
    # Delay open so browser loads after the server starts.
    threading.Timer(0.7, lambda: webbrowser.open(f"http://127.0.0.1:{port}/")).start()
    if IS_FROZEN:
        threading.Thread(target=heartbeat_watchdog, daemon=True).start()
    app.run(debug=not IS_FROZEN, use_reloader=False, port=port)
else:
    init_db()
