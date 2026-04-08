from extensions import db
from datetime import datetime

class InterviewSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    interviewer = db.relationship('User', foreign_keys=[staff_id], backref=db.backref('staff_slots', lazy=True))
    
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    student = db.relationship('User', foreign_keys=[student_id], backref=db.backref('student_bookings', lazy=True))
    
    reserved = db.Column(db.Boolean, default=False)
    start = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, default=30)
    confirmationCode = db.Column(db.String(20), unique=True, nullable=True)
