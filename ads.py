from openai import OpenAI
import os
from dotenv import load_dotenv

# Načti API key
load_dotenv()
client = OpenAI(api_key=os.getenv("API_OPENAI_KEY"))

# Vstup od uživatele
ico = input("Zadej IČO: ")

# Vytvoř dotaz
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": "Jsi český AI asistent. Když dostaneš IČO, najdeš název a adresu firmy v rejstříku ARES. Pokud to nejde, odpověz, že to neumíš."
        },
        {
            "role": "user",
            "content": f"Zjisti název a adresu firmy podle IČO {ico}."
        }
    ]
)

# Výstup
print("📍 Výsledek:")
print(response.choices[0].message.content)
