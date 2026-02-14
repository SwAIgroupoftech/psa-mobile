"""
reminder_watcher.py – background daemon that checks the SQLite‑based
reminders (reminder.py) and shows a native OS notification when a
reminder is due.

The rest of the PSA code (UI, Core, reminder.py) does not need any
modification – just replace this file with the version below and
restart the app (or re‑run `start_reminder_service(username)`).
"""

import os
import datetime
import time
import platform
import sys
import threading

# ----------------------------------------------------------------------
#   OS‑specific notifier (unchanged – keep the nice cross‑platform logic)
# ----------------------------------------------------------------------
_system = platform.system()

if _system == "Windows":
    try:
        from win10toast import ToastNotifier
        _win_toaster = ToastNotifier()
        def _notify(title: str, msg: str):
            _win_toaster.show_toast(title, msg, duration=6, threaded=True)
    except Exception:
        from plyer import notification
        def _notify(title: str, msg: str):
            notification.notify(title=title, message=msg, timeout=6)

elif _system == "Darwin":          # macOS
    try:
        import pync
        def _notify(title: str, msg: str):
            pync.notify(msg, title=title)
    except Exception:
        from plyer import notification
        def _notify(title: str, msg: str):
            notification.notify(title=title, message=msg, timeout=6)

else:                               # Linux / other *nix
    try:
        import notify2
        notify2.init("PSA Reminder")
        def _notify(title: str, msg: str):
            n = notify2.Notification(title, msg)
            n.set_timeout(6000)          # ms
            n.show()
    except Exception:
        from plyer import notification
        def _notify(title: str, msg: str):
            notification.notify(title=title, message=msg, timeout=6)


# ----------------------------------------------------------------------
#   Helper – import the SQLite‑based API from reminder.py
# ----------------------------------------------------------------------
# NOTE: reminder.py lives in the same directory as this watcher.
# We add the directory to sys.path just in case the script is launched
# from a different working directory.
_this_dir = os.path.abspath(os.path.dirname(__file__))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)

from reminder import load_reminders, save_reminders   # <-- SQLite helpers


# ----------------------------------------------------------------------
#   Main loop – checks every 30 seconds (same interval as before)
# ----------------------------------------------------------------------
def reminder_watcher(username: str, stop_event: threading.Event | None = None):
    """
    Background process that:
      1. Loads reminders from the SQLite DB (via ``load_reminders``).
      2. If a reminder's ``datetime`` matches the current minute,
         shows a native OS notification.
      3. Removes the fired reminder from the DB (via ``save_reminders``).

    Parameters
    ----------
    username : str
        The PSA user whose reminders we are watching.
    stop_event : threading.Event | None
        Optional flag to stop the loop gracefully (useful for tests).
    """
    while True:
        # Graceful shutdown?
        if stop_event and stop_event.is_set():
            break

        # ------------------------------------------------------------------
        #   1️⃣ Load all pending reminders from SQLite
        # ------------------------------------------------------------------
        reminders = load_reminders(username)          # list[{'id', 'text', 'datetime'}]

        # ------------------------------------------------------------------
        #   2️⃣ Current time string to compare with the DB field
        #       (we use minute‑precision – the same format that ``handle_reminder_input`` writes)
        # ------------------------------------------------------------------
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        updated = False
        for r in reminders[:]:      # iterate over a shallow copy so we can pop safely
            # ``r`` comes from SQLite, the timestamp field is called "datetime"
            if r.get("datetime") == now_str:
                # ---- Show native notification --------------------------------
                title = "🔔 PSA Reminder"
                msg   = r.get("text", "(no text)")
                try:
                    _notify(title, msg)
                except Exception as exc:
                    # Fallback: print to console (still visible in logs)
                    print(f"[Reminder] Failed native notify: {exc}", file=sys.stderr)

                # ---- Remove the reminder from the in‑memory list -------------
                reminders.remove(r)
                updated = True

        # ------------------------------------------------------------------
        #   3️⃣ Persist the cleaned‑up list back to SQLite (if anything changed)
        # ------------------------------------------------------------------
        if updated:
            # ``save_reminders`` overwrites the whole table – this is safe because
            # we only removed the already‑fired entries.
            save_reminders(username, reminders)

        # ------------------------------------------------------------------
        #   4️⃣ Sleep – same 30 seconds granularity as before
        # ------------------------------------------------------------------
        time.sleep(30)


# ----------------------------------------------------------------------
#   CLI entry‑point (kept for manual testing)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Background PSA reminder daemon (SQLite‑based)."
    )
    parser.add_argument("username", help="PSA username whose reminders to watch")
    args = parser.parse_args()

    try:
        print(f"[Reminder] Starting daemon for user: {args.username}")
        reminder_watcher(args.username)
    except KeyboardInterrupt:
        print("\n[Reminder] Daemon stopped by user")
