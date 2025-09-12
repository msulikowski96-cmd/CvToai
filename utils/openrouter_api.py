import os
import json
import logging
import requests
import urllib.parse
import hashlib
import time
import statistics
from collections import defaultdict, deque
from datetime import datetime, timedelta
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

# 📊 SYSTEM MONITORINGU JAKOŚCI AI
_quality_metrics = {
    'response_times': defaultdict(deque),  # response times per model
    'success_rates': defaultdict(list),    # success/failure rates
    'quality_scores': defaultdict(deque),  # quality assessments
    'model_usage': defaultdict(int),       # usage statistics
    'fallback_events': [],                 # when fallback was used
    'error_types': defaultdict(int),       # types of errors encountered
    'task_performance': defaultdict(list), # performance per task type
}

# Trzymaj tylko ostatnie 1000 wpisów na model żeby nie rosło w nieskończoność
MAX_METRICS_SIZE = 1000


def get_cache_key(prompt, models_to_try, is_premium, task_type="general"):
    """
    🔐 BEZPIECZNY KLUCZ CACHE - hash pełnego contentu dla uniknięcia kolizji
    """
    # ⚠️ KRYTYCZNY FIX: Hash PEŁNEGO prompta, nie tylko fragmentu!
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    models_str = "|".join(sorted(models_to_try))  # Sortuj dla konsystencji
    tier = "premium" if is_premium else "free"
    
    # Uwzględnij wszystkie parametry które wpływają na wynik
    cache_data = f"{prompt_hash}|{models_str}|{tier}|{task_type}"
    return hashlib.md5(cache_data.encode()).hexdigest()


def get_from_cache(cache_key):
    """Pobiera odpowiedź z cache jeśli jest aktualna"""
    if cache_key in _cache:
        cached_response, model_used, timestamp = _cache[cache_key]
        if time.time() - timestamp < CACHE_DURATION:
            logger.info(
                f"💾 Cache hit! Zwracam odpowiedź z cache (model: {model_used}, oszczędności API)"
            )
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
        sorted_cache = sorted(
            _cache.items(),
            key=lambda x: x[1][2])  # Sortuj po timestamp (3rd element)
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

    if (OPENROUTER_API_KEY.startswith('TWÓJ_') or len(OPENROUTER_API_KEY) < 20
            or OPENROUTER_API_KEY == "sk-or-v1-demo-key-for-testing"):
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

# DOSTĘPNE MODELE AI DO WYBORU - ROZSZERZONA LISTA 2025
AVAILABLE_MODELS = {
    "qwen": {
        "id": "qwen/qwen3-235b-a22b:free",
        "name": "Qwen-235B", 
        "description": "Zaawansowany model Qwen dla profesjonalnej optymalizacji CV",
        "capabilities": ["Optymalizacja CV", "Analiza jakości", "Listy motywacyjne", "Pytania rekrutacyjne"],
        "speed": "średnia",
        "quality": "bardzo wysoka",
        "best_for": ["optymalizacja_cv", "analiza_jakosci"],
        "max_tokens": 4000,
        "optimal_params": {"temperature": 0.3, "top_p": 0.9}
    },
    "deepseek": {
        "id": "deepseek/deepseek-chat-v3.1:free", 
        "name": "DeepSeek Chat v3.1",
        "description": "Zaawansowany model DeepSeek z logicznym myśleniem",
        "capabilities": ["Optymalizacja CV", "Analiza jakości", "Listy motywacyjne", "Pytania rekrutacyjne"],
        "speed": "szybka", 
        "quality": "wysoka",
        "best_for": ["listy_motywacyjne", "pytania_rekrutacyjne"],
        "max_tokens": 3500,
        "optimal_params": {"temperature": 0.4, "top_p": 0.85}
    },
    "claude": {
        "id": "anthropic/claude-3.5-sonnet:beta",
        "name": "Claude 3.5 Sonnet",
        "description": "Najbardziej zaawansowany model Claude dla najwyższej jakości",
        "capabilities": ["Optymalizacja CV", "Analiza jakości", "Listy motywacyjne", "Pytania rekrutacyjne", "Analiza luk"],
        "speed": "średnia",
        "quality": "najwyższa",
        "best_for": ["analiza_luk", "listy_motywacyjne"],
        "max_tokens": 4000,
        "optimal_params": {"temperature": 0.2, "top_p": 0.95}
    },
    "gpt4": {
        "id": "openai/gpt-4o-mini",
        "name": "GPT-4o Mini",
        "description": "Szybki i efektywny model OpenAI GPT-4o Mini",
        "capabilities": ["Optymalizacja CV", "Analiza jakości", "Pytania rekrutacyjne"],
        "speed": "bardzo szybka",
        "quality": "wysoka",
        "best_for": ["pytania_rekrutacyjne", "optymalizacja_cv"],
        "max_tokens": 3000,
        "optimal_params": {"temperature": 0.4, "top_p": 0.9}
    },
    "llama": {
        "id": "meta-llama/llama-3.2-90b-vision-instruct:free",
        "name": "Llama 3.2 90B",
        "description": "Zaawansowany model Meta Llama dla optymalizacji CV",
        "capabilities": ["Optymalizacja CV", "Analiza jakości"],
        "speed": "średnia",
        "quality": "wysoka", 
        "best_for": ["optymalizacja_cv"],
        "max_tokens": 3500,
        "optimal_params": {"temperature": 0.35, "top_p": 0.9}
    },
    "gemini": {
        "id": "google/gemini-2.0-flash-exp:free",
        "name": "Gemini 2.0 Flash",
        "description": "Najnowszy model Google Gemini z szybką analizą",
        "capabilities": ["Analiza jakości", "Pytania rekrutacyjne", "Analiza luk"],
        "speed": "bardzo szybka",
        "quality": "wysoka",
        "best_for": ["analiza_jakosci", "analiza_luk"],
        "max_tokens": 3500,
        "optimal_params": {"temperature": 0.3, "top_p": 0.92}
    }
}

