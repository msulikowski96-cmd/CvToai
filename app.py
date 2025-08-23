import os
import logging
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import uuid
from datetime import datetime
from utils.pdf_extraction import extract_text_from_pdf
from utils.openrouter_api import optimize_cv, analyze_cv_with_score

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///cv_optimizer.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
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

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Set login view after initialization
login_manager.login_view = 'login'  # type: ignore

# Add global template functions
@app.template_global()
def now():
    return datetime.utcnow()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# CV sessions are stored in database using CVUpload model

@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('dashboard.html')
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    from forms import RegisterForm
    form = RegisterForm()
    
    if form.validate_on_submit():
        from models import User
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.password_hash = generate_password_hash(form.password.data or '')
        db.session.add(user)
        db.session.commit()
        
        flash('Rejestracja przebiegła pomyślnie! Możesz się teraz zalogować.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    from forms import LoginForm
    form = LoginForm()
    
    if form.validate_on_submit():
        from models import User
        from sqlalchemy import or_
        
        username_or_email = form.username_or_email.data
        
        # Sprawdź czy to email czy nick
        if username_or_email and '@' in username_or_email:
            # Jeśli zawiera @, traktuj jako email
            user = User.query.filter_by(email=username_or_email).first()
        else:
            # W przeciwnym przypadku, sprawdź nick lub email
            user = User.query.filter(
                or_(User.username == username_or_email, User.email == username_or_email)
            ).first()
        
        if user and check_password_hash(user.password_hash, form.password.data or ''):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Witaj, {user.first_name}! Zalogowano pomyślnie.', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Nieprawidłowy nick/email lub hasło.', 'error')
    
    return render_template('auth/login.html', form=form)

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
            cv_text = extract_text_from_pdf(file_path)
            
            if not cv_text:
                os.remove(file_path)  # Clean up
                return jsonify({'success': False, 'message': 'Nie udało się wyodrębnić tekstu z pliku PDF'})
            
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Store session data in database
            from models import CVUpload
            cv_upload = CVUpload(  # type: ignore
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
        logging.error(f"Error in upload_cv: {str(e)}")
        return jsonify({'success': False, 'message': f'Wystąpił błąd podczas przetwarzania pliku: {str(e)}'})

@app.route('/optimize-cv', methods=['POST'])
@login_required
def optimize_cv_route():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        from models import CVUpload
        cv_upload = CVUpload.query.filter_by(session_id=session_id).first()
        
        if not cv_upload:
            return jsonify({'success': False, 'message': 'Sesja wygasła. Proszę przesłać CV ponownie.'})
        
        cv_text = cv_upload.original_text
        job_title = cv_upload.job_title
        job_description = cv_upload.job_description
        
        # Check if user has premium access (includes developer account)
        is_premium = current_user.is_premium_active()
        
        # Call OpenRouter API to optimize CV with premium status
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
        logging.error(f"Error in optimize_cv_route: {str(e)}")
        return jsonify({'success': False, 'message': f'Wystąpił błąd podczas optymalizacji CV: {str(e)}'})

@app.route('/analyze-cv', methods=['POST'])
@login_required
def analyze_cv_route():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        from models import CVUpload
        cv_upload = CVUpload.query.filter_by(session_id=session_id).first()
        
        if not cv_upload:
            return jsonify({'success': False, 'message': 'Sesja wygasła. Proszę przesłać CV ponownie.'})
        
        cv_text = cv_upload.original_text
        job_title = cv_upload.job_title
        job_description = cv_upload.job_description
        
        # Check if user has premium access (includes developer account)
        is_premium = current_user.is_premium_active()
        
        # Call OpenRouter API to analyze CV
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
        logging.error(f"Error in analyze_cv_route: {str(e)}")
        return jsonify({'success': False, 'message': f'Wystąpił błąd podczas analizy CV: {str(e)}'})

@app.route('/result/<session_id>')
@login_required
def result(session_id):
    from models import CVUpload
    cv_upload = CVUpload.query.filter_by(session_id=session_id).first()
    
    if not cv_upload:
        flash('Sesja wygasła. Proszę przesłać CV ponownie.', 'error')
        return redirect(url_for('index'))
    
    # Convert to dict format for template compatibility
    session_data = {
        'cv_text': cv_upload.original_text,
        'job_title': cv_upload.job_title,
        'job_description': cv_upload.job_description,
        'filename': cv_upload.filename,
        'optimized_cv': cv_upload.optimized_cv,
        'cv_analysis': cv_upload.cv_analysis,
        'created_at': cv_upload.created_at,
        'optimized_at': cv_upload.optimized_at,
        'analyzed_at': cv_upload.analyzed_at
    }
    
    return render_template('result.html', session_data=session_data, session_id=session_id)

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

if __name__ == '__main__':
    with app.app_context():
        import models
        db.create_all()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
