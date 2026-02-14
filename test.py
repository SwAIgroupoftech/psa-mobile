from core import AppCore
from conversations import load_conversation_summary

# Initialize
core = AppCore()

# Login (replace with your username/password)
core.login("Nachiketh", "naresh76", create_if_missing=True)

# Set a conversation ID
core.set_current_conversation("20260109193045")

# Simulate adding crucial mentions to DB
# (In real use, this happens automatically via create_conversation_summary)

# Test: Check if crucial mentions are loaded
summary = load_conversation_summary("Nachiketh")
if summary:
    print("✅ Summary loaded:")
    print(f"  Topics: {summary.get('topics')}")
    print(f"  Crucial: {summary.get('crucial_mentions')}")
else:
    print("⚠️ No summary found")

# Test: Build message payload
messages = core._build_message_payload("How are you?")

# Print system prompt
print("\n" + "="*80)
print("SYSTEM PROMPT:")
print("="*80)
print(messages[0]['content'])
print("="*80)
print(messages[1]['content'])
print("="*80)