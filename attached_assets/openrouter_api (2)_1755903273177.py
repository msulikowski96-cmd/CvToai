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
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()

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
DEEP_REASONING_PROMPT = """Jesteś światowej klasy ekspertem w rekrutacji i optymalizacji CV z 15-letnim doświadczeniem w branży HR. Posiadasz głęboką wiedzę o polskim rynku pracy, trendach rekrutacyjnych i wymaganiach pracodawców.

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

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://cv-optimizer-pro.repl.co/"
}

def send_api_request(prompt, max_tokens=2000, language='pl', user_tier='free', task_type='default', industry='general'):
    """
    Send a request to the OpenRouter API with enhanced configuration
    """
    if not OPENROUTER_API_KEY or not API_KEY_VALID:
        error_msg = "OpenRouter API key nie jest poprawnie skonfigurowany w pliku .env"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Language-specific system prompts
    language_prompts = {
        'pl': "Jesteś ekspertem w optymalizacji CV i doradcą kariery. ZAWSZE odpowiadaj w języku polskim, niezależnie od języka CV lub opisu pracy. Używaj polskiej terminologii HR i poprawnej polszczyzny. KRYTYCZNE: NIE DODAWAJ żadnych nowych firm, stanowisk, dat ani osiągnięć które nie są w oryginalnym CV - to oszukiwanie kandydata!",
        'en': "You are an expert resume editor and career advisor. ALWAYS respond in English, regardless of the language of the CV or job description. Use proper English HR terminology and grammar. CRITICAL: DO NOT ADD any new companies, positions, dates or achievements that are not in the original CV - this is deceiving the candidate!"
    }

    system_prompt = get_enhanced_system_prompt(task_type, language) + "\n" + language_prompts.get(language, language_prompts['pl'])

    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "top_p": 0.85,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1,
        "metadata": {
            "user_tier": user_tier,
            "task_type": task_type,
            "model_used": DEFAULT_MODEL,
            "optimization_level": "advanced",
            "industry": industry,
            "language": language
        }
    }

    try:
        logger.debug(f"Sending request to OpenRouter API")
        response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        logger.debug("Received response from OpenRouter API")

        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        else:
            raise ValueError("Unexpected API response format")

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        raise Exception(f"Failed to communicate with OpenRouter API: {str(e)}")

    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Error parsing API response: {str(e)}")
        raise Exception(f"Failed to parse OpenRouter API response: {str(e)}")

def analyze_cv_score(cv_text, job_description="", language='pl'):
    """
    Analizuje CV i przyznaje ocenę punktową 1-100 z szczegółowym uzasadnieniem
    """
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

    Odpowiedź w formacie JSON:
    {{
        "score": [liczba 1-100],
        "grade": "[A+/A/B+/B/C+/C/D/F]",
        "category_scores": {{
            "structure": [1-20],
            "clarity": [1-20], 
            "job_match": [1-20],
            "keywords": [1-15],
            "achievements": [1-15],
            "language": [1-10]
        }},
        "strengths": ["punkt mocny 1", "punkt mocny 2", "punkt mocny 3"],
        "weaknesses": ["słabość 1", "słabość 2", "słabość 3"],
        "recommendations": ["rekomendacja 1", "rekomendacja 2", "rekomendacja 3"],
        "summary": "Krótkie podsumowanie oceny CV"
    }}
    """
    return send_api_request(
        prompt, 
        max_tokens=2500, 
        language=language,
        user_tier='free',
        task_type='cv_optimization'
    )

def analyze_keywords_match(cv_text, job_description, language='pl'):
    """
    Analizuje dopasowanie słów kluczowych z CV do wymagań oferty pracy
    """
    if not job_description:
        return "Brak opisu stanowiska do analizy słów kluczowych."

    prompt = f"""
    Przeanalizuj dopasowanie słów kluczowych między CV a wymaganiami oferty pracy.

    CV:
    {cv_text}

    Oferta pracy:
    {job_description}

    Odpowiedź w formacie JSON:
    {{
        "match_percentage": [0-100],
        "found_keywords": ["słowo1", "słowo2", "słowo3"],
        "missing_keywords": ["brakujące1", "brakujące2", "brakujące3"],
        "recommendations": [
            "Dodaj umiejętność: [nazwa]",
            "Podkreśl doświadczenie w: [obszar]",
            "Użyj terminów branżowych: [terminy]"
        ],
        "priority_additions": ["najważniejsze słowo1", "najważniejsze słowo2"],
        "summary": "Krótkie podsumowanie analizy dopasowania"
    }}
    """
    return send_api_request(
        prompt, 
        max_tokens=2000, 
        language=language,
        user_tier='free',
        task_type='cv_optimization'
    )

def check_grammar_and_style(cv_text, language='pl'):
    """
    Sprawdza gramatykę, styl i poprawność językową CV
    """
    prompt = f"""
    Przeanalizuj poniższe CV pod kątem gramatyki, stylu i poprawności językowej.

    CV:
    {cv_text}

    Sprawdź:
    1. Błędy gramatyczne i ortograficzne
    2. Spójność czasów gramatycznych
    3. Profesjonalność języka
    4. Klarowność przekazu
    5. Zgodność z konwencjami CV

    Odpowiedź w formacie JSON:
    {{
        "grammar_score": [1-10],
        "style_score": [1-10],
        "professionalism_score": [1-10],
        "errors": [
            {{"type": "gramatyka", "text": "błędny tekst", "correction": "poprawka", "line": "sekcja"}},
            {{"type": "styl", "text": "tekst do poprawy", "suggestion": "sugestia", "line": "sekcja"}}
        ],
        "style_suggestions": [
            "Użyj bardziej dynamicznych czasowników akcji",
            "Unikaj powtórzeń słów",
            "Zachowaj spójny format dat"
        ],
        "overall_quality": "ocena ogólna jakości językowej",
        "summary": "Podsumowanie analizy językowej"
    }}
    """
    return send_api_request(
        prompt, 
        max_tokens=1500,
        language=language,
        user_tier='free',
        task_type='cv_optimization'
    )

