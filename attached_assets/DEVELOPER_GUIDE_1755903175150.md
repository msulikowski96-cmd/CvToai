
# 🚀 CV Optimizer Pro - Przewodnik Developera

## 📋 Przegląd Projektu

CV Optimizer Pro to zaawansowana aplikacja webowa wykorzystująca AI do optymalizacji CV i dokumentów aplikacyjnych. Aplikacja oferuje:

- **Upload i analiza CV** (PDF processing)
- **AI-powered optymalizacja** z OpenRouter API
- **System płatności** Stripe (9.99 PLN / 29.99 PLN Premium)
- **Kompletny system użytkowników** z autentykacją
- **Progressive Web App** (PWA) functionality
- **Premium dashboard** ze statystykami

## 🏗️ Architektura Aplikacji

### Backend Stack:
- **Flask** - Python web framework
- **SQLAlchemy** - ORM dla bazy danych
- **Flask-Login** - zarządzanie sesjami użytkowników
- **Flask-Bcrypt** - hashowanie haseł
- **PostgreSQL/SQLite** - baza danych (SQLite fallback)

### Frontend Stack:
- **Bootstrap 5** - responsive UI framework
- **Vanilla JavaScript** - interaktywność
- **Progressive Web App** - funkcjonalność offline
- **Glassmorphism Design** - nowoczesny UI

### External APIs:
- **OpenRouter** - AI/LLM integration
- **Stripe** - payment processing
- **PyPDF2** - PDF text extraction

## 📁 Struktura Plików

```
cv-optimizer-pro/
├── app.py                 # Main Flask application
├── models.py              # Database models (User, CVUpload, AnalysisResult)
├── forms.py               # WTForms validation forms
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (DO NOT COMMIT)
├── check_config.py        # Configuration validator
├── manifest.json          # PWA manifest
├── service-worker.js      # PWA service worker
├── 
├── static/
│   ├── css/
│   │   ├── custom.css              # Main styles
│   │   ├── enhanced-visibility.css # Accessibility improvements
│   │   ├── mobile-enhanced.css     # Mobile optimizations
│   │   ├── theme-toggle.css        # Dark/light theme
│   │   └── visual-enhancements.css # UI animations
│   ├── js/
│   │   ├── main.js                 # Core JavaScript functionality
│   │   └── theme-toggle.js         # Theme switching logic
│   └── icons/                      # PWA icons (16x16 to 512x512)
│
├── templates/
│   ├── base.html                   # Base template with navigation
│   ├── index.html                  # Main landing page
│   ├── checkout.html               # Payment page
│   ├── cv_generator.html           # CV builder interface
│   ├── ai_cv_generator.html        # AI-powered CV generator
│   ├── payment_options.html        # Pricing plans
│   ├── premium_dashboard.html      # Premium user dashboard
│   ├── auth/
│   │   ├── login.html              # User login
│   │   ├── register.html           # User registration
│   │   └── profile.html            # User profile management
│   └── [other pages...]
│
└── utils/
    ├── openrouter_api.py           # AI/LLM integration
    ├── pdf_extraction.py           # PDF text processing
    ├── cv_validator.py             # CV quality validation
    ├── rate_limiter.py             # API rate limiting
    ├── encryption.py               # Data encryption utilities
    ├── security_middleware.py      # Security headers
    └── notifications.py            # User notifications system
```

## 🔧 Konfiguracja Projektu

### 1. **Utwórz nowy Repl**
```bash
# W Replit stwórz nowy Python Repl
# Skopiuj wszystkie pliki do głównego katalogu
```

### 2. **Zainstaluj zależności**
```bash
pip install -r requirements.txt
```

### 3. **Skonfiguruj zmienne środowiskowe**
W panelu **Secrets** w Replit dodaj:

```env
# AI API (WYMAGANE)
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-api-key

# Payment Processing (WYMAGANE)
STRIPE_SECRET_KEY=sk_test_your-stripe-secret-key
VITE_STRIPE_PUBLIC_KEY=pk_test_your-stripe-public-key

# Security (WYMAGANE)
SECRET_KEY=your-super-secret-flask-key
SESSION_SECRET=your-session-secret-key

# Database (OPCJONALNE - SQLite fallback)
DATABASE_URL=postgresql://user:password@host:port/database

# Email (OPCJONALNE)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### 4. **Zainicjalizuj bazę danych**
```python
# Automatycznie tworzone przy pierwszym uruchomieniu
# Konto developer: username='developer', password='NewDev2024!'
```

## 💰 Model Biznesowy

### Poziomy dostępu:
1. **Free** - Podgląd z watermarkiem
2. **Single CV (9.99 PLN)** - Podstawowe funkcje AI
3. **Premium (29.99 PLN/mies)** - Pełny dostęp + dashboard

### Funkcje AI według poziomów:
```python
# Darmowe (z watermarkiem)
free_functions = ['preview_only']

