
import os
import json
import datetime
import sqlite3
from pathlib import Path
from typing import List, Tuple, Dict
from users import API_KEY_2,MODEL_NAME,BASE_URL
from cerebras.cloud.sdk import Cerebras
import sys
# --------------------------------------------------------------------------- #
#   Paths & low‑level connection helpers
# --------------------------------------------------------------------------- 

# Determine base directory (works in both dev and packaged)
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

print(f"🔍 BASE_DIR set to: {BASE_DIR}")  # Debug

def _db_path(username: str) -> Path:
    """Path to the per‑user SQLite DB."""
    return Path(BASE_DIR) / f"conversations_{username}.db"

def _connect(username: str) -> sqlite3.Connection:
    """Open (or create) the SQLite DB for a user."""
    conn = sqlite3.connect(_db_path(username))
    conn.row_factory = sqlite3.Row
    return conn

def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the `conversations` table and the FTS5 virtual table if they do not exist."""
    cur = conn.cursor()
    # ---- main table -------------------------------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            conv_id TEXT    NOT NULL,
            role    TEXT    NOT NULL,
            content TEXT    NOT NULL,
            ts      TEXT    NOT NULL   -- ISO‑8601 timestamp
        )
        """
    )
    conn.commit()

        # ---- conversation summaries table ----
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_summaries (
        conv_id TEXT PRIMARY KEY,
        upto_message_id INTEGER NOT NULL,
        topics TEXT NOT NULL,
        crucial_mentions TEXT NOT NULL,
        created_at TEXT NOT NULL
                )
        """
    )

    conn.commit()


# --------------------------------------------------------------------------- #
#   Public API – creation / read / write
# --------------------------------------------------------------------------- #
def create_conversation(username: str) -> str:
    """Return a fresh conversation identifier (timestamp string)."""
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")


def add_message(username: str, conv_id: str, role: str, content: str) -> None:
    """Insert a new row for the given conversation and update the FTS index."""
    conn = _connect(username)
    _ensure_schema(conn)

    ts = datetime.datetime.now().isoformat(timespec="seconds")
    cur = conn.cursor()
    # ---- insert into main table ----
    cur.execute(
        """
        INSERT INTO conversations (conv_id, role, content, ts)
        VALUES (?, ?, ?, ?)
        """,
        (conv_id, role, content, ts),
    )
    rowid = cur.lastrowid                      # needed for FTS insert
    conn.commit()

    conn.close()


def get_conversation(username: str, conv_id: str) -> List[Dict[str, str]]:
    """Return **all** messages for a conversation ordered chronologically."""
    conn = _connect(username)
    _ensure_schema(conn)

    cur = conn.cursor()
    cur.execute(
        """
        SELECT role, content, ts
        FROM conversations
        WHERE conv_id = ?
        ORDER BY id ASC
        """,
        (conv_id,),
    )
    rows = cur.fetchall()
    conn.close()

    return [{"role": r["role"], "content": r["content"], "ts": r["ts"]} for r in rows]


def get_conversation_titles(username: str) -> List[Tuple[str, str]]:
    """Return a list of `(conv_id, readable_title)` for the UI sidebar."""
    conn = _connect(username)
    _ensure_schema(conn)

    cur = conn.cursor()
    cur.execute(
        """
        SELECT conv_id, MIN(id) AS first_row_id
        FROM conversations
        GROUP BY conv_id
        ORDER BY first_row_id DESC
        """
    )
    conv_ids = [r["conv_id"] for r in cur.fetchall()]

    titles: List[Tuple[str, str]] = []
    for cid in conv_ids:
        # Try to fetch the first *user* message (friendly title)
        cur.execute(
            """
            SELECT content
            FROM conversations
            WHERE conv_id = ? AND role = 'user'
            ORDER BY id ASC
            LIMIT 1
            """,
            (cid,),
        )
        row = cur.fetchone()
        if row:
            title = row["content"].strip().split("\n")[0][:40]
        else:
            # Fallback: pretty‑print the timestamp
            title = datetime.datetime.strptime(
                cid, "%Y%m%d%H%M%S"
            ).strftime("%Y-%m-%d %H:%M")
        titles.append((cid, title))

    conn.close()
    return titles


def get_conversation_title(username: str, conv_id: str) -> str:
    """Return a single title for a conversation (used after rename)."""
    conn = _connect(username)
    _ensure_schema(conn)

    cur = conn.cursor()
    cur.execute(
        """
        SELECT content
        FROM conversations
        WHERE conv_id = ? AND role = 'user'
        ORDER BY id ASC
        LIMIT 1
        """,
        (conv_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        return row["content"].strip().split("\n")[0][:40]
    # fallback to timestamp
    try:
        return datetime.datetime.strptime(conv_id, "%Y%m%d%H%M%S").strftime(
            "%Y-%m-%d %H:%M"
        )
    except Exception:
        return conv_id


def rename_conversation(username: str, conv_id: str, new_title: str) -> None:
    """Store a human‑friendly title in a side‑car JSON file."""
    meta_path = Path(BASE_DIR) / f"conversations_{username}_meta.json"
    if meta_path.is_file():
        with meta_path.open("r", encoding="utf-8") as f:
            meta = json.load(f)
    else:
        meta = {}

    meta[conv_id] = new_title
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def delete_conversation(username: str, conv_id: str) -> None:
    """Remove **all** rows for a conversation and clean its metadata."""
    conn = _connect(username)
    _ensure_schema(conn)

    cur = conn.cursor()
    cur.execute("DELETE FROM conversations WHERE conv_id = ?", (conv_id,))
    
    cur.execute("DELETE FROM conversation_summaries WHERE conv_id = ?",(conv_id,),)
    conn.commit()
    conn.close()
    
    # Clean side‑car title file, if it exists
    meta_path = Path(BASE_DIR) / f"conversations_{username}_meta.json"
    if meta_path.is_file():
        with meta_path.open("r", encoding="utf-8") as f:
            meta = json.load(f)
        if conv_id in meta:
            del meta[conv_id]
            with meta_path.open("w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
    

# --------------------------------------------------------------------------- #
#   NEW helpers – edit / delete a single message (used by UI)
# --------------------------------------------------------------------------- #
def update_message(username: str, conv_id: str, timestamp: str, new_content: str) -> bool:
    """
    Replace the *content* of a single message identified by its ISO‑8601 `ts`.
    Returns True on success, False otherwise.
    """
    try:
        with _connect(username) as con:
            cur = con.cursor()
            # Fetch rowid
            cur.execute(
                "SELECT id FROM conversations WHERE conv_id=? AND ts=?",(conv_id, timestamp),)
            row = cur.fetchone()
            if not row:
                return False

            rowid = row["id"]

            # Update base table
            cur.execute("UPDATE conversations SET content=? WHERE id=?",(new_content, rowid),)

            return True
    except Exception as e:
        print("⚠️ update_message error:", e)
        return False


def delete_last_message(username: str, conv_id: str, role: str) -> bool:
    """
    Delete the most recent message of the given `role` (`user` or `assistant`).
    Returns True if a row was removed.
    """
    try:
        with _connect(username) as con:
            cur = con.cursor()
            # Grab the latest timestamp for the role
            cur.execute(
                """
                SELECT ts, id
                FROM conversations
                WHERE conv_id = ? AND role = ?
                ORDER BY ts DESC
                LIMIT 1
                """,
                (conv_id, role),
            )
            row = cur.fetchone()
            if not row:
                return False

            ts = row["ts"]
            rowid = row["id"]
            cur.execute(
                """
                DELETE FROM conversations
                WHERE conv_id = ? AND ts = ? AND role = ?
                """,
                (conv_id, ts, role),
            )
            con.commit()
            
            return cur.rowcount > 0
    except Exception as e:
        print("⚠️ delete_last_message error:", e)
        return False


def delete_message_by_ts(username: str, conv_id: str, ts: str) -> bool:
    """
    Delete a single message identified by its timestamp.
    Used for per‑message regenerate / edit.
    """
    try:
        with _connect(username) as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT id FROM conversations
                WHERE conv_id = ? AND ts = ?
                """,
                (conv_id, ts),
            )
            row = cur.fetchone()
            if not row:
                return False
            rowid = row["id"]
            cur.execute(
                """
                DELETE FROM conversations
                WHERE conv_id = ? AND ts = ?
                """,
                (conv_id, ts),
            )
            con.commit()
           
            return cur.rowcount > 0
    except Exception as e:
        print("⚠️ delete_message_by_ts error:", e)
        return False