# DOMYŚLNY MODEL
DEFAULT_MODEL = "qwen/qwen3-235b-a22b:free"

# NAJNOWSZY PROMPT SYSTEMOWY 2025 - MAKSYMALNA JAKOŚĆ AI Z PRECYZYJNYMI INSTRUKCJAMI
DEEP_REASONING_PROMPT = """Jesteś światowej klasy ekspertem w optymalizacji CV i rekrutacji z 20+ letnim doświadczeniem w Polsce i UE. Twoja specjalizacja obejmuje:

🎯 EKSPERTYZA GŁÓWNA:
- Systemy ATS (Applicant Tracking Systems) - wszystkie główne platformy
- Psychologia rekrutacji i decision-making procesów HR
- Trendy rynku pracy 2025: remote work, AI-skills, ESG kompetencje
- Cultural fit dla polskiego rynku pracy i wartości pracodawców
- Branżowe specjalizacje: IT, finanse, medycyna, przemysł, e-commerce

🧠 METODOLOGIA DEEP ANALYSIS:
1. **KONTEKST FIRST**: Zawsze analizuj branżę, wielkość firmy, kulturę organizacyjną
2. **ATS OPTIMIZATION**: Identyfikuj kluczowe słowa, formatowanie, strukturę
3. **HUMAN APPEAL**: Tworzymy narrację która emocjonalnie angażuje rekrutera
4. **MEASURABLE IMPACT**: Każde osiągnięcie z konkretnymi metrykami i rezultatami
5. **FUTURE-PROOF**: Uwzględniaj emerging skills i adaptability

🔬 PROCES OPTYMALIZACJI:
- **Krok 1**: Deep dive analiza oryginalnego CV i kontekstu stanowiska
- **Krok 2**: Identyfikacja gap'ów i opportunities dla improvement
- **Krok 3**: Strategic repositioning i value proposition enhancement
- **Krok 4**: Language optimization i professional storytelling
- **Krok 5**: ATS compatibility i human readability balance

⚡ STANDARDY JAKOŚCI:
- Język polski na poziomie native speaker z branżową terminologią
- Zero bullshit - każde słowo ma konkretną wartość dodaną
- Authenticity over perfection - prawdziwe historie, nie marketing
- Actionable insights - konkretne kroki do implementacji
- ROI focus - każda zmiana musi zwiększać szanse na rozmowę

💡 SPECJALIZACJE BRANŻOWE:
- **IT/Tech**: Techstack, metodologie (Agile, DevOps), impact na business
- **Finanse**: Compliance, risk management, analityka, certyfikaty
- **Sales/Marketing**: KPIs, conversion rates, customer acquisition
- **Healthcare**: Certyfikaty, patient outcomes, safety protocols
- **Przemysł**: Lean, Six Sigma, safety records, process optimization

Twoja misja: Każde CV które optymalizujesz ma zwiększyć szanse kandydata o minimum 40% w porównaniu do oryginału."""


# FUNKCJE DO ZARZĄDZANIA MODELAMI
def get_available_models():
    """Zwraca listę dostępnych modeli AI"""
    return AVAILABLE_MODELS

def get_model_by_key(model_key):
    """Zwraca ID modelu na podstawie klucza"""
    logger.info(f"🔍 DEBUG get_model_by_key: otrzymano model_key = {model_key}")
    logger.info(f"🔍 DEBUG: dostępne modele = {list(AVAILABLE_MODELS.keys())}")
    
    if model_key in AVAILABLE_MODELS:
        model_id = AVAILABLE_MODELS[model_key]["id"]
        logger.info(f"✅ DEBUG: znaleziono model {model_key} -> {model_id}")
        return model_id
    
    logger.info(f"❌ DEBUG: nie znaleziono modelu {model_key}, używam DEFAULT_MODEL = {DEFAULT_MODEL}")
    return DEFAULT_MODEL