def optimize_for_position(cv_text, job_title, job_description="", language='pl'):
    """
    Optymalizuje CV pod konkretne stanowisko
    """
    prompt = f"""
    Zoptymalizuj poniższe CV specjalnie pod stanowisko: {job_title}

    CV:
    {cv_text}

    {"Wymagania z oferty: " + job_description if job_description else ""}

    Stwórz zoptymalizowaną wersję CV, która:
    1. Podkreśla najważniejsze umiejętności dla tego stanowiska
    2. Reorganizuje sekcje według priorytetów dla tej roli
    3. Dostosowuje język do branżowych standardów
    4. Maksymalizuje dopasowanie do wymagań
    5. Zachowuje autentyczność i prawdziwość informacji

    Odpowiedź w formacie JSON:
    {{
        "optimized_cv": "Zoptymalizowana wersja CV",
        "key_changes": ["zmiana 1", "zmiana 2", "zmiana 3"],
        "focus_areas": ["obszar 1", "obszar 2", "obszar 3"],
        "added_elements": ["dodany element 1", "dodany element 2"],
        "positioning_strategy": "Strategia pozycjonowania kandydata",
        "summary": "Podsumowanie optymalizacji"
    }}
    """
    return send_api_request(
        prompt, 
        max_tokens=2500,
        language=language,
        user_tier='free',
        task_type='cv_optimization'
    )

def generate_interview_tips(cv_text, job_description="", language='pl'):
    """
    Generuje spersonalizowane tipy na rozmowę kwalifikacyjną
    """
    prompt = f"""
    Na podstawie CV i opisu stanowiska, przygotuj spersonalizowane tipy na rozmowę kwalifikacyjną.

    CV:
    {cv_text}

    {"Stanowisko: " + job_description if job_description else ""}

    Odpowiedź w formacie JSON:
    {{
        "preparation_tips": [
            "Przygotuj się na pytanie o [konkretny aspekt z CV]",
            "Przećwicz opowiadanie o projekcie [nazwa projektu]",
            "Badź gotowy na pytania techniczne o [umiejętność]"
        ],
        "strength_stories": [
            {{"strength": "umiejętność", "story_outline": "jak opowiedzieć o sukcesie", "example": "konkretny przykład z CV"}},
            {{"strength": "osiągnięcie", "story_outline": "struktura opowieści", "example": "przykład z doświadczenia"}}
        ],
        "weakness_preparation": [
            {{"potential_weakness": "obszar do poprawy", "how_to_address": "jak to przedstawić pozytywnie"}},
            {{"potential_weakness": "luka w CV", "how_to_address": "jak wytłumaczyć"}}
        ],
        "questions_to_ask": [
            "Przemyślane pytanie o firmę/zespół",
            "Pytanie o rozwój w roli",
            "Pytanie o wyzwania stanowiska"
        ],
        "research_suggestions": [
            "Sprawdź informacje o: [aspekt firmy]",
            "Poznaj ostatnie projekty firmy",
            "Zbadaj kulturę organizacyjną"
        ],
        "summary": "Kluczowe rady dla tego kandydata"
    }}
    """
    return send_api_request(
        prompt, 
        max_tokens=2000,
        language=language,
        user_tier='free',
        task_type='interview_prep'
    )

def generate_improved_cv(cv_text, improvement_focus='general', target_industry='', language='pl', is_premium=False, payment_verified=False):
    """
    Generate an improved version of CV based on focus area
    """
    focus_prompts = {
        'general': "Przeprowadź ogólną poprawę CV zwiększając jego atrakcyjność dla rekruterów",
        'structure': "Popraw strukturę i organizację CV dla lepszej czytelności",
        'content': "Wzbogać treść CV dodając więcej wartości do opisów",
        'keywords': "Zoptymalizuj CV pod kątem słów kluczowych branżowych",
        'achievements': "Przekształć obowiązki w konkretne osiągnięcia z mierzalnymi rezultatami"
    }

    industry_context = f"Branża docelowa: {target_industry}" if target_industry else ""

    prompt = f"""
    ZADANIE EKSPERCKIE: {focus_prompts.get(improvement_focus, focus_prompts['general'])}

    🎯 CELE POPRAWY:
    1. Zwiększ atrakcyjność CV dla rekruterów
    2. Popraw prezentację doświadczenia i umiejętności
    3. Zachowaj wszystkie oryginalne fakty
    4. Użyj profesjonalnej terminologii branżowej
    5. Zoptymalizuj pod kątem ATS

    {industry_context}

    ORYGINALNE CV:
    {cv_text}

    POZIOM USŁUGI: {"Premium Advanced" if is_premium else "Standard Paid"}

    Przeprowadź kompleksową poprawę CV zachowując wszystkie oryginalne fakty.

    Odpowiedź w formacie JSON:
    {{
        "improved_cv": "Poprawiona wersja CV z lepszą prezentacją",
        "improvements_made": [
            "Lista konkretnych poprawek wprowadzonych",
            "Każda poprawka z uzasadnieniem"
        ],
        "preserved_elements": [
            "Lista zachowanych oryginalnych elementów",
            "Potwierdzenie że nie dodano fałszywych informacji"
        ],
        "focus_area_improvements": "Szczegółowe poprawki w wybranym obszarze: {improvement_focus}",
        "recommendations": [
            "Dodatkowe rekomendacje dla kandydata",
            "Sugestie dalszych poprawek"
        ]
    }}
    """

    max_tokens = 4000 if is_premium else 2500

    return send_api_request(
        prompt,
        max_tokens=max_tokens,
        language=language,
        user_tier='premium' if is_premium else 'paid',
        task_type='cv_improvement'
    )


