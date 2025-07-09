import streamlit as st
import json
import os
import tempfile
from pathlib import Path
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd

# Import nového extraktoru
from main_extract_new import PDFExtractor
from main_fill import fill_document

# =============================================================================
# KONFIGURACE A POMOCNÉ FUNKCE
# =============================================================================

class AppConfig:
    """Konfigurace aplikace"""
    
    # Podporované formáty
    SUPPORTED_FORMATS = {
        "DOCX (Word)": {
            "extension": ".docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        },
        "PDF": {
            "extension": ".pdf", 
            "mime_type": "application/pdf"
        },
        "TXT (Text)": {
            "extension": ".txt",
            "mime_type": "text/plain"
        }
    }
    
    # Složky
    DIRECTORIES = ["output", "data", "templates"]
    
    # Stavové zprávy
    MESSAGES = {
        "success": "✅",
        "error": "❌", 
        "warning": "⚠️",
        "info": "ℹ️",
        "loading": "🔄"
    }

class FileManager:
    """Správa souborů a složek"""
    
    @staticmethod
    def ensure_directories():
        """Vytvoří potřebné složky"""
        for directory in AppConfig.DIRECTORIES:
            Path(directory).mkdir(exist_ok=True)
    
    @staticmethod
    def get_template_files() -> list:
        """Získá seznam dostupných šablon"""
        template_files = []
        current_dir = Path(".")
        
        # Hledej v aktuálním adresáři
        for file in current_dir.glob("*.docx"):
            if not file.name.startswith("~$"):
                template_files.append(file.name)
        
        # Hledej v podsložce templates/
        templates_dir = current_dir / "templates"
        if templates_dir.exists():
            for file in templates_dir.glob("*.docx"):
                if not file.name.startswith("~$"):
                    template_files.append(str(file))
        
        return template_files
    
    @staticmethod
    def generate_unique_filename(prefix: str = "dokument", format_type: str = "DOCX (Word)") -> str:
        """Generuje unikátní název souboru"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        extension = AppConfig.SUPPORTED_FORMATS[format_type]["extension"]
        return f"{prefix}_{timestamp}_{unique_id}{extension}"
    
    @staticmethod
    def get_mime_type(format_type: str) -> str:
        """Vrací MIME typ pro daný formát"""
        return AppConfig.SUPPORTED_FORMATS[format_type]["mime_type"]

class DataProcessor:
    """Zpracování a validace dat"""
    
    @staticmethod
    def process_uploaded_file(uploaded_file) -> Optional[Dict[str, Any]]:
        """Zpracuje nahraný soubor a vrátí extrahovaná data"""
        if not uploaded_file:
            return None
        
        try:
            # Uložení nahraného souboru
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                pdf_path = tmp_file.name
            
            # Extrakce dat
            extractor = PDFExtractor(pdf_path)
            extracted_data = extractor.extract_all_data()
            
            # Vyčištění dočasného souboru
            os.unlink(pdf_path)
            
            return {
                "personal_info": extracted_data.personal_info,
                "company_info": extracted_data.company_info,
                "raw_text": extracted_data.raw_text,
                "table_data": extracted_data.table_data,
                "table_df": extractor.get_dataframe()
            }
            
        except Exception as e:
            st.error(f"{AppConfig.MESSAGES['error']} Chyba při zpracování: {str(e)}")
            return None
    
    @staticmethod
    def save_data_to_json(data: Dict[str, Any], filename: str = "data.json"):
        """Uloží data do JSON souboru"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"{AppConfig.MESSAGES['error']} Chyba při ukládání: {str(e)}")
            return False

class UIComponents:
    """UI komponenty pro aplikaci"""
    
    @staticmethod
    def render_sidebar():
        """Vykreslí sidebar s nastavením"""
        with st.sidebar:
            st.header("⚙️ Nastavení")
            
            # API klíče
            openai_key = st.text_input("OpenAI API Key", type="password")
            assistant_id = st.text_input("Assistant ID")
            
            # Výstupní formát
            st.subheader("📄 Výstupní formát")
            output_format = st.selectbox(
                "Formát výstupního dokumentu",
                list(AppConfig.SUPPORTED_FORMATS.keys()),
                help="Vyberte formát pro vygenerovaný dokument"
            )
            
            # Šablony
            st.subheader("📋 Šablony")
            template_files = FileManager.get_template_files()
            
            if template_files:
                selected_template = st.selectbox(
                    "Vyberte šablonu", 
                    template_files,
                    help="Vyberte Word šablonu pro vyplnění"
                )
            else:
                st.warning(f"{AppConfig.MESSAGES['warning']} Nebyly nalezeny žádné Word šablony")
                st.info("Přidejte .docx soubory do složky projektu")
                selected_template = None
            
            return {
                "openai_key": openai_key,
                "assistant_id": assistant_id,
                "output_format": output_format,
                "selected_template": selected_template
            }
    
    @staticmethod
    def render_file_upload():
        """Vykreslí sekci pro nahrání souboru"""
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.header("📤 Nahrání souboru")
            
            uploaded_file = st.file_uploader(
                "Nahrajte formulář",
                type=['pdf', 'docx', 'doc'],
                help="Podporované formáty: PDF (doporučeno), DOCX, DOC"
            )
            
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
                st.success(f"{AppConfig.MESSAGES['success']} Soubor nahraný")
                st.info(f"Název: {uploaded_file.name}")
                st.info(f"Typ: {uploaded_file.type}")
                st.info(f"Velikost: {uploaded_file.size / 1024:.1f} KB")
                
                if uploaded_file.type != "application/pdf":
                    st.warning(f"{AppConfig.MESSAGES['warning']} Pro nejlepší výsledky použijte PDF formát")
            else:
                st.warning("⏳ Čekám na nahrání souboru")
        
        return uploaded_file
    
    @staticmethod
    def render_extraction_results(data: Dict[str, Any]):
        """Vykreslí výsledky extrakce"""
        if not data:
            return
        
        # Tabulka s daty
        if not data["table_df"].empty:
            st.header("📋 Extrahovaná tabulka z PDF")
            st.table(data["table_df"])
        else:
            st.info("Tabulka nebyla v dokumentu rozpoznána nebo je prázdná.")
        
        # Stáhnutí JSON
        st.markdown("---")
        st.subheader("📥 Stáhnout extrahovaná data")
        st.download_button(
            label="Stáhnout JSON",
            data=json.dumps(data["personal_info"], ensure_ascii=False, indent=2),
            file_name="extrahovana_data.json",
            mime="application/json"
        )
        
        # Debug informace
        with st.expander("📝 Zobrazit extrahovaný text z PDF", expanded=False):
            st.code(data["raw_text"], language="text")
        
        if data["company_info"]:
            with st.expander("🏢 Informace o firmě z ARES API", expanded=False):
                st.json(data["company_info"])
    
    @staticmethod
    def render_document_generation(settings: Dict[str, Any], data: Dict[str, Any]):
        """Vykreslí sekci pro generování dokumentu"""
        st.markdown("---")
        st.header("📄 Generování dokumentu")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if settings["selected_template"]:
                st.info(f"Použije se šablona: **{settings['selected_template']}**")
            else:
                st.error(f"{AppConfig.MESSAGES['error']} Nebyla vybrána šablona")
        
        with col2:
            if st.button("🚀 Vygeneruj dokument", type="primary", disabled=not settings["selected_template"]):
                UIComponents.generate_document(settings, data)
    
    @staticmethod
    def generate_document(settings: Dict[str, Any], data: Dict[str, Any]):
        """Vygeneruje dokument"""
        with st.spinner("Generuji dokument..."):
            try:
                # Uložení dat
                data_filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                data_path = Path("data") / data_filename
                
                if not DataProcessor.save_data_to_json(data["personal_info"], str(data_path)):
                    return
                
                # Generování výstupního souboru
                output_filename = FileManager.generate_unique_filename(
                    "vyplneny_dokument", 
                    settings["output_format"]
                )
                output_path = Path("output") / output_filename
                
                # Generování dokumentu
                generated_path = fill_document(settings["selected_template"], str(output_path))
                
                st.success(f"{AppConfig.MESSAGES['success']} Dokument vygenerován!")
                st.info(f"Výstupní soubor: {output_filename}")
                
                # Stáhnutí
                if os.path.exists(generated_path):
                    with open(generated_path, "rb") as file:
                        st.download_button(
                            label="📥 Stáhnout dokument",
                            data=file.read(),
                            file_name=output_filename,
                            mime=FileManager.get_mime_type(settings["output_format"])
                        )
                else:
                    st.error(f"{AppConfig.MESSAGES['error']} Soubor nebyl vytvořen")
                    
            except Exception as e:
                st.error(f"{AppConfig.MESSAGES['error']} Chyba při generování: {str(e)}")

# =============================================================================
# HLAVNÍ APLIKACE
# =============================================================================

def main():
    """Hlavní funkce aplikace"""
    
    # Konfigurace stránky
    st.set_page_config(
        page_title="PDF Data Extractor",
        page_icon="📄",
        layout="wide"
    )
    
    # Hlavní nadpis
    st.title("📄 PDF Data Extractor")
    st.markdown("---")
    
    # Vytvoření složek
    FileManager.ensure_directories()
    
    # Vykreslení sidebar
    settings = UIComponents.render_sidebar()
    
    # Vykreslení nahrání souboru
    uploaded_file = UIComponents.render_file_upload()
    
    # Zpracování nahraného souboru
    if uploaded_file:
        st.markdown("---")
        
        with st.spinner(f"{AppConfig.MESSAGES['loading']} Extrahuji data z PDF..."):
            data = DataProcessor.process_uploaded_file(uploaded_file)
            
            if data:
                st.success(f"{AppConfig.MESSAGES['success']} Data úspěšně extrahována!")
                
                # Uložení dat pro main_fill.py
                DataProcessor.save_data_to_json(data["personal_info"], "data.json")
                
                # Vykreslení výsledků
                UIComponents.render_extraction_results(data)
                
                # Generování dokumentu
                UIComponents.render_document_generation(settings, data)
            else:
                st.error(f"{AppConfig.MESSAGES['error']} Nepodařilo se extrahovat data")
    
    # Footer
    st.markdown("---")
    st.markdown("*Vytvořeno s ❤️ pomocí Streamlit*")

if __name__ == "__main__":
    main() 