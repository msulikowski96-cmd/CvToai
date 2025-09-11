import os
import json
import logging
import requests
from dotenv import load_dotenv

# Load environment variables with override
load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Load and validate OpenRouter API key
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()


# Validate API key format and content
def validate_api_key():
    if not OPENROUTER_API_KEY:
        logger.error("❌ OPENROUTER_API_KEY nie jest ustawiony w .env")
        return False

    if OPENROUTER_API_KEY.startswith('TWÓJ_') or len(OPENROUTER_API_KEY) < 20:
        logger.error(
            "❌ OPENROUTER_API_KEY zawiera przykładową wartość - ustaw prawdziwy klucz!"
        )
        return False

    if not OPENROUTER_API_KEY.startswith('sk-or-v1-'):
        logger.error("❌ OPENROUTER_API_KEY nie ma poprawnego formatu")
        return False

    logger.info(
        f"✅ OpenRouter API key załadowany poprawnie (długość: {len(OPENROUTER_API_KEY)})"
    )
    return True


# Validate on module import
API_KEY_VALID = validate_api_key()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# ZAAWANSOWANA KONFIGURACJA MODELI
DEFAULT_MODEL = "qwen/qwen3-235b-a22b:free"
PREMIUM_MODEL = "deepseek/deepseek-chat-v3.1:free"

# OPTYMALIZOWANY PROMPT SYSTEMOWY DLA MAKSYMALNEJ JAKOŚCI
ADVANCED_SYSTEM_PROMPT = """Jesteś światowej klasy ekspertem w rekrutacji i optymalizacji CV z 15-letnim doświadczeniem w branży HR. Posiadasz głęboką wiedzę o polskim rynku pracy, trendach rekrutacyjnych i wymaganiach pracodawców.

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


def send_api_request(prompt,
                     max_tokens=2000,
                     language='pl',
                     user_tier='free',
                     task_type='default'):
    """
    Send a request to the OpenRouter API with enhanced configuration
    """
    if not OPENROUTER_API_KEY or not API_KEY_VALID:
        error_msg = "OpenRouter API key nie jest poprawnie skonfigurowany w pliku .env"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Enhanced system prompt based on task type
    system_prompts = {
        'cv_optimization':
        ADVANCED_SYSTEM_PROMPT,
        'cv_analysis':
        ADVANCED_SYSTEM_PROMPT +
        "\n\nSkupisz się na szczegółowej analizie i ocenie CV pod kątem jakości i dopasowania do wymagań rynku pracy.",
        'keyword_analysis':
        ADVANCED_SYSTEM_PROMPT +
        "\n\nSpecjalizujesz się w analizie słów kluczowych i dopasowaniu CV do ofert pracy.",
        'grammar_check':
        ADVANCED_SYSTEM_PROMPT +
        "\n\nJesteś ekspertem językowym - sprawdzasz gramatykę, styl i poprawność językową CV."
    }

    system_prompt = system_prompts.get(task_type, ADVANCED_SYSTEM_PROMPT)

    payload = {
        "model":
        DEFAULT_MODEL,
        "messages": [{
            "role": "system",
            "content": system_prompt
        }, {
            "role": "user",
            "content": prompt
        }],
        "max_tokens":
        max_tokens,
        "temperature":
        0.3,
        "top_p":
        0.85,
        "frequency_penalty":
        0.1,
        "presence_penalty":
        0.1,
        "metadata": {
            "user_tier": user_tier,
            "task_type": task_type,
            "model_used": DEFAULT_MODEL,
            "optimization_level": "advanced",
            "language": language
        }
    }

    try:
        logger.debug(f"Sending request to OpenRouter API")
        response = requests.post(OPENROUTER_BASE_URL,
                                 headers=headers,
                                 json=payload,
                                 timeout=90)
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
    return send_api_request(prompt,
                            max_tokens=2500,
                            language=language,
                            user_tier='free',
                            task_type='cv_analysis')


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
    return send_api_request(prompt,
                            max_tokens=2000,
                            language=language,
                            user_tier='free',
                            task_type='keyword_analysis')


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
            {{"type": "gramatyka", "text": "błędny tekst", "correction": "poprawka", "section": "sekcja"}},
            {{"type": "styl", "text": "tekst do poprawy", "suggestion": "sugestia", "section": "sekcja"}}
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
    return send_api_request(prompt,
                            max_tokens=1500,
                            language=language,
                            user_tier='free',
                            task_type='grammar_check')


def optimize_for_position(cv_text,
                          job_title,
                          job_description="",
                          language='pl'):
    """
    Optymalizuje CV pod konkretne stanowisko z zaawansowaną analizą
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

    STRUKTURA ZOPTYMALIZOWANEGO CV:
    - **DANE KONTAKTOWE**
    - **PROFIL ZAWODOWY** (3-4 zdania dopasowane do stanowiska)
    - **DOŚWIADCZENIE ZAWODOWE** (od najnowszego, z akcent na umiejętności dla tej roli)
    - **UMIEJĘTNOŚCI KLUCZOWE** (priorytet dla wymagań stanowiska)
    - **WYKSZTAŁCENIE**
    - **CERTYFIKATY/KURSY** (jeśli są)
    - **JĘZYKI OBCE** (jeśli są)
    - **DODATKOWE INFORMACJE** (jeśli odpowiednie)

    WYMAGANIA:
    - Zachowaj wszystkie prawdziwe informacje z oryginalnego CV
    - Użyj słów kluczowych z opisu stanowiska
    - Podkreśl konkretne osiągnięcia i rezultaty
    - Dostosuj kolejność i akcenty do wymagań roli
    - Używaj aktywnych czasowników i konkretnych danych

    ⚠️ PAMIĘTAJ: NIE DODAWAJ żadnych informacji, których nie ma w oryginalnym CV!
    """
    return send_api_request(prompt,
                            max_tokens=3000,
                            language=language,
                            user_tier='free',
                            task_type='cv_optimization')


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
            "Jak przedstawić obszary do rozwoju w pozytywny sposób",
            "Przykłady słabości które można przekuć w siłę"
        ],
        "questions_to_ask": [
            "Przemyślane pytania do zadania rekruterowi",
            "Pytania pokazujące zaangażowanie i wiedzę o firmie"
        ],
        "red_flags_to_avoid": [
            "Czego nie mówić podczas rozmowy",
            "Błędy które mogą zniszczyć szanse"
        ],
        "summary": "Strategia na rozmowę kwalifikacyjną"
    }}
    """
    return send_api_request(prompt,
                            max_tokens=2000,
                            language=language,
                            user_tier='free',
                            task_type='cv_analysis')