def apply_recruiter_feedback_to_cv(cv_text, recruiter_feedback, job_description="", language='pl', is_premium=False, payment_verified=False):
    """Apply recruiter feedback to improve CV"""
    prompt = f"""
    Zastosuj poniższe uwagi rekrutera do CV i popraw je zgodnie z sugestiami.

    ORYGINALNE CV:
    {cv_text}

    UWAGI REKRUTERA:
    {feedback}

    OPIS STANOWISKA (jeśli dostępny):
    {job_description}

    Przepisz CV uwzględniając wszystkie uwagi rekrutera. Zwróć tylko poprawione CV w formacie JSON:
    {{
        "improved_cv": "Poprawione CV z zastosowanymi uwagami",
        "changes_made": ["Lista zastosowanych zmian"],
        "improvement_summary": "Podsumowanie ulepszeń"
    }}
    """
    return send_api_request(
        prompt, 
        max_tokens=3000,
        language=language,
        user_tier='premium' if is_premium else ('paid' if payment_verified else 'free'),
        task_type='cv_optimization'
    )

def analyze_polish_job_posting(job_description, language='pl'):
    """
    Analizuje polskie ogłoszenia o pracę i wyciąga kluczowe informacje
    """
    prompt = f"""
    Przeanalizuj poniższe polskie ogłoszenie o pracę i wyciągnij z niego najważniejsze informacje.

    OGŁOSZENIE O PRACĘ:
    {job_description}

    Wyciągnij i uporządkuj następujące informacje:

    1. PODSTAWOWE INFORMACJE:
    - Stanowisko/pozycja
    - Branża/sektor
    - Lokalizacja pracy
    - Typ umowy/zatrudnienia

    2. WYMAGANIA KLUCZOWE:
    - Wykształcenie
    - Doświadczenie zawodowe
    - Specyficzne umiejętności techniczne
    - Uprawnienia/certyfikaty (np. prawo jazdy, kursy)
    - Umiejętności miękkie

    3. OBOWIĄZKI I ZAKRES PRACY:
    - Główne zadania
    - Odpowiedzialności
    - Specyficzne czynności

    4. WARUNKI PRACY:
    - Godziny pracy
    - System pracy (pełny etat, zmianowy, weekendy)
    - Wynagrodzenie (jeśli podane)
    - Benefity i dodatki

    5. SŁOWA KLUCZOWE BRANŻOWE:
    - Terminologia specjalistyczna
    - Najważniejsze pojęcia z ogłoszenia
    - Frazy które powinny pojawić się w CV

    Odpowiedź w formacie JSON:
    {{
        "job_title": "dokładny tytuł stanowiska",
        "industry": "branża/sektor",
        "location": "lokalizacja",
        "employment_type": "typ zatrudnienia",
        "key_requirements": [
            "wymóg 1",
            "wymóg 2", 
            "wymóg 3"
        ],
        "main_responsibilities": [
            "obowiązek 1",
            "obowiązek 2",
            "obowiązek 3"
        ],
        "technical_skills": [
            "umiejętność techniczna 1",
            "umiejętność techniczna 2"
        ],
        "soft_skills": [
            "umiejętność miękka 1",
            "umiejętność miękka 2"
        ],
        "work_conditions": {{
            "hours": "godziny pracy",
            "schedule": "harmonogram",
            "salary_info": "informacje o wynagrodzeniu",
            "benefits": ["benefit 1", "benefit 2"]
        }},
        "industry_keywords": [
            "słowo kluczowe 1",
            "słowo kluczowe 2",
            "słowo kluczowe 3",
            "słowo kluczowe 4",
            "słowo kluczowe 5"
        ],
        "critical_phrases": [
            "kluczowa fraza 1",
            "kluczowa fraza 2",
            "kluczowa fraza 3"
        ],
        "experience_level": "poziom doświadczenia",
        "education_requirements": "wymagane wykształcenie",
        "summary": "zwięzłe podsumowanie stanowiska i wymagań"
    }}
    """
    return send_api_request(
        prompt, 
        max_tokens=2000,
        language=language,
        user_tier='free',
        task_type='cv_optimization'
    )

def optimize_cv_for_specific_position(cv_text, target_position, job_description, company_name="", language='pl', is_premium=False, payment_verified=False):
    """
    ZAAWANSOWANA OPTYMALIZACJA CV - analizuje każde poprzednie stanowisko i inteligentnie je przepisuje
    pod kątem konkretnego stanowiska docelowego, zachowując pełną autentyczność danych
    """
    prompt = f"""
    ZADANIE: Przepisz to CV używając WYŁĄCZNIE faktów z oryginalnego tekstu. NIE DODAWAJ, NIE WYMYŚLAJ, NIE TWÓRZ nowych informacji.

    ⚠️ KRYTYCZNE ZASADY - MUSZĄ BYĆ BEZWZGLĘDNIE PRZESTRZEGANE:
    1. ❌ ABSOLUTNY ZAKAZ: NIE wolno dodawać żadnych nowych firm, stanowisk, dat, osiągnięć, umiejętności
    2. ❌ ABSOLUTNY ZAKAZ: NIE wolno zmieniac dat zatrudnienia, nazw firm, tytułów stanowisk
    3. ❌ ABSOLUTNY ZAKAZ: NIE wolno dodawać obowiązków które nie są w oryginalnym CV
    4. ✅ DOZWOLONE: Tylko lepsze sformułowanie istniejących opisów używając lepszych słów
    5. ✅ DOZWOLONE: Reorganizacja kolejności sekcji dla lepszej prezentacji
    6. ✅ DOZWOLONE: Użycie synonimów i lepszej terminologii branżowej

    STANOWISKO DOCELOWE: {target_position}
    FIRMA DOCELOWA: {company_name}
    WYMAGANIA Z OGŁOSZENIA:
    {job_description}

    ORYGINALNE CV (UŻYWAJ TYLKO TYCH FAKTÓW):
    {cv_text}

    PRZEPISZ CV zachowując wszystkie oryginalne fakty, ale lepiej je prezentując. Odpowiedź w formacie JSON:

    {{
        "optimized_cv": "Przepisane CV z lepszym sformułowaniem, ale tymi samymi faktami",
        "changes_made": ["Lista rzeczywistych zmian - tylko stylistycznych"],
        "preserved_facts": ["Lista zachowanych oryginalnych faktów"],
        "warning_check": "Potwierdzam że nie dodałem żadnych nowych faktów, firm ani stanowisk"
    }}

    PAMIĘTAJ: Jeśli dodasz choćby jeden wymyślony szczegół, naruszysz zaufanie kandydata!
    """

    max_tokens = 8000 if is_premium or payment_verified else 4000

    return send_api_request(
        prompt,
        max_tokens=max_tokens,
        language=language,
        user_tier='premium' if is_premium else ('paid' if payment_verified else 'free'),
        task_type='cv_optimization'
    )