# Za 9.99 PLN
basic_paid_functions = [
    'optimize_cv',           # Optymalizacja CV
    'ats_optimization_check', # Sprawdzenie ATS
    'grammar_check'          # Sprawdzenie gramatyki
]

# Premium 29.99 PLN/miesiąc
premium_functions = [
    'recruiter_feedback',         # Opinia rekrutera
    'cover_letter',              # List motywacyjny
    'cv_score',                  # Analiza punktacji
    'interview_tips',            # Wskazówki do rozmowy
    'keyword_analysis',          # Analiza słów kluczowych
    'position_optimization',     # Optymalizacja pod stanowisko
    'interview_questions',       # Pytania rekrutacyjne
    'advanced_position_optimization', # Zaawansowana optymalizacja
    'ai_cv_generator'            # Generator CV AI
]
```

## 🔌 Kluczowe API Endpointy

### Authentication:
```python
@app.route('/login', methods=['GET', 'POST'])
@app.route('/register', methods=['GET', 'POST'])
@app.route('/logout')
```

### CV Processing:
```python
@app.route('/upload-cv', methods=['POST'])          # Upload PDF/text
@app.route('/process-cv', methods=['POST'])         # AI analysis
@app.route('/generate-improve-cv', methods=['POST']) # AI improvements
```

### Payment:
```python
@app.route('/create-payment-intent', methods=['POST'])     # Single payment
@app.route('/create-premium-subscription', methods=['POST']) # Premium sub
@app.route('/verify-payment', methods=['POST'])            # Payment verification
```

### CV Generator:
```python
@app.route('/create-cv-payment', methods=['POST'])    # CV builder payment
@app.route('/generate-cv-pdf', methods=['POST'])      # PDF generation
@app.route('/api/generate-ai-cv', methods=['POST'])   # AI CV generation
```

## 🧠 AI Integration (OpenRouter)

### Główne funkcje AI:
```python
# utils/openrouter_api.py

def optimize_cv(cv_text, job_description, language='pl', is_premium=False):
    """Optymalizacja CV pod konkretne stanowisko"""
    
def generate_recruiter_feedback(cv_text, job_description, language='pl'):
    """Generowanie opinii rekrutera"""
    
def generate_cover_letter(cv_text, job_description, language='pl'):
    """Generowanie listu motywacyjnego"""
    
def ats_optimization_check(cv_text, job_description, language='pl'):
    """Sprawdzenie kompatybilności z ATS"""
    
def generate_interview_questions(cv_text, job_description, language='pl'):
    """Generowanie pytań rekrutacyjnych"""
```

### Przykład konfiguracji AI:
```python
import requests
import os

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

def call_openrouter_api(prompt, max_tokens=2000, model="anthropic/claude-3.5-sonnet"):
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    
    response = requests.post(OPENROUTER_API_URL, headers=headers, json=data)
    return response.json()['choices'][0]['message']['content']
```

## 💳 Stripe Payment Integration

### Konfiguracja Stripe:
```python
import stripe

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Jednorazowa płatność (9.99 PLN)
def create_payment_intent():
    intent = stripe.PaymentIntent.create(
        amount=999,  # 9.99 PLN w groszach
        currency='pln',
        metadata={'service': 'cv_optimization'}
    )
    return intent

# Subskrypcja Premium (29.99 PLN/mies)
def create_subscription():
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'pln',
                'product_data': {'name': 'CV Optimizer Premium'},
                'unit_amount': 2999,
                'recurring': {'interval': 'month'},
            },
            'quantity': 1,
        }],
        mode='subscription',
        success_url='your-success-url',
        cancel_url='your-cancel-url'
    )
    return session
```

## 🗄️ Database Models

### User Model:
```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    premium_until = db.Column(db.DateTime)  # Premium expiration
    stripe_customer_id = db.Column(db.String(100))
    
    def is_premium_active(self):
        return self.premium_until and datetime.utcnow() < self.premium_until
    
    def is_developer(self):
        return self.username == 'developer'
