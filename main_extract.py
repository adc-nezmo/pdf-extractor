import pdfplumber
import os
import re
import json
import time
import requests
from dotenv import load_dotenv
import pandas as pd

# Načti environment proměnné
load_dotenv()

pdf_file = "zadost.pdf"
output_json = "data.json"

# === Funkce pro dohledání informací o firmě přes ARES API ===
def get_company_info_via_ares(ico: str) -> dict:
    """
    Dohledá informace o firmě podle IČO pomocí ARES API (Ministerstvo financí ČR).
    """
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
        
        # ARES API endpoint
        url = f"https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}"
        
        # Headers pro ARES API
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extrahuj základní informace
            company_info = {
                "ico": ico,
                "firma_nazev": "",
                "firma_sidlo": "",
                "status": "",
                "typ_subjektu": "",
                "obor_podnikani": ""
            }
            
            # Název firmy
            if 'obchodniJmeno' in data:
                company_info["firma_nazev"] = data['obchodniJmeno']
            
            # Adresa sídla
            if 'sidlo' in data:
                sidlo = data['sidlo']
                ulice = str(sidlo['ulice']) if 'ulice' in sidlo and sidlo['ulice'] else ""
                cislo = str(sidlo['cisloDomovni']) if 'cisloDomovni' in sidlo and sidlo['cisloDomovni'] else ""
                cast_obce = str(sidlo['castObce']) if 'castObce' in sidlo and sidlo['castObce'] else ""
                obec = str(sidlo['obec']) if 'obec' in sidlo and sidlo['obec'] else ""
                psc = str(sidlo['psc']) if 'psc' in sidlo and sidlo['psc'] else ""
                textova_adresa = str(sidlo['textovaAdresa']) if 'textovaAdresa' in sidlo and sidlo['textovaAdresa'] else ""
                
                adresa = ""
                # Pokud není ulice, ale je textovaAdresa, použij ji celou a naformátuj PSČ
                if not ulice and textova_adresa:
                    # Najdi a naformátuj PSČ (pět číslic) na xxx xx
                    adresa = re.sub(r"(\b\d{3})(\d{2}\b)", r"\1 \2", textova_adresa)
                else:
                    # Sestav ulice a číslo
                    if ulice:
                        adresa += ulice
                        if cislo:
                            adresa += f" {cislo}"
                    elif cislo:
                        adresa += cislo
                    # PSČ
                    if psc:
                        # Formátuj PSČ na 3+2 číslice s mezerou
                        if len(psc) == 5:
                            psc_fmt = f"{psc[:3]} {psc[3:]}"
                        else:
                            psc_fmt = psc
                        adresa += f", {psc_fmt}"
                    # Část obce
                    if cast_obce:
                        adresa += f", {cast_obce}"
                    # Obec
                    if obec:
                        adresa += f", {obec}"
                company_info["firma_sidlo"] = adresa.strip(", ")
            
            # Status (aktivní/neaktivní)
            if 'stav' in data:
                company_info["status"] = data['stav']
            
            # Typ subjektu
            if 'pravniForma' in data:
                company_info["typ_subjektu"] = data['pravniForma']
            
            # Obor podnikání (pokud je dostupný)
            if 'predmetPodnikani' in data and data['predmetPodnikani']:
                # Vezme první obor podnikání
                obor = data['predmetPodnikani'][0] if isinstance(data['predmetPodnikani'], list) else data['predmetPodnikani']
                company_info["obor_podnikani"] = obor
            
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
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Chyba při připojení k ARES API: {e}")
        return {
            "ico": ico,
            "firma_nazev": "",
            "firma_sidlo": "",
            "status": "Chyba připojení",
            "typ_subjektu": "",
            "obor_podnikani": ""
        }
    except Exception as e:
        print(f"❌ Neočekávaná chyba: {e}")
        return {
            "ico": ico,
            "firma_nazev": "",
            "firma_sidlo": "",
            "status": "Chyba zpracování",
            "typ_subjektu": "",
            "obor_podnikani": ""
        }