def generate_complete_cv_content(target_position, experience_level, industry, brief_background, language='pl'):
    """
    Generate complete CV content from minimal user input using AI
    """
    prompt = f"""
    ZADANIE: Wygeneruj kompletną treść CV na podstawie minimalnych informacji od użytkownika.

    DANE WEJŚCIOWE:
    - Docelowe stanowisko: {target_position}
    - Poziom doświadczenia: {experience_level} (junior/mid/senior)
    - Branża: {industry}
    - Krótki opis doświadczenia: {brief_background}

    WYGENERUJ REALISTYCZNĄ TREŚĆ CV:

    1. PROFESSIONAL SUMMARY (80-120 słów):
    - Stwórz przekonujące podsumowanie zawodowe
    - Dopasowane do poziomu doświadczenia i stanowiska
    - Użyj słów kluczowych z branży

    2. DOŚWIADCZENIE ZAWODOWE (3-4 stanowiska):
    - Wygeneruj realistyczne stanowiska progresywne w karierze
    - Każde stanowisko: tytuł, firma (prawdopodobna nazwa), okres, 3-4 obowiązki
    - Dostosuj do poziomu experience_level:
      * Junior: 1-2 lata doświadczenia, podstawowe role
      * Mid: 3-5 lat, stanowiska specjalistyczne
      * Senior: 5+ lat, role kierownicze/eksperckie

    3. WYKSZTAŁCENIE:
    - Wygeneruj odpowiednie wykształcenie dla branży
    - Kierunek studiów pasujący do stanowiska
    - Realistyczne nazwy uczelni (polskie)

    4. UMIEJĘTNOŚCI:
    - Lista 8-12 umiejętności kluczowych dla stanowiska
    - Mix hard skills i soft skills
    - Aktualne technologie/narzędzia branżowe

    Odpowiedź w formacie JSON:
    {{
        "professional_title": "Tytuł zawodowy do CV",
        "professional_summary": "Podsumowanie zawodowe 80-120 słów",
        "experience_suggestions": [
            {{
                "title": "Stanowisko",
                "company": "Nazwa firmy", 
                "startDate": "2022-01",
                "endDate": "obecnie",
                "description": "Opis obowiązków i osiągnięć (3-4 punkty)"
            }},
            {{
                "title": "Poprzednie stanowisko",
                "company": "Poprzednia firma",
                "startDate": "2020-06", 
                "endDate": "2021-12",
                "description": "Opis obowiązków z poprzedniej pracy"
            }}
        ],
        "education_suggestions": [
            {{
                "degree": "Kierunek studiów",
                "school": "Nazwa uczelni",
                "startYear": "2018",
                "endYear": "2022"
            }}
        ],
        "skills_list": "Umiejętność 1, Umiejętność 2, Umiejętność 3, Umiejętność 4, Umiejętność 5, Umiejętność 6, Umiejętność 7, Umiejętność 8",
        "career_level": "{experience_level}",
        "industry_focus": "{industry}",
        "generation_notes": "Informacje o logice generowania tego CV"
    }}
    """
    return send_api_request(
        prompt,
        max_tokens=4000,
        language=language,
        user_tier='free',
        task_type='cv_optimization'
    )

def optimize_cv(cv_text, job_description, language='pl', is_premium=False, payment_verified=False):
    """
    Create a clean, optimized version of CV using ONLY authentic data from the original CV
    Returns only the improved CV text without extra metadata
    """
    prompt = f"""
    ZADANIE: Stwórz ulepszoną wersję CV używając WYŁĄCZNIE prawdziwych informacji z oryginalnego CV.

    ZASADY OPTYMALIZACJI:
    1. ❌ ZAKAZ WYMYŚLANIA: NIE dodawaj nowych firm, stanowisk, dat, osiągnięć
    2. ❌ ZAKAZ DODAWANIA: NIE twórz nowych umiejętności, certyfikatów, projektów
    3. ✅ PRZEPISZ: Sformułuj istniejące informacje bardziej profesjonalnie
    4. ✅ UPORZĄDKUJ: Lepiej zorganizuj strukturę CV
    5. ✅ ULEPSZ: Użyj lepszych słów kluczowych i terminologii branżowej

    STRUKTURA ZOPTYMALIZOWANEGO CV:

    [DANE OSOBOWE]
    - Zachowaj dokładnie dane kontaktowe z oryginalnego CV

    [PODSUMOWANIE ZAWODOWE] 
    - Stwórz zwięzłe podsumowanie na podstawie doświadczenia z CV
    - 2-3 zdania o kluczowych umiejętnościach i doświadczeniu
    - Użyj tylko faktów z oryginalnego CV

    [DOŚWIADCZENIE ZAWODOWE]
    - Zachowaj wszystkie firmy, stanowiska i daty z oryginału
    - Przepisz opisy obowiązków używając lepszych czasowników akcji
    - Każde stanowisko: 3-4 punkty z konkretnymi obowiązkami
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

    POZIOM PREMIUM:
    - Szczegółowe opisy każdego stanowiska (5-6 punktów)
    - Rozbudowane podsumowanie zawodowe
    - Zaawansowana terminologia branżowa
    - Profesjonalne formatowanie
    """
    else:
        max_tokens = 2500
        prompt += f"""

    POZIOM STANDARD:
    - Podstawowa optymalizacja CV (3-4 punkty na stanowisko)
    - Zwięzłe podsumowanie zawodowe
    - Czytelne formatowanie
    """

    return send_api_request(
        prompt,
        max_tokens=max_tokens,
        language=language,
        user_tier='premium' if is_premium else ('paid' if payment_verified else 'free'),
        task_type='cv_optimization'
    )

