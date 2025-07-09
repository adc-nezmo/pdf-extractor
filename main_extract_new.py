import pdfplumber
import re
import json
import requests
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Načti environment proměnné
load_dotenv()

@dataclass
class ExtractedData:
    """Datová třída pro extrahovaná data"""
    personal_info: Optional[Dict[str, str]] = None
    company_info: Optional[Dict[str, str]] = None
    raw_text: str = ""
    table_data: Optional[List[Dict[str, str]]] = None
    
    def __post_init__(self):
        if self.personal_info is None:
            self.personal_info = {}
        if self.company_info is None:
            self.company_info = {}
        if self.table_data is None:
            self.table_data = []

class PDFExtractor:
    """Hlavní třída pro extrakci dat z PDF formulářů"""
    
    def __init__(self, pdf_file: str):
        self.pdf_file = pdf_file
        self.text = ""
        self.extracted_data = ExtractedData()
        
        # Definice polí pro extrakci
        self.field_definitions = {
            "Příjmení/Jméno": {
                "keys": ["prijmeni", "jmeno"],
                "pattern": r"Příjmení/Jméno\s+([A-Za-zÁ-Žá-ž\- ]+)",
                "processor": self._split_name
            },
            "Rodné číslo/Datum narození": {
                "keys": ["rodne_cislo", "datum_narozeni"],
                "pattern": r"Rodné číslo/Datum narození\s+([0-9]{9,10})\s+([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{4})",
                "processor": self._split_rc_date
            },
            "Místo narození: město/stát": {
                "keys": ["misto_narozeni_mesto", "misto_narozeni_stat"],
                "pattern": r"Místo narození: město/stát\s+([A-Za-z0-9 .\-]+)\s+([A-Za-z ]+)",
                "processor": self._split_city_state
            },
            "Pohlaví/Státní občanství": {
                "keys": ["pohlavi", "statni_obcanstvi"],
                "pattern": r"Pohlaví/Státní občanství\s+([a-zA-Zěščřžýáíéúůó ]+)\s+([a-zA-ZěščřžýáíéúůóĚŠČŘŽÝÁÍÉÚŮÓ ]+)",
                "processor": self._split_gender_citizenship
            },
            "Telefon/E-mail": {
                "keys": ["telefon", "email"],
                "pattern": r"Telefon/E-mail\s+([0-9 ]+)\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
                "processor": self._split_phone_email
            },
            "IČO zaměstnavatele nebo OSVČ": {
                "keys": ["ico"],
                "pattern": r"IČO zaměstnavatele nebo OSVČ\s+([0-9]{8})",
                "processor": lambda x: x
            },
            "Čistý příjem": {
                "keys": ["cisty_prijem"],
                "pattern": r"Čistý příjem\s+([0-9\.,]+)",
                "processor": self._normalize_number
            },
            "Měsíční životní náklady": {
                "keys": ["mesicni_naklady"],
                "pattern": r"Měsíční životní náklady.*?([0-9\.,]+)",
                "processor": self._normalize_number
            },
            "Datum nástupu": {
                "keys": ["datum_nastupu"],
                "pattern": r"Datum nástupu do zaměstnání nebo zahájení podnikání\s+([0-9]{2}\.[0-9]{2}\.[0-9]{4})",
                "processor": lambda x: x
            },
            "Nejvyšší dosažené vzdělání": {
                "keys": ["nejvyssi_vzdelani"],
                "pattern": r"Nejvyšší dosažené vzdělání\s+[0-9]+\s+([A-Za-zěščřžýáíéúůóĚŠČŘŽÝÁÍÉÚŮÓ ]+)",
                "processor": lambda x: x.strip()
            },
            "Povolání/Ekonomický sektor": {
                "keys": ["povolani"],
                "pattern": r"Povolání/Ekonomický sektor\s+([A-Za-zěščřžýáíéúůóĚŠČŘŽÝÁÍÉÚŮÓ, ]+)",
                "processor": lambda x: x.strip()
            }
        }
    
    def extract_text_from_pdf(self) -> str:
        """Extrahuje text z PDF souboru"""
        text = ""
        try:
            with pdfplumber.open(self.pdf_file) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
            
            # Ulož extrahovaný text pro debugování
            with open("extrahovany_text.txt", "w", encoding="utf-8") as f:
                f.write(text)
            
            print("✅ Text úspěšně extrahován z PDF")
            return text
        except Exception as e:
            print(f"❌ Chyba při extrakci textu: {e}")
            return ""
    
    def _split_name(self, full_name: str) -> Tuple[str, str]:
        """Rozdělí celé jméno na příjmení a jméno"""
        parts = full_name.strip().split()
        if len(parts) >= 2:
            return parts[0], " ".join(parts[1:])
        elif len(parts) == 1:
            return parts[0], ""
        return "", ""
    
    def _split_rc_date(self, match) -> Tuple[str, str]:
        """Rozdělí rodné číslo a datum narození"""
        return match.group(1), match.group(2)
    
    def _split_city_state(self, match) -> Tuple[str, str]:
        """Rozdělí město a stát narození"""
        return match.group(1).strip(), match.group(2).strip()
    
    def _split_gender_citizenship(self, match) -> Tuple[str, str]:
        """Rozdělí pohlaví a státní občanství"""
        return match.group(1).strip(), match.group(2).strip()
    
    def _split_phone_email(self, match) -> Tuple[str, str]:
        """Rozdělí telefon a email"""
        phone = match.group(1).replace(" ", "")
        email = match.group(2)
        return phone, email
    
    def _normalize_number(self, number_str: str) -> str:
        """Normalizuje číselné hodnoty (odstraní mezery, převede čárky na tečky)"""
        return number_str.replace(".", "").replace(",", ".")
    
    def extract_personal_data(self) -> Dict[str, str]:
        """Extrahuje osobní data pomocí regex patternů"""
        personal_data = {}
        
        for field_name, field_def in self.field_definitions.items():
            pattern = field_def["pattern"]
            keys = field_def["keys"]
            processor = field_def["processor"]
            
            match = re.search(pattern, self.text)
            if match:
                if len(keys) == 1:
                    # Jedna hodnota
                    value = processor(match.group(1))
                    personal_data[keys[0]] = value
                elif len(keys) == 2:
                    # Dvě hodnoty
                    if processor == self._split_name:
                        value1, value2 = processor(match.group(1))
                    elif processor == self._split_rc_date:
                        value1, value2 = processor(match)
                    elif processor == self._split_city_state:
                        value1, value2 = processor(match)
                    elif processor == self._split_gender_citizenship:
                        value1, value2 = processor(match)
                    elif processor == self._split_phone_email:
                        value1, value2 = processor(match)
                    else:
                        value1, value2 = match.group(1), match.group(2)
                    
                    personal_data[keys[0]] = value1
                    personal_data[keys[1]] = value2
        
        return personal_data
    
    def extract_table_data(self) -> List[Dict[str, str]]:
        """Extrahuje data z tabulky pomocí strukturovaného přístupu"""
        table_data = []
        lines = self.text.split('\n')
        in_table = False
        
        for line in lines:
            # Najdi začátek tabulky
            if 'I. Osobní údaje žadatele' in line:
                in_table = True
                continue
            
            if in_table:
                # Konec tabulky
                if line.strip() == '' or re.match(r'II\.', line):
                    break
                
                # Rozdělení na části
                parts = re.split(r'\s{2,}|\t', line)
                parts = [p.strip() for p in parts if p.strip()]
                
                if len(parts) >= 2:
                    label = parts[0]
                    value1 = parts[1] if len(parts) > 1 else ''
                    value2 = parts[2] if len(parts) > 2 else ''
                    
                    # Přidej do tabulky
                    if value1:
                        table_data.append({'Pole': label, 'Hodnota': value1})
                    if value2:
                        table_data.append({'Pole': f"{label} (2)", 'Hodnota': value2})
        
        return table_data
    
    def get_company_info_via_ares(self, ico: str) -> Dict[str, str]:
        """Dohledá informace o firmě podle IČO pomocí ARES API"""
        if not ico or len(ico) != 8:
            print(f"⚠️ Neplatné IČO: {ico}")
            return {
                "ico": ico,
                "firma_nazev": "",
                "firma_sidlo": "",
                "status": "",
                "typ_subjektu": "",
                "obor_podnikani": ""
            }
        
        try:
            print(f"🔍 Dohledávám informace o firmě s IČO: {ico}")
            
            url = f"https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                company_info = {
                    "ico": ico,
                    "firma_nazev": data.get('obchodniJmeno', ''),
                    "firma_sidlo": self._format_address(data.get('sidlo', {})),
                    "status": data.get('stav', ''),
                    "typ_subjektu": data.get('pravniForma', ''),
                    "obor_podnikani": self._get_business_field(data)
                }
                
                print(f"✅ Informace o firmě dohledány: {company_info['firma_nazev']}")
                return company_info
                
            elif response.status_code == 404:
                print(f"❌ Firma s IČO {ico} nebyla nalezena v ARES")
                return {
                    "ico": ico,
                    "firma_nazev": "",
                    "firma_sidlo": "",
                    "status": "Nenalezeno",
                    "typ_subjektu": "",
                    "obor_podnikani": ""
                }
            else:
                print(f"❌ Chyba při dotazu na ARES: HTTP {response.status_code}")
                return {
                    "ico": ico,
                    "firma_nazev": "",
                    "firma_sidlo": "",
                    "status": f"Chyba HTTP {response.status_code}",
                    "typ_subjektu": "",
                    "obor_podnikani": ""
                }
                
        except Exception as e:
            print(f"❌ Chyba při dohledávání firmy: {e}")
            return {
                "ico": ico,
                "firma_nazev": "",
                "firma_sidlo": "",
                "status": "Chyba připojení",
                "typ_subjektu": "",
                "obor_podnikani": ""
            }
    
    def _format_address(self, sidlo: Dict) -> str:
        """Formátuje adresu sídla firmy"""
        if not sidlo:
            return ""
        
        ulice = str(sidlo.get('ulice', ''))
        cislo = str(sidlo.get('cisloDomovni', ''))
        cast_obce = str(sidlo.get('castObce', ''))
        obec = str(sidlo.get('obec', ''))
        psc = str(sidlo.get('psc', ''))
        textova_adresa = str(sidlo.get('textovaAdresa', ''))
        
        if not ulice and textova_adresa:
            # Použij textovou adresu a naformátuj PSČ
            return re.sub(r"(\b\d{3})(\d{2}\b)", r"\1 \2", textova_adresa)
        
        adresa_parts = []
        if ulice:
            adresa_parts.append(ulice)
            if cislo:
                adresa_parts.append(cislo)
        elif cislo:
            adresa_parts.append(cislo)
        
        if psc:
            if len(psc) == 5:
                psc_fmt = f"{psc[:3]} {psc[3:]}"
            else:
                psc_fmt = psc
            adresa_parts.append(psc_fmt)
        
        if cast_obce:
            adresa_parts.append(cast_obce)
        
        if obec:
            adresa_parts.append(obec)
        
        return ", ".join(adresa_parts)
    
    def _get_business_field(self, data: Dict) -> str:
        """Extrahuje obor podnikání z ARES dat"""
        if 'predmetPodnikani' in data and data['predmetPodnikani']:
            obor = data['predmetPodnikani'][0] if isinstance(data['predmetPodnikani'], list) else data['predmetPodnikani']
            return obor
        return ""
    
    def extract_all_data(self) -> ExtractedData:
        """Hlavní metoda pro extrakci všech dat"""
        print("🔄 Začínám extrakci dat z PDF...")
        
        # 1. Extrahuj text z PDF
        self.text = self.extract_text_from_pdf()
        if not self.text:
            print("❌ Nepodařilo se extrahovat text z PDF")
            return self.extracted_data
        
        self.extracted_data.raw_text = self.text
        
        # 2. Extrahuj osobní data
        print("📋 Extrahuji osobní data...")
        personal_data = self.extract_personal_data()
        self.extracted_data.personal_info = personal_data
        
        # 3. Extrahuj tabulková data
        print("📊 Extrahuji tabulková data...")
        table_data = self.extract_table_data()
        self.extracted_data.table_data = table_data
        
        # 4. Dohledej informace o firmě
        if personal_data.get("ico"):
            print("🏢 Dohledávám informace o firmě...")
            company_info = self.get_company_info_via_ares(personal_data["ico"])
            self.extracted_data.company_info = company_info
            # Přidej informace o firmě do osobních dat
            self.extracted_data.personal_info.update(company_info)
        
        print("✅ Extrakce dokončena")
        return self.extracted_data
    
    def save_to_json(self, output_file: str = "data.json"):
        """Uloží extrahovaná data do JSON souboru"""
        data_to_save = {
            "personal_info": self.extracted_data.personal_info,
            "company_info": self.extracted_data.company_info,
            "table_data": self.extracted_data.table_data
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Data uložena do {output_file}")
    
    def get_dataframe(self) -> pd.DataFrame:
        """Vrátí data jako pandas DataFrame"""
        if self.extracted_data.table_data:
            return pd.DataFrame(self.extracted_data.table_data)
        
        # Pokud není tabulková data, vytvoř DataFrame z osobních dat
        if self.extracted_data.personal_info:
            table_rows = []
            for key, value in self.extracted_data.personal_info.items():
                if value:  # Přidej pouze neprázdné hodnoty
                    table_rows.append({'Pole': key, 'Hodnota': str(value)})
            return pd.DataFrame(table_rows)
        
        return pd.DataFrame()

def main():
    """Hlavní funkce pro spuštění extrakce"""
    pdf_file = "zadost.pdf"
    
    # Vytvoř instanci extraktoru
    extractor = PDFExtractor(pdf_file)
    
    # Extrahuj všechna data
    extracted_data = extractor.extract_all_data()
    
    # Ulož do JSON
    extractor.save_to_json()
    
    # Vypiš výsledky
    print("\n" + "="*50)
    print("VYTAŽENÁ DATA:")
    print("="*50)
    print(json.dumps(extracted_data.personal_info, ensure_ascii=False, indent=2))
    
    # Vytvoř DataFrame pro Streamlit
    df = extractor.get_dataframe()
    if not df.empty:
        print("\n📊 TABULKOVÁ DATA:")
        print(df.to_string(index=False))

if __name__ == "__main__":
    main() 