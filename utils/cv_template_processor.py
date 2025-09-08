
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
        
        # Wyodrębnij imię i nazwisko (pierwsza linia lub linia z wielkich liter)
        lines = cv_text.strip().split('\n')
        for line in lines[:5]:  # Sprawdź pierwsze 5 linii
            line = line.strip()
            if line and len(line.split()) <= 4 and any(c.isupper() for c in line):
                # Prawdopodobnie imię i nazwisko
                cv_data['name'] = line
                break
        
        # Wyodrębnij email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, cv_text)
        if emails:
            cv_data['email'] = emails[0]
        
        # Wyodrębnij telefon
        phone_pattern = r'(?:\+48\s?)?(?:\d{3}[\s-]?\d{3}[\s-]?\d{3}|\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2})'
        phones = re.findall(phone_pattern, cv_text)
        if phones:
            cv_data['phone'] = phones[0]
        
        # Wyodrębnij lokalizację (szukaj miast)
        location_keywords = ['warszawa', 'kraków', 'poznań', 'wrocław', 'gdańsk', 'łódź', 'katowice', 'polska']
        for line in lines:
            line_lower = line.lower()
            for keyword in location_keywords:
                if keyword in line_lower:
                    cv_data['location'] = line.strip()
                    break
            if cv_data['location']:
                break
        
        # Wyodrębnij sekcje CV
        current_section = None
        current_content = []
        
        section_markers = {
            'streszczenie': 'summary',
            'profil': 'summary',
            'o mnie': 'summary',
            'umiejętności': 'skills',
            'kompetencje': 'skills',
            'doświadczenie': 'experience',
            'praca': 'experience',
            'wykształcenie': 'education',
            'edukacja': 'education',
            'zainteresowania': 'interests',
            'hobby': 'interests',
            'dodatkowe': 'additional_info'
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Sprawdź czy to nagłówek sekcji
            line_lower = line.lower()
            found_section = None
            for marker, section in section_markers.items():
                if marker in line_lower and len(line) < 50:
                    found_section = section
                    break
            
            if found_section:
                # Przetwórz poprzednią sekcję
                if current_section and current_content:
                    process_section_content(cv_data, current_section, current_content)
                
                current_section = found_section
                current_content = []
            else:
                if current_section:
                    current_content.append(line)
        
        # Przetwórz ostatnią sekcję
        if current_section and current_content:
            process_section_content(cv_data, current_section, current_content)
        
        # Jeśli nie znaleziono nazwiska, użyj domyślnego
        if not cv_data['name']:
            cv_data['name'] = 'Kandydat'
        
        # Generuj subtitle na podstawie doświadczenia lub umiejętności
        if not cv_data['subtitle']:
            if cv_data['experience']:
                cv_data['subtitle'] = f"Doświadczony {cv_data['experience'][0].get('position', 'Specjalista')}"
            elif cv_data['skills']:
                cv_data['subtitle'] = f"Specjalista {cv_data['skills'][0]}"
            else:
                cv_data['subtitle'] = 'Profesjonalista'
        
        return cv_data
        
    except Exception as e:
        logger.error(f"Error parsing CV: {str(e)}")
        return get_default_cv_data()

def process_section_content(cv_data, section, content):
    """
    Przetwarza zawartość sekcji CV
    """
    if section == 'summary':
        cv_data['summary'] = ' '.join(content)
    
    elif section == 'skills':
        for line in content:
            # Podziel umiejętności po przecinkach lub liniach
            if ',' in line:
                skills = [s.strip() for s in line.split(',') if s.strip()]
                cv_data['skills'].extend(skills)
            elif line.strip():
                cv_data['skills'].append(line.strip())
    
    elif section == 'experience':
        exp_item = parse_experience_item(content)
        if exp_item:
            cv_data['experience'].append(exp_item)
    
    elif section == 'education':
        edu_item = parse_education_item(content)
        if edu_item:
            cv_data['education'].append(edu_item)
    
    elif section == 'interests':
        for line in content:
            if ',' in line:
                interests = [i.strip() for i in line.split(',') if i.strip()]
                cv_data['interests'].extend(interests)
            elif line.strip():
                cv_data['interests'].append(line.strip())
    
    elif section == 'additional_info':
        cv_data['additional_info'].extend([line for line in content if line.strip()])

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
    
    # Pierwsza linia to prawdopodobnie stanowisko
    if content:
        exp['position'] = content[0]
    
    # Szukaj daty i firmy w kolejnych liniach
    for line in content[1:]:
        # Sprawdź czy zawiera datę
        if re.search(r'\d{4}', line) or any(month in line.lower() for month in 
                                          ['styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec',
                                           'lipiec', 'sierpień', 'wrzesień', 'październik', 'listopad', 'grudzień']):
            exp['period'] = line
        elif not exp['company'] and not line.startswith('-') and not line.startswith('•'):
            exp['company'] = line
        elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
            exp['responsibilities'].append(line.lstrip('- •*').strip())
        elif line.strip() and len(line) > 20:  # Prawdopodobnie opis obowiązków
            exp['responsibilities'].append(line.strip())
    
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
    
    if content:
        edu['title'] = content[0]
    
    for line in content[1:]:
        if re.search(r'\d{4}', line):
            edu['period'] = line
        elif not edu['institution']:
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