def generate_recruiter_feedback(cv_text, job_description="", language='pl'):
    """
    Generate feedback on a CV as if from an AI recruiter
    """
    context = ""
    if job_description:
        context = f"Opis stanowiska do kontekstu:\n{job_description}"

    prompt = f"""
    ZADANIE: Jesteś doświadczonym rekruterem. Przeanalizuj to CV i udziel szczegółowej, konstruktywnej opinii w języku polskim.

    ⚠️ KLUCZOWE: Oceniaj TYLKO to co faktycznie jest w CV. NIE ZAKŁADAJ, NIE DOMYŚLAJ się i NIE DODAWAJ informacji, których tam nie ma.

    Uwzględnij w ocenie:
    1. Ogólne wrażenie i pierwsza reakcja na podstawie faktycznej treści CV
    2. Mocne strony i słabości wynikające z konkretnych informacji w CV
    3. Ocena formatowania i struktury CV
    4. Jakość treści i sposób prezentacji faktycznych doświadczeń
    5. Kompatybilność z systemami ATS
    6. Konkretne sugestie poprawek oparte na tym co jest w CV
    7. Ocena ogólna w skali 1-10
    8. Prawdopodobieństwo zaproszenia na rozmowę

    {context}

    CV do oceny:
    {cv_text}

    Odpowiedź w formacie JSON:
    {{
        "overall_impression": "Pierwsze wrażenie oparte na faktycznej treści CV",
        "rating": [1-10],
        "strengths": [
            "Mocna strona 1 (konkretnie z CV)",
            "Mocna strona 2 (konkretnie z CV)", 
            "Mocna strona 3 (konkretnie z CV)"
        ],
        "weaknesses": [
            "Słabość 1 z sugestią poprawy (bazując na CV)",
            "Słabość 2 z sugestią poprawy (bazując na CV)",
            "Słabość 3 z sugestią poprawy (bazując na CV)"
        ],
        "formatting_assessment": "Ocena layoutu, struktury i czytelności faktycznej treści",
        "content_quality": "Ocena jakości treści rzeczywiście obecnej w CV",
        "ats_compatibility": "Czy CV przejdzie przez systemy automatycznej selekcji",
        "specific_improvements": [
            "Konkretna poprawa 1 (oparta na faktach z CV)",
            "Konkretna poprawa 2 (oparta na faktach z CV)",
            "Konkretna poprawa 3 (oparta na faktach z CV)"
        ],
        "interview_probability": "Prawdopodobieństwo zaproszenia oparte na faktach z CV",
        "recruiter_summary": "Podsumowanie z perspektywy rekrutera - tylko fakty z CV"
    }}

    Bądź szczery, ale konstruktywny. Oceniaj tylko to co rzeczywiście jest w CV, nie dodawaj od siebie.
    """
    return send_api_request(
        prompt, 
        max_tokens=3000, 
        language=language,
        user_tier='premium',
        task_type='recruiter_feedback'
    )

def generate_cover_letter(cv_text, job_description, language='pl'):
    """
    Generate a cover letter based on a CV and job description
    """
    prompt = f"""
    ZADANIE: Napisz spersonalizowany list motywacyjny w języku polskim WYŁĄCZNIE na podstawie faktów z CV.

    ⚠️ ABSOLUTNE WYMAGANIA:
    - Używaj TYLKO informacji faktycznie obecnych w CV
    - NIE WYMYŚLAJ doświadczeń, projektów, osiągnięć ani umiejętności
    - NIE DODAWaj informacji, których nie ma w oryginalnym CV
    - Jeśli w CV brakuje jakichś informacji - nie uzupełniaj ich

    List motywacyjny powinien:
    - Być profesjonalnie sformatowany
    - Podkreślać umiejętności i doświadczenia faktycznie wymienione w CV
    - Łączyć prawdziwe doświadczenie kandydata z wymaganiami stanowiska
    - Zawierać przekonujące wprowadzenie oparte na faktach z CV
    - Mieć około 300-400 słów
    - Być napisany naturalnym, profesjonalnym językiem polskim

    Struktura listu:
    1. Nagłówek z danymi kontaktowymi
    2. Zwrot do adresata
    3. Wprowadzenie - dlaczego aplikujesz
    4. Główna treść - dopasowanie doświadczenia do wymagań
    5. Zakończenie z wyrażeniem zainteresowania
    6. Pozdrowienia

    Opis stanowiska:
    {job_description}

    CV kandydata:
    {cv_text}

    Napisz kompletny list motywacyjny w języku polskim. Użyj profesjonalnego, ale ciepłego tonu.
    """
    return send_api_request(
        prompt,
        max_tokens=2000,
        language=language,
        user_tier='free',
        task_type='cover_letter'
    )