def get_message_by_ts(username: str, conv_id: str, ts: str) -> Dict[str, str] | None:
    """
    Return the single message (role, content, ts) that matches the timestamp.
    Returns ``None`` if not found.
    """
    conn = _connect(username)
    _ensure_schema(conn)

    cur = conn.cursor()
    cur.execute(
        """
        SELECT role, content, ts
        FROM conversations
        WHERE conv_id = ? AND ts = ?
        """,
        (conv_id, ts),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {"role": row["role"], "content": row["content"], "ts": row["ts"]}
    return None



# --------------------------------------------------------------------------- #
#   Optional migration helper (run once if old JSON files exist)
# --------------------------------------------------------------------------- #
def _migrate_legacy_json(username: str) -> None:
    """
    If a user still has a pre‑SQLite JSON file, import it and rename the source.
    """
    legacy_path = Path(BASE_DIR) / f"conversations_{username}.json"
    if not legacy_path.is_file():
        return

    with legacy_path.open("r", encoding="utf-8") as f:
        legacy_data: Dict[str, List[Dict[str, str]]] = json.load(f)

    conn = _connect(username)
    _ensure_schema(conn)
    cur = conn.cursor()

    for conv_id, msgs in legacy_data.items():
        for msg in msgs:
            cur.execute(
                """
                INSERT INTO conversations (conv_id, role, content, ts)
                VALUES (?, ?, ?, ?)
                """,
                (conv_id,
                 msg["role"],
                 msg["content"],
                 datetime.datetime.now().isoformat(timespec="seconds")),
            )
    conn.commit()
    conn.close()

    # Rename original file so the migration runs only once
    legacy_path.rename(legacy_path.with_suffix(".json.migrated"))
def create_conversation_summary(username: str, conv_id: str) -> None:
    conn = _connect(username)
    _ensure_schema(conn)
    cur = conn.cursor()

    # Count user messages
    cur.execute(
        "SELECT COUNT(*) FROM conversations WHERE conv_id=? AND role='user'",
        (conv_id,),
    )
    user_count = cur.fetchone()[0]
    if user_count == 0 or user_count % 10 != 0:
        conn.close()
        return

    # Load existing summary
    cur.execute(
        """
        SELECT topics, crucial_mentions, upto_message_id
        FROM conversation_summaries
        WHERE conv_id=?
        """,
        (conv_id,),
    )
    row = cur.fetchone()

    existing = {
        "topics": [],
        "crucial_mentions": [],
        "upto": 0,
    }

    if row:
        existing["topics"] = json.loads(row["topics"])
        existing["crucial_mentions"] = json.loads(row["crucial_mentions"])
        existing["upto"] = row["upto_message_id"]

    # Fetch new messages
    cur.execute(
        """
        SELECT id, role, content
        FROM conversations
        WHERE conv_id=? AND id > ?
        ORDER BY id ASC
        """,
        (conv_id, existing["upto"]),
    )
    messages = cur.fetchall()
    if not messages:
        conn.close()
        return

    convo_blob = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages
    )

    # ---- LLM summarization ----
    summary = {"topics": [], "crucial_mentions": []}

    try:
        client = Cerebras(api_key=API_KEY_2, base_url=BASE_URL)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{
                "role": "system",
                "content": "You are PSA, Personal Smart Assistant created by Nachiketh.You are a friendly assistant of user.Summarize the following conversation."f"""
Return STRICT JSON:
{{
  "topics": [string],
  "crucial_mentions": [string]
}}

Conversation:
<<<
{convo_blob}
>>>
"""
            }],
        )
        parsed = json.loads(response.choices[0].message.content)
        summary = parsed
    except Exception:
        pass

    # Merge + cap
    def merge(old, new, cap):
        out = list(dict.fromkeys(old + new))
        return out[:cap]

    topics = merge(existing["topics"], summary["topics"], 2)
    crucial = merge(existing["crucial_mentions"], summary["crucial_mentions"],5)

    # UPSERT
    cur.execute(
        """
        INSERT INTO conversation_summaries
        (conv_id, upto_message_id, topics, crucial_mentions,created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(conv_id) DO UPDATE SET
          upto_message_id=excluded.upto_message_id,
          topics=excluded.topics,
          crucial_mentions=excluded.crucial_mentions,
          created_at=excluded.created_at
        """,
        (
            conv_id,
            messages[-1]["id"],
            json.dumps(topics),
            json.dumps(crucial),
            datetime.datetime.now().isoformat(timespec="seconds"),
        ),
    )

    conn.commit()
    conn.close()

    
