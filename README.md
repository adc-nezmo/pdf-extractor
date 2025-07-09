# PDF Data Extractor s AI Agentem

Tento skript extrahuje data z PDF formuláře a dohledává informace o firmách podle IČO pomocí AI agenta.

## Instalace

1. Nainstalujte závislosti:
```bash
pip install -r requirements.txt
```

2. Vytvořte soubor `.env` s následujícím obsahem:
```
API_OPENAI_KEY=your_openai_api_key_here
GPT_ASSISTANT_ID=your_assistant_id_here
```

## Nastavení

1. **Získejte OpenAI API klíč** na https://platform.openai.com/api-keys

2. **Vytvořte asistenta** spuštěním:
```bash
python create_assistant.py
```

3. **Zkopírujte ID asistenta** z výstupu a vložte ho do `.env` souboru

## Použití

Spusťte skript pro extrakci dat z PDF:
```bash
python main_extract.py
```

Skript:
- Extrahuje text z `zadost.pdf`
- Parsuje osobní údaje (jméno, adresa, IČO, atd.)
- Dohledá informace o firmě podle IČO pomocí AI agenta
- Uloží všechna data do `data.json`

## Struktura dat

Výstupní JSON obsahuje:
- Osobní údaje (jméno, příjmení, rodné číslo, adresa)
- Kontaktní údaje (telefon, email)
- Pracovní údaje (povolání, IČO zaměstnavatele)
- Finanční údaje (čistý příjem, měsíční náklady)
- Informace o firmě (název, adresa, status, obor podnikání)

## Soubory

- `main_extract.py` - Hlavní skript pro extrakci dat
- `create_assistant.py` - Vytvoření AI asistenta
- `run_query.py` - Testovací skript pro AI agenta
- `requirements.txt` - Python závislosti
- `zadost.pdf` - Vstupní PDF formulář
- `data.json` - Výstupní data 