def analyze_job_url(url):
    """
    Extract job description from a URL with improved handling for popular job sites
    """
    try:
        logger.debug(f"Analyzing job URL: {url}")

        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL format")

        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        job_text = ""
        domain = parsed_url.netloc.lower()

        if 'linkedin.com' in domain:
            containers = soup.select('.description__text, .show-more-less-html, .jobs-description__content')
            if containers:
                job_text = containers[0].get_text(separator='\n', strip=True)

        elif 'indeed.com' in domain:
            container = soup.select_one('#jobDescriptionText')
            if container:
                job_text = container.get_text(separator='\n', strip=True)

        elif 'pracuj.pl' in domain:
            containers = soup.select('[data-test="section-benefit-expectations-text"], [data-test="section-description-text"]')
            if containers:
                job_text = '\n'.join([c.get_text(separator='\n', strip=True) for c in containers])

        elif 'olx.pl' in domain or 'praca.pl' in domain:
            containers = soup.select('.offer-description, .offer-content, .description')
            if containers:
                job_text = containers[0].get_text(separator='\n', strip=True)

        if not job_text:
            potential_containers = soup.select('.job-description, .description, .details, article, .job-content, [class*=job], [class*=description], [class*=offer]')
            if potential_containers:
                for container in potential_containers:
                    container_text = container.get_text(separator='\n', strip=True)
                    if len(container_text) > len(job_text):
                        job_text = container_text

            if not job_text and soup.body:
                for tag in soup.select('nav, header, footer, script, style, iframe'):
                    tag.decompose()

                job_text = soup.body.get_text(separator='\n', strip=True)

                if len(job_text) > 10000:
                    paragraphs = job_text.split('\n')
                    keywords = ['requirements', 'responsibilities', 'qualifications', 'skills', 'experience', 'about the job',
                                'wymagania', 'obowiązki', 'kwalifikacje', 'umiejętności', 'doświadczenie', 'o pracy']

                    relevant_paragraphs = []
                    found_relevant = False

                    for paragraph in paragraphs:
                        if any(keyword.lower() in paragraph.lower() for keyword in keywords):
                            found_relevant = True
                        if found_relevant and len(paragraph.strip()) > 50:
                            relevant_paragraphs.append(paragraph)

                    if relevant_paragraphs:
                        job_text = '\n'.join(relevant_paragraphs)


        job_text = '\n'.join([' '.join(line.split()) for line in job_text.split('\n') if line.strip()])

        if not job_text:
            raise ValueError("Could not extract job description from the URL")

        logger.debug(f"Successfully extracted job description from URL")

        if len(job_text) > 4000:
            logger.debug(f"Job description is long ({len(job_text)} chars), summarizing with AI")
            job_text = summarize_job_description(job_text)

        return job_text

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching job URL: {str(e)}")
        raise Exception(f"Failed to fetch job posting from URL: {str(e)}")

    except Exception as e:
        logger.error(f"Error analyzing job URL: {str(e)}")
        raise Exception(f"Failed to analyze job posting: {str(e)}")

def summarize_job_description(job_text):
    """
    Summarize a long job description using the AI
    """
    prompt = f"""
    ZADANIE: Wyciągnij i podsumuj kluczowe informacje z tego ogłoszenia o pracę w języku polskim.

    Uwzględnij:
    1. Stanowisko i nazwa firmy (jeśli podane)
    2. Wymagane umiejętności i kwalifikacje
    3. Obowiązki i zakres zadań
    4. Preferowane doświadczenie
    5. Inne ważne szczegóły (benefity, lokalizacja, itp.)
    6. TOP 5 słów kluczowych krytycznych dla tego stanowiska

    Tekst ogłoszenia:
    {job_text[:4000]}...

    Stwórz zwięzłe ale kompletne podsumowanie tego ogłoszenia, skupiając się na informacjach istotnych dla optymalizacji CV.
    Na końcu umieść sekcję "KLUCZOWE SŁOWA:" z 5 najważniejszymi terminami.

    Odpowiedź w języku polskim.
    """
    return send_api_request(
        prompt,
        max_tokens=1500,
        language='pl',
        user_tier='free',
        task_type='cv_optimization'
    )

def ats_optimization_check(cv_text, job_description="", language='pl'):
    """
    Check CV against ATS (Applicant Tracking System) and provide suggestions for improvement
    """
    context = ""
    if job_description:
        context = f"Ogłoszenie o pracę dla odniesienia:\n{job_description[:2000]}"

    prompt = f"""
    TASK: Przeprowadź dogłębną analizę CV pod kątem kompatybilności z systemami ATS (Applicant Tracking System) i wykryj potencjalne problemy.

    Przeprowadź następujące analizy:

    1. WYKRYWANIE PROBLEMÓW STRUKTURALNYCH:
       - Znajdź sekcje, które są w nieodpowiednich miejscach (np. doświadczenie zawodowe w sekcji zainteresowań)
       - Wskaż niespójności w układzie i formatowaniu
       - Zidentyfikuj zduplikowane informacje w różnych sekcjach
       - Zaznacz fragmenty tekstu, które wyglądają na wygenerowane przez AI
       - Znajdź ciągi znaków bez znaczenia lub losowe znaki

    2. ANALIZA FORMATOWANIA ATS:
       - Wykryj problemy z formatowaniem, które mogą utrudnić odczyt przez systemy ATS
       - Sprawdź, czy nagłówki sekcji są odpowiednio wyróżnione
       - Zweryfikuj, czy tekst jest odpowiednio podzielony na sekcje
       - Oceń czytelność dla systemów automatycznych

    3. ANALIZA SŁÓW KLUCZOWYCH:
       - Sprawdź gęstość słów kluczowych i trafność ich wykorzystania
       - Zidentyfikuj brakujące słowa kluczowe z branży/stanowiska
       - Oceń rozmieszczenie słów kluczowych w dokumencie

    4. OCENA KOMPLETNOŚCI:
       - Zidentyfikuj brakujące sekcje lub informacje, które są często wymagane przez ATS
       - Wskaż informacje, które należy uzupełnić

    5. WERYFIKACJA AUTENTYCZNOŚCI:
       - Zaznacz fragmenty, które wyglądają na sztuczne lub wygenerowane przez AI
       - Podkreśl niespójności między różnymi częściami CV

    6. OCENA OGÓLNA:
       - Oceń ogólną skuteczność CV w systemach ATS w skali 1-10
       - Podaj główne powody obniżonej oceny

    {context}

    CV do analizy:
    {cv_text}

    Odpowiedz w tym samym języku co CV. Jeśli CV jest po polsku, odpowiedz po polsku.
    Dodaj główny nagłówek: "ANALIZA ATS CV"

    Format odpowiedzi:

    ## ANALIZA ATS CV

    1. OCENA OGÓLNA (skala 1-10): [ocena]

    2. PROBLEMY KRYTYCZNE:
    [Lista wykrytych krytycznych problemów]

    3. PROBLEMY ZE STRUKTURĄ:
    [Lista problemów strukturalnych]

    4. PROBLEMY Z FORMATOWANIEM ATS:
    [Lista problemów z formatowaniem]

    5. ANALIZA SŁÓW KLUCZOWYCH:
    [Wyniki analizy słów kluczowych]

    6. BRAKUJĄCE INFORMACJE:
    [Lista brakujących informacji]

    7. PODEJRZANE ELEMENTY:
    [Lista elementów, które wydają się wygenerowane przez AI lub są niespójne]

    8. REKOMENDACJE NAPRAWCZE:
    [Konkretne sugestie, jak naprawić zidentyfikowane problemy]

    9. PODSUMOWANIE:
    [Krótkie podsumowanie i zachęta]
    """
    return send_api_request(
        prompt,
        max_tokens=1800,
        language=language,
        user_tier='free',
        task_type='cv_optimization'
    )