# === Normalizace titulu ===
def normalize_title(title_str):
    if not title_str:
        return ""
    title_str = title_str.lower().replace(".", "").strip()
    if "bakal" in title_str:
        return "Bc."
    if "inžen" in title_str or "ing" in title_str:
        return "Ing."
    if "doktor" in title_str or title_str.startswith("phd") or "ph.d" in title_str:
        return "Ph.D."
    if "magistr" in title_str or "mgr" in title_str:
        return "Mgr."
    if "mudr" in title_str:
        return "MUDr."
    return title_str

# === Extrakce textu z PDF ===
text = ""
with pdfplumber.open(pdf_file) as pdf:
    for page in pdf.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"

# Ulož extrahovaný text do souboru pro analýzu
with open("extrahovany_text.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("="*40)
print("VYTAŽENÝ TEXT Z PDF:")
print("="*40)
print(text)
print("="*40)

data = {}

# === Extrakce helper ===
def search_and_store(pattern, key, processor=lambda x: x):
    match = re.search(pattern, text)
    if match:
        data[key] = processor(match.group(1).strip())

# === Parsování údajů ===
# (Všechny staré regexy pro osobní údaje jsou zakomentovány/odstraněny)
#search_and_store(r"IČO zaměstnavatele nebo OSVČ\\s*[:\\-]?\\s*([0-9 ]{8,})", "ico", lambda x: re.sub(r'\\D', '', x)[:8])
#search_and_store(r"IČO\\s*zaměstnavatele\\s*nebo\\s*OSVČ\\s*[:\\-]?\\s*([0-9 ]{8,})", "ico", lambda x: re.sub(r'\\D', '', x)[:8])
#search_and_store(r"IČO\\s*:?\\s*([0-9 ]{8,})", "ico", lambda x: re.sub(r'\\D', '', x)[:8])
#search_and_store(r"Rodné číslo\\s*:?[ \\t]*([0-9 ]{9,10})", "rodne_cislo", lambda x: re.sub(r'\\D', '', x)[:10])
#search_and_store(r"Datum narození\\s*:?[ \\t]*([0-9]{1,2}\\.\\s*[0-9]{1,2}\\.\\s*[0-9]{2,4})", "datum_narozeni", lambda x: re.sub(r'\\s*\\.\\s*', '.', x.strip()))
#rc_datum_match = re.search(r"([0-9 ]{9,10})\\s+([0-9]{1,2}\\.\\s*[0-9]{1,2}\\.\\s*[0-9]{2,4})", text)
#if rc_datum_match:
#    data["rodne_cislo"] = re.sub(r'\\D', '', rc_datum_match.group(1))
#    data["datum_narozeni"] = re.sub(r'\\s*\\.\\s*', '.', rc_datum_match.group(2).replace(' ', ''))
#search_and_store(r"Příjmení/Jméno\\s+([^\\n]+)", "jmeno_prijmeni")
#if "jmeno_prijmeni" in data:
#    parts = data["jmeno_prijmeni"].strip().split()
#    if len(parts) >= 2:
#        data["prijmeni"] = parts[0]
#        data["jmeno"] = " ".join(parts[1:])
#    elif len(parts) == 1:
#        data["prijmeni"] = parts[0]
#    del data["jmeno_prijmeni"]
#checklist_match = re.search(r"([A-Za-zěščřžýáíéúůóĚŠČŘŽÝÁÍÉÚŮÓ\\-]+)\\s+([A-Za-zěščřžýáíéúůóĚŠČŘŽÝÁÍÉÚŮÓ\\-]+),\\s*RČ:\\s*([0-9 ]{9,10})", text)
#if checklist_match:
#    data["jmeno"] = checklist_match.group(1)
#    data["prijmeni"] = checklist_match.group(2)
#    data["rodne_cislo"] = re.sub(r'\\D', '', checklist_match.group(3))
#adresa_match = re.search(r"([A-Za-zěščřžýáíéúůóĚŠČŘŽÝÁÍÉÚŮÓ\\- ]+)\\s+(\\d+[a-zA-Z]?)\\,?\\s*(\\d{3}\\s?\\d{2})\\s*([A-Za-zěščřžýáíéúůóĚŠČŘŽÝÁÍÉÚŮÓ\\- ]+)", text)
#if adresa_match:
#    data['ulice'] = adresa_match.group(1).strip()
#    data['cislo'] = adresa_match.group(2).strip()
#    data['psc'] = re.sub(r'\\s+', '', adresa_match.group(3))
#    data['mesto'] = adresa_match.group(4).strip()
#    data['adresa'] = f"{data['ulice']} {data['cislo']}, {data['psc']} {data['mesto']}"
#search_and_store(r"Místo narození: město/stát\\s+([^\\n]+)", "misto_narozeni")
#telefon_match = re.search(r"(\\+420\\s*)?([0-9]{3}[\\s-]?[0-9]{3}[\\s-]?[0-9]{3})", text)
#if telefon_match:
#    tel = telefon_match.group(2).replace(" ", "").replace("-", "")
#    data["telefon"] = f"{tel[:3]} {tel[3:6]} {tel[6:]}"
#email_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+)", text)
#if email_match:
#    data["email"] = email_match.group(1)
#search_and_store(r"Povolání/Ekonomický sektor\\s+([^\\n]+)", "povolani", lambda p: re.sub(r'(\\d)\\s+([A-Za-zÁ-Žá-ž])', r'\\1, \\2', p))
#search_and_store(r"Datum nástupu.*?([0-9]{2}\\.[0-9]{2}\\.[0-9]{4})", "datum_nastupu", lambda x: re.sub(r'[^0-9\\.]', '', x)[:10])
#search_and_store(r"Místo trvalého pobytu dle průkazu: ulice; číslo/PSČ; obec\\s+([^\\n]+)", "adresa")
#search_and_store(r"Čistý příjem\\s+([0-9\\.,]+)", "cisty_prijem", lambda x: x.replace(".", "").replace(",", "."))
#search_and_store(r"Měsíční životní náklady.*?\\s+([0-9\\.,]+)", "mesicni_naklady", lambda x: x.replace(".", "").replace(",", "."))
#search_and_store(r"Titul\\s*[:\\-]?\\s*([^\\n]+)", "titul", normalize_title)
#search_and_store(r"Nejvyšší dosažené vzdělání\\s+([^\\n]+)", "nejvyssi_vzdelani")
#search_and_store(r"Datum nástupu do zaměstnání nebo zahájení podnikání\\s+([0-9]{2}\\.[0-9]{2}\\.[0-9]{4})", "datum_nastupu_zamestnani", lambda x: re.sub(r'[^0-9\\.]', '', x)[:10])
#data.pop("statni_obcanstvi", None)

# === Firma dle IČO pomocí ARES API ===
if data.get("ico"):
    print(f"\n🔍 Dohledávám informace o firmě s IČO: {data['ico']}")
    company_info = get_company_info_via_ares(data["ico"])
    data.update(company_info)
    print(f"✅ Informace o firmě dohledány: {company_info.get('firma_nazev', 'N/A')}")
else:
    print("⚠️ IČO nebylo nalezeno v PDF")

# === Ulož JSON ===
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("\n✅ Data uložena do data.json:")
print(json.dumps(data, ensure_ascii=False, indent=2))

# === Nová tabulková extrakce pro hlavní skript ===
def extract_table_data(text):
    """
    Extrahuje data z tabulky "I. Osobní údaje žadatele/ů" pomocí alias mapy.
    """
    # === Alias map pro převod názvů polí na interní klíče ===
    alias_map = {
        "Příjmení/Jméno": ["prijmeni", "jmeno"],
        "Rodné číslo/Datum narození": ["rodne_cislo", "datum_narozeni"],
        "Místo narození: město/stát": ["misto_narozeni", "misto_narozeni_stat"],
        "Pohlaví/Státní občanství": ["pohlavi", "statni_obcanstvi"],
        "Telefon/E-mail": ["telefon", "email"],
        "Vydal: stát; orgán/Platnost do": ["vydal_doklad", "platnost_dokladu"],
        "Místo trvalého pobytu dle průkazu: ulice; číslo/PSČ; obec": "trvale_bydliste",
        "Místo trvalého pobytu dle průkazu: stát": "trvale_bydliste_stat",
        "Korespondenční adresa v ČR: ulice; číslo/PSČ; obec": "korespondencni_adresa",
        "Stát bydliště/Měna státu bydliště": ["stat_bydliste", "mena_bydliste"],
        "Stát bydliště (uveďte stát, v němž máte bydliště déle než 1 rok)": "stat_bydliste_dlouhodobe",
        "Způsob současného bydlení/Délka pobytu v měsících": ["typ_bydleni", "delka_pobytu_mesice"],
        "IČO zaměstnavatele nebo OSVČ": "ico",
        "PSČ zaměstnavatele nebo místa podnikání": "psc_zamestnavatele",
        "Společníkem zaměstnavatele": "spolecnik",
        "Typ kontraktu": "typ_kontraktu",
        "Datum nástupu do zaměstnání nebo zahájení podnikání": "datum_nastupu",
        "Splácení dluhu z příjmu v: stát/měna": ["dluh_stat", "dluh_mena"],
        "Čistý příjem": "cisty_prijem",
        "Zdroj příjmu": "zdroj_prijmu",
        "Měsíční životní náklady domácnosti včetně nákladů na bydlení/Označení domácnosti": ["mesicni_naklady_domacnost", "oznaceni_domacnosti"]
    }

    extracted_data = {}
    lines = text.split('\n')
    in_table = False
    
    for line in lines:
        # Najdi začátek tabulky
        if 'I. Osobní údaje žadatele' in line:
            in_table = True
            continue
        
        if in_table:
            # Konec tabulky
            if line.strip() == '' or re.match(r'II\.', line):
                in_table = False
                break
            
            # Rozdělení na části (label, value1, value2)
            parts = re.split(r'\s{2,}|\t', line)
            parts = [p.strip() for p in parts if p.strip()]
            
            if len(parts) >= 2:
                label = parts[0]
                value1 = parts[1] if len(parts) > 1 else ''
                value2 = parts[2] if len(parts) > 2 else ''
                
                alias = alias_map.get(label, label)
                
                if isinstance(alias, list):
                    # Pokud je alias list, rozděl value1 a value2 do těchto klíčů
                    key1 = alias[0]
                    key2 = alias[1] if len(alias) > 1 else None
                    
                    if value1:
                        extracted_data[key1] = value1
                    if key2 and value2:
                        extracted_data[key2] = value2
                else:
                    # Pokud je alias str, použij pouze value1
                    if value1:
                        extracted_data[alias] = value1
    
    return extracted_data

# === Tabulková extrakce už byla spuštěna výše ===

# === Funkce pro Streamlit ===
def extract_data_from_pdf(pdf_file_path):
    """
    Extrahuje data z PDF souboru a vrací je jako slovník + extrahovaný text + tabulku etiket a hodnot.
    Pro použití ve Streamlit aplikaci.
    """
    import pdfplumber
    import re
    import requests
    import os
    import pandas as pd
    from dotenv import load_dotenv
    load_dotenv()

    # Extrakce textu z PDF
    text = ""
    with pdfplumber.open(pdf_file_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    # === Předzpracování: odřízni vše před 'I. Osobní údaje žadatele' ===
    osobni_udaje_start = re.search(r'(I\.\s*Osobní údaje žadatele.*)', text, re.DOTALL)
    if osobni_udaje_start:
        text = osobni_udaje_start.group(1)

    data = {}
    ares_response = None

    # === Extrakce helper ===
    def search_and_store(pattern, key, processor=lambda x: x):
        match = re.search(pattern, text)
        if match:
            data[key] = processor(match.group(1).strip())
    
    # === Přesná extrakce údajů podle formátu ===
    # Příjmení/Jméno
    jmeno_match = re.search(r"Příjmení/Jméno\s+([A-Za-zÁ-Žá-ž\- ]+)", text)
    if jmeno_match:
        jmeno_cely = jmeno_match.group(1).strip()
        parts = jmeno_cely.split()
        if len(parts) >= 2:
            data["prijmeni"] = parts[0]
            data["jmeno"] = " ".join(parts[1:])
        else:
            data["jmeno"] = jmeno_cely

    # Rodné číslo/Datum narození
    rc_datum_match = re.search(r"Rodné číslo/Datum narození\s+([0-9]{9,10})\s+([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{4})", text)
    if rc_datum_match:
        data["rodne_cislo"] = rc_datum_match.group(1)
        data["datum_narozeni"] = rc_datum_match.group(2)

    # Místo narození: město/stát
    misto_narozeni_match = re.search(r"Místo narození: město/stát\s+([A-Za-z0-9 .\-]+)\s+([A-Za-z ]+)", text)
    if misto_narozeni_match:
        data["misto_narozeni_mesto"] = misto_narozeni_match.group(1).strip()
        data["misto_narozeni_stat"] = misto_narozeni_match.group(2).strip()

    # Pohlaví/Státní občanství
    pohlavi_obcanstvi_match = re.search(r"Pohlaví/Státní občanství\s+([a-zA-Zěščřžýáíéúůó ]+)\s+([a-zA-ZěščřžýáíéúůóĚŠČŘŽÝÁÍÉÚŮÓ ]+)", text)
    if pohlavi_obcanstvi_match:
        data["pohlavi"] = pohlavi_obcanstvi_match.group(1).strip()
        data["statni_obcanstvi"] = pohlavi_obcanstvi_match.group(2).strip()

    # Telefon/E-mail
    tel_email_match = re.search(r"Telefon/E-mail\s+([0-9 ]+)\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", text)
    if tel_email_match:
        data["telefon"] = tel_email_match.group(1).replace(" ", "")
        data["email"] = tel_email_match.group(2)

    # Nejvyšší dosažené vzdělání
    vzdelani_match = re.search(r"Nejvyšší dosažené vzdělání\s+[0-9]+\s+([A-Za-zěščřžýáíéúůóĚŠČŘŽÝÁÍÉÚŮÓ ]+)", text)
    if vzdelani_match:
        data["nejvyssi_vzdelani"] = vzdelani_match.group(1).strip()

    # Povolání/Ekonomický sektor
    povolani_match = re.search(r"Povolání/Ekonomický sektor\s+([A-Za-zěščřžýáíéúůóĚŠČŘŽÝÁÍÉÚŮÓ, ]+)", text)
    if povolani_match:
        data["povolani"] = povolani_match.group(1).strip()

    # IČO zaměstnavatele nebo OSVČ
    ico_match = re.search(r"IČO zaměstnavatele nebo OSVČ\s+([0-9]{8})", text)
    if ico_match:
        data["ico"] = ico_match.group(1)

    # Datum nástupu do zaměstnání nebo zahájení podnikání
    nastup_match = re.search(r"Datum nástupu do zaměstnání nebo zahájení podnikání\s+([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text)
    if nastup_match:
        data["datum_nastupu"] = nastup_match.group(1)

    # Čistý příjem
    prijem_match = re.search(r"Čistý příjem\s+([0-9\.,]+)", text)
    if prijem_match:
        data["cisty_prijem"] = prijem_match.group(1).replace(".", "").replace(",", ".")

    # Měsíční životní náklady domácnosti včetně nákladů na bydlení
    naklady_match = re.search(r"Měsíční životní náklady domácnosti včetně nákladů na\s+([0-9\.,]+)", text)
    if naklady_match:
        data["mesicni_naklady"] = naklady_match.group(1).replace(".", "").replace(",", ".")

    # Firma dle IČO
    if "ico" in data and data["ico"]:
        company_info = get_company_info_via_ares(data["ico"])
        data.update(company_info)
        ares_response = company_info
    # === Alias map pro převod názvů polí na interní klíče ===
    alias_map = {
        "Příjmení/Jméno": ["prijmeni", "jmeno"],
        "Rodné číslo/Datum narození": ["rodne_cislo", "datum_narozeni"],
        "Místo narození: město/stát": ["misto_narozeni_mesto", "misto_narozeni_stat"],
        "Pohlaví/Státní občanství": ["pohlavi", "statni_obcanstvi"],
        "Telefon/E-mail": ["telefon", "email"],
        "Vydal: stát; orgán/Platnost do": ["vydal_doklad", "platnost_dokladu"],
        "Místo trvalého pobytu dle průkazu: ulice; číslo": "trvale_bydliste_ulice_cislo",
        "PSČ; obec": "trvale_bydliste_psc_obec",
        "Místo trvalého pobytu dle průkazu: stát": "trvale_bydliste_stat",
        "Korespondenční adresa v ČR: ulice; číslo": "korespondencni_adresa_ulice_cislo",
        "Korespondenční adresa v ČR: PSČ; obec": "korespondencni_adresa_psc_obec",
        "Stát bydliště": "stat_bydliste",
        "Měna státu bydliště": "mena_bydliste",
        "Stát bydliště (uveďte stát, v němž máte bydliště déle než 1 rok)": "stat_bydliste_dlouhodobe",
        "Způsob současného bydlení": "typ_bydleni",
        "Délka pobytu v měsících": "delka_pobytu_mesice",
        "IČO zaměstnavatele nebo OSVČ": "ico_zamestnavatele",
        "PSČ zaměstnavatele nebo místa podnikání": "psc_zamestnavatele",
        "Společníkem zaměstnavatele": "spolecnik",
        "Typ kontraktu": "typ_kontraktu",
        "Datum nástupu do zaměstnání nebo zahájení podnikání": "datum_nastupu",
        "stát": "dluh_stat",
        "měna": "dluh_mena",
        "Čistý příjem": "cisty_prijem",
        "Zdroj příjmu": "zdroj_prijmu",
        "Měsíční životní náklady domácnosti včetně nákladů na bydlení": "mesicni_naklady_domacnost",
        "Označení domácnosti": "oznaceni_domacnosti"
    }

    # === Nová extrakce tabulky (3 sloupce: label | value1 | value2) ===
    table_rows = []
    alias_dict = {}
    in_table = False
    json_rows = []
    for page in pdfplumber.open(pdf_file_path).pages:
        lines = page.extract_text().splitlines()
        for line in lines:
            # Najdi začátek tabulky podle typického nadpisu
            if 'I. Osobní údaje žadatele' in line:
                in_table = True
                continue
            if in_table:
                # Konec tabulky (prázdný řádek nebo začátek další sekce)
                if line.strip() == '' or re.match(r'II\.', line):
                    in_table = False
                    break
                # Rozdělení na části (label, value1, value2)
                parts = re.split(r'\s{2,}|\t|\|', line)
                parts = [p.strip() for p in parts if p.strip()]
                if len(parts) >= 2:
                    label = parts[0]
                    value1 = parts[1] if len(parts) > 1 else ''
                    value2 = parts[2] if len(parts) > 2 else ''
                    alias = alias_map.get(label, label)
                    if isinstance(alias, list):
                        # Pokud je alias list, rozděl value1 a value2 do těchto klíčů
                        key1 = alias[0]
                        key2 = alias[1] if len(alias) > 1 else None
                        row = {}
                        row[key1] = value1 if value1 else ''
                        if key2:
                            row[key2] = value2 if value2 else ''
                        json_rows.append(row)
                        # Tabulka pro Streamlit
                        table_rows.append({'Pole': key1, 'Hodnota': value1})
                        if key2:
                            table_rows.append({'Pole': key2, 'Hodnota': value2})
                        # Slovník s aliasy (pro původní dict)
                        alias_dict[key1] = value1 if value1 else ''
                        if key2:
                            alias_dict[key2] = value2 if value2 else ''
                    else:
                        # Pokud je alias str, použij pouze value1
                        row = {alias: value1 if value1 else ''}
                        json_rows.append(row)
                        alias_dict[alias] = value1 if value1 else ''
                        table_rows.append({'Pole': alias, 'Hodnota': value1})
    table_df = pd.DataFrame(table_rows)
    return data, text, ares_response, table_df, alias_dict, json_rows

# === Tabulková extrakce (spustit PRVNÍ) ===
def extract_table_data_simple(text):
    """
    Vylepšená tabulková extrakce: hledá labely podle začátku řádku a hodnoty vezme jako vše za label.
    Pro zalomené řádky spojí s následujícím, pokud je potřeba.
    """
    extracted_data = {}
    lines = text.split('\n')
    in_table = False
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Najdi začátek tabulky
        if 'I. Osobní údaje žadatele' in line:
            in_table = True
            i += 1
            continue
        if in_table:
            # Konec tabulky
            if line == '' or line.startswith('II.'):
                break
            # Labely a extrakce hodnot
            if line.startswith('Příjmení/Jméno'):
                values = line[len('Příjmení/Jméno'):].strip().split()
                if len(values) >= 2:
                    extracted_data['prijmeni'] = values[0]
                    extracted_data['jmeno'] = ' '.join(values[1:])
                elif len(values) == 1:
                    extracted_data['jmeno'] = values[0]
            elif line.startswith('Rodné číslo/Datum narození'):
                values = line[len('Rodné číslo/Datum narození'):].strip().split()
                if len(values) >= 2:
                    extracted_data['rodne_cislo'] = values[0]
                    extracted_data['datum_narozeni'] = values[1]
            elif line.startswith('Místo narození: město/stát'):
                values = line[len('Místo narození: město/stát'):].strip().split()
                if len(values) >= 2:
                    extracted_data['misto_narozeni_mesto'] = values[0]
                    extracted_data['misto_narozeni_stat'] = ' '.join(values[1:])
            elif line.startswith('Pohlaví/Státní občanství'):
                values = line[len('Pohlaví/Státní občanství'):].strip().split()
                if len(values) >= 2:
                    extracted_data['pohlavi'] = values[0]
                    extracted_data['statni_obcanstvi'] = ' '.join(values[1:])
            elif line.startswith('Telefon/E-mail'):
                values = line[len('Telefon/E-mail'):].strip().split()
                if len(values) >= 2:
                    extracted_data['telefon'] = values[0]
                    extracted_data['email'] = values[1]
            elif line.startswith('IČO zaměstnavatele nebo OSVČ'):
                value = line[len('IČO zaměstnavatele nebo OSVČ'):].strip()
                extracted_data['ico'] = value
            elif line.startswith('Čistý příjem'):
                value = line[len('Čistý příjem'):].strip().replace('.', '').replace(',', '.')
                extracted_data['cisty_prijem'] = value
            elif line.startswith('Měsíční životní náklady domácnosti včetně nákladů na'):
                # Spoj s dalším řádkem, pokud vypadá jako pokračování
                value = line[len('Měsíční životní náklady domácnosti včetně nákladů na'):].strip()
                if i+1 < len(lines) and not lines[i+1].startswith('bydlení/Označení domácnosti') and not lines[i+1].startswith('II.'):
                    value += ' ' + lines[i+1].strip()
                    i += 1
                value = value.replace('.', '').replace(',', '.')
                extracted_data['mesicni_naklady'] = value
            elif line.startswith('Datum nástupu do zaměstnání nebo zahájení podnikání'):
                value = line[len('Datum nástupu do zaměstnání nebo zahájení podnikání'):].strip()
                extracted_data['datum_nastupu'] = value
            elif line.startswith('Nejvyšší dosažené vzdělání'):
                values = line[len('Nejvyšší dosažené vzdělání'):].strip().split()
                if len(values) >= 2:
                    extracted_data['nejvyssi_vzdelani'] = ' '.join(values[1:])
            elif line.startswith('Povolání/Ekonomický sektor'):
                values = line[len('Povolání/Ekonomický sektor'):].strip().split()
                if len(values) >= 2:
                    extracted_data['povolani'] = ' '.join(values[:-1])
                    extracted_data['ekonomicky_sektor'] = values[-1]
        i += 1
    return extracted_data

# Spusť tabulkovou extrakci PRVNÍ
table_data = extract_table_data_simple(text)
data.update(table_data)

if __name__ == "__main__":
    pass
