
# -*- coding: utf-8 -*-
import re
import json
from flask import render_template_string
import logging

logger = logging.getLogger(__name__)

def parse_cv_to_structured_data(cv_text):
    """
    Parsuje tekst CV i wyodrębnia strukturalne dane do szablonu
    """
    try:
        # Inicjalizuj strukturę danych
        cv_data = {
            'name': '',
            'subtitle': '',
            'phone': '',
            'email': '',
            'location': '',
            'summary': '',
            'skills': [],
            'education': [],
            'experience': [],
            'interests': [],
            'additional_info': []
        }
        
        # Wyczyść tekst i podziel na linie
        lines = [line.strip() for line in cv_text.strip().split('\n') if line.strip()]
        
        # Ulepszone wyodrębnianie imienia i nazwiska
        name_patterns = [
            r'^([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)$',  # Jan Kowalski
            r'^([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\s+[A-ZĄĆĘŁŃÓŚŹŻ]\.\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)$',  # Jan M. Kowalski
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+)$',  # John Smith
        ]
        
        for line in lines[:10]:  # Sprawdź pierwsze 10 linii
            for pattern in name_patterns:
                if re.match(pattern, line):
                    cv_data['name'] = line
                    break
            if cv_data['name']:
                break
        
        # Jeśli nie znaleziono, szukaj w pierwszych 3 liniach
        if not cv_data['name']:
            for line in lines[:3]:
                words = line.split()
                if 2 <= len(words) <= 3 and all(len(word) > 1 for word in words):
                    if any(c.isupper() for c in line) and not any(char in line for char in '@.+()'):
                        cv_data['name'] = line
                        break
        
        # Ulepszone wyodrębnianie emaila
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        emails = re.findall(email_pattern, cv_text, re.IGNORECASE)
        if emails:
            cv_data['email'] = emails[0]
        
        # Ulepszone wyodrębnianie telefonu
        phone_patterns = [
            r'(?:\+48[\s-]?)?(?:\d{3}[\s-]?\d{3}[\s-]?\d{3})',  # +48 123 456 789
            r'(?:\+48[\s-]?)?(?:\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2})',  # +48 12 345 67 89
            r'(?:\+48[\s-]?)?\(?\d{2,3}\)?[\s-]?\d{3}[\s-]?\d{3}',  # (12) 345 678
            r'\b\d{9}\b',  # 123456789
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, cv_text)
            if phones:
                cv_data['phone'] = phones[0]
                break
        
        # Ulepszone wyodrębnianie lokalizacji
        location_keywords = [
            'warszawa', 'kraków', 'poznań', 'wrocław', 'gdańsk', 'łódź', 'katowice', 
            'szczecin', 'bydgoszcz', 'lublin', 'białystok', 'częstochowa', 'radom',
            'sosnowiec', 'toruń', 'kielce', 'gliwice', 'zabrze', 'bytom', 'bielsko',
            'polska', 'poland', 'mazowieckie', 'małopolskie', 'śląskie'
        ]
        
        for line in lines:
            line_lower = line.lower()
            for keyword in location_keywords:
                if keyword in line_lower and len(line) < 50:  # Nie za długa linia
                    cv_data['location'] = line.strip()
                    break
            if cv_data['location']:
                break
        
        # Ulepszone wyodrębnianie sekcji CV
        current_section = None
        current_content = []
        
        # Rozszerzone markery sekcji z różnymi wariantami
        section_markers = {
            'streszczenie': 'summary',
            'profil': 'summary',
            'profil zawodowy': 'summary',
            'o mnie': 'summary',
            'opis': 'summary',
            'cel zawodowy': 'summary',
            'umiejętności': 'skills',
            'kompetencje': 'skills',
            'skills': 'skills',
            'technologie': 'skills',
            'narzędzia': 'skills',
            'języki programowania': 'skills',
            'doświadczenie': 'experience',
            'doświadczenie zawodowe': 'experience',
            'praca': 'experience',
            'historia zatrudnienia': 'experience',
            'kariera': 'experience',
            'work experience': 'experience',
            'wykształcenie': 'education',
            'edukacja': 'education',
            'education': 'education',
            'szkoły': 'education',
            'studia': 'education',
            'kursy': 'education',
            'certyfikaty': 'education',
            'zainteresowania': 'interests',
            'hobby': 'interests',
            'interests': 'interests',
            'pasje': 'interests',
            'dodatkowe': 'additional_info',
            'dodatkowe informacje': 'additional_info',
            'inne': 'additional_info',
            'projekty': 'additional_info',
            'osiągnięcia': 'additional_info'
        }
        
        for i, line in enumerate(lines):
            if not line:
                continue
                
            # Sprawdź czy to nagłówek sekcji
            line_lower = line.lower().strip('.:,-')
            found_section = None
            
            # Dokładne dopasowanie
            if line_lower in section_markers:
                found_section = section_markers[line_lower]
            else:
                # Częściowe dopasowanie dla nagłówków sekcji
                for marker, section in section_markers.items():
                    if (marker in line_lower and 
                        len(line) < 60 and 
                        len(line.split()) <= 4 and
                        not any(char in line for char in '@+()') and  # Nie telefon/email
                        not re.search(r'\d{4}', line)):  # Nie data
                        found_section = section
                        break
            
            if found_section:
                # Przetwórz poprzednią sekcję
                if current_section and current_content:
                    process_section_content(cv_data, current_section, current_content)
                
                current_section = found_section
                current_content = []
            else:
                # Dodaj do bieżącej sekcji jeśli istnieje
                if current_section:
                    current_content.append(line)
                elif not cv_data['summary'] and len(line) > 20:
                    # Jeśli jeszcze nie ma sekcji i linia jest długa, może to być streszczenie
                    cv_data['summary'] = line
        
        # Przetwórz ostatnią sekcję
        if current_section and current_content:
            process_section_content(cv_data, current_section, current_content)
        
        # Generuj brakujące dane
        if not cv_data['name']:
            # Spróbuj znaleźć imię w tekście
            words = cv_text.split()[:20]  # Pierwsze 20 słów
            for word in words:
                if (len(word) > 2 and 
                    word[0].isupper() and 
                    word[1:].islower() and 
                    word.isalpha()):
                    cv_data['name'] = word + ' [Nazwisko]'
                    break
            if not cv_data['name']:
                cv_data['name'] = 'Kandydat'
        
        # Generuj subtitle na podstawie doświadczenia lub umiejętności
        if not cv_data['subtitle']:
            if cv_data['experience'] and cv_data['experience'][0]['position']:
                position = cv_data['experience'][0]['position']
                cv_data['subtitle'] = f"{position}"
            elif cv_data['skills']:
                first_skill = cv_data['skills'][0]
                cv_data['subtitle'] = f"Specjalista - {first_skill}"
            else:
                cv_data['subtitle'] = 'Profesjonalista'
        
        # Usuń duplikaty z list
        cv_data['skills'] = list(dict.fromkeys(cv_data['skills']))  # Zachowaj kolejność
        cv_data['interests'] = list(dict.fromkeys(cv_data['interests']))
        cv_data['additional_info'] = list(dict.fromkeys(cv_data['additional_info']))
        
        # Ogranicz liczbę elementów żeby CV nie było za długie
        cv_data['skills'] = cv_data['skills'][:10]
        cv_data['interests'] = cv_data['interests'][:8]
        cv_data['additional_info'] = cv_data['additional_info'][:5]
        
        return cv_data
        
    except Exception as e:
        logger.error(f"Error parsing CV: {str(e)}")
        return get_default_cv_data()

