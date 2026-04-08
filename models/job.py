from extensions import db
from datetime import datetime

class JobListing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    employer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    employer = db.relationship('User', foreign_keys=[employer_id], backref=db.backref('jobs', lazy=True))

    def markClosed(self):
        self.status = 'closed'
        db.session.commit()