# Funkcja kompatybilności z istniejącym kodem
def optimize_cv(cv_text, job_title, job_description="", is_premium=False):
    """
    Enhanced CV optimization using advanced AI capabilities
    """
    try:
        # Pierwsze podejście - zaawansowana optymalizacja
        result = optimize_for_position(cv_text, job_title, job_description,
                                       'pl')
        if result:
            return result

        # Fallback do podstawowej optymalizacji
        user_tier = 'premium' if is_premium else 'paid'
        max_tokens = 4000 if is_premium else 2500

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
        - **DANE KONTAKTOWE**
        - **PROFIL ZAWODOWY** (3-4 zdania)
        - **DOŚWIADCZENIE ZAWODOWE** (od najnowszego)
        - **WYKSZTAŁCENIE**
        - **UMIEJĘTNOŚCI TECHNICZNE/KLUCZOWE**
        - **JĘZYKI OBCE** (jeśli są)
        - **DODATKOWE INFORMACJE** (certyfikaty, kursy, itp.)

        WYMAGANIA FORMATOWANIA:
        - Używaj **pogrubienia** dla nagłówków sekcji
        - Używaj • dla list
        - Zachowaj profesjonalną strukturę
        - Każda pozycja zawodowa: Stanowisko | Firma | Daty | Opis osiągnięć
        - Skupiaj się na konkretnych osiągnięciach i rezultatach

        ⚠️ KRYTYCZNE: NIE DODAWAJ żadnych informacji, których nie ma w oryginalnym CV!
        """

        optimized_cv = send_api_request(prompt,
                                        max_tokens=max_tokens,
                                        user_tier=user_tier,
                                        task_type='cv_optimization')
        return optimized_cv

    except Exception as e:
        logger.error(f"Błąd optymalizacji CV: {str(e)}")
        return None


def get_model_performance_stats():
    """
    Zwróć informacje o używanych modelach AI
    """
    return {
        "current_model": DEFAULT_MODEL,
        "model_family": "Qwen 235B & DeepSeek Chat v3.1",
        "model_provider": "Alibaba Cloud & DeepSeek",
        "optimization_level": "Advanced",
        "capabilities": [
            "Zaawansowana analiza CV w języku polskim"
        ]
    }


def get_model_performance_stats():
    """
    Zwróć informacje o używanych modelach AI - Qwen i DeepSeek
    """
    return {
        "current_model": DEFAULT_MODEL,
        "model_family": "Qwen 235B & DeepSeek Chat v3.1",
        "model_provider": "Alibaba Cloud & DeepSeek",
        "optimization_level": "Advanced",
        "capabilities": [
            "Zaawansowana analiza CV w języku polskim"
        ]
    }