def analyze_cv_strengths(cv_text, job_title="analityk danych", language='pl'):
    """
    Analyze CV strengths for a specific job position and provide improvement suggestions
    """
    prompt = f"""
    ZADANIE: Przeprowadź dogłębną analizę mocnych stron tego CV w kontekście stanowiska {job_title}.

    1. Zidentyfikuj i szczegółowo omów 5-7 najsilniejszych elementów CV, które są najbardziej wartościowe dla pracodawcy.
    2. Dla każdej mocnej strony wyjaśnij, dlaczego jest ona istotna właśnie dla stanowiska {job_title}.
    3. Zaproponuj konkretne ulepszenia, które mogłyby wzmocnić te mocne strony.
    4. Wskaż obszary, które mogłyby zostać dodane lub rozbudowane, aby CV było jeszcze lepiej dopasowane do stanowiska.
    5. Zaproponuj, jak lepiej zaprezentować osiągnięcia i umiejętności, aby były bardziej przekonujące.

    CV:
    {cv_text}

    Pamiętaj, aby Twoja analiza była praktyczna i pomocna. Używaj konkretnych przykładów z CV i odnoś je do wymagań typowych dla stanowiska {job_title}.
    """
    return send_api_request(
        prompt,
        max_tokens=2500,
        language=language,
        user_tier='free',
        task_type='cv_optimization'
    )

def generate_interview_questions(cv_text, job_description="", language='pl'):
    """
    Generate likely interview questions based on CV and job description
    """
    context = ""
    if job_description:
        context = f"Uwzględnij poniższe ogłoszenie o pracę przy tworzeniu pytań:\n{job_description[:2000]}"

    prompt = f"""
    TASK: Wygeneruj zestaw potencjalnych pytań rekrutacyjnych, które kandydat może otrzymać podczas rozmowy kwalifikacyjnej.

    Pytania powinny być:
    1. Specyficzne dla doświadczenia i umiejętności kandydata wymienionych w CV
    2. Dopasowane do stanowiska (jeśli podano opis stanowiska)
    3. Zróżnicowane - połączenie pytań technicznych, behawioralnych i sytuacyjnych
    4. Realistyczne i często zadawane przez rekruterów

    Uwzględnij po co najmniej 3 pytania z każdej kategorii:
    - Pytania o doświadczenie zawodowe
    - Pytania techniczne/o umiejętności
    - Pytania behawioralne
    - Pytania sytuacyjne
    - Pytania o motywację i dopasowanie do firmy/stanowiska

    {context}

    CV:
    {cv_text}

    Odpowiedz w tym samym języku co CV. Jeśli CV jest po polsku, odpowiedz po polsku.
    Dodatkowo, do każdego pytania dodaj krótką wskazówkę, jak można by na nie odpowiedzieć w oparciu o informacje z CV.
    Format odpowiedzi:
    - Pytanie rekrutacyjne
      * Wskazówka jak odpowiedzieć: [wskazówka]
    """
    return send_api_request(
        prompt,
        max_tokens=2000,
        language=language,
        user_tier='free',
        task_type='interview_prep'
    )

def get_enhanced_system_prompt(task_type, language='pl'):
    """
    Generuje spersonalizowany prompt systemowy dla różnych typów zadań
    """
    base_prompt = DEEP_REASONING_PROMPT

    task_specific_prompts = {
        'cv_optimization': """

🔥 SPECJALIZACJA: OPTYMALIZACJA CV
- Analizujesz każde słowo pod kątem wpływu na rekrutera
- Znasz najnowsze trendy w formatowaniu CV
- Potrafisz dostosować styl do różnych branż i stanowisk
- Maksymalizujesz szanse przejścia przez filtry ATS
- Przepisujesz istniejące doświadczenia używając faktów z CV
- PAMIĘTAJ: Tylko poprawiaj sformułowania, NIE dodawaj nowych firm, stanowisk, dat!""",

        'recruiter_feedback': """

👔 SPECJALIZACJA: OPINIE REKRUTERA
- Myślisz jak senior recruiter z doświadczeniem w różnych branżach
- Dostrzegasz detale, które umykają innym
- Oceniasz CV pod kątem pierwszego wrażenia (6 sekund)
- Znasz typowe błędy kandydatów i jak ich unikać
- Potrafisz przewidzieć reakcję hiring managera""",

        'cover_letter': """

📄 SPECJALIZACJA: LISTY MOTYWACYJNE
- Tworzysz przekonujące narracje osobiste
- Łączysz doświadczenia kandydata z potrzebami firmy
- Używasz psychologii przekonywania w copywritingu
- Dostosowujesz ton do kultury organizacyjnej
- Unikasz szablonowych zwrotów i klisz""",

        'interview_prep': """

🎤 SPECJALIZACJA: PRZYGOTOWANIE DO ROZMÓW
- Przewidujesz pytania na podstawie CV i stanowiska
- Znasz techniki odpowiadania (STAR, CAR)
- Pomagasz w przygotowaniu historii sukcesu
- Analizujesz potencjalne słabości i jak je przedstawić
- Przygotowujesz do różnych typów rozmów (HR, techniczne, z przełożonym)""",

        'cv_improvement': """

🌟 SPECJALIZACJA: POPRAWA CV
- Skupiasz się na specyficznych aspektach CV (struktura, treść, słowa kluczowe, osiągnięcia)
- Dostosowujesz podejście do wybranego obszaru poprawy
- Zapewniasz lepszą prezentację kandydatury
- Generujesz praktyczne rekomendacje"""
    }

    return base_prompt + task_specific_prompts.get(task_type, "")

