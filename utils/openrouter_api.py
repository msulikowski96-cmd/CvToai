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
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY",
                                    "sk-or-v1-demo-key-for-testing").strip()


# Validate API key format and content
def validate_api_key():
    if not OPENROUTER_API_KEY:
        logger.error("❌ OPENROUTER_API_KEY nie jest ustawiony w pliku .env")
        return False

    if OPENROUTER_API_KEY.startswith('TWÓJ_') or len(OPENROUTER_API_KEY) < 20:
        logger.error(
            "❌ OPENROUTER_API_KEY w .env zawiera przykładową wartość - ustaw prawdziwy klucz!"
        )
        return False

    if not OPENROUTER_API_KEY.startswith('sk-or-v1-'):
        logger.error(
            "❌ OPENROUTER_API_KEY nie ma poprawnego formatu (powinien zaczynać się od 'sk-or-v1-')"
        )
        return False

    logger.info(
        f"✅ OpenRouter API key załadowany poprawnie (długość: {len(OPENROUTER_API_KEY)})"
    )
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


def make_openrouter_request(prompt, model=None, is_premium=False, max_retries=2):
    """Make a request to OpenRouter API with retry mechanism"""
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
        "messages": [{
            "role": "system",
            "content": DEEP_REASONING_PROMPT
        }, {
            "role": "user",
            "content": prompt
        }],
        "temperature": 0.3,
        "max_tokens": 3000,  # Zmniejszone dla szybszej odpowiedzi
        "top_p": 0.9,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1
    }

    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Sending request to OpenRouter API (attempt {attempt + 1}/{max_retries + 1}) with model: {model}")

            # Zoptymalizowany timeout dla stabilności
            response = requests.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=data,
                timeout=(5, 60),  # (connection timeout, read timeout)
                stream=False
            )
            response.raise_for_status()

            result = response.json()
            logger.debug(f"Raw API response: {result}")

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                logger.info(f"✅ OpenRouter API zwróciło odpowiedź (długość: {len(content)} znaków)")
                return content
            else:
                logger.error(f"❌ Nieoczekiwany format odpowiedzi API: {result}")
                if attempt == max_retries:
                    raise ValueError("Nieoczekiwany format odpowiedzi API")

        except requests.exceptions.Timeout as e:
            logger.warning(f"Timeout na próbie {attempt + 1}: {str(e)}")
            if attempt == max_retries:
                logger.error("Przekroczono maksymalną liczbę prób - timeout")
                return None
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Błąd połączenia na próbie {attempt + 1}: {str(e)}")
            if attempt == max_retries:
                logger.error("Przekroczono maksymalną liczbę prób - błąd połączenia")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Błąd zapytania API: {str(e)}")
            if attempt == max_retries:
                return None
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Błąd parsowania odpowiedzi API: {str(e)}")
            if attempt == max_retries:
                return None

        # Krótkie opóźnienie przed ponowną próbą
        if attempt < max_retries:
            import time
            time.sleep(1)

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


def analyze_cv_with_score(cv_text,
                          job_title,
                          job_description="",
                          is_premium=False):
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


def generate_cover_letter(cv_text,
                          job_title,
                          job_description="",
                          company_name="",
                          is_premium=False):
    """
    Generuje profesjonalny list motywacyjny na podstawie CV i opisu stanowiska używając AI
    """
    try:
        # Przygotowanie danych firmy
        company_info = f" w firmie {company_name}" if company_name else ""
        job_desc_info = f"\n\nOpis stanowiska:\n{job_description}" if job_description else ""

        prompt = f"""
🎯 ZADANIE: Wygeneruj profesjonalny list motywacyjny w języku polskim

📋 DANE WEJŚCIOWE:
• Stanowisko: {job_title}{company_info}
• CV kandydata: {cv_text[:3000]}...{job_desc_info}

✅ WYMAGANIA LISTU MOTYWACYJNEGO:
1. Format profesjonalny (nagłówek, zwroty grzecznościowe, podpis)
2. Długość: 3-4 akapity (około 250-350 słów)
3. Personalizacja pod konkretne stanowisko
4. Podkreślenie najważniejszych kwalifikacji z CV
5. Wykazanie motywacji i zaangażowania
6. Profesjonalny, ale ciepły ton komunikacji

📝 STRUKTURA LISTU:
1. **Nagłówek** - data, zwrot grzecznościowy
2. **Wstęp** - przedstawienie się i cel listu
3. **Główna część** - kwalifikacje, doświadczenie, motywacja
4. **Zakończenie** - zaproszenie do kontaktu, podziękowania
5. **Podpis** - zwroty końcowe

🚀 DODATKOWE WSKAZÓWKI:
• Użyj konkretnych przykładów z CV
• Dostosuj ton do branży i stanowiska
• Podkreśl wartość, jaką kandydat wniesie do firmy
• Unikaj powtarzania informacji z CV - uzupełnij je
• Zachowaj autentyczność i profesjonalizm

Wygeneruj teraz kompletny list motywacyjny:
        """

        logger.info(
            f"📧 Generowanie listu motywacyjnego dla stanowiska: {job_title}")

        cover_letter = make_openrouter_request(prompt, is_premium=is_premium)

        if cover_letter:
            logger.info(
                f"✅ List motywacyjny wygenerowany pomyślnie (długość: {len(cover_letter)} znaków)"
            )

            return {
                'success': True,
                'cover_letter': cover_letter,
                'job_title': job_title,
                'company_name': company_name,
                'model_used': PREMIUM_MODEL if is_premium else FREE_MODEL
            }
        else:
            logger.error("❌ Brak odpowiedzi z API lub nieprawidłowa struktura")
            return None

    except Exception as e:
        logger.error(
            f"❌ Błąd podczas generowania listu motywacyjnego: {str(e)}")
        return None