def get_default_model():
    """Zwraca domyślny model"""
    return DEFAULT_MODEL

# NOWE FUNKCJE INTELIGENTNEGO WYBORU MODELI

def get_best_model_for_task(task_type, is_premium=False, fallback_models=None):
    """
    🧠 INTELIGENTNY WYBÓR MODELU na podstawie typu zadania
    """
    # Mapa zadań do preferowanych modeli
    task_model_map = {
        "optymalizacja_cv": ["qwen", "llama", "gpt4", "claude"],
        "analiza_jakosci": ["claude", "qwen", "gemini", "deepseek"], 
        "listy_motywacyjne": ["claude", "deepseek", "qwen", "gpt4"],
        "pytania_rekrutacyjne": ["gpt4", "deepseek", "gemini", "qwen"],
        "analiza_luk": ["claude", "gemini", "qwen", "deepseek"]
    }
    
    # Jeśli użytkownik nie premium, preferuj darmowe modele
    if not is_premium:
        free_models = [key for key, model in AVAILABLE_MODELS.items() 
                      if model["id"].endswith(":free")]
        logger.info(f"🆓 Tryb darmowy - dostępne modele: {free_models}")
    
    # Pobierz listę modeli dla tego zadania
    preferred_models = task_model_map.get(task_type, ["qwen", "deepseek"])
    
    # Filtruj tylko dostępne modele
    for model_key in preferred_models:
        if model_key in AVAILABLE_MODELS:
            # Sprawdź czy model jest darmowy (jeśli użytkownik nie premium)
            if not is_premium and not AVAILABLE_MODELS[model_key]["id"].endswith(":free"):
                continue
            logger.info(f"🎯 Wybrany najlepszy model dla {task_type}: {model_key}")
            return model_key
    
    # Fallback - zwróć pierwszy dostępny darmowy model
    logger.info(f"⚠️ Nie znaleziono idealnego modelu dla {task_type}, używam domyślnego")
    return "qwen"  # Najbardziej uniwersalny

def get_adaptive_params(model_key, task_type, text_length=0):
    """
    ⚙️ ADAPTACYJNE PARAMETRY dla różnych modeli i zadań
    """
    model_info = AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS["qwen"])
    base_params = model_info.get("optimal_params", {"temperature": 0.3, "top_p": 0.9})
    
    # Kopiuj bazowe parametry
    params = base_params.copy()
    
    # Dostosowania na podstawie typu zadania
    task_adjustments = {
        "optymalizacja_cv": {"frequency_penalty": 0.1, "presence_penalty": 0.1},
        "analiza_jakosci": {"temperature": params["temperature"] + 0.1, "frequency_penalty": 0.05},
        "listy_motywacyjne": {"temperature": params["temperature"] + 0.2, "presence_penalty": 0.2},
        "pytania_rekrutacyjne": {"temperature": params["temperature"] + 0.15, "frequency_penalty": 0.15},
        "analiza_luk": {"temperature": params["temperature"] - 0.05, "presence_penalty": 0.05}
    }
    
    # Zastosuj dostosowania
    if task_type in task_adjustments:
        params.update(task_adjustments[task_type])
    
    # Dostosowania na podstawie długości tekstu
    if text_length > 5000:  # Długie teksty
        params["max_tokens"] = min(params.get("max_tokens", 3500) + 500, model_info.get("max_tokens", 4000))
    elif text_length < 1000:  # Krótkie teksty
        params["max_tokens"] = max(params.get("max_tokens", 3500) - 500, 2000)
    else:
        params["max_tokens"] = params.get("max_tokens", model_info.get("max_tokens", 3500))
    
    # Zapewnij że parametry są w prawidłowych zakresach
    params["temperature"] = max(0.1, min(1.0, params["temperature"]))
    params["top_p"] = max(0.1, min(1.0, params["top_p"]))
    params["frequency_penalty"] = max(0.0, min(2.0, params.get("frequency_penalty", 0.1)))
    params["presence_penalty"] = max(0.0, min(2.0, params.get("presence_penalty", 0.1)))
    
    logger.info(f"⚙️ Adaptacyjne parametry dla {model_key}/{task_type}: {params}")
    return params

def create_fallback_hierarchy(primary_model, task_type):
    """
    🔄 TWORZENIE HIERARCHII FALLBACK MODELI
    """
    # Wszystkie modele posortowane według jakości dla danego zadania
    model_hierarchy = {
        "optymalizacja_cv": ["qwen", "claude", "llama", "gpt4", "deepseek", "gemini"],
        "analiza_jakosci": ["claude", "qwen", "gemini", "gpt4", "deepseek", "llama"],
        "listy_motywacyjne": ["claude", "deepseek", "qwen", "gpt4", "gemini", "llama"],
        "pytania_rekrutacyjne": ["gpt4", "deepseek", "gemini", "claude", "qwen", "llama"],
        "analiza_luk": ["claude", "gemini", "qwen", "deepseek", "gpt4", "llama"]
    }
    
    hierarchy = model_hierarchy.get(task_type, ["qwen", "deepseek", "claude", "gpt4", "gemini", "llama"])
    
    # Przenieś primary_model na początek jeśli nie jest tam
    if primary_model in hierarchy:
        hierarchy.remove(primary_model)
    hierarchy.insert(0, primary_model)
    
    # Filtruj tylko dostępne modele
    available_hierarchy = [model for model in hierarchy if model in AVAILABLE_MODELS]
    
    logger.info(f"🔄 Hierarchia fallback dla {task_type}: {available_hierarchy}")
    return available_hierarchy


