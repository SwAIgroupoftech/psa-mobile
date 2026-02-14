# -------------------------------------------------------------------------
#  core.py – Application logic for PSA
# -------------------------------------------------------------------------
"""
Key change:
-------------
* `get_psa_reply(self, user_input, recent_history=None)` – still returns the
  complete reply (kept for backward compatibility). It now simply joins the
  chunks produced by the streaming call, so the behaviour is identical to the
  old implementation from the caller's point of view.
* `get_psa_stream(self, user_input, recent_history=None)` – NEW.
  Returns a **generator** that yields partial response strings as they arrive
  from the Cerebras API. Use this from the UI to get a word‑by‑word “typing”
  animation.
* `is_file_placeholder` – helper to recognise the `[FILE] …` marker that the
  UI inserts when a user attaches a document or image.
"""

import re
import datetime
from typing import Generator, List, Dict, Optional

from cerebras.cloud.sdk import Cerebras
from users import CEREBRAS_API_KEY

# --------------------------------------------------------------------------- #
#   User‑related helpers (imported from users.py)
# --------------------------------------------------------------------------- #
from users import (
    signup,
    login,
    load_memory as users_load_memory,
    save_memory as users_save_memory,
    detect_and_update_intelligent_memory,
)
from conversations import load_conversation_summary
# --------------------------------------------------------------------------- #
#   Reminder helpers (imported from reminder.py)
# --------------------------------------------------------------------------- #
from reminder import (
    save_reminders as users_save_reminders,
    load_reminders as users_load_reminders,
)
# Web tools import
try:
    from web_tools import (
        search_web, search_and_fetch, 
        format_search_results_for_llm, format_fetched_content_for_llm,
        should_search_web, extract_search_query
    )
    WEB_TOOLS_AVAILABLE = True
except ImportError:
    WEB_TOOLS_AVAILABLE = False
    print("⚠️ web_tools.py not found - web search disabled")
