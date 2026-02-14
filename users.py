# --------------------------------------------------------------------------- #
#   users.py – authentication + encrypted per‑user memory (SQLite backend)
# --------------------------------------------------------------------------- #

import os
import json
import re
import base64
import hashlib
import sqlite3
from typing import Dict, List
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent/'.env'
load_dotenv(dotenv_path=env_path)

# --------------------------------------------------------------------------- #
#   CONSTANTS
# --------------------------------------------------------------------------- #
USERS_FILE = "users.json"          # tiny JSON that stores only username → password‑hash
MEM_DB_SUFFIX = ".db"             # each user gets memory_<username>.db


# --------------------------------------------------------------------------- #
#   PASSWORD HELPERS (unchanged)
# --------------------------------------------------------------------------- #
def hash_password(password: str, salt: bytes | None = None) -> str:
    """
    Return a string ``salt_hex:hash_hex`` using PBKDF2‑HMAC‑SHA256.
    390 000 iterations → same security level you already had.
    """
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390_000)
    return f"{salt.hex()}:{dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Return True if *password* matches the stored ``salt:hash`` string."""
    try:
        salt_hex, hash_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
    except Exception:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390_000)
    return dk.hex() == hash_hex


# --------------------------------------------------------------------------- #
#   USER DATABASE (tiny JSON)
# --------------------------------------------------------------------------- #
def load_users() -> dict:
    """Read the whole ``users.json`` file (creates empty dict if missing)."""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}


def save_users(users: dict) -> None:
    """Write the full users dict back to disk."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)


def signup(username: str, password: str) -> tuple[bool, str]:
    """Create a new account – returns (ok, message)."""
    users = load_users()
    if username in users:
        return (
            False,
            f"PSA: I know you! Don't fool me. Please login, {username}.",
        )
    users[username] = {"password": hash_password(password)}
    save_users(users)
    return True, f"Signup successful! Welcome to PSA, {username}."


def login(username: str, password: str) -> tuple[bool, str]:
    """Log in an existing user – returns (ok, message)."""
    users = load_users()
    if username not in users:
        return (
            False,
            f"PSA: I don't know you yet. Please signup, {username}.",
        )
    if verify_password(password, users[username]["password"]):
        return True, f"PSA: Welcome back, {username}."
    return False, "PSA: I guess your password is wrong. Check it again."


# --------------------------------------------------------------------------- #
#   ENCRYPTION HELPERS (same as before)
# --------------------------------------------------------------------------- #
def derive_key(password: str) -> bytes:
    """Derive a deterministic Fernet key from the password (fixed salt)."""
    salt = b"psa_fixed_salt"
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390_000, dklen=32)
    return base64.urlsafe_b64encode(dk)


def encrypt_data(data: str, password: str) -> bytes:
    """Encrypt a plain‑text string → bytes."""
    key = derive_key(password)
    f = Fernet(key)
    return f.encrypt(data.encode("utf-8"))


def decrypt_data(token: bytes, password: str) -> str | None:
    """Decrypt the bytes produced by ``encrypt_data`` → plain string."""
    key = derive_key(password)
    f = Fernet(key)
    try:
        return f.decrypt(token).decode("utf-8")
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#   MEMORY – SQLite BACKEND (still encrypted per value)
# --------------------------------------------------------------------------- #
def _mem_db_path(username: str) -> str:
    """Path to the per‑user memory DB, e.g. ``memory_john.db``."""
    return f"memory_{username}{MEM_DB_SUFFIX}"


def _mem_connect(username: str) -> sqlite3.Connection:
    """Open (or create) the DB for *username* and ensure the schema."""
    conn = sqlite3.connect(_mem_db_path(username))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS memory (
            category TEXT NOT NULL,
            value    TEXT NOT NULL,
            PRIMARY KEY (category, value)
        )
        """
    )
    conn.commit()
    return conn


def load_memory(username: str, password: str) -> Dict[str, List[str]]:
    """
    Return the full memory dict for *username*.
    The values are decrypted on the fly.
    """
    conn = _mem_connect(username)
    cur = conn.cursor()
    cur.execute("SELECT category, value FROM memory")
    rows = cur.fetchall()
    conn.close()

    # Build the dict with all default categories
    mem: Dict[str, List[str]] = {
        "name": [],
        "likes": [],
        "dislikes": [],
        "hobbies": [],
        "goals": [],
        "facts": [],
    }

    for cat, enc_val in rows:
        plain = decrypt_data(enc_val.encode("utf-8"), password)
        if plain is not None:
            mem.setdefault(cat, []).append(plain)

    # Guarantees that every key exists even if the table was empty.
    for k in ["name", "likes", "dislikes", "hobbies", "goals", "facts"]:
        mem.setdefault(k, [])
    return mem


def save_memory(memory: Dict[str, List[str]], username: str, password: str) -> None:
    """
    Overwrite the whole memory table with the supplied dict.
    Each individual value is encrypted with the user’s password.
    """
    conn = _mem_connect(username)
    cur = conn.cursor()
    cur.execute("DELETE FROM memory")     # clear old data
    for cat, values in memory.items():
        for val in values:
            enc = encrypt_data(val, password)          # bytes
            cur.execute(
                "INSERT INTO memory (category, value) VALUES (?, ?)",
                (cat, enc.decode("utf-8")),
            )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------- #