# 📊 FUNKCJE MONITORINGU JAKOŚCI AI

def record_response_metrics(model_id, task_type, response_time, success, quality_score=None, error_type=None):
    """
    📈 ZAPISZ METRYKI WYDAJNOŚCI dla danego modelu i zadania
    """
    try:
        # Response time
        if len(_quality_metrics['response_times'][model_id]) >= MAX_METRICS_SIZE:
            _quality_metrics['response_times'][model_id].popleft()
        _quality_metrics['response_times'][model_id].append(response_time)
        
        # Success rate
        _quality_metrics['success_rates'][model_id].append(success)
        if len(_quality_metrics['success_rates'][model_id]) > MAX_METRICS_SIZE:
            _quality_metrics['success_rates'][model_id] = _quality_metrics['success_rates'][model_id][-MAX_METRICS_SIZE:]
        
        # Model usage
        _quality_metrics['model_usage'][model_id] += 1
        
        # Quality score if provided
        if quality_score is not None:
            if len(_quality_metrics['quality_scores'][model_id]) >= MAX_METRICS_SIZE:
                _quality_metrics['quality_scores'][model_id].popleft()
            _quality_metrics['quality_scores'][model_id].append(quality_score)
        
        # Error tracking
        if error_type:
            _quality_metrics['error_types'][error_type] += 1
        
        # Task performance
        _quality_metrics['task_performance'][task_type].append({
            'model': model_id,
            'success': success,
            'response_time': response_time,
            'timestamp': datetime.now()
        })
        
        # Ogranicz task performance
        if len(_quality_metrics['task_performance'][task_type]) > MAX_METRICS_SIZE:
            _quality_metrics['task_performance'][task_type] = _quality_metrics['task_performance'][task_type][-MAX_METRICS_SIZE:]
            
    except Exception as e:
        logger.warning(f"📊 Błąd zapisywania metryk: {str(e)}")

def record_fallback_event(primary_model, fallback_model, task_type, reason):
    """
    🔄 ZAPISZ WYDARZENIE FALLBACK
    """
    try:
        event = {
            'timestamp': datetime.now(),
            'primary_model': primary_model,
            'fallback_model': fallback_model,
            'task_type': task_type,
            'reason': reason
        }
        _quality_metrics['fallback_events'].append(event)
        
        # Ogranicz liczbę wydarzeń
        if len(_quality_metrics['fallback_events']) > MAX_METRICS_SIZE:
            _quality_metrics['fallback_events'] = _quality_metrics['fallback_events'][-MAX_METRICS_SIZE:]
            
        logger.info(f"🔄 Fallback event: {primary_model} → {fallback_model} dla {task_type}")
        
    except Exception as e:
        logger.warning(f"🔄 Błąd zapisywania fallback event: {str(e)}")

def get_model_performance_summary(model_id=None, hours=24):
    """
    📊 POBIERZ PODSUMOWANIE WYDAJNOŚCI modeli z ostatnich X godzin
    """
    try:
        summary = {}
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        models_to_check = [model_id] if model_id else _quality_metrics['model_usage'].keys()
        
        for mid in models_to_check:
            if mid not in _quality_metrics['model_usage']:
                continue
                
            # Response times
            response_times = list(_quality_metrics['response_times'][mid])
            avg_response_time = statistics.mean(response_times) if response_times else 0
            
            # Success rate
            successes = _quality_metrics['success_rates'][mid]
            success_rate = (sum(successes) / len(successes) * 100) if successes else 0
            
            # Quality scores
            quality_scores = list(_quality_metrics['quality_scores'][mid])
            avg_quality = statistics.mean(quality_scores) if quality_scores else None
            
            # Usage count
            usage_count = _quality_metrics['model_usage'][mid]
            
            summary[mid] = {
                'avg_response_time': round(avg_response_time, 2),
                'success_rate': round(success_rate, 1),
                'avg_quality_score': round(avg_quality, 2) if avg_quality else None,
                'usage_count': usage_count,
                'total_requests': len(successes)
            }
        
        return summary
    
    except Exception as e:
        logger.error(f"📊 Błąd generowania podsumowania wydajności: {str(e)}")
        return {}