# --------------------------------------------------------------------------- #
#   Core class – independent of any Qt UI
# --------------------------------------------------------------------------- #
class AppCore:
    """Core logic that lives independently of the Qt UI."""

    # ------------------------------------------------------------------- #
    #   Construction / basic state
    # ------------------------------------------------------------------- #
    def __init__(self):
        self.user_id: Optional[str] = None          # same as username – legacy
        self.username: Optional[str] = None
        self.password: str = ""
        self.memories: Dict[str, List[str]] = {}
        self.reminders: List[Dict[str, str]] = []   # {"text":..., "datetime":...}
        self.client = Cerebras(api_key=CEREBRAS_API_KEY)
        self.private_mode : bool = False
        self.current_conv_id: Optional[str] = None

        # NEW flag – controls whether the intelligent‑memory update is performed.
        # It mirrors the UI checkbox “Enable Memory”.
        self.enable_memory_update: bool = True

    def set_current_conversation(self, conv_id: Optional[str]) -> None:
        self.current_conv_id = conv_id
    # ------------------------------------------------------------------- #
    #   PUBLIC method to change the memory‑update flag from the UI
    # ------------------------------------------------------------------- #
    def set_memory_update(self, on: bool) -> None:
        """Called by the UI when the “Enable Memory” checkbox changes."""
        self.enable_memory_update = on

    # ------------------------------------------------------------------- #
    #   AUTHENTICATION
    # ------------------------------------------------------------------- #
    def login(self, username: str, password: str, create_if_missing: bool = False):
        """Log in (or optionally create the account first)."""
        if create_if_missing:
            ok, msg = signup(username, password)
            if not ok:
                return False, msg

        ok, msg = login(username, password)
        if ok:
            self.user_id = username
            self.username = username
            self.password = password
            self.load_user_data()
            return True, msg
        return False, msg

    def logout(self):
        self.user_id = None
        self.username = None
        self.password = ""
        self.memories = {}
        self.reminders = []
        self.private_mode = False

    # ------------------------------------------------------------------- #
    #   PERSISTENCE (memory + reminders)
    # ------------------------------------------------------------------- #
    def load_user_data(self):
        """Load the encrypted user‑memory and reminder list."""
        if self.user_id:
            self.memories = users_load_memory(self.user_id, self.password)
            self.reminders = users_load_reminders(self.user_id)       

    def persist(self):
        """Write memory and reminders back to disk."""
        if self.user_id:
            users_save_memory(self.memories, self.user_id, self.password)
            users_save_reminders(self.user_id, self.reminders)
      
     
    def set_private_mode(self, on: bool):
        self.private_mode = on
    # ------------------------------------------------------------------- #
    #   INTERNAL: build the full message list for the LLM
    # ------------------------------------------------------------------- #
    def _build_message_payload(self,user_input: str,recent_history: Optional[List[Dict[str, str]]] = None,) -> List[Dict[str, str]]:

    # --------------------------------------------------- static system prompt
        memory_context = (
        "You are PSA, Personal Smart Assistant created by Nachiketh. "
        "You are a friendly assistant of user. You have a long term memory "
        "about user. You have a reminder system. You should always be "
        "friendly and personalize the answer based on memory. If it is a "
        "general question not needed to personalize deeply. Always be "
        "supportive to the user. Be emotionally connected to user and act like a human friend. "
        "Do not hallucinate citations. "
        "No need to mention why you are personlizing the answer. "
        "Use the present conversation for context and memory for personalization"
        )

        messages = [{"role": "system", "content": memory_context}]
        # ✅ ALWAYS define first
        
        summary_parts = []
        if self.memories and not self.private_mode:
            memory = []
            for category, values in self.memories.items():
                if values:
                    memory.append(f"{category.upper()}: {', '.join(values)}")
            
            if memory:
                memory_context_str = (
                    "This is what you knwo about user:\n" +
                    "\n".join(memory)
                )
                messages.append({"role": "system", "content": memory_context_str})



        # --------------------------------------------------- conversation summary (current conversation only)
        
        summary = load_conversation_summary(self.user_id)

        if summary:
            topics = summary.get("topics") or []
            if topics:
                summary_parts.append("Topics:\n- " + "\n- ".join(topics))

            crucial = summary.get("crucial_mentions") or []
            messages.append({"role": "system", "content":f"these are crucial mentions about user from past conversations: {crucial}"})


        if summary_parts:
            summary_text = (
            "This is a summary of the current conversation so far. "
            "Use it only for continuity. Do not repeat it explicitly.\n\n"
            + "\n\n".join(summary_parts)
            )

            messages.append(
            {"role": "system", "content": summary_text}
            )
        if recent_history:
            messages.extend(recent_history)

        messages.append({"role":"user","content":user_input})    
        return messages

    # ------------------------------------------------------------------- #
    #   MAIN: non‑streaming version (kept for compatibility)
    # ------------------------------------------------------------------- #
    def get_psa_reply(self,
                      user_input: str,
                      recent_history: Optional[List[Dict[str, str]]] = None) -> str:
        
        # Join all streamed chunks into one string
        return "".join(self.get_psa_stream(user_input, recent_history))

    # ------------------------------------------------------------------- #
    #   NEW: streaming version – yields partial strings
    # ------------------------------------------------------------------- #
    def get_psa_stream(self,
                       user_input: str,
                       recent_history: Optional[List[Dict[str, str]]] = None,
                       ) -> Generator[str, None, None]:
       
        if not self.user_id:
            yield "Error: Not logged in."
            return

        # --------------------------------------------------- intelligent memory update
        # NEW guard – only run if the UI has enabled memory updates.
        if self.enable_memory_update:
            self.memories = detect_and_update_intelligent_memory(
                user_input, self.memories, self.user_id, self.password
            )
            users_save_memory(self.memories, self.user_id, self.password)

        # --------------------------------------------------- reminder shortcut detection
        reminder_match = re.match(
            r"remind me to (.+) on (\d{4}-\d{2}-\d{2}) at (\d{2}:\d{2})",
            user_input,
            re.IGNORECASE,
        )
        if reminder_match:
            text, date, time = reminder_match.groups()
            reminder_time = f"{date} {time}"
            self.reminders.append({"text": text, "datetime": reminder_time})
            users_save_reminders(self.user_id, self.reminders)
            yield f"✅ I’ll remind you to **{text}** on `{date}` at `{time}`."
            return

        # --------------------------------------------------- build payload
        # --------------------------------------------------- web search detection
        web_context = ""
        if WEB_TOOLS_AVAILABLE and should_search_web(user_input):
            yield "🔍 Searching the web...\n\n"
            
            query = extract_search_query(user_input)
            search_data = search_and_fetch(query, fetch_top=2)
            web_context = format_search_results_for_llm(search_data['results'])
            
            if search_data['fetched']:
                web_context += "\n\n" + format_fetched_content_for_llm(search_data['fetched'])
        
        # --------------------------------------------------- build payload
        messages = self._build_message_payload(user_input, recent_history)
        
        # Add web search context if we have it
        if web_context:
            messages.insert(-1, {
                "role": "system",
                "content": f"Web Search Results:\n{web_context}\n\nUse this information to answer the user's question."
            })

        # --------------------------------------------------- stream from LLM
        try:
            stream = self.client.chat.completions.create(
                model="gpt-oss-120b",
                messages=messages,
                stream=True,               # <-- streaming flag
            )
            for chunk in stream:
                # Cerebras (like OpenAI) returns chunk.choices[0].delta.content
                content = getattr(chunk.choices[0].delta, "content", None)
                if content:
                    yield content
        except Exception as e:
            # In the unlikely event streaming fails, fall back to a normal call
            # and still emit something rather than crashing.
            from traceback import format_exc
            yield f"\n❗ Streaming error – falling back to normal completion.\n{format_exc()}"
            try:
                completion = self.client.chat.completions.create(
                    model="gpt-oss-120b",
                    messages=messages,
                )
                reply_md = completion.choices[0].message.content.strip()
                yield reply_md
            except Exception as e2:
                yield f"\n❌ PSA error: {e2}"
                return
    
    # ------------------------------------------------------------------- #
    #   Helper methods for UI display
    # ------------------------------------------------------------------- #
    def get_memory_data_for_display(self) -> Dict[str, List[str]]:
        """Return the full memory dict (used by the UI)."""
        return self.memories

    def get_reminders_for_display(self) -> List[Dict[str, str]]:
        """Return the list of reminder dicts (used by the UI)."""
        return self.reminders

    # ------------------------------------------------------------------- #
    #   Utility – recognise file placeholder inserted by the UI
    # ------------------------------------------------------------------- #
    @staticmethod
    def is_file_placeholder(text: str) -> bool:
        """
        The UI records an attached file as ``[FILE] <absolute‑path>``.
        This helper lets callers know that the message should be treated
        as a file reference rather than normal text.
        """
        return text.startswith("[FILE] ")


