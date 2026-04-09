from extensions import db
from datetime import datetime

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_listing.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(50), default='Submitted', nullable=False)
    gpa_snapshot = db.Column(db.Float, nullable=True)
    preferred_hours_snapshot = db.Column(db.String(100), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'job_id', name='uq_student_job'),
    )

    student = db.relationship('User', foreign_keys=[student_id], backref=db.backref('applications', lazy=True))
    job = db.relationship('JobListing', foreign_keys=[job_id], backref=db.backref('applications', lazy=True))
    documents = db.relationship('ApplicationDocument', backref='application', lazy=True, cascade='all, delete-orphan')


class ApplicationDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
