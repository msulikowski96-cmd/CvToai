import os
import json
import logging
import requests
import urllib.parse
import hashlib
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Create persistent session for connection reuse
session = requests.Session()
session.headers.update({
    'User-Agent': 'CV-Optimizer-Pro/1.0',
    'Connection': 'keep-alive'
})

# 💾 INTELLIGENT CACHING SYSTEM - oszczędza koszty API
_cache = {}
CACHE_DURATION = 3600  # 1 godzina w sekundach

def get_cache_key(prompt, models_to_try, is_premium):
    """Generuje unikalny klucz cache dla zapytania - POPRAWIONY"""
    # Używaj całej hierarchii modeli w kluczu
    models_str = "|".join(models_to_try)
    cache_data = f"{prompt[:500]}|{models_str}|{is_premium}"
    return hashlib.md5(cache_data.encode()).hexdigest()

def get_from_cache(cache_key):
    """Pobiera odpowiedź z cache jeśli jest aktualna"""
    if cache_key in _cache:
        cached_response, model_used, timestamp = _cache[cache_key]
        if time.time() - timestamp < CACHE_DURATION:
            logger.info(f"💾 Cache hit! Zwracam odpowiedź z cache (model: {model_used}, oszczędności API)")
            return cached_response
        else:
            # Usuń przestarzały cache
            del _cache[cache_key]
    return None

def save_to_cache(cache_key, response, model_used):
    """Zapisuje odpowiedź do cache z informacją o użytym modelu"""
    _cache[cache_key] = (response, model_used, time.time())
    
    # Czyść stary cache co jakiś czas (maksymalnie 100 wpisów)
    if len(_cache) > 100:
        # Usuń najstarsze wpisy
        sorted_cache = sorted(_cache.items(), key=lambda x: x[1][2])  # Sortuj po timestamp (3rd element)
        for key, _ in sorted_cache[:20]:  # Usuń 20 najstarszych
            del _cache[key]
    
    logger.info(f"💾 Zapisano do cache (obecny rozmiar: {len(_cache)} wpisów)")

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

    if (OPENROUTER_API_KEY.startswith('TWÓJ_') or 
        len(OPENROUTER_API_KEY) < 20 or 
        OPENROUTER_API_KEY == "sk-or-v1-demo-key-for-testing"):
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

# WYŁĄCZNIE JEDEN MODEL QWEN ZGODNIE Z ŻYCZENIEM UŻYTKOWNIKA
SINGLE_MODEL = "qwen/qwen3-235b-a22b:free"

# NAJNOWSZY PROMPT SYSTEMOWY 2025 - MAKSYMALNA JAKOŚĆ AI
DEEP_REASONING_PROMPT = """Jesteś ekspertem świata w optymalizacji CV z 20-letnim doświadczeniem w rekrutacji oraz AI. Masz specjalistyczną wiedzę o:

🎯 KOMPETENCJE GŁÓWNE:
- Analiza CV pod kątem systemów ATS (Applicant Tracking Systems)
- Optymalizacja pod konkretne stanowiska i branże w Polsce
- Psychologia rekrutacji i co przyciąga uwagę HR-owców
- Najnowsze trendy rynku pracy 2025 w Polsce i UE
- Formatowanie CV zgodne z europejskimi standardami

🧠 STRATEGIA MYŚLENIA:
1. ANALIZUJ głęboko każde słowo w kontekście stanowiska
2. DOPASUJ język i terminologię do branży
3. OPTYMALIZUJ pod kątem słów kluczowych ATS
4. ZACHOWAJ autentyczność i prawdę o kandydacie
5. ZASTOSUJ najlepsze praktyki formatowania

⚡ JAKOŚĆ ODPOWIEDZI:
- Używaj precyzyjnego, profesjonalnego języka polskiego
- Dawaj konkretne, actionable wskazówki
- Uwzględniaj cultural fit dla polskiego rynku pracy
- Bądź kreatywny ale faktualny w opisach doświadczenia

Twoja misja: Stworzyć CV które przejdzie przez ATS i zachwyci rekruterów."""


# UPROSZCZONA FUNKCJA - TYLKO JEDEN MODEL
def get_single_model():
    """Zwraca jedyny dozwolony model"""
    return SINGLE_MODEL


