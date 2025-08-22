import os
import json
import logging
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

logger = logging.getLogger(__name__)

# OpenRouter API configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen-2.5-72b-instruct:free"

def validate_api_key():
    """Validate OpenRouter API key"""
    if not OPENROUTER_API_KEY:
        logger.error("❌ OPENROUTER_API_KEY nie jest ustawiony")
        return False

    if OPENROUTER_API_KEY.startswith('TWÓJ_') or len(OPENROUTER_API_KEY) < 20:
        logger.error("❌ OPENROUTER_API_KEY zawiera przykładową wartość")
        return False

    if not OPENROUTER_API_KEY.startswith('sk-or-v1-'):
        logger.error("❌ OPENROUTER_API_KEY nie ma poprawnego formatu")
        return False

    logger.info("✅ OpenRouter API key załadowany poprawnie")
    return True

# Validate on module import
API_KEY_VALID = validate_api_key()

def send_api_request(prompt, max_tokens=3000, temperature=0.7):
    """Send request to OpenRouter API"""
    if not API_KEY_VALID:
        raise ValueError("OpenRouter API key nie jest poprawnie skonfigurowany")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://cv-optimizer-pro.repl.co/"
    }

    system_prompt = """Jesteś ekspertem w optymalizacji CV i doradcą kariery. 
    Twoja specjalizacja to:
    - Optymalizacja CV pod kątem systemów ATS i rekruterów
    - Znajomość polskiego rynku pracy
    - Pisanie profesjonalnych CV dostosowanych do stanowisk
    
    WAŻNE ZASADY:
    - ZAWSZE odpowiadaj w języku polskim
    - NIE DODAWAJ żadnych nowych firm, stanowisk, dat ani osiągnięć które nie są w oryginalnym CV
    - MOŻNA TYLKO lepiej sformułować istniejące prawdziwe informacje
    - Używaj profesjonalnej terminologii HR
    - Skoncentruj się na klarowności i skuteczności przekazu"""

    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.85,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1
    }

    try:
        logger.debug("Wysyłanie zapytania do OpenRouter API")
        response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        logger.debug("Otrzymano odpowiedź z OpenRouter API")

        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        else:
            raise ValueError("Nieoczekiwany format odpowiedzi API")

    except requests.exceptions.RequestException as e:
        logger.error(f"Błąd zapytania API: {str(e)}")
        raise Exception(f"Nie udało się połączyć z OpenRouter API: {str(e)}")

    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Błąd parsowania odpowiedzi API: {str(e)}")
        raise Exception(f"Nie udało się przetworzyć odpowiedzi OpenRouter API: {str(e)}")

def optimize_cv(cv_text, job_title, job_description=""):
    """Optimize CV for specific position"""
    # Demo mode if no API key
    if not API_KEY_VALID:
        return generate_demo_cv_optimization(cv_text, job_title, job_description)
    
    prompt = f"""
    Stwórz całkowicie nowe, zoptymalizowane CV na podstawie poniższych informacji.

    ORYGINALNE CV:
    {cv_text}

    STANOWISKO: {job_title}

    OPIS STANOWISKA/OGŁOSZENIA:
    {job_description}

    Zadanie: Napisz całkowicie nowe, profesjonalne CV które:

    1. **Zachowuje wszystkie prawdziwe informacje** z oryginalnego CV
    2. **Reorganizuje treść** dla maksymalnej skuteczności
    3. **Dostosowuje język** do branży i stanowiska
    4. **Podkreśla najważniejsze umiejętności** dla tej roli
    5. **Używa słów kluczowych** z opisu stanowiska
    6. **Poprawia strukturę i czytelność**
    7. **Optymalizuje pod systemy ATS**

    STRUKTURA NOWEGO CV:
    - Dane kontaktowe
    - Profil zawodowy / Podsumowanie (3-4 zdania)
    - Doświadczenie zawodowe (od najnowszego)
    - Wykształcenie
    - Umiejętności techniczne/kluczowe
    - Języki obce (jeśli są)
    - Dodatkowe informacje (certyfikaty, kursy, itp.)

    WYMAGANIA FORMATOWANIA:
    - Używaj **pogrubienia** dla nagłówków sekcji
    - Używaj • dla list
    - Zachowaj profesjonalną strukturę
    - Każda pozycja zawodowa: Stanowisko | Firma | Daty | Opis osiągnięć
    - Skupiaj się na konkretnych osiągnięciach i rezultatach

    ⚠️ KRYTYCZNE: NIE DODAWAJ żadnych informacji, których nie ma w oryginalnym CV!
    """

    try:
        optimized_cv = send_api_request(prompt, max_tokens=3000, temperature=0.3)
        return optimized_cv
    except Exception as e:
        logger.error(f"Błąd optymalizacji CV: {str(e)}")
        return None

def generate_demo_cv_optimization(cv_text, job_title, job_description=""):
    """Generate demo CV optimization when API key is not available"""
    return f"""
**DEMO: ZOPTYMALIZOWANE CV dla stanowiska {job_title}**

*To jest przykład optymalizacji CV. Aby otrzymać pełną optymalizację AI, skonfiguruj OPENROUTER_API_KEY.*

---

**PROFIL ZAWODOWY**
[Bazując na przesłanym CV] - profesjonalista z doświadczeniem dopasowanym do wymagań stanowiska {job_title}. 

**DOŚWIADCZENIE ZAWODOWE**
[Zreorganizowane informacje z oryginalnego CV z fokusem na umiejętności wymagane dla {job_title}]

**UMIEJĘTNOŚCI KLUCZOWE**
• Umiejętności techniczne dopasowane do {job_title}
• Doświadczenie branżowe zgodne z wymaganiami
• Kompetencje miękkie ważne dla tej roli

**WYKSZTAŁCENIE**
[Informacje o wykształceniu z oryginalnego CV]

**JĘZYKI OBCE**
[Jeśli występują w oryginalnym CV]

---
*UWAGA: To jest wersja demonstracyjna. Pełna optymalizacja AI wymaga konfiguracji klucza API.*

**ORYGINALNE CV:**
{cv_text[:500]}...
"""
