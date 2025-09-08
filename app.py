import os
import sys
import logging
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from sqlalchemy import or_
import stripe

# Force UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'C.UTF-8'
os.environ['LANG'] = 'C.UTF-8'

# Skip reconfigure on systems where it's not available
try:
    if hasattr(sys.stdout, 'reconfigure') and callable(
            getattr(sys.stdout, 'reconfigure', None)):
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
    if hasattr(sys.stderr, 'reconfigure') and callable(
            getattr(sys.stderr, 'reconfigure', None)):
        if sys.stderr.encoding != 'utf-8':
            sys.stderr.reconfigure(encoding='utf-8')  # type: ignore
except (AttributeError, OSError):
    pass

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET",
                                "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# --- DODAJ TUTAJ ---
from flask import send_from_directory
import os

@app.route('/ads.txt')
def ads_txt():
    # Plik ads.txt musi być w katalogu głównym obok tego pliku .py
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'ads.txt')


# Configure the database - using Neon Database (PostgreSQL)
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    # Fallback to SQLite for development if no Neon database URL
    database_url = "sqlite:///cv_optimizer.db"
    logger.warning("No DATABASE_URL found, using SQLite fallback")
else:
    logger.info("Using Neon Database (PostgreSQL)")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
logger.info(
    f"Using database: {'PostgreSQL' if 'postgresql' in database_url else 'SQLite'}"
)

# Configure database engine options based on database type
if database_url and database_url.startswith("sqlite"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
    }
    logger.info("Using SQLite database configuration")
else:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "connect_args": {
            "options": "-c client_encoding=utf8"
        }
    }
    logger.info("Using PostgreSQL database configuration")

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

# Stripe configuration
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

# Initialize Stripe only if keys are available
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    logger.info("Stripe initialized successfully")
else:
    logger.warning("Stripe keys not found - payment functionality disabled")

# Cennik
PRICING = {
    'single_cv': {
        'price': 1900,  # 19 zł w groszach
        'currency': 'PLN',
        'name': 'Jednorazowa optymalizacja CV',
        'description': 'Optymalizacja jednego CV bez dodatkowych funkcji'
    },
    'monthly_package': {
        'price': 4900,  # 49 zł w groszach  
        'currency': 'PLN',
        'name': 'Pełny pakiet miesięczny',
        'description': 'CV + list motywacyjny + pytania + analiza luk kompetencyjnych'
    }
}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize the app with the extension
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = 'Zaloguj się, aby uzyskać dostęp do tej strony.'
login_manager.login_message_category = 'info'
login_manager.login_view = 'auth.login'  # type: ignore


# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    premium_until = db.Column(db.DateTime)
    stripe_customer_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)

    # Relacje dla statystyk
    cv_uploads = db.relationship('CVUpload', backref='user', lazy=True)

    def is_premium_active(self):
        if self.is_developer():
            return True
        
        # Sprawdź aktywną subskrypcję
        active_subscription = Subscription.query.filter_by(
            user_id=self.id, 
            status='active'
        ).first()
        
        if active_subscription and active_subscription.is_active():
            return True
            
        return self.premium_until and datetime.utcnow() < self.premium_until

    def can_optimize_cv(self):
        """Sprawdza czy użytkownik może optymalizować CV"""
        if self.is_developer():
            return True
            
        # Sprawdź aktywną subskrypcję (pełny pakiet)
        if self.is_premium_active():
            return True
            
        # Sprawdź jednorazowe płatności
        single_payment = SinglePayment.query.filter_by(user_id=self.id).filter(
            SinglePayment.cv_optimizations_used < SinglePayment.cv_optimizations_limit
        ).first()
        
        return single_payment is not None

    def can_use_full_features(self):
        """Sprawdza czy użytkownik ma dostęp do pełnych funkcji (list motywacyjny, pytania, analiza)"""
        if self.is_developer():
            return True
            
        # Tylko subskrybenci mają dostęp do pełnych funkcji
        return self.is_premium_active()

    def use_cv_optimization(self):
        """Używa jedną optymalizację CV z jednorazowej płatności"""
        single_payment = SinglePayment.query.filter_by(user_id=self.id).filter(
            SinglePayment.cv_optimizations_used < SinglePayment.cv_optimizations_limit
        ).first()
        
        if single_payment:
            return single_payment.use_optimization()
        return False

    def get_payment_status(self):
        """Zwraca status płatności użytkownika"""
        if self.is_developer():
            return {'type': 'developer', 'status': 'active'}
            
        # Sprawdź subskrypcję
        subscription = Subscription.query.filter_by(
            user_id=self.id, 
            status='active'
        ).first()
        
        if subscription and subscription.is_active():
            return {
                'type': 'subscription',
                'status': 'active',
                'expires': subscription.current_period_end,
                'plan': subscription.plan_type
            }
            
        # Sprawdź jednorazowe płatności
        single_payment = SinglePayment.query.filter_by(user_id=self.id).filter(
            SinglePayment.cv_optimizations_used < SinglePayment.cv_optimizations_limit
        ).first()
        
        if single_payment:
            return {
                'type': 'single',
                'status': 'active',
                'optimizations_left': single_payment.cv_optimizations_limit - single_payment.cv_optimizations_used
            }
            
        return {'type': 'free', 'status': 'inactive'}

    def is_developer(self):
        return self.username == 'developer'

    def get_cv_count(self):
        """Zwraca liczbę przesłanych CV"""
        return CVUpload.query.filter_by(user_id=self.id).count()

    def get_optimized_cv_count(self):
        """Zwraca liczbę zoptymalizowanych CV"""
        return CVUpload.query.filter_by(user_id=self.id).filter(
            CVUpload.optimized_cv.isnot(None)).count()

    def get_analyzed_cv_count(self):
        """Zwraca liczbę przeanalizowanych CV"""
        return CVUpload.query.filter_by(user_id=self.id).filter(
            CVUpload.cv_analysis.isnot(None)).count()

    def get_success_rate(self):
        """Oblicza wskaźnik sukcesu optymalizacji"""
        total = self.get_cv_count()
        if total == 0:
            return 0
        optimized = self.get_optimized_cv_count()
        return round((optimized / total) * 100, 1)

    def get_account_age_days(self):
        """Zwraca wiek konta w dniach"""
        return (datetime.utcnow() - self.created_at).days

    def get_recent_activity(self, days=30):
        """Zwraca aktywność z ostatnich dni"""
        from sqlalchemy import func
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return CVUpload.query.filter(CVUpload.user_id == self.id,
                                     CVUpload.created_at
                                     >= cutoff_date).count()

    def get_statistics(self):
        """Zwraca statystyki użytkownika"""
        stats = UserStatistics.query.filter_by(user_id=self.id).first()
        if not stats:
            stats = UserStatistics()
            stats.user_id = self.id
            db.session.add(stats)
            db.session.commit()
        return stats

    def __repr__(self):
        return f'<User {self.username}>'


class CVUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=True)
    optimized_cv = db.Column(db.Text, nullable=True)
    cv_analysis = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    optimized_at = db.Column(db.DateTime, nullable=True)
    analyzed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<CVUpload {self.filename}>'


class UserStatistics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_logins = db.Column(db.Integer, default=0)
    total_time_spent = db.Column(db.Integer, default=0)  # w minutach
    preferred_job_categories = db.Column(db.Text)  # JSON string
    avg_optimization_time = db.Column(db.Float, default=0.0)  # w minutach
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,
                           default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<UserStatistics User:{self.user_id}>'


class CoverLetter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cv_upload_id = db.Column(db.Integer,
                             db.ForeignKey('cv_upload.id'),
                             nullable=False)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=True)
    company_name = db.Column(db.String(200), nullable=True)
    cover_letter_content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    generated_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<CoverLetter {self.job_title}>'


class InterviewQuestions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cv_upload_id = db.Column(db.Integer,
                             db.ForeignKey('cv_upload.id'),
                             nullable=False)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=True)
    questions_content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    generated_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<InterviewQuestions {self.job_title}>'


class SkillsGapAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cv_upload_id = db.Column(db.Integer,
                             db.ForeignKey('cv_upload.id'),
                             nullable=False)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=True)
    analysis_content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    analyzed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<SkillsGapAnalysis {self.job_title}>'


class StripePayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stripe_payment_intent_id = db.Column(db.String(200), unique=True, nullable=False)
    stripe_session_id = db.Column(db.String(200), unique=True, nullable=True)
    amount = db.Column(db.Integer, nullable=False)  # kwota w groszach
    currency = db.Column(db.String(3), default='PLN')
    payment_type = db.Column(db.String(50), nullable=False)  # 'single_cv' lub 'monthly_package'
    status = db.Column(db.String(50), default='pending')  # pending, completed, failed, refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relacja do użytkownika
    user = db.relationship('User', backref=db.backref('payments', lazy=True))

    def __repr__(self):
        return f'<StripePayment {self.payment_type}: {self.amount/100} {self.currency}>'


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stripe_subscription_id = db.Column(db.String(200), unique=True, nullable=False)
    stripe_customer_id = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # active, canceled, past_due, etc.
    plan_type = db.Column(db.String(50), default='monthly_package')
    amount = db.Column(db.Integer, nullable=False)  # 4900 (49 zł)
    currency = db.Column(db.String(3), default='PLN')
    current_period_start = db.Column(db.DateTime, nullable=False)
    current_period_end = db.Column(db.DateTime, nullable=False)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacja do użytkownika
    user = db.relationship('User', backref=db.backref('subscriptions', lazy=True))

    def is_active(self):
        return (self.status == 'active' and 
                datetime.utcnow() < self.current_period_end)

    def __repr__(self):
        return f'<Subscription {self.plan_type}: {self.status}>'


class SinglePayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('stripe_payment.id'), nullable=False)
    cv_optimizations_used = db.Column(db.Integer, default=0)
    cv_optimizations_limit = db.Column(db.Integer, default=1)  # 1 optymalizacja za 19 zł
    expires_at = db.Column(db.DateTime, nullable=True)  # Brak wygaśnięcia dla jednorazowej
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacje
    user = db.relationship('User', backref=db.backref('single_payments', lazy=True))
    payment = db.relationship('StripePayment', backref=db.backref('single_payment', uselist=False))

    def can_optimize_cv(self):
        return self.cv_optimizations_used < self.cv_optimizations_limit

    def use_optimization(self):
        if self.can_optimize_cv():
            self.cv_optimizations_used += 1
            db.session.commit()
            return True
        return False

    def __repr__(self):
        return f'<SinglePayment {self.cv_optimizations_used}/{self.cv_optimizations_limit}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Add global template functions