def make_openrouter_request(prompt, model=None, is_premium=False, max_retries=3, max_tokens=None, use_streaming=False, use_cache=True):
    """
    🚀 UPROSZCZONA FUNKCJA - TYLKO JEDEN MODEL QWEN
    """
    if not API_KEY_VALID:
        logger.error("API key is not valid")
        return None

    # UŻYWAMY TYLKO JEDNEGO MODELU
    model_to_use = SINGLE_MODEL
    logger.info(f"🤖 Używam wyłącznie model: {model_to_use}")

    # 💾 SPRAWDŹ CACHE NAJPIERW 
    cache_key = get_cache_key(prompt, [model_to_use], is_premium)
    
    if use_cache:
        cached_response = get_from_cache(cache_key)
        if cached_response:
            return cached_response

    # Parametry zoptymalizowane dla Qwen
    params = {
        "temperature": 0.3,          # Stabilna temperatura dla Qwen
        "top_p": 0.9,               # Dobre fokusowanie na najlepszych tokenach
        "frequency_penalty": 0.1,    # Unikaj powtórzeń
        "presence_penalty": 0.1,     # Zachęcaj do różnorodności
        "max_tokens": max_tokens or 3500  # Dobre długie odpowiedzi
    }
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://cv-optimizer-pro.replit.app",
        "X-Title": "CV Optimizer Pro"
    }

    data = {
        "model": model_to_use,
        "messages": [{
            "role": "system", 
            "content": DEEP_REASONING_PROMPT
        }, {
            "role": "user",
            "content": prompt
        }],
        **params
    }

    # Próbuj z retry mechanism
    for attempt in range(max_retries):
        try:
            logger.info(f"📡 Sending request to OpenRouter API (attempt {attempt + 1}/{max_retries}) with model: {model_to_use}")

            response = session.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=data,
                timeout=(5, 45),
                stream=use_streaming
            )
            response.raise_for_status()

            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                logger.info(f"✅ Model {model_to_use} zwrócił odpowiedź (długość: {len(content)} znaków)")
                
                # 💾 ZAPISZ DO CACHE
                if use_cache:
                    save_to_cache(cache_key, content, model_to_use)
                    
                return content
            else:
                logger.warning(f"⚠️ Nieoczekiwany format odpowiedzi: {result}")
                        
        except requests.exceptions.Timeout:
            logger.warning(f"⏰ Timeout na próbie {attempt + 1}")
                        
        except requests.exceptions.RequestException as e:
            logger.warning(f"🚫 Błąd zapytania na próbie {attempt + 1}: {str(e)}")
                        
        except Exception as e:
            logger.warning(f"❌ Nieoczekiwany błąd: {str(e)}")
        
        # Opóźnienie przed ponowną próbą
        if attempt < max_retries - 1:
            import time
            time.sleep(1.5)
    
    # Jeśli wszystkie próby zawiodły
    logger.error(f"❌ Model {model_to_use} nie odpowiedział po {max_retries} próbach")
    return None