def process_section_content(cv_data, section, content):
    """
    Przetwarza zawartość sekcji CV
    """
    if not content:
        return
        
    if section == 'summary':
        # Połącz linie w jeden tekst, zachowując akapity
        summary_text = ' '.join(content).strip()
        if summary_text:
            cv_data['summary'] = summary_text
    
    elif section == 'skills':
        for line in content:
            line = line.strip()
            if not line:
                continue
            
            # Różne sposoby separowania umiejętności
            separators = [',', '•', '-', '|', '/', ';']
            skills_found = False
            
            for sep in separators:
                if sep in line:
                    skills = [s.strip() for s in line.split(sep) if s.strip() and len(s.strip()) > 1]
                    if skills:
                        cv_data['skills'].extend(skills)
                        skills_found = True
                        break
            
            if not skills_found and len(line) > 1:
                cv_data['skills'].append(line)
    
    elif section == 'experience':
        # Grupuj linie w doświadczenia
        current_exp = []
        for line in content:
            if line.strip():
                current_exp.append(line.strip())
        
        if current_exp:
            exp_item = parse_experience_item(current_exp)
            if exp_item:
                cv_data['experience'].append(exp_item)
    
    elif section == 'education':
        # Grupuj linie w wykształcenie
        current_edu = []
        for line in content:
            if line.strip():
                current_edu.append(line.strip())
        
        if current_edu:
            edu_item = parse_education_item(current_edu)
            if edu_item:
                cv_data['education'].append(edu_item)
    
    elif section == 'interests':
        for line in content:
            line = line.strip()
            if not line:
                continue
                
            separators = [',', '•', '-', '|', ';']
            interests_found = False
            
            for sep in separators:
                if sep in line:
                    interests = [i.strip() for i in line.split(sep) if i.strip() and len(i.strip()) > 1]
                    if interests:
                        cv_data['interests'].extend(interests)
                        interests_found = True
                        break
            
            if not interests_found and len(line) > 1:
                cv_data['interests'].append(line)
    
    elif section == 'additional_info':
        valid_info = [line.strip() for line in content if line.strip() and len(line.strip()) > 3]
        cv_data['additional_info'].extend(valid_info)