@app.template_global()
def now():
    return datetime.utcnow()

@app.template_global()
def generate_cv_html(cv_text):
    """Generate formatted HTML CV for templates"""
    try:
        from utils.cv_template_processor import generate_cv_html as process_cv_html
        return process_cv_html(cv_text)
    except Exception as e:
        logger.error(f"Error generating CV HTML in template: {str(e)}")
        return None


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/profile')
@login_required
def profile():
    """Strona profilu użytkownika z dodatkowymi statystykami"""
    user_stats = current_user.get_statistics()

    # Dodatkowe statystyki
    stats_data = {
        'cv_count': current_user.get_cv_count(),
        'optimized_count': current_user.get_optimized_cv_count(),
        'analyzed_count': current_user.get_analyzed_cv_count(),
        'success_rate': current_user.get_success_rate(),
        'account_age': current_user.get_account_age_days(),
        'recent_activity': current_user.get_recent_activity(),
        'last_login': current_user.last_login,
        'is_premium': current_user.is_premium_active(),
        'total_logins': user_stats.total_logins,
        'total_time_spent': user_stats.total_time_spent,
        'user_statistics': user_stats
    }

    # Ostatnie CV
    recent_cvs = CVUpload.query.filter_by(user_id=current_user.id).order_by(
        CVUpload.created_at.desc()).limit(5).all()

    return render_template('auth/profile.html',
                           stats=stats_data,
                           recent_cvs=recent_cvs)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Zostałeś wylogowany.', 'info')
    return redirect(url_for('index'))


@app.route('/upload-cv', methods=['POST'])
@login_required
def upload_cv():
    try:
        if 'cv_file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'Nie wybrano pliku CV'
            })

        file = request.files['cv_file']
        job_title = request.form.get('job_title', '').strip()
        job_description = request.form.get('job_description', '').strip()

        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'Nie wybrano pliku CV'
            })

        if not job_title:
            return jsonify({
                'success': False,
                'message': 'Nazwa stanowiska jest wymagana'
            })

        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)

            # Extract text from PDF
            from utils.pdf_extraction import extract_text_from_pdf
            cv_text = extract_text_from_pdf(file_path)

            if not cv_text:
                os.remove(file_path)
                return jsonify({
                    'success':
                    False,
                    'message':
                    'Nie udało się wyodrębnić tekstu z pliku PDF'
                })

            # Generate session ID
            session_id = str(uuid.uuid4())

            # Ensure UTF-8 encoding for all text fields
            def ensure_utf8(text):
                if text is None:
                    return None
                if isinstance(text, bytes):
                    return text.decode('utf-8', errors='replace')
                try:
                    # Test if string can be encoded to UTF-8
                    text.encode('utf-8')
                    return text
                except UnicodeEncodeError:
                    return text.encode('utf-8',
                                       errors='replace').decode('utf-8')

            # Store CV data in the database
            new_cv_upload = CVUpload()
            new_cv_upload.user_id = current_user.id
            new_cv_upload.session_id = session_id
            new_cv_upload.filename = ensure_utf8(filename)
            new_cv_upload.original_text = ensure_utf8(cv_text)
            new_cv_upload.job_title = ensure_utf8(job_title)
            new_cv_upload.job_description = ensure_utf8(job_description)
            db.session.add(new_cv_upload)
            db.session.commit()

            # Clean up uploaded file
            os.remove(file_path)

            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': 'CV zostało przesłane pomyślnie'
            })

        return jsonify({
            'success':
            False,
            'message':
            'Nieprawidłowy format pliku. Dozwolone tylko pliki PDF.'
        })

    except Exception as e:
        logger.error(f"Error in upload_cv: {str(e)}")
        return jsonify({
            'success':
            False,
            'message':
            f'Wystąpił błąd podczas przetwarzania pliku: {str(e)}'
        })