def optimize_cv(cv_text, job_title, job_description="", is_premium=False, payment_verified=False):
    """
    Optymalizuje CV za pomocą OpenRouter AI (Claude 3.5 Sonnet) i formatuje w profesjonalnym szablonie HTML
    """
    prompt = f"""
    Jesteś ekspertem od optymalizacji CV. Twoim zadaniem jest przepisanie podanego CV tak, aby było bardziej atrakcyjne dla rekruterów i lepiej dopasowane do stanowiska: {job_title}

    ZASADY OPTYMALIZACJI:
    1. NIE DODAWAJ żadnych fałszywych informacji
    2. NIE WYMIŚLAJ stanowisk, firm, dat ani umiejętności
    3. PRZEPISZ tylko to co jest w oryginalnym CV
    4. ULEPSZAJ sformułowania używając słów kluczowych z opisu stanowiska
    5. ZACHOWAJ wszystkie prawdziwe fakty z oryginalnego CV

    [PODSUMOWANIE ZAWODOWE] 
    - Stwórz zwięzłe podsumowanie na podstawie doświadczenia z CV
    - 2-3 zdania o kluczowych umiejętnościach i doświadczeniu
    - Użyj tylko faktów z oryginalnego CV

    [DOŚWIADCZENIE ZAWODOWE]
    - KRYTYCZNY FORMAT: Każde stanowisko musi zaczynać się od "--- STANOWISKO ---"
    - Struktura każdego stanowiska:
      --- STANOWISKO ---
      **Nazwa stanowiska**
      **Nazwa firmy**
      *Okres pracy (rok-rok)*
      - Pierwszy obowiązek
      - Drugi obowiązek  
      - Trzeci obowiązek
      
    - Zachowaj wszystkie firmy, stanowiska i daty z oryginału
    - Przepisz opisy obowiązków używając lepszych czasowników akcji
    - Każde stanowisko: 3-4 punkty z konkretnymi obowiązkami
    - KONIECZNIE używaj separatora "--- STANOWISKO ---" przed każdym nowym stanowiskiem
    - Różnicuj opisy podobnych stanowisk

    [WYKSZTAŁCENIE]
    - Przepisz dokładnie informacje z oryginalnego CV
    - Nie dodawaj kursów których nie ma w oryginale

    [UMIEJĘTNOŚCI]
    - Użyj tylko umiejętności wymienione w oryginalnym CV
    - Pogrupuj je logicznie (Techniczne, Komunikacyjne, itp.)

    ORYGINALNE CV:
    {cv_text}

    OPIS STANOWISKA (dla kontekstu):
    {job_description}

    ZWRÓĆ TYLKO KOMPLETNY TEKST ZOPTYMALIZOWANEGO CV - nic więcej.
    Nie dodawaj JSON, metadanych ani komentarzy.
    Po prostu wygeneruj gotowe CV do użycia.
    """

    # Rozszerzony limit tokenów dla płacących użytkowników
    if is_premium or payment_verified:
        max_tokens = 4000
        prompt += f"""

    DODATKOWE INSTRUKCJE DLA UŻYTKOWNIKÓW PREMIUM:
    - Stwórz bardziej szczegółowe opisy stanowisk (4-5 punktów zamiast 3-4)
    - Dodaj więcej słów kluczowych z branży
    - Ulepszaj strukturę CV dla maksymalnej czytelności
    - Optymalizuj pod systemy ATS (Applicant Tracking Systems)
    """
    else:
        max_tokens = 2500

    try:
        response = make_openrouter_request(
            prompt, 
            is_premium=(is_premium or payment_verified),
            max_tokens=max_tokens
        )

        if response:
            # Zwróć zoptymalizowane CV jako sformatowany tekst
            # HTML będzie generowany dopiero przy wyświetlaniu w view_cv
            return response.strip()
        else:
            logger.error("Empty response from OpenRouter API")
            return None

    except Exception as e:
        logger.error(f"Error in optimize_cv: {str(e)}")
        return None


def analyze_cv_quality(cv_text, job_title, job_description="", is_premium=False):
    """
    Zaawansowana analiza jakości CV z oceną 0-100 punktów i szczegółowymi wskazówkami AI
    """
    try:
        # Bardziej zaawansowany prompt dla lepszej analizy
        prompt = f"""
🎯 ZADANIE: Przeprowadź PROFESJONALNĄ ANALIZĘ JAKOŚCI CV dla stanowiska "{job_title}"

📋 DANE WEJŚCIOWE:
CV DO ANALIZY:
{cv_text[:4000]}

OPIS STANOWISKA:
{job_description[:2000]}

🔍 KRYTERIA OCENY (każde 0-20 punktów):
1. **STRUKTURA I FORMATOWANIE** (0-20p)
   - Czytelność i organizacja sekcji
   - Użycie właściwych nagłówków
   - Długość i proporcje treści

2. **JAKOŚĆ TREŚCI** (0-20p)
   - Konkretne osiągnięcia i wyniki
   - Użycie liczb i metryk
   - Profesjonalizm opisów

3. **DOPASOWANIE DO STANOWISKA** (0-20p)
   - Zgodność z wymaganiami
   - Słowa kluczowe z oferty
   - Relevantne doświadczenie

4. **DOŚWIADCZENIE I UMIEJĘTNOŚCI** (0-20p)
   - Progresja kariery
   - Różnorodność umiejętności
   - Poziom senioratu

5. **KOMPLETNOŚĆ I SZCZEGÓŁY** (0-20p)
   - Wszystkie potrzebne sekcje
   - Daty i okresy pracy
   - Informacje kontaktowe

📊 WYMAGANY FORMAT ODPOWIEDZI:
```
OCENA KOŃCOWA: [0-100]/100

SZCZEGÓŁOWA PUNKTACJA:
• Struktura i formatowanie: [0-20]/20
• Jakość treści: [0-20]/20  
• Dopasowanie do stanowiska: [0-20]/20
• Doświadczenie i umiejętności: [0-20]/20
• Kompletność i szczegóły: [0-20]/20

🟢 MOCNE STRONY:
- [minimum 3 konkretne punkty]

🟡 OBSZARY DO POPRAWY:
- [minimum 3 konkretne sugestie]

🔥 KLUCZOWE REKOMENDACJE:
- [3-5 najważniejszych zmian do wprowadzenia]

💡 SŁOWA KLUCZOWE DO DODANIA:
- [5-7 słów kluczowych z opisu stanowiska]

🎯 WSKAZÓWKI BRANŻOWE:
- [2-3 specyficzne porady dla tej branży/stanowiska]
```

✅ DODATKOWE INSTRUKCJE:
- Bądź konkretny i praktyczny
- Wskaż dokładnie CO i GDZIE poprawić
- Oceń realistycznie ale konstruktywnie
- Napisz w języku polskim
- Używaj emoji dla lepszej czytelności
"""

        # Użyj lepszych parametrów dla premium użytkowników
        max_tokens = 3000 if is_premium else 2000
        
        logger.info(f"🔍 Analizowanie jakości CV dla stanowiska: {job_title}")
        
        response = make_openrouter_request(
            prompt, 
            is_premium=is_premium,
            max_tokens=max_tokens
        )
        
        if response:
            logger.info(f"✅ Analiza CV ukończona pomyślnie (długość: {len(response)} znaków)")
            return response.strip()
        else:
            logger.error("❌ Brak odpowiedzi z API lub nieprawidłowa struktura")
            return None
            
    except Exception as e:
        logger.error(f"❌ Błąd podczas analizy CV: {str(e)}")
        return None


