# 🚀 Streamlit PDF Data Extractor

Jednoduchá webová aplikace pro extrakci dat z PDF formulářů a generování Word dokumentů.

## 📋 Instalace

1. **Nainstalujte závislosti:**
```bash
pip install -r requirements.txt
```

2. **Nastavte environment proměnné:**
Vytvořte soubor `.env` s:
```
API_OPENAI_KEY=your_openai_api_key_here
GPT_ASSISTANT_ID=your_assistant_id_here
```

## 🎯 Spuštění aplikace

```bash
streamlit run app.py
```

Aplikace se otevře na `http://localhost:8501`

## 📱 Jak aplikace funguje

### 1. **Nahrání souboru**
- Klikněte na "Browse files" nebo přetáhněte soubor
- **Podporované formáty:**
  - **PDF** (doporučeno) - nejlepší kvalita extrakce
  - **DOCX** - základní podpora
  - **DOC** - omezená podpora
- **Flexibilní názvy** - aplikace přijme jakýkoliv název souboru

### 2. **Automatická extrakce**
- Aplikace automaticky extrahuje data z nahraného souboru
- Zobrazí se progress bar během zpracování
- Data se rozdělí do kategorií (Osobní, Kontakt, Práce, Firma)

### 3. **Editace dat**
- Všechna extrahovaná data můžete upravit
- Data jsou rozdělena do přehledných tabů
- Změny se automaticky uloží

### 4. **Výběr šablony a formátu**
- V sidebaru vyberte Word šablonu
- **Automatické hledání** - aplikace najde všechny .docx soubory
- Podporuje složky: `./` a `./templates/`
- **Výběr výstupního formátu:**
  - **DOCX (Word)** - plná podpora formátování
  - **PDF** - pro tisk a archivaci
  - **TXT (Text)** - jednoduchý text

### 5. **Generování dokumentu**
- Klikněte na "🚀 Vygeneruj dokument"
- Aplikace vyplní šablonu vašimi daty
- **Unikátní názvy** - každý soubor má timestamp a ID
- Dokument si můžete stáhnout ve vybraném formátu

## 🎨 Funkce

- ✅ **Drag & Drop** nahrávání souborů
- ✅ **Flexibilní názvy** - přijme jakýkoliv název souboru
- ✅ **Více vstupních formátů** - PDF, DOCX, DOC
- ✅ **Více výstupních formátů** - DOCX, PDF, TXT
- ✅ **Automatická extrakce** dat
- ✅ **Editace** extrahovaných dat
- ✅ **Automatické hledání** šablon
- ✅ **Unikátní názvy** výstupních souborů
- ✅ **Organizované složky** - data/, output/, templates/
- ✅ **Progress bars** pro zpracování
- ✅ **Stažení** výsledného dokumentu
- ✅ **Responsivní design**

## 📁 Struktura složek

```
csob/
├── app.py              # Streamlit aplikace
├── main_extract.py     # Extrakce dat z PDF
├── main_fill.py        # Vyplňování dokumentů
├── templates/          # Word šablony
│   ├── pop_jmeno.docx
│   └── vyplnena.docx
├── output/             # Vygenerované dokumenty
│   ├── vyplneny_dokument_YYYYMMDD_HHMMSS_XXXX.docx
│   ├── vyplneny_dokument_YYYYMMDD_HHMMSS_XXXX.pdf
│   └── vyplneny_dokument_YYYYMMDD_HHMMSS_XXXX.txt
├── data/               # Extrahovaná data
│   └── data_YYYYMMDD_HHMMSS.json
└── requirements.txt    # Python závislosti
```

## 🔧 Konfigurace

### API klíče
V sidebaru můžete nastavit:
- **OpenAI API Key** - pro AI funkce
- **Assistant ID** - pro AI asistenta

### Šablony
Přidejte vlastní Word šablony:
- **Složka `templates/`** - doporučené umístění
- **Kořenová složka** - také podporované
- Používejte placeholder `((nazev_pole))` pro vkládání dat
- Dostupné pole: `jmeno`, `prijmeni`, `ico`, `firma_nazev`, atd.

### Názvy souborů
Aplikace je **flexibilní s názvy**:
- **Vstupní soubory** - jakýkoliv název (PDF, DOCX, DOC)
- **Šablony** - jakýkoliv název .docx
- **Výstupní soubory** - automaticky generované unikátní názvy
- **Data soubory** - automaticky generované s timestampem

## 📋 Doporučení pro typy souborů

### **Vstupní soubory:**
- **PDF** (doporučeno) - nejlepší kvalita extrakce, zachovává formátování
- **DOCX** - základní podpora, omezená extrakce
- **DOC** - omezená podpora, starší formát

### **Výstupní soubory:**
- **DOCX (Word)** - plná podpora formátování, editovatelný
- **PDF** - pro tisk a archivaci, neměnný formát
- **TXT (Text)** - jednoduchý text, univerzální kompatibilita

### **Šablony:**
- **DOCX** - jediný podporovaný formát pro šablony
- Používejte placeholder `((nazev_pole))` pro vkládání dat

## 🚀 Deployment

### Lokální spuštění
```bash
streamlit run app.py
```

### Cloud deployment
Aplikaci můžete nasadit na:
- **Streamlit Cloud** (zdarma)
- **Heroku**
- **Google Cloud Run**
- **AWS**

## 🐛 Řešení problémů

### Chyba: "Module not found"
```bash
pip install -r requirements.txt
```

### Chyba: "PDF cannot be read"
- Zkontrolujte, že PDF není poškozené
- Zkuste jiný PDF soubor
- **Název souboru nezáleží** - aplikace přijme jakýkoliv název

### Chyba: "Template not found"
- Přidejte Word šablony do složky `templates/`
- Nebo do kořenové složky projektu
- Zkontrolujte, že soubory mají příponu `.docx`

### Chyba: "Output directory not found"
- Aplikace automaticky vytvoří složky `output/`, `data/`, `templates/`
- Zkontrolujte oprávnění k zápisu

## 📞 Podpora

Pro technickou podporu kontaktujte vývojáře. 