@app.route('/generate-cover-letter', methods=['POST'])
@login_required
def generate_cover_letter_route():
    """Generuje list motywacyjny na podstawie przesłanego CV"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        job_title = data.get('job_title', '').strip()
        job_description = data.get('job_description', '').strip()
        company_name = data.get('company_name', '').strip()

        if not session_id:
            return jsonify({'success': False, 'message': 'Brak ID sesji'})

        if not job_title:
            return jsonify({
                'success': False,
                'message': 'Nazwa stanowiska jest wymagana'
            })

        # Sprawdź czy użytkownik ma dostęp do pełnych funkcji
        if not current_user.can_use_full_features():
            return jsonify({
                'success': False,
                'message': 'List motywacyjny jest dostępny tylko w pełnym pakiecie miesięcznym za 49 zł/msc.',
                'redirect_to_pricing': True
            })

        # Pobierz CV z bazy danych
        cv_upload = CVUpload.query.filter_by(session_id=session_id,
                                             user_id=current_user.id).first()
        if not cv_upload:
            return jsonify({
                'success': False,
                'message': 'Nie znaleziono przesłanego CV'
            })

        # Sprawdź czy użytkownik ma dostęp premium
        is_premium = current_user.is_premium_active()

        # Generuj list motywacyjny
        from utils.openrouter_api import generate_cover_letter
        result = generate_cover_letter(cv_text=cv_upload.original_text,
                                       job_title=job_title,
                                       job_description=job_description,
                                       company_name=company_name,
                                       is_premium=is_premium)

        if not result or not result.get('success'):
            return jsonify({
                'success':
                False,
                'message':
                'Nie udało się wygenerować listu motywacyjnego'
            })

        # Zapisz list motywacyjny w bazie danych
        cover_letter_session_id = str(uuid.uuid4())
        new_cover_letter = CoverLetter()
        new_cover_letter.user_id = current_user.id
        new_cover_letter.cv_upload_id = cv_upload.id
        new_cover_letter.session_id = cover_letter_session_id
        new_cover_letter.job_title = job_title
        new_cover_letter.job_description = job_description
        new_cover_letter.company_name = company_name
        new_cover_letter.cover_letter_content = result['cover_letter']
        new_cover_letter.generated_at = datetime.utcnow()

        db.session.add(new_cover_letter)
        db.session.commit()

        return jsonify({
            'success':
            True,
            'cover_letter':
            result['cover_letter'],
            'cover_letter_session_id':
            cover_letter_session_id,
            'message':
            'List motywacyjny został wygenerowany pomyślnie'
        })

    except Exception as e:
        logger.error(f"Error in generate_cover_letter_route: {str(e)}")
        error_message = "Wystąpił błąd podczas generowania listu motywacyjnego"
        if any(keyword in str(e).lower() for keyword in ["timeout", "timed out", "worker timeout"]):
            error_message = "Zapytanie trwa zbyt długo - spróbuj ponownie. Jeśli problem się powtarza, skróć opis stanowiska."
        elif "connection" in str(e).lower():
            error_message = "Błąd połączenia z API - sprawdź połączenie internetowe"
        return jsonify({
            'success': False,
            'message': error_message
        })


@app.route('/generate-interview-questions', methods=['POST'])
@login_required
def generate_interview_questions_route():
    """Generuje pytania na rozmowę kwalifikacyjną na podstawie CV"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        job_title = data.get('job_title', '').strip()
        job_description = data.get('job_description', '').strip()

        if not session_id:
            return jsonify({'success': False, 'message': 'Brak ID sesji'})

        if not job_title:
            return jsonify({
                'success': False,
                'message': 'Nazwa stanowiska jest wymagana'
            })

        # Sprawdź czy użytkownik ma dostęp do pełnych funkcji
        if not current_user.can_use_full_features():
            return jsonify({
                'success': False,
                'message': 'Pytania na rozmowę są dostępne tylko w pełnym pakiecie miesięcznym za 49 zł/msc.',
                'redirect_to_pricing': True
            })

        # Pobierz CV z bazy danych
        cv_upload = CVUpload.query.filter_by(session_id=session_id,
                                             user_id=current_user.id).first()
        if not cv_upload:
            return jsonify({
                'success': False,
                'message': 'Nie znaleziono przesłanego CV'
            })

        # Sprawdź czy użytkownik ma dostęp premium
        is_premium = current_user.is_premium_active()

        # Generuj pytania na rozmowę
        from utils.openrouter_api import generate_interview_questions
        result = generate_interview_questions(cv_text=cv_upload.original_text,
                                            job_title=job_title,
                                            job_description=job_description,
                                            is_premium=is_premium)

        if not result or not result.get('success'):
            return jsonify({
                'success':
                False,
                'message':
                'Nie udało się wygenerować pytań na rozmowę'
            })

        # Zapisz pytania w bazie danych
        questions_session_id = str(uuid.uuid4())
        new_questions = InterviewQuestions()
        new_questions.user_id = current_user.id
        new_questions.cv_upload_id = cv_upload.id
        new_questions.session_id = questions_session_id
        new_questions.job_title = job_title
        new_questions.job_description = job_description
        new_questions.questions_content = result['questions']
        new_questions.generated_at = datetime.utcnow()

        db.session.add(new_questions)
        db.session.commit()

        return jsonify({
            'success': True,
            'questions': result['questions'],
            'questions_session_id': questions_session_id,
            'message': 'Pytania na rozmowę zostały wygenerowane pomyślnie'
        })

    except Exception as e:
        logger.error(f"Error in generate_interview_questions_route: {str(e)}")
        error_message = "Wystąpił błąd podczas generowania pytań na rozmowę"
        if any(keyword in str(e).lower() for keyword in ["timeout", "timed out", "worker timeout"]):
            error_message = "Zapytanie trwa zbyt długo - spróbuj ponownie. Jeśli problem się powtarza, skróć opis stanowiska."
        elif "connection" in str(e).lower():
            error_message = "Błąd połączenia z API - sprawdź połączenie internetowe"
        return jsonify({
            'success': False,
            'message': error_message
        })