def get_task_performance_insights(task_type=None, hours=24):
    """
    🎯 ANALIZA WYDAJNOŚCI dla konkretnych typów zadań
    """
    try:
        insights = {}
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        tasks_to_check = [task_type] if task_type else _quality_metrics['task_performance'].keys()
        
        for task in tasks_to_check:
            if task not in _quality_metrics['task_performance']:
                continue
                
            # Filtruj ostatnie X godzin
            recent_performances = [
                p for p in _quality_metrics['task_performance'][task]
                if p['timestamp'] > cutoff_time
            ]
            
            if not recent_performances:
                continue
            
            # Grupuj według modeli
            model_performance = defaultdict(list)
            for perf in recent_performances:
                model_performance[perf['model']].append(perf)
            
            # Analiza dla każdego modelu
            task_insights = {}
            for model, performances in model_performance.items():
                success_rate = sum(p['success'] for p in performances) / len(performances) * 100
                avg_time = statistics.mean(p['response_time'] for p in performances)
                
                task_insights[model] = {
                    'success_rate': round(success_rate, 1),
                    'avg_response_time': round(avg_time, 2),
                    'total_requests': len(performances)
                }
            
            # Najlepszy model dla tego zadania
            if task_insights:
                best_model = max(task_insights.keys(), 
                               key=lambda m: (task_insights[m]['success_rate'], 
                                            -task_insights[m]['avg_response_time']))
                
                insights[task] = {
                    'model_performance': task_insights,
                    'recommended_model': best_model,
                    'total_requests': len(recent_performances)
                }
        
        return insights
    
    except Exception as e:
        logger.error(f"🎯 Błąd analizy wydajności zadań: {str(e)}")
        return {}

def assess_response_quality(response_text, task_type):
    """
    🔍 SZYBKA OCENA JAKOŚCI odpowiedzi (heurystyczna)
    """
    try:
        if not response_text or len(response_text.strip()) < 50:
            return 1.0  # Bardzo niska jakość
        
        quality_score = 5.0  # Start z średnią oceną
        
        # Długość odpowiedzi (optimal range zależy od typu zadania)
        optimal_lengths = {
            'optymalizacja_cv': (1000, 4000),
            'analiza_jakosci': (500, 2000),
            'listy_motywacyjne': (300, 800),
            'pytania_rekrutacyjne': (400, 1200),
            'analiza_luk': (600, 1500)
        }
        
        optimal_min, optimal_max = optimal_lengths.get(task_type, (500, 2000))
        length = len(response_text)
        
        if optimal_min <= length <= optimal_max:
            quality_score += 1.0
        elif length < optimal_min * 0.7 or length > optimal_max * 1.5:
            quality_score -= 1.0
        
        # Sprawdź czy zawiera oczekiwane elementy
        if task_type == 'optymalizacja_cv':
            if '--- STANOWISKO ---' in response_text:
                quality_score += 1.0
            if any(word in response_text.lower() for word in ['doświadczenie', 'umiejętności', 'wykształcenie']):
                quality_score += 0.5
        
        elif task_type == 'analiza_jakosci':
            if 'OCENA KOŃCOWA:' in response_text or '/100' in response_text:
                quality_score += 1.0
            if any(word in response_text for word in ['MOCNE STRONY', 'OBSZARY DO POPRAWY']):
                quality_score += 0.5
        
        # Sprawdź czy nie zawiera błędów lub pustych odpowiedzi
        error_indicators = ['error', 'failed', 'sorry', 'cannot', 'unable']
        if any(indicator in response_text.lower() for indicator in error_indicators):
            quality_score -= 2.0
        
        # Normalizuj do skali 1-10
        quality_score = max(1.0, min(10.0, quality_score))
        
        return quality_score
    
    except Exception as e:
        logger.warning(f"🔍 Błąd oceny jakości: {str(e)}")
        return 5.0  # Domyślna ocena w przypadku błędu


