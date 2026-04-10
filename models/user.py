from flask_login import UserMixin
from extensions import db
from datetime import datetime

class SavedJob(db.Model):
    __tablename__ = 'saved_jobs'
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_listing.id'), primary_key=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    job = db.relationship('JobListing', foreign_keys=[job_id])

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(50), nullable=False)

    __mapper_args__ = {
        'polymorphic_on': role,
        'polymorphic_identity': 'user'
    }

class Employer(User):
    __mapper_args__ = {
        'polymorphic_identity': 'employer'
    }

class Employee(User):
    __mapper_args__ = {
        'polymorphic_identity': 'employee'
    }

class Student(User):
    __mapper_args__ = {
        'polymorphic_identity': 'student'
    }

    gpa = db.Column(db.Float, nullable=True)
    preferred_hours = db.Column(db.String(100), nullable=True)
    saved_jobs = db.relationship('SavedJob', backref='student', lazy=True)
