import os
import time
from dotenv import load_dotenv
from openai import OpenAI

# 1. Načti proměnné z .env
load_dotenv()
api_key = os.getenv("API_OPENAI_KEY")
assistant_id = os.getenv("GPT_ASSISTANT_ID")

if not api_key or not assistant_id:
    raise ValueError("Chybí API_OPENAI_KEY nebo GPT_ASSISTANT_ID v .env")

client = OpenAI(api_key=api_key)

# 2. Vytvoř thread (vlákno)
thread = client.beta.threads.create()

# 3. Přidej uživatelský dotaz
ico = "02405873"  # Lze změnit na libovolné IČO
user_message = f"Zjisti název a adresu firmy nebo OSVČ podle IČO {ico}. Najdi na internetu, ne v ARES."
client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content=user_message
)

# 4. Spusť asistenta
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant_id
)

# 5. Počkej na odpověď
while True:
    run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    if run_status.status == "completed":
        break
    elif run_status.status in ["failed", "cancelled"]:
        raise Exception(f"Run failed with status: {run_status.status}")
    time.sleep(1)

# 6. Získej odpověď asistenta (pouze textové bloky)
messages = client.beta.threads.messages.list(thread_id=thread.id)
latest = messages.data[0]
for content in latest.content:
    if getattr(content, "type", None) == "text":
        print("🧠 Odpověď asistenta:\n", content.text.value)