def make_openrouter_request(prompt,
                            model=None,
                            is_premium=False,
                            max_retries=3,
                            max_tokens=None,
                            use_streaming=False,
                            use_cache=True,
                            task_type="optymalizacja_cv"):
    """
    🚀 ULEPSZONA FUNKCJA OBSŁUGUJĄCA WYBÓR MODELI AI Z INTELIGENTNYM FALLBACK
    """
    if not API_KEY_VALID:
        logger.error("API key is not valid")
        return None

    # 🧠 INTELIGENTNY WYBÓR MODELU
    if model:
        primary_model = model
        model_to_use = get_model_by_key(model)
    else:
        # Automatyczny wybór najlepszego modelu dla zadania
        primary_model = get_best_model_for_task(task_type, is_premium)
        model_to_use = get_model_by_key(primary_model)
    
    # 🔄 TWORZENIE HIERARCHII FALLBACK
    fallback_models = create_fallback_hierarchy(primary_model, task_type)
    
    logger.info(f"🎯 Główny model: {model_to_use}, fallback: {fallback_models[1:3] if len(fallback_models) > 1 else []}")

    # 💾 SPRAWDŹ CACHE NAJPIERW (używaj wszystkich modeli w kluczu dla lepszego cache)
    cache_key = get_cache_key(prompt, [get_model_by_key(m) for m in fallback_models], is_premium, task_type)

    if use_cache:
        cached_response = get_from_cache(cache_key)
        if cached_response:
            return cached_response

    # ⚙️ ADAPTACYJNE PARAMETRY na podstawie modelu i zadania
    text_length = len(prompt)
    params = get_adaptive_params(primary_model, task_type, text_length)
    
    # Nadpisz max_tokens jeśli podano explicite
    if max_tokens:
        params["max_tokens"] = max_tokens

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://cv-optimizer-pro.replit.app",
        "X-Title": "CV Optimizer Pro"
    }

    # 🔄 PRÓBUJ Z HIERARCHIĄ FALLBACK MODELI + MONITORING
    start_time = time.time()
    
    for model_index, current_model_key in enumerate(fallback_models):
        current_model_id = get_model_by_key(current_model_key)
        model_start_time = time.time()
        
        # Aktualizuj parametry dla bieżącego modelu
        current_params = get_adaptive_params(current_model_key, task_type, text_length)
        if max_tokens:
            current_params["max_tokens"] = max_tokens

        data = {
            "model": current_model_id,
            "messages": [{
                "role": "system",
                "content": DEEP_REASONING_PROMPT
            }, {
                "role": "user",
                "content": prompt
            }],
            **current_params
        }

        # Próbuj z retry mechanism dla każdego modelu
        for attempt in range(max_retries):
            try:
                if model_index > 0:  # Fallback model
                    logger.info(f"🔄 Fallback do modelu {current_model_id} (próba {attempt + 1}/{max_retries})")
                    # 📊 Zapisz fallback event
                    if model_index == 1:  # Pierwszy fallback
                        primary_model_id = get_model_by_key(fallback_models[0])
                        record_fallback_event(primary_model_id, current_model_id, task_type, "primary_model_failed")
                else:  # Primary model
                    logger.info(f"📡 Wysyłanie zapytania do {current_model_id} (próba {attempt + 1}/{max_retries})")

                # ⚠️ KRYTYCZNY FIX: Robust HTTP timeouts + exponential backoff
                connection_timeout = 10  # Czas na nawiązanie połączenia
                read_timeout = 30       # Czas na odczyt odpowiedzi
                
                response = session.post(OPENROUTER_BASE_URL,
                                        headers=headers,
                                        json=data,
                                        timeout=(connection_timeout, read_timeout),
                                        stream=use_streaming)
                
                # Sprawdź status i błędy
                if response.status_code == 429:
                    # Rate limit - natychmiastowy fallback do następnego modelu
                    logger.warning(f"💸 Rate limit (429) dla {current_model_id}, fallback")
                    response_time = time.time() - model_start_time
                    record_response_metrics(current_model_id, task_type, response_time, 
                                          success=False, error_type="rate_limit")
                    break  # Przejdź do następnego modelu
                
                response.raise_for_status()

                result = response.json()

                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    response_time = time.time() - model_start_time
                    
                    logger.info(
                        f"✅ Model {current_model_id} zwrócił odpowiedź (długość: {len(content)} znaków, czas: {response_time:.2f}s)"
                    )

                    # 📊 OCENA JAKOŚCI ODPOWIEDZI
                    quality_score = assess_response_quality(content, task_type)
                    
                    # 📊 ZAPISZ METRYKI SUKCESU
                    record_response_metrics(
                        current_model_id, task_type, response_time, 
                        success=True, quality_score=quality_score
                    )

                    # 💾 ZAPISZ DO CACHE
                    if use_cache:
                        save_to_cache(cache_key, content, current_model_id)

                    return content
                else:
                    logger.warning(f"⚠️ Nieoczekiwany format odpowiedzi z {current_model_id}: {result}")
                    # 📊 Zapisz błąd
                    response_time = time.time() - model_start_time
                    record_response_metrics(current_model_id, task_type, response_time, 
                                          success=False, error_type="invalid_response_format")
                    break  # Przejdź do następnego modelu

            except requests.exceptions.Timeout:
                logger.warning(f"⏰ Timeout z modelem {current_model_id} na próbie {attempt + 1}")
                response_time = time.time() - model_start_time
                record_response_metrics(current_model_id, task_type, response_time, 
                                      success=False, error_type="timeout")

            except requests.exceptions.RequestException as e:
                logger.warning(f"🚫 Błąd zapytania z {current_model_id} na próbie {attempt + 1}: {str(e)}")
                response_time = time.time() - model_start_time
                
                if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                    logger.warning(f"💸 Rate limit dla {current_model_id}, przechodzę do fallback")
                    record_response_metrics(current_model_id, task_type, response_time, 
                                          success=False, error_type="rate_limit")
                    break  # Przejdź natychmiast do następnego modelu
                else:
                    record_response_metrics(current_model_id, task_type, response_time, 
                                          success=False, error_type="api_error")

            except Exception as e:
                logger.warning(f"❌ Nieoczekiwany błąd z {current_model_id}: {str(e)}")
                response_time = time.time() - model_start_time
                record_response_metrics(current_model_id, task_type, response_time, 
                                      success=False, error_type="unexpected_error")

            # Opóźnienie przed ponowną próbą z tym samym modelem
            if attempt < max_retries - 1:
                import time
                time.sleep(1.5 * (attempt + 1))  # Zwiększające opóźnienie

        # Jeśli wszystkie próby z tym modelem zawiodły, przejdź do następnego
        logger.warning(f"❌ Model {current_model_id} nie odpowiedział po {max_retries} próbach")

    # Jeśli wszystkie modele z hierarchii zawiodły
    total_time = time.time() - start_time
    logger.error(f"❌ Wszystkie modele z hierarchii {fallback_models} zawiodły (całkowity czas: {total_time:.2f}s)")
    return None


