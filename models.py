from app import db
from datetime import datetime

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
