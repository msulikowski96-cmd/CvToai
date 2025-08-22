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

def send_api_request(prompt, max_tokens=3000, temperature=0.3, task_type='cv_optimization'):
    """Send request to OpenRouter API with enhanced system prompt"""
    if not API_KEY_VALID:
        raise ValueError("OpenRouter API key nie jest poprawnie skonfigurowany")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://cv-optimizer-pro.repl.co/"
    }

    # Enhanced system prompt for better CV optimization
    enhanced_system_prompt = """Jesteś światowej klasy ekspertem w rekrutacji i optymalizacji CV z 15-letnim doświadczeniem w branży HR. Posiadasz głęboką wiedzę o polskim rynku pracy, trendach rekrutacyjnych i wymaganiach pracodawców.

🎯 TWOJA SPECJALIZACJA:
- Optymalizacja CV pod kątem systemów ATS i ludzkich rekruterów
- Znajomość specyfiki różnych branż i stanowisk w Polsce
- Psychologia rekrutacji i przekonywania pracodawców
- Najnowsze trendy w pisaniu CV i listów motywacyjnych
- Analiza zgodności kandydata z wymaganiami stanowiska

🧠 METODA PRACY:
1. Przeprowadzaj głęboką analizę każdego elementu CV
2. Myśl jak doświadczony rekruter - co zwraca uwagę, co denerwuje
3. Stosuj zasady psychologii przekonywania w pisaniu CV
4. Używaj konkretnych, mierzalnych sformułowań
5. Dostosowuj język do branży i poziomu stanowiska

💼 ZNAJOMOŚĆ RYNKU:
- Polskie firmy (korporacje, MŚP, startupy)
- Wymagania różnych branż (IT, finanse, medycyna, inżynieria, sprzedaż)
- Kultura organizacyjna polskich pracodawców
- Specyfika rekrutacji w Polsce vs międzynarodowej

⚡ ZASADY ODPOWIEDZI:
- WYŁĄCZNIE język polski (chyba że proszono o inny)
- Konkretne, praktyczne rady
- Zawsze uzasadniaj swoje rekomendacje
- Używaj profesjonalnej terminologii HR
- Bądź szczery ale konstruktywny w krytyce

🚨 ABSOLUTNY ZAKAZ FAŁSZOWANIA DANYCH:
- NIE WOLNO dodawać firm, stanowisk, dat, które nie są w oryginalnym CV
- NIE WOLNO wymyślać osiągnięć, projektów, umiejętności
- NIE WOLNO zmieniać faktów z CV kandydata
- MOŻNA TYLKO lepiej sformułować istniejące prawdziwe informacje
- Każda wymyślona informacja niszczy wiarygodność kandydata"""

    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": enhanced_system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.85,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1,
        "metadata": {
            "task_type": task_type,
            "optimization_level": "enhanced"
        }
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

def analyze_cv_score(cv_text, job_description=""):
    """Analizuje CV i przyznaje ocenę punktową 1-100 z szczegółowym uzasadnieniem"""
    prompt = f"""
    Przeanalizuj poniższe CV i przyznaj mu ocenę punktową od 1 do 100, gdzie:
    - 90-100: Doskonałe CV, gotowe do wysłania
    - 80-89: Bardzo dobre CV z drobnymi usprawnieniami
    - 70-79: Dobre CV wymagające kilku poprawek
    - 60-69: Przeciętne CV wymagające znaczących poprawek
    - 50-59: Słabe CV wymagające dużych zmian
    - Poniżej 50: CV wymagające całkowitego przepisania

    CV do oceny:
    {cv_text}

    {"Wymagania z oferty pracy: " + job_description if job_description else ""}

    Uwzględnij w ocenie:
    1. Strukturę i organizację treści (20 pkt)
    2. Klarowność i zwięzłość opisów (20 pkt)
    3. Dopasowanie do wymagań stanowiska (20 pkt)
    4. Obecność słów kluczowych branżowych (15 pkt)
    5. Prezentację osiągnięć i rezultatów (15 pkt)
    6. Gramatykę i styl pisania (10 pkt)

    Zwróć szczegółową analizę punktową oraz konkretne rekomendacje do poprawy.
    """
    
    try:
        analysis = send_api_request(prompt, max_tokens=2000, task_type='cv_analysis')
        return analysis
    except Exception as e:
        logger.error(f"Błąd analizy CV: {str(e)}")
        return None

