
import os
import sys
import logging
import uuid
from datetime import datetime

# Force UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from sqlalchemy import or_

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
database_url = os.environ.get("DATABASE_URL", "sqlite:///cv_optimizer.db")

# Add UTF-8 charset for SQLite
if database_url.startswith("sqlite"):
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url + "?charset=utf8mb4"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "connect_args": {"charset": "utf8mb4"} if not database_url.startswith("postgresql") else {}
}

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize the app with the extension
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = 'Zaloguj się, aby uzyskać dostęp do tej strony.'
login_manager.login_message_category = 'info'
login_manager.login_view = 'auth.login'

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
    
    def is_premium_active(self):
        if self.is_developer():
            return True
        return self.premium_until and datetime.utcnow() < self.premium_until
    
    def is_developer(self):
        return self.username == 'developer'
    
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Add global template functions
@app.template_global()
def now():
    return datetime.utcnow()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('dashboard.html')
    return render_template('index.html')



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
            return jsonify({'success': False, 'message': 'Nie wybrano pliku CV'})
        
        file = request.files['cv_file']
        job_title = request.form.get('job_title', '').strip()
        job_description = request.form.get('job_description', '').strip()
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nie wybrano pliku CV'})
        
        if not job_title:
            return jsonify({'success': False, 'message': 'Nazwa stanowiska jest wymagana'})
        
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            # Extract text from PDF
            from utils.pdf_extraction import extract_text_from_pdf
            cv_text = extract_text_from_pdf(file_path)
            
            if not cv_text:
                os.remove(file_path)
                return jsonify({'success': False, 'message': 'Nie udało się wyodrębnić tekstu z pliku PDF'})
            
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Store session data in database
            cv_upload = CVUpload(
                user_id=current_user.id,
                session_id=session_id,
                filename=filename,
                original_text=cv_text,
                job_title=job_title,
                job_description=job_description
            )
            db.session.add(cv_upload)
            db.session.commit()
            
            # Clean up uploaded file
            os.remove(file_path)
            
            return jsonify({
                'success': True, 
                'session_id': session_id,
                'message': 'CV zostało przesłane pomyślnie'
            })
        
        return jsonify({'success': False, 'message': 'Nieprawidłowy format pliku. Dozwolone tylko pliki PDF.'})
    
    except Exception as e:
        logger.error(f"Error in upload_cv: {str(e)}")
        return jsonify({'success': False, 'message': f'Wystąpił błąd podczas przetwarzania pliku: {str(e)}'})

@app.route('/optimize-cv', methods=['POST'])
@login_required
def optimize_cv_route():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        cv_upload = CVUpload.query.filter_by(session_id=session_id, user_id=current_user.id).first()
        
        if not cv_upload:
            return jsonify({'success': False, 'message': 'Sesja wygasła. Proszę przesłać CV ponownie.'})
        
        cv_text = cv_upload.original_text
        job_title = cv_upload.job_title
        job_description = cv_upload.job_description
        
        # Check if user has premium access
        is_premium = current_user.is_premium_active()
        
        # Call OpenRouter API to optimize CV
        from utils.openrouter_api import optimize_cv
        optimized_cv = optimize_cv(cv_text, job_title, job_description, is_premium=is_premium)
        
        if not optimized_cv:
            return jsonify({'success': False, 'message': 'Nie udało się zoptymalizować CV. Spróbuj ponownie.'})
        
        # Store optimized CV in database
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
        return jsonify({'success': False, 'message': f'Wystąpił błąd podczas optymalizacji CV: {str(e)}'})

@app.route('/analyze-cv', methods=['POST'])
@login_required
def analyze_cv_route():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        cv_upload = CVUpload.query.filter_by(session_id=session_id, user_id=current_user.id).first()
        
        if not cv_upload:
            return jsonify({'success': False, 'message': 'Sesja wygasła. Proszę przesłać CV ponownie.'})
        
        cv_text = cv_upload.original_text
        job_title = cv_upload.job_title
        job_description = cv_upload.job_description
        
        # Check if user has premium access
        is_premium = current_user.is_premium_active()
        
        # Call OpenRouter API to analyze CV
        from utils.openrouter_api import analyze_cv_with_score
        cv_analysis = analyze_cv_with_score(cv_text, job_title, job_description, is_premium=is_premium)
        
        if not cv_analysis:
            return jsonify({'success': False, 'message': 'Nie udało się przeanalizować CV. Spróbuj ponownie.'})
        
        # Store analysis in database
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
        return jsonify({'success': False, 'message': f'Wystąpił błąd podczas analizy CV: {str(e)}'})

@app.route('/result/<session_id>')
@login_required
def result(session_id):
    cv_upload = CVUpload.query.filter_by(session_id=session_id, user_id=current_user.id).first()
    
    if not cv_upload:
        flash('Sesja wygasła. Proszę przesłać CV ponownie.', 'error')
        return redirect(url_for('index'))
    
    return render_template('result.html', cv_upload=cv_upload, session_id=session_id)

@app.route('/health')
def health():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'message': 'Plik jest za duży. Maksymalny rozmiar to 16MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'success': False, 'message': 'Wystąpił błąd wewnętrzny serwera.'}), 500

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
                or_(User.username == username_or_email, User.email == username_or_email)
            ).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Witaj, {user.first_name}! Zalogowano pomyślnie.', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
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
        if not all([username, email, first_name, last_name, password, password2]):
            flash('Wszystkie pola są wymagane.', 'error')
            return render_template('auth/register.html')
        
        if password != password2:
            flash('Hasła muszą być identyczne.', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Hasło musi mieć co najmniej 6 znaków.', 'error')
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
        
        flash('Rejestracja przebiegła pomyślnie! Możesz się teraz zalogować.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

# Register blueprint
app.register_blueprint(auth)

# Create database tables
with app.app_context():
    db.create_all()
    
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
        
        logger.info("Created developer account - username: developer, password: developer123")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