#   REGEX PATTERNS – used by the intelligent‑memory detector
# --------------------------------------------------------------------------- #
like_patterns = [
     r"\bi (?:really |absolutely )?love (.+?)(?:\.|!|$)",
    r"\bi (?:really |absolutely )?like (.+?)(?:\.|!|$)",
    r"\bi am a (?:big |huge )?fan of (.+?)(?:\.|!|$)",
    r"\bi am crazy about (.+?)(?:\.|!|$)",
    r"\bi enjoy (.+?)(?:\.|!|$)",
    r"\bi am really into (.+?)(?:\.|!|$)",
    r"my favorite (?:thing|food|sport|team|player|show|movie|book|game) is (.+?)(?:\.|!|$)",
    r"(.+?) is (?:really |so )?(?:awesome|amazing|great|fantastic)(?:\.|!|$)",
]

dislike_patterns = [
    r"\bi (?:really |absolutely )?hate (.+?)(?:\.|!|$)",
    r"\bi (?:really |absolutely )?dislike (.+?)(?:\.|!|$)",
    r"\bi (?:really )?don'?t like (.+?)(?:\.|!|$)",
    r"\bi cannot stand (.+?)(?:\.|!|$)",
    r"\bi can'?t stand (.+?)(?:\.|!|$)",
    r"\bi am not (?:a fan of|into) (.+?)(?:\.|!|$)",
    r"\bi am averse to (.+?)(?:\.|!|$)",
    r"\bi don'?t care for (.+?)(?:\.|!|$)",
    r"(.+?) is (?:terrible|awful|bad|horrible)(?:\.|!|$)",
]

goal_patterns = [
    r"\bmy goal is (?:to )?(.+?)(?:\.|!|$)",
    r"\bi want to (.+?)(?:\.|!|$)",
    r"\bi wanna  (.+?)(?:\.|!|$)",
    r"\bi plan to (.+?)(?:\.|!|$)",
    r"\bi aim to (.+?)(?:\.|!|$)",
    r"\bmy ambition is (?:to )?(.+?)(?:\.|!|$)",
    r"\bi am working toward(?:s)? (.+?)(?:\.|!|$)",
    r"\bone day i want to (.+?)(?:\.|!|$)",
    r"\bmy dream is to (.+?)(?:\.|!|$)",
    r"\bi hope to (.+?)(?:\.|!|$)",
]

hobby_patterns = [
    r"\bmy hobby is (.+?)(?:\.|!|$)",
    r"\bin my free time,? i (.+?)(?:\.|!|$)",
    r"\bmy pastime is (.+?)(?:\.|!|$)",
    r"\bi love doing (.+?)(?:\.|!|$)",
    r"\bi am into (.+?)(?:\.|!|$)",
    r"\bon weekends,? i (?:like to |enjoy )?(.+?)(?:\.|!|$)",
    r"\bi enjoy (.+?) as a hobby(?:\.|!|$)",
]

fact_patterns = [
   r"\bremember that (.+?)(?:\.|!|$)",
    r"\bjust so you know,? (.+?)(?:\.|!|$)",
    r"\bfyi:? (.+?)(?:\.|!|$)",
    r"\bfor your (?:information|reference),? (.+?)(?:\.|!|$)",
    r"\bkeep in mind (?:that )?(.+?)(?:\.|!|$)",
]

name_patterns = [
    r"\bmy name is (.+?)(?:\.|!|$)",
    r"\bi am (.+?)(?:\.|!|$)",
    r"\bcall me (.+?)(?:\.|!|$)",
    r"\byou can call me (.+?)(?:\.|!|$)",
    r"\beveryone calls me (.+?)(?:\.|!|$)",
    r"\bmy friends call me (.+?)(?:\.|!|$)",
]

# --------------------------------------------------------------------------- #
#   INTELLIGENT MEMORY DETECTOR
# --------------------------------------------------------------------------- #
def detect_and_update_intelligent_memory(
    user_input: str,
    memory: Dict[str, List[str]],
    username: str,
    password: str,
) -> Dict[str, List[str]]:
    """
    Scan *user_input* for any of the known patterns and add the extracted
    values to the appropriate memory bucket (if they are not already there).
    The function also persists the updated memory immediately.
    """
    updated = False

    # Ensure every category key exists – defensive programming.
    for k in ["name", "likes", "dislikes", "hobbies", "goals", "facts"]:
        memory.setdefault(k, [])

    # Mapping of category → list of patterns
    category_map = {
        "likes": like_patterns,
        "dislikes": dislike_patterns,
        "goals": goal_patterns,
        "hobbies": hobby_patterns,
        "facts": fact_patterns,
        "name": name_patterns,
    }

    for category, patterns in category_map.items():
        for pat in patterns:
            m = re.search(pat, user_input, re.IGNORECASE)
            if m:
                value = m.group(1).strip()
                if value and value not in memory.get(category, []):
                    memory[category].append(value)
                    updated = True

    if updated:
        # Persist the new memory immediately so that subsequent calls see it.
        save_memory(memory, username, password)

    return memory

CEREBRAS_API_KEY="csk-hkv2y8efmem6wtxjprdkr366cm8nchwvyxykwetdeemwwtf4"
API_KEY_2="csk-ev4686hht6h32e3cce944vmh8chcjj963fknk64hf4xp6t8e"
BASE_URL="https://api.cerebras.ai"
MODEL_NAME="gpt-oss-120b"
GEMINI_API_KEY = "AIzaSyD3rcef9HlAtZgmDSQIgZ_Bykrlvj9DLsA"