def parse_experience_item(content):
    """
    Parsuje element doświadczenia zawodowego
    """
    if not content:
        return None
    
    exp = {
        'position': '',
        'company': '',
        'period': '',
        'responsibilities': []
    }
    
    # Pierwsza niepusta linia to prawdopodobnie stanowisko
    for line in content:
        if line.strip() and not exp['position']:
            exp['position'] = line.strip()
            break
    
    # Szukaj daty, firmy i obowiązków
    date_patterns = [
        r'\d{4}[\s-]*\d{4}',  # 2020-2024
        r'\d{1,2}[\./]\d{4}[\s-]*\d{1,2}[\./]\d{4}',  # 01/2020 - 12/2024
        r'(?:styczeń|luty|marzec|kwiecień|maj|czerwiec|lipiec|sierpień|wrzesień|październik|listopad|grudzień)',
        r'(?:january|february|march|april|may|june|july|august|september|october|november|december)',
        r'obecnie|present|current'
    ]
    
    responsibility_markers = ['-', '•', '*', '▸', '→', '◦']
    
    for line in content[1:] if len(content) > 1 else []:
        line = line.strip()
        if not line:
            continue
            
        # Sprawdź czy zawiera datę
        is_date = any(re.search(pattern, line.lower()) for pattern in date_patterns)
        
        if is_date and not exp['period']:
            exp['period'] = line
        elif (not exp['company'] and 
              not any(line.startswith(marker) for marker in responsibility_markers) and
              not is_date and
              len(line) > 2 and len(line) < 100):
            exp['company'] = line
        elif any(line.startswith(marker) for marker in responsibility_markers):
            # Usuń marker i dodaj do obowiązków
            responsibility = line
            for marker in responsibility_markers:
                if responsibility.startswith(marker):
                    responsibility = responsibility[len(marker):].strip()
                    break
            if responsibility:
                exp['responsibilities'].append(responsibility)
        elif line and len(line) > 15 and not is_date and exp['company']:
            # Długa linia bez markera - prawdopodobnie opis obowiązków
            exp['responsibilities'].append(line)
    
    return exp if exp['position'] else None

def parse_education_item(content):
    """
    Parsuje element wykształcenia
    """
    if not content:
        return None
    
    edu = {
        'title': '',
        'institution': '',
        'period': ''
    }
    
    # Pierwsza linia to tytuł/kierunek
    for line in content:
        if line.strip() and not edu['title']:
            edu['title'] = line.strip()
            break
    
    # Szukaj uczelni i okresu
    date_patterns = [
        r'\d{4}[\s-]*\d{4}',  # 2020-2024
        r'\d{1,2}[\./]\d{4}[\s-]*\d{1,2}[\./]\d{4}',  # 01/2020 - 12/2024
    ]
    
    for line in content[1:] if len(content) > 1 else []:
        line = line.strip()
        if not line:
            continue
            
        # Sprawdź czy zawiera datę
        is_date = any(re.search(pattern, line) for pattern in date_patterns)
        
        if is_date and not edu['period']:
            edu['period'] = line
        elif not edu['institution'] and not is_date and len(line) > 3:
            edu['institution'] = line
    
    return edu if edu['title'] else None

def get_default_cv_data():
    """
    Zwraca domyślną strukturę danych CV
    """
    return {
        'name': 'Kandydat',
        'subtitle': 'Profesjonalista',
        'phone': '',
        'email': '',
        'location': '',
        'summary': '',
        'skills': [],
        'education': [],
        'experience': [],
        'interests': [],
        'additional_info': []
    }

def generate_cv_html(cv_text):
    """
    Generuje sformatowane HTML CV na podstawie tekstu
    """
    try:
        if not cv_text or not cv_text.strip():
            return None
            
        # Parsuj CV do strukturalnych danych
        cv_data = parse_cv_to_structured_data(cv_text)
        
        # Sprawdź czy cv_data jest prawidłowe
        if not cv_data or not isinstance(cv_data, dict):
            logger.error("Failed to parse CV data")
            return None
        
        # Wczytaj szablon
        try:
            with open('templates/cv_template.html', 'r', encoding='utf-8') as f:
                template_content = f.read()
        except FileNotFoundError:
            logger.error("CV template file not found")
            return None
        
        # Renderuj szablon z danymi
        html_cv = render_template_string(template_content, **cv_data)
        
        # Sprawdź czy HTML został wygenerowany poprawnie
        if html_cv and len(html_cv.strip()) > 100:  # Podstawowa walidacja długości
            return html_cv
        else:
            logger.error("Generated HTML is too short or empty")
            return None
        
    except Exception as e:
        logger.error(f"Error generating CV HTML: {str(e)}")
        return None

def extract_plain_text_from_html(html_content):
    """
    Wyodrębnia czysty tekst z HTML CV (dla kompatybilności wstecznej)
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Usuń style i script
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Pobierz tekst
        text = soup.get_text()
        
        # Wyczyść tekst
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
        
    except Exception as e:
        logger.error(f"Error extracting text from HTML: {str(e)}")
        return html_content  # Zwróć oryginalny HTML jako fallback
