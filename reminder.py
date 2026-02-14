# reminder.py – SQLite backend for reminders
# ---------------------------------------------------------
# Public API (unchanged):
#   load_reminders(username) -> List[dict]
#   save_reminders(username, reminders)   – kept for compatibility
#   handle_reminder_input(user_input, username) -> str   (add)
#   show_reminder_notification(reminder) – still uses QMessageBox (Qt)
#   check_reminders(username) – runs the ticking loop (now DB‑based)
# ---------------------------------------------------------

import sqlite3
import datetime
import re
from plyer import notification
from PyQt6.QtWidgets import QMessageBox

DB_SUFFIX = ".db"


def _db_path(username: str) -> str:
    return f"reminders_{username}{DB_SUFFIX}"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            text      TEXT NOT NULL,
            dt        TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _connect(username: str) -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(username))
    _ensure_schema(conn)
    return conn


# ------------------------------------------------------------------------ #
#  PUBLIC API
# ------------------------------------------------------------------------ #
def load_reminders(username: str) -> list[dict]:
    """Return all stored reminders for the user."""
    conn = _connect(username)
    cur = conn.cursor()
    cur.execute("SELECT id, text, dt FROM reminders ORDER BY dt")
    rows = cur.fetchall()
    conn.close()
    return [{"id": rid, "text": txt, "datetime": dt} for rid, txt, dt in rows]


def save_reminders(username: str, reminders: list[dict]) -> None:
    """
    Overwrite the whole reminder table with the supplied list.
    Kept only for backward compatibility; the UI never calls it after the switch.
    """
    conn = _connect(username)
    cur = conn.cursor()
    cur.execute("DELETE FROM reminders")
    for r in reminders:
        cur.execute(
            "INSERT INTO reminders (text, dt) VALUES (?, ?)",
            (r["text"], r["datetime"]),
        )
    conn.commit()
    conn.close()


# ------------------------------------------------------------------------ #
#  Core helper – add / list / delete
# ------------------------------------------------------------------------ #
reminder_add_pattern = r"remind on (\d{2}/\d{2}/\d{2} at \d{1,2}:\d{2}\s?(?:am|pm|AM|PM)?) to (.+)"
reminder_list_pattern = r"(show|list) reminders"
reminder_remove_pattern = r"(delete|remove) reminder (\d+)"


def handle_reminder_input(user_input: str, username: str) -> str:
    """
    Parse a natural‑language “remind on … at … to …” command
    and persist it in the user‑specific DB.
    """
    # 1️⃣ Grab the date‑time string and the reminder text
    match = re.search(reminder_add_pattern, user_input, re.IGNORECASE)
    if not match:
        return "❌ Sorry, I didn’t understand the reminder format. " \
               "Try:  remind on 27/03/25 at 6:30 PM to <your text>"

    dt_str, text = match.groups()           # e.g. "27/03/25 at 6:30 PM", "study Tamil"

    # 2️⃣ Split the date from the time
    date_part, time_part = dt_str.split(" at ")
    day, month, yr = map(int, date_part.split("/"))
    # Assuming two‑digit year belongs to 2000‑2099
    year = 2000 + yr

    # 3️⃣ Parse the time (handles both 12‑h with AM/PM)
    try:
        t = datetime.datetime.strptime(time_part.strip(), "%I:%M %p")
    except ValueError:                     # fallback to 24‑h format
        t = datetime.datetime.strptime(time_part.strip(), "%H:%M")

    # 4️⃣ Build the exact datetime for the reminder
    reminder_dt = datetime.datetime(year, month, day,
                                    hour=t.hour, minute=t.minute,
                                    second=0, microsecond=0)

    iso = reminder_dt.strftime("%Y-%m-%d %H:%M")   # store as ISO string

    # 5️⃣ Persist to SQLite
    conn = _connect(username)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reminders (text, dt) VALUES (?, ?)",
        (text, iso)
    )
    conn.commit()
    conn.close()

    # 6️⃣ Friendly feedback
    return f"✅ Reminder added – I’ll ping you at {iso}."

