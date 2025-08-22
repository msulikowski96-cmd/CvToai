import os
import logging
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import uuid
from datetime import datetime
from utils.pdf_extraction import extract_text_from_pdf
from utils.openrouter_api import optimize_cv

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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# In-memory storage for CV sessions (for MVP)
cv_sessions = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload-cv', methods=['POST'])
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
            
            # Store session data
            cv_sessions[session_id] = {
                'cv_text': cv_text,
                'job_title': job_title,
                'job_description': job_description,
                'filename': filename,
                'created_at': datetime.now()
            }
            
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
def optimize_cv_route():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id or session_id not in cv_sessions:
            return jsonify({'success': False, 'message': 'Sesja wygasła. Proszę przesłać CV ponownie.'})
        
        session_data = cv_sessions[session_id]
        cv_text = session_data['cv_text']
        job_title = session_data['job_title']
        job_description = session_data['job_description']
        
        # Call OpenRouter API to optimize CV
        optimized_cv = optimize_cv(cv_text, job_title, job_description)
        
        if not optimized_cv:
            return jsonify({'success': False, 'message': 'Nie udało się zoptymalizować CV. Spróbuj ponownie.'})
        
        # Store optimized CV in session
        cv_sessions[session_id]['optimized_cv'] = optimized_cv
        cv_sessions[session_id]['optimized_at'] = datetime.now()
        
        return jsonify({
            'success': True,
            'optimized_cv': optimized_cv,
            'message': 'CV zostało pomyślnie zoptymalizowane'
        })
    
    except Exception as e:
        logging.error(f"Error in optimize_cv_route: {str(e)}")
        return jsonify({'success': False, 'message': f'Wystąpił błąd podczas optymalizacji CV: {str(e)}'})

@app.route('/result/<session_id>')
def result(session_id):
    if session_id not in cv_sessions:
        flash('Sesja wygasła. Proszę przesłać CV ponownie.', 'error')
        return redirect(url_for('index'))
    
    session_data = cv_sessions[session_id]
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