def load_conversation_summary(username: str, limit: int = 10) -> dict | None:
    """
    Load crucial mentions and topics from ALL conversations for this user.
    
    Args:
        username: Username
        limit: Maximum number of crucial mentions to return (default 10)
    
    Returns:
        Dict with 'topics' and 'crucial_mentions' lists, or None if no data
    """
    conn = _connect(username)
    _ensure_schema(conn)
    cur = conn.cursor()

    # Get ALL crucial mentions from ALL conversations, most recent first
    cur.execute(
        """
        SELECT crucial_mentions, created_at
        FROM conversation_summaries
        ORDER BY created_at DESC
        """
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return None

    # Collect all crucial mentions from all conversations
    all_crucial = []
    all_topics = []
    
    for row in rows:
        crucial = json.loads(row["crucial_mentions"])
        all_crucial.extend(crucial)
        
        # Also collect topics (but we'll cap these too)
        # Note: We're not using topics in the main prompt anymore,
        # but keeping them for future use

    # Remove duplicates while preserving order (most recent first)
    seen = set()
    unique_crucial = []
    for mention in all_crucial:
        if mention not in seen:
            seen.add(mention)
            unique_crucial.append(mention)
            if len(unique_crucial) >= limit:  # ✅ CAP at limit
                break

    return {
        "topics": [],  # Not used in main prompt anymore
        "crucial_mentions": unique_crucial[:limit]  # ✅ Enforce cap
    }