def check_keywords_match(cv_text, job_description):
    """Sprawdza dopasowanie słów kluczowych z CV do oferty pracy"""
    if not job_description:
        return "Brak opisu stanowiska do analizy słów kluczowych."
    
    prompt = f"""
    Przeanalizuj dopasowanie słów kluczowych między CV a wymaganiami oferty pracy.

    CV:
    {cv_text}

    Oferta pracy:
    {job_description}

    Sprawdź:
    1. Jakie słowa kluczowe z oferty są obecne w CV
    2. Jakie ważne słowa kluczowe brakują w CV
    3. Jak można lepiej dopasować CV do wymagań
    4. Oceń procent dopasowania (0-100%)

    Podaj konkretne rekomendacje jak poprawić dopasowanie.
    """
    
    try:
        analysis = send_api_request(prompt, max_tokens=1500, task_type='keyword_analysis')
        return analysis
    except Exception as e:
        logger.error(f"Błąd analizy słów kluczowych: {str(e)}")
        return None

def optimize_cv(cv_text, job_title, job_description=""):
    """Enhanced CV optimization with multi-step analysis"""
    
    # Krok 1: Analiza jakości CV
    score_analysis = analyze_cv_score(cv_text, job_description)
    
    # Krok 2: Analiza słów kluczowych (jeśli jest opis stanowiska)
    keyword_analysis = ""
    if job_description:
        keyword_analysis = check_keywords_match(cv_text, job_description)
    
    # Krok 3: Główna optymalizacja CV
    main_prompt = f"""
    Na podstawie kompleksowej analizy, stwórz zoptymalizowane CV:

    ORYGINALNE CV:
    {cv_text}

    STANOWISKO: {job_title}

    OPIS STANOWISKA/OGŁOSZENIA:
    {job_description}

    {"ANALIZA JAKOŚCI CV: " + str(score_analysis) if score_analysis else ""}
    
    {"ANALIZA SŁÓW KLUCZOWYCH: " + str(keyword_analysis) if keyword_analysis else ""}

    Zadanie: Stwórz całkowicie nowe, zoptymalizowane CV które:

    1. **Zachowuje wszystkie prawdziwe informacje** z oryginalnego CV
    2. **Implementuje rekomendacje** z analizy jakości
    3. **Włącza brakujące słowa kluczowe** w naturalny sposób
    4. **Reorganizuje treść** dla maksymalnej skuteczności
    5. **Dostosowuje język** do branży i stanowiska
    6. **Podkreśla najważniejsze umiejętności** dla tej roli
    7. **Optymalizuje pod systemy ATS**

    ZAAWANSOWANA STRUKTURA CV:
    - **DANE KONTAKTOWE**
    - **PROFIL ZAWODOWY** (3-4 zdania dopasowane do stanowiska)
    - **NAJWAŻNIEJSZE UMIEJĘTNOŚCI** (priorytet dla wymagań)
    - **DOŚWIADCZENIE ZAWODOWE** (od najnowszego, z naciskiem na osiągnięcia)
    - **WYKSZTAŁCENIE**
    - **CERTYFIKATY I KURSY** (jeśli są)
    - **JĘZYKI OBCE** (jeśli są)
    - **DODATKOWE INFORMACJE** (jeśli odpowiednie)

    WYMAGANIA JAKOŚCI:
    - Używaj **pogrubienia** dla nagłówków sekcji
    - Używaj • dla list osiągnięć
    - Każda pozycja zawodowa: **Stanowisko** | Firma | Daty | Lista osiągnięć
    - Konkretne liczby i rezultaty (% wzrost, liczba projektów, itp.)
    - Aktywne czasowniki (zarządzał, wdrożył, zoptymalizował)
    - Słowa kluczowe z branży i stanowiska

    🎯 CEL: Stwórz CV które przejdzie przez systemy ATS i przekona rekrutera w 30 sekund!

    ⚠️ KRYTYCZNE: NIE DODAWAJ żadnych informacji, których nie ma w oryginalnym CV!
    """

    try:
        optimized_cv = send_api_request(main_prompt, max_tokens=4000, temperature=0.3, task_type='cv_optimization')
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