# -------------------------------------------------------------------------
#  Reminder daemon launcher (unchanged – kept at the bottom of the file)
# -------------------------------------------------------------------------
import subprocess
import sys
import pathlib
import logging

# Simple logger configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def _resolve_watcher_path() -> Optional[pathlib.Path]:
    """
    Returns the absolute Path to reminder_watcher.py.
    Returns None if the file cannot be located.
    """
    try:
        this_dir = pathlib.Path(__file__).resolve().parent
        watcher = this_dir / "reminder_watcher.py"
        if watcher.is_file():
            return watcher
        logging.error(f"reminder_watcher.py not found at expected location: {watcher}")
        return None
    except Exception:
        logging.exception("Failed to resolve watcher path")
        return None


def start_reminder_service(username: Optional[str]):
    """
    Launches the background reminder daemon (reminder_watcher.py) as a detached process.
    Must be called *after* the user’s username is known.
    """
    if not username:
        logging.error("Cannot start reminder service: username is None or empty.")
        return

    watcher_path = _resolve_watcher_path()
    if not watcher_path:
        # The error is already logged inside _resolve_watcher_path()
        return

    cmd = [sys.executable, str(watcher_path), str(username)]

    try:
        if sys.platform.startswith("win"):
            DETACHED = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            subprocess.Popen(
                cmd,
                creationflags=DETACHED,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            logging.info(f"Started Windows reminder daemon for user '{username}'.")
        else:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
            logging.info(f"Started reminder daemon for user {username} on {sys.platform}.")
    except Exception as exc:
        logging.exception(f"Failed to launch reminder daemon: {exc}")
