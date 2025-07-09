import streamlit as st
import json
import os
import tempfile
from pathlib import Path
import shutil
import uuid
from datetime import datetime
from main_extract_new import PDFExtractor
from main_fill import fill_document
import pandas as pd

# Konfigurace stránky
st.set_page_config(
    page_title="PDF Data Extractor",
    page_icon="📄",
    layout="wide"
)

# Hlavní nadpis
st.title("📄 PDF Data Extractor")
st.markdown("---")

# Funkce pro generování unikátních názvů souborů
def generate_unique_filename(prefix="dokument", format_type="docx"):
    """Generuje unikátní název souboru s timestampem"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    # Mapování formátů na přípony
    format_extensions = {
        "DOCX (Word)": ".docx",
        "PDF": ".pdf", 
        "TXT (Text)": ".txt"
    }
    
    extension = format_extensions.get(format_type, ".docx")
    return f"{prefix}_{timestamp}_{unique_id}{extension}"

def get_mime_type(format_type):
    """Vrací MIME typ pro daný formát"""
    mime_types = {
        "DOCX (Word)": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "PDF": "application/pdf",
        "TXT (Text)": "text/plain"
    }
    return mime_types.get(format_type, "application/octet-stream")

def get_template_files():
    """Získá seznam všech dostupných Word šablon"""
    current_dir = Path(".")
    template_files = []
    
    # Hledej v aktuálním adresáři
    for file in current_dir.glob("*.docx"):
        if not file.name.startswith("~$"):  # Ignoruj dočasné soubory
            template_files.append(file.name)
    
    # Hledej v podsložce templates/ pokud existuje
    templates_dir = current_dir / "templates"
    if templates_dir.exists():
        for file in templates_dir.glob("*.docx"):
            if not file.name.startswith("~$"):
                template_files.append(str(file))
    
    return template_files

def ensure_directories():
    """Vytvoří potřebné složky pokud neexistují"""
    directories = ["output", "data", "templates"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

# Volání až po definici funkce
ensure_directories()

# Sidebar pro nastavení
with st.sidebar:
    st.header("⚙️ Nastavení")
    
    # API klíče
    openai_key = st.text_input("OpenAI API Key", type="password")
    assistant_id = st.text_input("Assistant ID")
    
    # Výstupní formát
    st.subheader("📄 Výstupní formát")
    output_format = st.selectbox(
        "Formát výstupního dokumentu",
        ["DOCX (Word)", "PDF", "TXT (Text)"],
        help="Vyberte formát pro vygenerovaný dokument"
    )
    
    # Šablony
    st.subheader("📋 Šablony")
    template_files = get_template_files()
    
    if template_files:
        selected_template = st.selectbox(
            "Vyberte šablonu", 
            template_files,
            help="Vyberte Word šablonu pro vyplnění"
        )
    else:
        st.warning("⚠️ Nebyly nalezeny žádné Word šablony")
        st.info("Přidejte .docx soubory do složky projektu")
        selected_template = None

# Hlavní obsah
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📤 Nahrání souboru")
    
    # File uploader s rozšířenou podporou
    uploaded_file = st.file_uploader(
        "Nahrajte formulář",
        type=['pdf', 'docx', 'doc'],
        help="Podporované formáty: PDF (doporučeno), DOCX, DOC"
    )
    
    # Informace o formátech
    if not uploaded_file:
        st.info("""
        **📋 Podporované formáty:**
        - **PDF** (doporučeno) - nejlepší kvalita extrakce
        - **DOCX** - základní podpora
        - **DOC** - omezená podpora
        """)

with col2:
    st.header("📊 Status")
    if uploaded_file:
        st.success("✅ Soubor nahraný")
        st.info(f"Název: {uploaded_file.name}")
        st.info(f"Typ: {uploaded_file.type}")
        st.info(f"Velikost: {uploaded_file.size / 1024:.1f} KB")
        
        # Varování pro ne-PDF soubory
        if uploaded_file.type != "application/pdf":
            st.warning("⚠️ Pro nejlepší výsledky použijte PDF formát")
    else:
        st.warning("⏳ Čekám na nahrání souboru")

# Zpracování po nahrání
if uploaded_file:
    st.markdown("---")
    
    # Progress bar
    with st.spinner("🔍 Extrahuji data z PDF..."):
        # Uložení nahraného souboru
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            pdf_path = tmp_file.name
        
        # Extrakce dat pomocí nového skriptu
        try:
            extractor = PDFExtractor(pdf_path)
            extracted_data = extractor.extract_all_data()
            
            # Rozdělení dat pro kompatibilitu
            data = extracted_data.personal_info
            extracted_text = extracted_data.raw_text
            ares_response = extracted_data.company_info
            table_df = extractor.get_dataframe()
            alias_dict = extracted_data.personal_info  # Použijeme personal_info jako alias_dict
            json_rows = extracted_data.table_data
            
            st.success("✅ Data úspěšně extrahována!")
            # Ulož data do data.json pro main_fill.py
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(alias_dict, f, ensure_ascii=False, indent=2)
            # Vyčištění dočasného souboru
            os.unlink(pdf_path)
        except Exception as e:
            st.error(f"❌ Chyba při extrakci: {str(e)}")
            data, extracted_text, ares_response, table_df, alias_dict, json_rows = { }, "", None, pd.DataFrame(), { }, [ ]

    # Po extrakci dat (např. data, text, ares_response, table_df = ...)
    if not table_df.empty:
        st.header("📋 Extrahovaná tabulka z PDF")
        st.table(table_df)
    else:
        st.info("Tabulka nebyla v dokumentu rozpoznána nebo je prázdná.")

    # Možnost stáhnout nový JSON (list slovníků)
    st.markdown("---")
    st.subheader("📥 Stáhnout extrahovaný JSON (list slovníků)")
    st.download_button(
        label="Stáhnout JSON",
        data=json.dumps(json_rows, ensure_ascii=False, indent=2),
        file_name="extrahovana_data.json",
        mime="application/json"
    )
    
    # Debug: Zobrazení extrahovaného textu
    with st.expander("📝 Zobrazit extrahovaný text z PDF", expanded=False):
        st.code(extracted_text, language="text")
    
    # Debug: Zobrazení odpovědi z ARES API
    if ares_response:
        with st.expander("🏢 Odpověď z ARES API", expanded=False):
            st.json(ares_response)
    
    # Generování dokumentu
    st.markdown("---")
    st.header("📄 Generování dokumentu")
    
    col_gen1, col_gen2 = st.columns([3, 1])
    
    with col_gen1:
        if selected_template:
            st.info(f"Použije se šablona: **{selected_template}**")
        else:
            st.error("❌ Nebyla vybrána šablona")
    
    with col_gen2:
        if st.button("🚀 Vygeneruj dokument", type="primary", disabled=not selected_template):
            with st.spinner("Generuji dokument..."):
                try:
                    # Generování unikátního názvu pro data.json
                    data_filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    data_path = Path("data") / data_filename
                    
                    # Uložení editovaných dat
                    with open(data_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    # Generování unikátního názvu pro výstupní soubor
                    output_filename = generate_unique_filename("vyplneny_dokument", output_format)
                    output_path = Path("output") / output_filename
                    
                    # Generování dokumentu s novým názvem
                    generated_path = fill_document(selected_template, str(output_path))
                    
                    st.success("✅ Dokument vygenerován!")
                    st.info(f"Výstupní soubor: {output_filename}")
                    
                    # Stáhnutí
                    if os.path.exists(generated_path):
                        with open(generated_path, "rb") as file:
                            st.download_button(
                                label="📥 Stáhnout dokument",
                                data=file.read(),
                                file_name=output_filename,
                                mime=get_mime_type(output_format)
                            )
                    else:
                        st.error("❌ Soubor nebyl vytvořen")
                        
                except Exception as e:
                    st.error(f"❌ Chyba při generování: {str(e)}")

# Footer
st.markdown("---")
st.markdown("*Vytvořeno s ❤️ pomocí Streamlit*") 