def enhanced_cv_optimization_with_reasoning(cv_text, job_description, language='pl', is_premium=False, payment_verified=False):
    """
    Enhanced CV optimization with AI reasoning - premium feature
    """
    prompt = f"""
    ZADANIE EKSPERCKIE: Przeprowadź zaawansowaną optymalizację CV z głęboką analizą i uzasadnieniem każdej zmiany.

    🧠 DEEP REASONING PROCESS:
    1. Analizuj każde zdanie CV pod kątem wartości dla rekrutera
    2. Identyfikuj ukryte potencjały i transferable skills
    3. Dostosuj positioning strategy do target audience
    4. Optymalizuj pod kątem psychology of persuasion
    5. Maksymalizuj ATS compatibility i human readability

    ORYGINALNE CV:
    {cv_text}

    KONTEKST STANOWISKA:
    {job_description}

    LEVEL OPTYMALIZACJI: {"Premium Advanced" if is_premium else ("Paid Standard" if payment_verified else "Basic")}

    Przeprowadź KOMPLETNĄ optymalizację używając TYLKO faktów z oryginalnego CV:

    {{
        "reasoning_process": {{
            "industry_analysis": "Rozpoznana branża i jej specyfika",
            "candidate_positioning": "Jak pozycjonujemy kandydata",
            "optimization_strategy": "Strategia optymalizacji",
            "key_insights": ["insight 1", "insight 2", "insight 3"]
        }},
        "optimized_cv": "Kompletne zoptymalizowane CV",
        "improvements_made": [
            "Szczegółowy opis poprawy 1 z uzasadnieniem",
            "Szczegółowy opis poprawy 2 z uzasadnieniem",
            "Szczegółowy opis poprawy 3 z uzasadnieniem"
        ],
        "ats_optimization": {{
            "keyword_density": "[0-100]",
            "structure_score": "[0-100]",
            "readability_score": "[0-100]"
        }},
        "success_probability": "[0-100]% szans na zainteresowanie rekrutera",
        "next_steps": "Rekomendacje dalszych działań"
    }}
    """

    max_tokens = 6000 if is_premium or payment_verified else 3000

    return send_api_request(
        prompt,
        max_tokens=max_tokens,
        language=language,
        user_tier='premium' if is_premium else ('paid' if payment_verified else 'free'),
        task_type='cv_optimization'
    )

def get_model_performance_stats():
    """
    Zwróć informacje o używanych modelach AI - tylko Qwen z rozszerzonymi możliwościami
    """
    return {
        "current_model": DEFAULT_MODEL,
        "model_family": "Qwen 2.5 72B Instruct",
        "model_provider": "Alibaba Cloud",
        "optimization_level": "Advanced",
        "capabilities": [
            "Zaawansowana analiza CV w języku polskim",
            "Inteligentna optymalizacja treści zawodowych", 
            "Personalizowane rekomendacje kariery",
            "Profesjonalne sprawdzanie gramatyki i stylu",
            "Precyzyjne dopasowanie do stanowisk",
            "Psychologia rekrutacji i przekonywania",
            "Analiza trendów rynku pracy"
        ],
        "enhanced_features": {
            "adaptive_prompts": True,
            "context_awareness": True,
            "industry_specialization": True,
            "ats_optimization": True,
            "psychology_based": True
        },
        "performance": {
            "response_quality": "Ekspertowa",
            "polish_language_support": "Natywne z kontekstem kulturowym",
            "processing_speed": "Optymalna",
            "consistency": "Bardzo wysoka",
            "creativity": "Zaawansowana",
            "accuracy": "Precyzyjna"
        },
        "parameters": {
            "temperature": 0.8,
            "top_p": 0.95,
            "max_tokens": "4000-8000",
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1
        }
    }

def intelligent_response_parser(response_text, expected_format='json'):
    """
    A more robust parser that tries to extract and validate structured data.
    """
    if expected_format == 'json':
        import re
        # Attempt to find JSON within the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_string = json_match.group(0)
            try:
                data = json.loads(json_string)
                # Basic validation: check if it's a dictionary (common for JSON responses)
                if isinstance(data, dict):
                    return data
                else:
                    logger.warning("Parsed JSON is not a dictionary.")
                    return {"error": "Parsed JSON is not a dictionary.", "raw_response": response_text}
            except json.JSONDecodeError:
                logger.warning("Failed to decode JSON from extracted string.")
                return {"error": "Failed to decode JSON.", "extracted_json": json_string, "raw_response": response_text}
            except Exception as e:
                logger.error(f"An unexpected error occurred during JSON parsing: {e}")
                return {"error": f"An unexpected error occurred during parsing: {e}", "raw_response": response_text}
        else:
            logger.warning("No JSON object found in the response.")
            return {"error": "No JSON object found in the response.", "raw_response": response_text}
    else:
        # If other formats are needed in the future, add them here
        return {"error": f"Unsupported expected format: {expected_format}", "raw_response": response_text}