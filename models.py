from app import db
from datetime import datetime
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    premium_until = db.Column(db.DateTime)
    stripe_customer_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def is_premium_active(self):
        return self.premium_until and datetime.utcnow() < self.premium_until
    
    def is_developer(self):
        return self.username == 'developer'
    
    def __repr__(self):
        return f'<User {self.username}>'

class CVUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text)
    optimized_cv = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    optimized_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<CVUpload {self.filename}>'

class AnalysisResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cv_upload_id = db.Column(db.Integer, db.ForeignKey('cv_upload.id'), nullable=False)
    analysis_type = db.Column(db.String(50), nullable=False)
    result_data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AnalysisResult {self.analysis_type}>'