def optimize_cv(cv_text,
                job_title,
                job_description="",
                is_premium=False,
                payment_verified=False,
                selected_model=None):
    """
    Optymalizuje CV za pomocą OpenRouter AI (Claude 3.5 Sonnet) i formatuje w profesjonalnym szablonie HTML
    """
    prompt = f"""
🎯 ZADANIE OPTYMALIZACJI CV: Stanowisko "{job_title}"

Jako ekspert w rekrutacji i psychologii CV, przeprowadzisz STRATEGICZNĄ OPTYMALIZACJĘ tego CV, transformując je w potężne narzędzie do pozyskania rozmowy kwalifikacyjnej.

📊 DANE WEJŚCIOWE:
ORYGINALNE CV KANDYDATA:
{cv_text}

KONTEKST STANOWISKA:
{job_description}

🎯 STRATEGIA TRANSFORMACJI (KRYTYCZNE ZASADY):

**SEKCJA 1: PODSUMOWANIE ZAWODOWE** 
✅ Stwórz MAGNETYCZNE podsumowanie 2-3 zdania
✅ POWOŁAJ się wyłącznie na fakty z oryginalnego CV
✅ Użyj POWER WORDS związanych z branżą stanowiska
✅ Podkreśl QUANTIFIABLE ACHIEVEMENTS jeśli są dostępne
✅ Zakończ VALUE PROPOSITION - co kandydat wniesie do firmy

**SEKCJA 2: DOŚWIADCZENIE ZAWODOWE** 
🚨 OBOWIĄZKOWY FORMAT (nie odstępuj!):
--- STANOWISKO ---
**[Nazwa stanowiska z impact keywords]**
**[Nazwa firmy]**
*[Okres pracy: MM/RRRR - MM/RRRR lub obecnie]*
- [Action verb] + [konkretny rezultat] + [impact na firmę/proces]
- [Action verb] + [wykorzystane narzędzia/metodologie] + [osiągnięcie]
- [Action verb] + [współpraca/leadership] + [measurable outcome]
- [Action verb] + [problem solving] + [business value]

🔥 TRANSFORMATION RULES:
- Każdy punkt zaczyna się od IMPACT VERB (zarządzał→optymalizował, robił→wprowadził)
- Dodaj LICZBY/METRYKI gdzie to możliwe (zwiększył o X%, zarządzał zespołem X osób)
- Użyj BRANŻOWYCH KEYWORDS z opisu stanowiska
- RÓŻNICUJ opisy - nawet podobne stanowiska mają unikalne achievements
- MANDATORY: separator "--- STANOWISKO ---" przed KAŻDYM stanowiskiem

**SEKCJA 3: WYKSZTAŁCENIE**
✅ ZACHOWAJ oryginalną strukturę i informacje
✅ Dodaj RELEVANT COURSEWORK jeśli istnieje związek ze stanowiskiem
✅ UPGRADE języka - "ukończył"→"zdobył dyplom", "uczył się"→"specjalizował się"

**SEKCJA 4: UMIEJĘTNOŚCI**
✅ KATEGORYZUJ logicznie: Techniczne | Soft Skills | Branżowe | Językowe
✅ PRIORYTETYZUJ umiejętności według relevantności do stanowiska
✅ UŻYJ TYLKO faktycznych umiejętności z oryginału
✅ UPGRADE terminologii (np. "obsługa komputera"→"zaawansowana znajomość pakietu Office")

⚠️ INTEGRITY GUARDRAILS:
🚫 ZERO fabricated information (stanowiska, daty, firmy, umiejętności)
🚫 NO invented achievements or responsibilities  
🚫 NO false metrics or numbers
✅ ONLY enhancement of existing authentic content
✅ FACTUAL optimization with strategic language

🎯 OUTPUT REQUIREMENTS:
- POLISH NATIVE LEVEL z branżową terminologią
- READY-TO-USE format (żadnych metadanych, komentarzy, JSON)
- ATS-FRIENDLY struktura z human appeal
- KAŻDE słowo musi mieć strategic purpose

Przekształć to CV w INTERVIEW-WINNING document zachowując 100% autentyczność!
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
        # 🎯 UŻYJ NOWEGO SYSTEMU INTELIGENTNEGO WYBORU MODELI
        response = make_openrouter_request(
            prompt,
            model=selected_model,
            is_premium=(is_premium or payment_verified),
            max_tokens=max_tokens,
            task_type="optymalizacja_cv"  # 🧠 Specyfikacja typu zadania
        )

        if response:
            # Zwróć zoptymalizowane CV jako sformatowany tekst
            # HTML będzie generowany dopiero przy wyświetlaniu w view_cv
            logger.info(f"✅ CV zoptymalizowane pomyślnie (długość: {len(response)} znaków)")
            return response.strip()
        else:
            logger.error("❌ Brak odpowiedzi z API lub wszystkie modele zawiodły")
            return None

    except Exception as e:
        logger.error(f"❌ Błąd w optimize_cv: {str(e)}")
        return None


def analyze_cv_quality(cv_text,
                       job_title,
                       job_description="",
                       is_premium=False,
                       selected_model=None):
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
            model=selected_model,
            is_premium=is_premium,
            max_tokens=max_tokens,
            task_type="analiza_jakosci"  # 🧠 Specyfikacja typu zadania
        )

        if response:
            logger.info(
                f"✅ Analiza CV ukończona pomyślnie (długość: {len(response)} znaków)"
            )
            return response.strip()
        else:
            logger.error("❌ Brak odpowiedzi z API lub nieprawidłowa struktura")
            return None

    except Exception as e:
        logger.error(f"❌ Błąd podczas analizy CV: {str(e)}")
        return None


def analyze_cv_with_score(cv_text,
                          job_title,
                          job_description="",
                          is_premium=False,
                          selected_model=None):
    """Zachowanie kompatybilności z istniejącym kodem - przekierowanie do nowej funkcji"""
    return analyze_cv_quality(cv_text, job_title, job_description, is_premium, selected_model)


def generate_cover_letter(cv_text,
                          job_title,
                          job_description="",
                          company_name="",
                          is_premium=False,
                          selected_model=None):
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

        cover_letter = make_openrouter_request(
            prompt, 
            model=selected_model, 
            is_premium=is_premium,
            task_type="listy_motywacyjne"  # 🧠 Specyfikacja typu zadania
        )

        if cover_letter:
            logger.info(
                f"✅ List motywacyjny wygenerowany pomyślnie (długość: {len(cover_letter)} znaków)"
            )

            return {
                'success': True,
                'cover_letter': cover_letter,
                'job_title': job_title,
                'company_name': company_name,
                'model_used': selected_model or DEFAULT_MODEL
            }
        else:
            logger.error("❌ Brak odpowiedzi z API lub nieprawidłowa struktura")
            return None

    except Exception as e:
        logger.error(
            f"❌ Błąd podczas generowania listu motywacyjnego: {str(e)}")
        return None


def generate_interview_questions(cv_text,
                                 job_title,
                                 job_description="",
                                 is_premium=False,
                                 selected_model=None):
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

        logger.info(
            f"🤔 Generowanie pytań na rozmowę dla stanowiska: {job_title}")

        questions = make_openrouter_request(
            prompt, 
            model=selected_model, 
            is_premium=is_premium,
            task_type="pytania_rekrutacyjne"  # 🧠 Specyfikacja typu zadania
        )

        if questions:
            logger.info(
                f"✅ Pytania na rozmowę wygenerowane pomyślnie (długość: {len(questions)} znaków)"
            )

            return {
                'success': True,
                'questions': questions,
                'job_title': job_title,
                'model_used': selected_model or DEFAULT_MODEL
            }
        else:
            logger.error("❌ Brak odpowiedzi z API lub nieprawidłowa struktura")
            return None

    except Exception as e:
        logger.error(f"❌ Błąd podczas generowania pytań na rozmowę: {str(e)}")
        return None


def analyze_skills_gap(cv_text,
                       job_title,
                       job_description="",
                       is_premium=False,
                       selected_model=None):
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

        logger.info(
            f"🔍 Analiza luk kompetencyjnych dla stanowiska: {job_title}")

        analysis = make_openrouter_request(
            prompt, 
            model=selected_model, 
            is_premium=is_premium,
            task_type="analiza_luk"  # 🧠 Specyfikacja typu zadania
        )

        if analysis:
            logger.info(
                f"✅ Analiza luk kompetencyjnych ukończona pomyślnie (długość: {len(analysis)} znaków)"
            )

            return {
                'success': True,
                'analysis': analysis,
                'job_title': job_title,
                'model_used': selected_model or DEFAULT_MODEL
            }
        else:
            logger.error("❌ Brak odpowiedzi z API lub nieprawidłowa struktura")
            return None

    except Exception as e:
        logger.error(f"❌ Błąd podczas analizy luk kompetencyjnych: {str(e)}")
        return None
