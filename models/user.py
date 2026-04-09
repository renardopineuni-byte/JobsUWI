from flask_login import UserMixin
from extensions import db

saved_jobs_table = db.Table('saved_jobs',
    db.Column('student_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('job_id', db.Integer, db.ForeignKey('job_listing.id'), primary_key=True)
)

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
    
    saved_jobs = db.relationship('JobListing', secondary=saved_jobs_table,
                                 backref=db.backref('saved_by_students', lazy='dynamic'))