```

### CV Upload Model:
```python
class CVUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    filename = db.Column(db.String(255), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    job_description = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### Analysis Result Model:
```python
class AnalysisResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cv_upload_id = db.Column(db.Integer, db.ForeignKey('cv_uploads.id'))
    analysis_type = db.Column(db.String(50), nullable=False)
    result_data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## 📱 Progressive Web App (PWA)

### Manifest.json:
```json
{
    "name": "CV Optimizer Pro",
    "short_name": "CV Optimizer",
    "description": "Optymalizuj swoje CV z AI",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#1a1a1a",
    "theme_color": "#6366f1",
    "icons": [
        {
            "src": "/static/icons/icon-192x192.png",
            "sizes": "192x192",
            "type": "image/png"
        }
    ]
}
```

### Service Worker:
```javascript
// service-worker.js
const CACHE_NAME = 'cv-optimizer-v1';
const urlsToCache = [
    '/',
    '/static/css/custom.css',
    '/static/js/main.js',
    '/static/icons/icon-192x192.png'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
    );
});
```

## 🔒 Security Features

### Implementowane zabezpieczenia:
- **CSRF Protection** - Flask-WTF tokens
- **Password Hashing** - bcrypt
- **Session Security** - secure cookies
- **Rate Limiting** - API call limits
- **Data Encryption** - sensitive data
- **Input Validation** - XSS prevention

### Przykład middleware:
```python
# utils/security_middleware.py
def init_app(app):
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
```

## 🚀 Deployment na Replit

### 1. **Utwórz repozytorium**
```bash
# Push kod na GitHub
git init
git add .
git commit -m "Initial CV Optimizer Pro"
git push origin main
```

### 2. **Deploy na Replit**
- Stwórz nowy Repl z GitHub repo
- Ustaw environment variables w Secrets
- Kliknij Run

### 3. **Konfiguracja domeny**
- W Replit przejdź do Deployments
- Skonfiguruj custom domain (opcjonalne)

## 📊 Monitoring i Analytics

### Śledzenie użycia:
```python
# utils/analytics.py
def track_cv_optimization(user_id, optimization_type):
    """Track CV optimization events"""
    
def track_payment(user_id, amount, payment_type):
    """Track payment events"""
    
def generate_usage_stats():
    """Generate usage statistics for admin dashboard"""
```

## 🧪 Testing Strategy

### Jednostki do testowania:
1. **User Authentication** - login/register/logout
2. **CV Upload** - PDF processing
3. **AI Integration** - OpenRouter API calls
4. **Payment Flow** - Stripe integration
5. **Database Operations** - CRUD operations
6. **Security** - CSRF, XSS, authentication

### Przykład testu:
```python
def test_cv_upload():
    with app.test_client() as client:
        # Login as test user
        client.post('/login', data={'username': 'test', 'password': 'test'})
        
        # Upload CV
        response = client.post('/upload-cv', data={
            'cv_file': (BytesIO(b'test pdf content'), 'test.pdf')
        })
        
        assert response.status_code == 200
        assert 'success' in response.get_json()
```

## 📈 Scaling Considerations

### Performance optimizations:
1. **Database indexing** - user_id, email fields
2. **Session optimization** - limit session data size
3. **Caching** - static files, frequently accessed data
4. **Rate limiting** - prevent API abuse
5. **Async processing** - background tasks for heavy AI operations

### Monitoring:
```python
# Performance monitoring
@app.before_request
def monitor_session_size():
    session_size = len(pickle.dumps(dict(session)))
    if session_size > 9500:  # 9.5KB warning
        optimize_session_data()
```

## 🎯 Najlepsze Praktyki

### 1. **Environment Management**
```python
# Zawsze używaj zmiennych środowiskowych
API_KEY = os.environ.get('OPENROUTER_API_KEY')
if not API_KEY:
    raise ValueError("API key not configured")
```

### 2. **Error Handling**
```python
try:
    result = call_ai_api(prompt)
except Exception as e:
    logger.error(f"AI API error: {str(e)}")
    return jsonify({'error': 'Service temporarily unavailable'})
```

### 3. **User Experience**
- Loading indicators dla AI operations
- Clear error messages
- Progressive enhancement
- Mobile-first design

### 4. **Data Protection**
- Minimal data collection
- GDPR compliance
- Secure data storage
- Regular security audits

## 🚀 Następne kroki

1. **Fork this Repl** lub skopiuj strukturę
2. **Ustaw API keys** w Replit Secrets
3. **Dostosuj UI/UX** do swojej marki
4. **Dodaj unique features** (np. inne języki, branże)
5. **Deploy i testuj** na prawdziwych użytkownikach

---

**Powodzenia z tworzeniem własnej aplikacji CV Optimizer!** 🎉

Jeśli masz pytania, sprawdź kod źródłowy lub skontaktuj się przez Issues na GitHub.