def analyze_cv_with_score(cv_text, job_title, job_description="", is_premium=False):
    """Zachowanie kompatybilności z istniejącym kodem - przekierowanie do nowej funkcji"""
    return analyze_cv_quality(cv_text, job_title, job_description, is_premium)


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
                'model_used': SINGLE_MODEL
            }
        else:
            logger.error("❌ Brak odpowiedzi z API lub nieprawidłowa struktura")
            return None

    except Exception as e:
        logger.error(
            f"❌ Błąd podczas generowania listu motywacyjnego: {str(e)}")
        return None


def generate_interview_questions(cv_text, job_title, job_description="", is_premium=False):
    """
    Generuje personalizowane pytania na rozmowę kwalifikacyjną na podstawie CV i opisu stanowiska
    """
    try:
        job_desc_info = f"\n\nOpis stanowiska:\n{job_description}" if job_description else ""

        prompt = f"""
    🎯 ZADANIE: Wygeneruj personalizowane pytania na rozmowę kwalifikacyjną w języku polskim

    📋 DANE WEJŚCIOWE:
    • Stanowisko: {job_title}
    • CV kandydata: {cv_text[:3000]}...{job_desc_info}

    ✅ WYMAGANIA PYTAŃ:
    1. 10-15 pytań dostosowanych do profilu kandydata
    2. Pytania powinny być różnorodne: techniczne, behawioralne, sytuacyjne
    3. Uwzględnij doświadczenie i umiejętności z CV
    4. Dodaj pytania specyficzne dla branży i stanowiska
    5. Uwzględnij poziom doświadczenia kandydata

    📝 KATEGORIE PYTAŃ:
    1. **Pytania podstawowe** - o doświadczeniu i motywacji
    2. **Pytania techniczne** - o konkretne umiejętności z CV
    3. **Pytania behawioralne** - o sytuacje i zachowania
    4. **Pytania sytuacyjne** - scenariusze problemowe
    5. **Pytania o firmę** - zainteresowanie pozycją i firmą

    🎤 FORMAT ODPOWIEDZI:
    PYTANIA PODSTAWOWE:
    1. [pytanie]
    2. [pytanie]

    PYTANIA TECHNICZNE:
    1. [pytanie]
    2. [pytanie]

    PYTANIA BEHAWIORALNE:
    1. [pytanie]
    2. [pytanie]

    PYTANIA SYTUACYJNE:
    1. [pytanie]
    2. [pytanie]

    PYTANIA O FIRMĘ I STANOWISKO:
    1. [pytanie]
    2. [pytanie]

    🚀 WSKAZÓWKI:
    • Każde pytanie powinno być konkretne i merytoryczne
    • Uwzględnij słowa kluczowe z opisu stanowiska
    • Dostosuj poziom trudności do doświadczenia kandydata
    • Dodaj pytania sprawdzające soft skills

    Wygeneruj teraz personalizowane pytania na rozmowę kwalifikacyjną:
            """

        logger.info(f"🤔 Generowanie pytań na rozmowę dla stanowiska: {job_title}")

        questions = make_openrouter_request(prompt, is_premium=is_premium)

        if questions:
            logger.info(f"✅ Pytania na rozmowę wygenerowane pomyślnie (długość: {len(questions)} znaków)")

            return {
                'success': True,
                'questions': questions,
                'job_title': job_title,
                'model_used': SINGLE_MODEL
            }
        else:
            logger.error("❌ Brak odpowiedzi z API lub nieprawidłowa struktura")
            return None

    except Exception as e:
        logger.error(f"❌ Błąd podczas generowania pytań na rozmowę: {str(e)}")
        return None


