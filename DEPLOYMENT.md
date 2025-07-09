# 🚀 Nasazení PDF Data Extractor

## Možnosti nasazení pro klienta

### 1. Streamlit Cloud (DOPORUČUJI)
**Nejjednodušší způsob - zdarma**

1. Nahrajte kód na GitHub
2. Jděte na https://share.streamlit.io
3. Připojte GitHub repozitář
4. Nastavte:
   - Repository: `vase-username/pdf-extractor`
   - Main file: `app_new.py`
5. Klikněte "Deploy"

**Výsledek:** `https://pdf-extractor-XXXX.streamlit.app`

### 2. Heroku
**Populární platforma**

```bash
# Instalace
brew install heroku/brew/heroku

# Nasazení
heroku login
heroku create vase-aplikace
git push heroku main
```

### 3. Railway
**Moderní alternativa**

1. Jděte na https://railway.app
2. Připojte GitHub repozitář
3. Automatické nasazení

## 📁 Potřebné soubory

- ✅ `app_new.py` - Hlavní aplikace
- ✅ `main_extract_new.py` - Extrakce dat
- ✅ `main_fill.py` - Generování dokumentů
- ✅ `requirements.txt` - Závislosti
- ✅ `Procfile` - Pro Heroku
- ✅ `.streamlit/config.toml` - Konfigurace

## 🔧 Funkce aplikace

- 📤 Nahrávání PDF formulářů
- 🔍 Automatická extrakce dat
- 🏢 Dohledávání firem přes ARES API
- 📄 Generování vyplněných dokumentů
- 📥 Stahování výsledků

## 💡 Tipy pro nasazení

1. **Testujte lokálně** před nasazením
2. **Zkontrolujte requirements.txt** - všechny závislosti
3. **Přidejte .gitignore** pro citlivé soubory
4. **Nastavte environment proměnné** pro API klíče

## 🆘 Řešení problémů

**Chyba: Module not found**
- Zkontrolujte `requirements.txt`
- Přidejte chybějící balíčky

**Chyba: Port already in use**
- Změňte port v `Procfile`
- Nebo použijte `$PORT` proměnnou

**Chyba: File not found**
- Zkontrolujte cestu k `app_new.py`
- Ujistěte se, že soubor existuje 