@app.route('/analyze-skills-gap', methods=['POST'])
@login_required
def analyze_skills_gap_route():
    """Analizuje luki kompetencyjne między CV a wymaganiami stanowiska"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        job_title = data.get('job_title', '').strip()
        job_description = data.get('job_description', '').strip()

        if not session_id:
            return jsonify({'success': False, 'message': 'Brak ID sesji'})

        if not job_title:
            return jsonify({
                'success': False,
                'message': 'Nazwa stanowiska jest wymagana'
            })

        # Sprawdź czy użytkownik ma dostęp do pełnych funkcji
        if not current_user.can_use_full_features():
            return jsonify({
                'success': False,
                'message': 'Analiza luk kompetencyjnych jest dostępna tylko w pełnym pakiecie miesięcznym za 49 zł/msc.',
                'redirect_to_pricing': True
            })

        # Pobierz CV z bazy danych
        cv_upload = CVUpload.query.filter_by(session_id=session_id,
                                             user_id=current_user.id).first()
        if not cv_upload:
            return jsonify({
                'success': False,
                'message': 'Nie znaleziono przesłanego CV'
            })

        # Sprawdź czy użytkownik ma dostęp premium
        is_premium = current_user.is_premium_active()

        # Analizuj luki kompetencyjne
        from utils.openrouter_api import analyze_skills_gap
        result = analyze_skills_gap(cv_text=cv_upload.original_text,
                                  job_title=job_title,
                                  job_description=job_description,
                                  is_premium=is_premium)

        if not result or not result.get('success'):
            return jsonify({
                'success':
                False,
                'message':
                'Nie udało się przeanalizować luk kompetencyjnych'
            })

        # Zapisz analizę w bazie danych
        analysis_session_id = str(uuid.uuid4())
        new_analysis = SkillsGapAnalysis()
        new_analysis.user_id = current_user.id
        new_analysis.cv_upload_id = cv_upload.id
        new_analysis.session_id = analysis_session_id
        new_analysis.job_title = job_title
        new_analysis.job_description = job_description
        new_analysis.analysis_content = result['analysis']
        new_analysis.analyzed_at = datetime.utcnow()

        db.session.add(new_analysis)
        db.session.commit()

        return jsonify({
            'success': True,
            'analysis': result['analysis'],
            'analysis_session_id': analysis_session_id,
            'message': 'Analiza luk kompetencyjnych została ukończona pomyślnie'
        })

    except Exception as e:
        logger.error(f"Error in analyze_skills_gap_route: {str(e)}")
        error_message = "Wystąpił błąd podczas analizy luk kompetencyjnych"
        if any(keyword in str(e).lower() for keyword in ["timeout", "timed out", "worker timeout"]):
            error_message = "Zapytanie trwa zbyt długo - spróbuj ponownie. Jeśli problem się powtarza, skróć opis stanowiska."
        elif "connection" in str(e).lower():
            error_message = "Błąd połączenia z API - sprawdź połączenie internetowe"
        return jsonify({
            'success': False,
            'message': error_message
        })


@app.route('/optimize-cv', methods=['POST'])
@login_required
def optimize_cv_route():
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        cv_upload = CVUpload.query.filter_by(session_id=session_id,
                                             user_id=current_user.id).first()

        if not cv_upload:
            return jsonify({
                'success':
                False,
                'message':
                'Sesja wygasła. Proszę przesłać CV ponownie.'
            })

        # Sprawdź czy użytkownik może optymalizować CV
        if not current_user.can_optimize_cv():
            payment_status = current_user.get_payment_status()
            if payment_status['type'] == 'free':
                return jsonify({
                    'success': False,
                    'message': 'Aby optymalizować CV, musisz wykupić jednorazową optymalizację (19 zł) lub pełny pakiet (49 zł/msc).',
                    'redirect_to_pricing': True
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Wykorzystałeś już dostępne optymalizacje CV.'
                })

        cv_text = cv_upload.original_text
        job_title = cv_upload.job_title
        job_description = cv_upload.job_description

        # Check if user has premium access
        is_premium = current_user.is_premium_active()

        # Call OpenRouter API to optimize CV
        from utils.openrouter_api import optimize_cv
        optimized_cv = optimize_cv(cv_text,
                                   job_title,
                                   job_description,
                                   is_premium=is_premium)

        if not optimized_cv:
            return jsonify({
                'success':
                False,
                'message':
                'Nie udało się zoptymalizować CV. Spróbuj ponownie.'
            })

        # Użyj optymalizacji (dla jednorazowych płatności)
        if not current_user.is_premium_active():
            current_user.use_cv_optimization()

        # Store optimized CV in the database
        cv_upload.optimized_cv = optimized_cv
        cv_upload.optimized_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'optimized_cv': optimized_cv,
            'message': 'CV zostało pomyślnie zoptymalizowane'
        })

    except Exception as e:
        logger.error(f"Error in optimize_cv_route: {str(e)}")
        error_message = "Wystąpił błąd podczas optymalizacji CV"
        if any(keyword in str(e).lower() for keyword in ["timeout", "timed out", "worker timeout"]):
            error_message = "Zapytanie trwa zbyt długo - spróbuj ponownie. Jeśli problem się powtarza, skróć tekst CV."
        elif "connection" in str(e).lower():
            error_message = "Błąd połączenia z API - sprawdź połączenie internetowe"
        return jsonify({
            'success': False,
            'message': error_message
        })


@app.route('/analyze-cv', methods=['POST'])
@login_required
def analyze_cv_route():
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        cv_upload = CVUpload.query.filter_by(session_id=session_id,
                                             user_id=current_user.id).first()

        if not cv_upload:
            return jsonify({
                'success':
                False,
                'message':
                'Sesja wygasła. Proszę przesłać CV ponownie.'
            })

        cv_text = cv_upload.original_text
        job_title = cv_upload.job_title
        job_description = cv_upload.job_description

        # Check if user has premium access
        is_premium = current_user.is_premium_active()

        # Call OpenRouter API to analyze CV
        from utils.openrouter_api import analyze_cv_with_score
        cv_analysis = analyze_cv_with_score(cv_text,
                                            job_title,
                                            job_description,
                                            is_premium=is_premium)

        if not cv_analysis:
            return jsonify({
                'success':
                False,
                'message':
                'Nie udało się przeanalizować CV. Spróbuj ponownie.'
            })

        # Store analysis in the database
        cv_upload.cv_analysis = cv_analysis
        cv_upload.analyzed_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'cv_analysis': cv_analysis,
            'message': 'CV zostało pomyślnie przeanalizowane'
        })

    except Exception as e:
        logger.error(f"Error in analyze_cv_route: {str(e)}")
        error_message = "Wystąpił błąd podczas analizy CV"
        if any(keyword in str(e).lower() for keyword in ["timeout", "timed out", "worker timeout"]):
            error_message = "Zapytanie trwa zbyt długo - spróbuj ponownie. Jeśli problem się powtarza, skróć tekst CV."
        elif "connection" in str(e).lower():
            error_message = "Błąd połączenia z API - sprawdź połączenie internetowe"
        return jsonify({
            'success': False,
            'message': error_message
        })


@app.route('/result/<session_id>')
@login_required
def result(session_id):
    cv_upload = CVUpload.query.filter_by(session_id=session_id,
                                         user_id=current_user.id).first()

    if not cv_upload:
        flash('Sesja wygasła. Proszę przesłać CV ponownie.', 'error')
        return redirect(url_for('index'))

    # Pobierz powiązane listy motywacyjne
    cover_letters = CoverLetter.query.filter_by(
        cv_upload_id=cv_upload.id).all()

    # Pobierz powiązane pytania na rozmowę
    interview_questions = InterviewQuestions.query.filter_by(
        cv_upload_id=cv_upload.id).all()

    # Pobierz powiązane analizy luk kompetencyjnych
    skills_analyses = SkillsGapAnalysis.query.filter_by(
        cv_upload_id=cv_upload.id).all()

    return render_template('result.html',
                           cv_upload=cv_upload,
                           session_id=session_id,
                           cover_letters=cover_letters,
                           interview_questions=interview_questions,
                           skills_analyses=skills_analyses)


@app.route('/cover-letter/<session_id>')
@login_required
def view_cover_letter(session_id):
    """Wyświetl wygenerowany list motywacyjny"""
    cover_letter = CoverLetter.query.filter_by(
        session_id=session_id, user_id=current_user.id).first_or_404()
    cv_upload = CVUpload.query.get(cover_letter.cv_upload_id)
    return render_template('cover_letter.html',
                           cover_letter=cover_letter,
                           cv_upload=cv_upload)


@app.route('/interview-questions/<session_id>')
@login_required
def view_interview_questions(session_id):
    """Wyświetl wygenerowane pytania na rozmowę kwalifikacyjną"""
    questions = InterviewQuestions.query.filter_by(
        session_id=session_id, user_id=current_user.id).first_or_404()
    cv_upload = CVUpload.query.get(questions.cv_upload_id)
    return render_template('interview_questions.html',
                           questions=questions,
                           cv_upload=cv_upload)


@app.route('/skills-gap-analysis/<session_id>')
@login_required
def view_skills_gap_analysis(session_id):
    """Wyświetl analizę luk kompetencyjnych"""
    analysis = SkillsGapAnalysis.query.filter_by(
        session_id=session_id, user_id=current_user.id).first_or_404()
    cv_upload = CVUpload.query.get(analysis.cv_upload_id)
    return render_template('skills_gap_analysis.html',
                           analysis=analysis,
                           cv_upload=cv_upload)


@app.route('/view-cv/<session_id>')
@login_required
def view_cv(session_id):
    """Wyświetl zoptymalizowane CV w nowym oknie z formatowaniem"""
    cv_upload = CVUpload.query.filter_by(session_id=session_id,
                                         user_id=current_user.id).first_or_404()
    
    if not cv_upload.optimized_cv:
        flash('CV nie zostało jeszcze zoptymalizowane.', 'error')
        return redirect(url_for('result', session_id=session_id))
    
    return render_template('view_cv.html', cv_upload=cv_upload)


@app.route('/health')
def health():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}


@app.route('/contact')
def contact():
    """Strona kontakt"""
    return render_template('contact.html')


@app.route('/privacy-policy')
def privacy_policy():
    """Polityka prywatności"""
    return render_template('privacy_policy.html')


@app.route('/terms-of-service')
def terms_of_service():
    """Regulamin serwisu"""
    return render_template('terms_of_service.html')


@app.route('/about')
def about():
    """O nas"""
    return render_template('about.html')


@app.route('/pricing')
@login_required 
def pricing():
    """Strona z cennikiem"""
    user_payment_status = current_user.get_payment_status()
    return render_template('pricing.html', 
                         pricing=PRICING,
                         user_status=user_payment_status,
                         stripe_public_key=STRIPE_PUBLISHABLE_KEY)


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Tworzy sesję płatności Stripe"""
    try:
        # Sprawdź czy Stripe jest skonfigurowany
        if not STRIPE_SECRET_KEY:
            return jsonify({'error': 'System płatności nie jest dostępny'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Brak danych żądania'}), 400
            
        payment_type = data.get('payment_type')
        
        if payment_type not in PRICING:
            return jsonify({'error': 'Nieprawidłowy typ płatności'}), 400
            
        price_info = PRICING[payment_type]
        
        # Sprawdź czy użytkownik już ma aktywną subskrypcję
        if payment_type == 'monthly_package':
            existing_subscription = Subscription.query.filter_by(
                user_id=current_user.id,
                status='active'
            ).first()
            
            if existing_subscription and existing_subscription.is_active():
                return jsonify({'error': 'Masz już aktywną subskrypcję'}), 400
        
        # Utwórz lub pobierz Stripe customer
        try:
            if not current_user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=current_user.email,
                    name=f"{current_user.first_name} {current_user.last_name}",
                    metadata={'user_id': str(current_user.id)}
                )
                current_user.stripe_customer_id = customer.id
                db.session.commit()
        except Exception as stripe_error:
            logger.error(f"Error creating Stripe customer: {str(stripe_error)}")
            return jsonify({'error': 'Błąd tworzenia konta płatności'}), 500
        
        # Konfiguracja sesji checkout
        try:
            if payment_type == 'single_cv':
                # Jednorazowa płatność
                checkout_session = stripe.checkout.Session.create(
                    customer=current_user.stripe_customer_id,
                    payment_method_types=['card', 'blik', 'p24'],
                    line_items=[{
                        'price_data': {
                            'currency': price_info['currency'].lower(),
                            'product_data': {
                                'name': price_info['name'],
                                'description': price_info['description'],
                            },
                            'unit_amount': price_info['price'],
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                    cancel_url=url_for('pricing', _external=True),
                    metadata={
                        'user_id': str(current_user.id),
                        'payment_type': payment_type
                    }
                )
            else:
                # Subskrypcja miesięczna
                checkout_session = stripe.checkout.Session.create(
                    customer=current_user.stripe_customer_id,
                    payment_method_types=['card', 'blik', 'p24'],
                    line_items=[{
                        'price_data': {
                            'currency': price_info['currency'].lower(),
                            'product_data': {
                                'name': price_info['name'],
                                'description': price_info['description'],
                            },
                            'unit_amount': price_info['price'],
                            'recurring': {'interval': 'month'},
                        },
                        'quantity': 1,
                    }],
                    mode='subscription',
                    success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                    cancel_url=url_for('pricing', _external=True),
                    metadata={
                        'user_id': str(current_user.id),
                        'payment_type': payment_type
                    }
                )
            
            return jsonify({'checkout_url': checkout_session.url})
            
        except stripe.error.StripeError as stripe_error:
            logger.error(f"Stripe error creating checkout session: {str(stripe_error)}")
            return jsonify({'error': 'Błąd systemu płatności'}), 500
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return jsonify({'error': 'Wystąpił błąd podczas tworzenia sesji płatności'}), 500


@app.route('/payment-success')
@login_required
def payment_success():
    """Strona sukcesu płatności"""
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            # Pobierz sesję z Stripe
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            
            if checkout_session.payment_status == 'paid':
                payment_type = checkout_session.metadata.get('payment_type')
                
                # Zapisz płatność w bazie danych
                if payment_type == 'single_cv':
                    process_single_payment(checkout_session)
                elif payment_type == 'monthly_package':
                    process_subscription_payment(checkout_session)
                
                flash('Płatność została zrealizowana pomyślnie!', 'success')
            else:
                flash('Wystąpił problem z płatnością.', 'error')
                
        except Exception as e:
            logger.error(f"Error processing payment success: {str(e)}")
            flash('Wystąpił błąd podczas przetwarzania płatności.', 'error')
    
    return render_template('payment_success.html')


@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Webhook do obsługi eventów Stripe"""
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("Stripe webhook secret not configured")
        return '', 400
        
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return '', 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        return '', 400

    try:
        # Obsługa eventów
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            handle_checkout_session_completed(session)
        
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            handle_subscription_payment_succeeded(invoice)
            
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            handle_subscription_deleted(subscription)
        
        logger.info(f"Processed webhook event: {event['type']}")
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return '', 500

    return '', 200


def process_single_payment(checkout_session):
    """Przetwarza jednorazową płatność"""
    try:
        user_id = int(checkout_session.metadata.get('user_id'))
        user = User.query.get(user_id)
        
        if not user:
            logger.error(f"User not found for payment: {user_id}")
            return
        
        # Zapisz płatność
        payment = StripePayment()
        payment.user_id = user_id
        payment.stripe_payment_intent_id = checkout_session.payment_intent
        payment.stripe_session_id = checkout_session.id
        payment.amount = checkout_session.amount_total
        payment.currency = checkout_session.currency.upper()
        payment.payment_type = 'single_cv'
        payment.status = 'completed'
        payment.completed_at = datetime.utcnow()
        
        db.session.add(payment)
        db.session.flush()
        
        # Utwórz rekord jednorazowej płatności
        single_payment = SinglePayment()
        single_payment.user_id = user_id
        single_payment.payment_id = payment.id
        single_payment.cv_optimizations_used = 0
        single_payment.cv_optimizations_limit = 1
        
        db.session.add(single_payment)
        db.session.commit()
        
        logger.info(f"Single payment processed for user {user_id}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing single payment: {str(e)}")


def process_subscription_payment(checkout_session):
    """Przetwarza płatność subskrypcji"""
    try:
        user_id = int(checkout_session.metadata.get('user_id'))
        user = User.query.get(user_id)
        
        if not user:
            logger.error(f"User not found for subscription: {user_id}")
            return
        
        # Pobierz subskrypcję z Stripe
        stripe_subscription = stripe.Subscription.retrieve(checkout_session.subscription)
        
        # Zapisz płatność
        payment = StripePayment()
        payment.user_id = user_id
        payment.stripe_payment_intent_id = checkout_session.payment_intent
        payment.stripe_session_id = checkout_session.id
        payment.amount = checkout_session.amount_total
        payment.currency = checkout_session.currency.upper()
        payment.payment_type = 'monthly_package'
        payment.status = 'completed'
        payment.completed_at = datetime.utcnow()
        
        db.session.add(payment)
        
        # Zapisz subskrypcję
        subscription = Subscription()
        subscription.user_id = user_id
        subscription.stripe_subscription_id = stripe_subscription.id
        subscription.stripe_customer_id = stripe_subscription.customer
        subscription.status = stripe_subscription.status
        subscription.plan_type = 'monthly_package'
        subscription.amount = stripe_subscription.items.data[0].price.unit_amount
        subscription.currency = stripe_subscription.items.data[0].price.currency.upper()
        subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
        subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
        
        db.session.add(subscription)
        db.session.commit()
        
        logger.info(f"Subscription processed for user {user_id}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing subscription: {str(e)}")


def handle_checkout_session_completed(session):
    """Obsługuje zakończoną sesję checkout"""
    user_id = session['metadata'].get('user_id')
    payment_type = session['metadata'].get('payment_type')
    
    if user_id and payment_type:
        user = User.query.get(int(user_id))
        if user:
            if payment_type == 'single_cv':
                # Logika już obsłużona w process_single_payment
                pass
            elif payment_type == 'monthly_package':
                # Logika już obsłużona w process_subscription_payment
                pass


def handle_subscription_payment_succeeded(invoice):
    """Obsługuje udaną płatność subskrypcji"""
    subscription_id = invoice['subscription']
    subscription_obj = Subscription.query.filter_by(
        stripe_subscription_id=subscription_id
    ).first()
    
    if subscription_obj:
        # Aktualizuj daty subskrypcji
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        subscription_obj.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
        subscription_obj.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
        subscription_obj.status = stripe_subscription.status
        db.session.commit()


def handle_subscription_deleted(subscription):
    """Obsługuje usunięcie subskrypcji"""
    subscription_obj = Subscription.query.filter_by(
        stripe_subscription_id=subscription['id']
    ).first()
    
    if subscription_obj:
        subscription_obj.status = 'canceled'
        db.session.commit()


# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({
        'success': False,
        'message': 'Plik jest za duży. Maksymalny rozmiar to 16MB.'
    }), 413


@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'success': False,
        'message': 'Wystąpił błąd wewnętrzny serwera.'
    }), 500


# Create auth blueprint
from flask import Blueprint

auth = Blueprint('auth', __name__, url_prefix='/auth')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '').strip()

        if not username_or_email or not password:
            flash('Wypełnij wszystkie pola.', 'error')
            return render_template('auth/login.html')

        # Find user
        if '@' in username_or_email:
            user = User.query.filter_by(email=username_or_email).first()
        else:
            user = User.query.filter(
                or_(User.username == username_or_email,
                    User.email == username_or_email)).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            user.last_login = datetime.utcnow()

            # Aktualizuj statystyki logowania
            user_stats = user.get_statistics()
            user_stats.total_logins += 1
            user_stats.updated_at = datetime.utcnow()

            db.session.commit()

            flash(f'Witaj, {user.first_name}! Zalogowano pomyślnie.',
                  'success')

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(
                url_for('index'))
        else:
            flash('Nieprawidłowy nick/email lub hasło.', 'error')

    return render_template('auth/login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '').strip()
        password2 = request.form.get('password2', '').strip()

        # Validation
        if not all(
            [username, email, first_name, last_name, password, password2]):
            flash('Wszystkie pola są wymagane.', 'error')
            return render_template('auth/register.html')

        if password != password2:
            flash('Hasła muszą być identyczne.', 'error')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Hasło musi mieć co najnajmniej 6 znaków.', 'error')
            return render_template('auth/register.html')

        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Ten nick jest już zajęty.', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Ten email jest już zarejestrowany.', 'error')
            return render_template('auth/register.html')

        # Create user
        user = User()
        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.password_hash = generate_password_hash(password)

        db.session.add(user)
        db.session.commit()

        flash('Rejestracja przebiegła pomyślnie! Możesz się teraz zalogować.',
              'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


# Register blueprint
app.register_blueprint(auth)

# Create database tables with error handling
try:
    with app.app_context():
        db.create_all()
        logger.info("Database tables created successfully")

        # Create developer account if it doesn't exist
        developer = User.query.filter_by(username='developer').first()
        if not developer:
            developer = User()
            developer.username = 'developer'
            developer.email = 'developer@cvoptimizer.pro'
            developer.first_name = 'Developer'
            developer.last_name = 'Account'
            developer.password_hash = generate_password_hash('developer123')
            developer.active = True
            developer.created_at = datetime.utcnow()

            db.session.add(developer)
            db.session.commit()

            logger.info(
                "Created developer account - username: developer, password: developer123"
            )
        else:
            logger.info("Developer account already exists")

except Exception as e:
    logger.error(f"Database initialization failed: {str(e)}")
    logger.info("The app may still work for non-database operations")

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
