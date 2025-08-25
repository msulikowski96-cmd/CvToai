
import os
import json
import logging
import requests
import urllib.parse
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables from .env file with override
load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Load and validate OpenRouter API key
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "sk-or-v1-demo-key-for-testing").strip()

# Validate API key format and content
def validate_api_key():
    if not OPENROUTER_API_KEY:
        logger.error("❌ OPENROUTER_API_KEY nie jest ustawiony w pliku .env")
        return False

    if OPENROUTER_API_KEY.startswith('TWÓJ_') or len(OPENROUTER_API_KEY) < 20:
        logger.error("❌ OPENROUTER_API_KEY w .env zawiera przykładową wartość - ustaw prawdziwy klucz!")
        return False

    if not OPENROUTER_API_KEY.startswith('sk-or-v1-'):
        logger.error("❌ OPENROUTER_API_KEY nie ma poprawnego formatu (powinien zaczynać się od 'sk-or-v1-')")
        return False

    logger.info(f"✅ OpenRouter API key załadowany poprawnie (długość: {len(OPENROUTER_API_KEY)})")
    return True

# Validate on module import
API_KEY_VALID = validate_api_key()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "qwen/qwen-2.5-72b-instruct:free"

# ZAAWANSOWANA KONFIGURACJA QWEN - MAKSYMALNA JAKOŚĆ
DEFAULT_MODEL = "qwen/qwen-2.5-72b-instruct:free"
PREMIUM_MODEL = "qwen/qwen-2.5-72b-instruct:free"
PAID_MODEL = "qwen/qwen-2.5-72b-instruct:free"
FREE_MODEL = "qwen/qwen-2.5-72b-instruct:free"

# OPTYMALIZOWANY PROMPT SYSTEMOWY DLA QWEN
DEEP_REASONING_PROMPT = """Jesteś światowej klasy ekspertem w rekrutacji i optymalizacji CV z 15-letnim doświadczeniem w branży HR. Posiadasz głęboką wiedzę o polskim rynku pracy, trendach rekrutacyjnych i najlepszych praktykach w tworzeniu CV."""

def make_openrouter_request(prompt, model=None, is_premium=False):
    """Make a request to OpenRouter API"""
    if not API_KEY_VALID:
        logger.error("API key is not valid")
        return None
    
    if model is None:
        model = PREMIUM_MODEL if is_premium else FREE_MODEL
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://cv-optimizer-pro.replit.app",
        "X-Title": "CV Optimizer Pro"
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": DEEP_REASONING_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
        "top_p": 0.9,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1
    }
    
    try:
        logger.info(f"Sending request to OpenRouter API with model: {model}")
        response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        else:
            raise ValueError("Nieoczekiwany format odpowiedzi API")

    except requests.exceptions.RequestException as e:
        logger.error(f"Błąd zapytania API: {str(e)}")
        return None

    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Błąd parsowania odpowiedzi API: {str(e)}")
        return None

def optimize_cv(cv_text, job_title, job_description="", is_premium=False):
    """Optimize CV for a specific job"""
    prompt = f"""
    ZADANIE: Zoptymalizuj poniższe CV pod stanowisko "{job_title}"

    OPIS STANOWISKA:
    {job_description}

    CV DO OPTYMALIZACJI:
    {cv_text}

    INSTRUKCJE:
    1. Dostosuj CV pod konkretne stanowisko
    2. Dodaj odpowiednie słowa kluczowe
    3. Popraw formatowanie i strukturę
    4. Zwiększ atrakcyjność dla rekruterów
    5. Zachowaj prawdziwość informacji
    6. Napisz w języku polskim

    Zwróć TYLKO zoptymalizowane CV bez dodatkowych komentarzy.
    """
    
    return make_openrouter_request(prompt, is_premium=is_premium)

def analyze_cv_with_score(cv_text, job_title, job_description="", is_premium=False):
    """Analyze CV and provide detailed feedback with score"""
    prompt = f"""
    ZADANIE: Przeanalizuj poniższe CV pod kątem stanowiska "{job_title}" i oceń je

    OPIS STANOWISKA:
    {job_description}

    CV DO ANALIZY:
    {cv_text}

    INSTRUKCJE:
    1. Oceń CV w skali 1-100 punktów
    2. Podaj szczegółową analizę mocnych stron
    3. Wskaż obszary do poprawy
    4. Zasugeruj konkretne zmiany
    5. Oceń dopasowanie do stanowiska
    6. Napisz w języku polskim

    FORMAT ODPOWIEDZI:
    OCENA: [liczba]/100

    MOCNE STRONY:
    - [punkt 1]
    - [punkt 2]

    OBSZARY DO POPRAWY:
    - [punkt 1]
    - [punkt 2]

    REKOMENDACJE:
    - [rekomendacja 1]
    - [rekomendacja 2]
    """
    
    return make_openrouter_request(prompt, is_premium=is_premium)

def generate_cover_letter(cv_text, job_title, job_description="", is_premium=False):
    """Generate cover letter based on CV and job description"""
    prompt = f"""
    ZADANIE: Napisz profesjonalny list motywacyjny na podstawie CV

    STANOWISKO: {job_title}
    
    OPIS STANOWISKA:
    {job_description}

    CV:
    {cv_text}

    INSTRUKCJE:
    1. Napisz profesjonalny list motywacyjny
    2. Dopasuj do stanowiska i firmy
    3. Podkreśl najważniejsze kwalifikacje z CV
    4. Użyj profesjonalnego tonu
    5. Napisz w języku polskim
    6. Długość: 3-4 akapity

    Zwróć TYLKO list motywacyjny bez dodatkowych komentarzy.
    """
    
    return make_openrouter_request(prompt, is_premium=is_premium)