def analyze_skills_gap(cv_text, job_title, job_description="", is_premium=False):
    """
    Analizuje luki kompetencyjne między CV a wymaganiami stanowiska
    """
    try:
        job_desc_info = f"\n\nOpis stanowiska:\n{job_description}" if job_description else ""

        prompt = f"""
    🎯 ZADANIE: Przeprowadź szczegółową analizę luk kompetencyjnych w języku polskim

    📋 DANE WEJŚCIOWE:
    • Stanowisko: {job_title}
    • CV kandydata: {cv_text[:3000]}...{job_desc_info}

    ✅ CELE ANALIZY:
    1. Porównaj umiejętności z CV z wymaganiami stanowiska
    2. Zidentyfikuj mocne strony kandydata
    3. Wykryj luki kompetencyjne i brakujące umiejętności
    4. Zasugeruj sposoby rozwoju i uzupełnienia braków
    5. Oceń ogólne dopasowanie do stanowiska (0-100%)

    📊 FORMAT ODPOWIEDZI:

    OCENA OGÓLNA: [XX]% dopasowania do stanowiska

    MOCNE STRONY KANDYDATA:
    ✅ [umiejętność 1] - [krótkie uzasadnienie]
    ✅ [umiejętność 2] - [krótkie uzasadnienie]
    ✅ [umiejętność 3] - [krótkie uzasadnienie]

    LUKI KOMPETENCYJNE:
    ❌ [brakująca umiejętność 1] - [dlaczego jest potrzebna]
    ❌ [brakująca umiejętność 2] - [dlaczego jest potrzebna]
    ❌ [brakująca umiejętność 3] - [dlaczego jest potrzebna]

    REKOMENDACJE ROZWOJU:
    🎓 [konkretna rekomendacja 1] - [kurs/certyfikat/doświadczenie]
    🎓 [konkretna rekomendacja 2] - [kurs/certyfikat/doświadczenie]
    🎓 [konkretna rekomendacja 3] - [kurs/certyfikat/doświadczenie]

    PRIORYTET ROZWOJU:
    🔥 WYSOKI PRIORYTET: [umiejętności kluczowe dla stanowiska]
    🔸 ŚREDNI PRIORYTET: [umiejętności przydatne]
    🔹 NISKI PRIORYTET: [umiejętności dodatkowe]

    PLAN DZIAŁANIA (3-6 miesięcy):
    1. [konkretny krok do podjęcia]
    2. [konkretny krok do podjęcia]
    3. [konkretny krok do podjęcia]

    🚀 WSKAZÓWKI:
    • Skup się na umiejętnościach technicznych i soft skills
    • Uwzględnij trendy w branży
    • Zasugeruj konkretne zasoby edukacyjne
    • Oceń realność pozyskania brakujących kompetencji

    Przeprowadź teraz szczegółową analizę luk kompetencyjnych:
            """

        logger.info(f"🔍 Analiza luk kompetencyjnych dla stanowiska: {job_title}")

        analysis = make_openrouter_request(prompt, is_premium=is_premium)

        if analysis:
            logger.info(f"✅ Analiza luk kompetencyjnych ukończona pomyślnie (długość: {len(analysis)} znaków)")

            return {
                'success': True,
                'analysis': analysis,
                'job_title': job_title,
                'model_used': SINGLE_MODEL
            }
        else:
            logger.error("❌ Brak odpowiedzi z API lub nieprawidłowa struktura")
            return None

    except Exception as e:
        logger.error(f"❌ Błąd podczas analizy luk kompetencyjnych: {str(e)}")
        return None