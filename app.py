from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False) # 'employer', 'employee', 'student'

class JobListing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending') # 'pending', 'approved', 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    employer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    employer = db.relationship('User', backref=db.backref('jobs', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    jobs = JobListing.query.filter_by(status='approved').order_by(JobListing.created_at.desc()).all()
    return render_template('index.html', jobs=jobs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password: # Simple plain text for now, can hash later
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login failed. Check your username and password.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already exists.')
        else:
            new_user = User(username=username, password=password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created! You can now login.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit_job():
    if current_user.role != 'employer':
        flash('Only employers can submit jobs.')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        company = request.form.get('company')
        description = request.form.get('description')
        
        new_job = JobListing(title=title, company=company, description=description, employer_id=current_user.id)
        db.session.add(new_job)
        db.session.commit()
        flash('Job listing submitted and awaiting approval!')
        return redirect(url_for('dashboard'))
    
    return render_template('submit.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'employer':
        jobs = JobListing.query.filter_by(employer_id=current_user.id).all()
        return render_template('dashboard.html', jobs=jobs)
    elif current_user.role == 'employee':
        pending_jobs = JobListing.query.filter_by(status='pending').all()
        return render_template('admin.html', jobs=pending_jobs)
    return redirect(url_for('index'))

@app.route('/approve/<int:job_id>')
@login_required
def approve_job(job_id):
    if current_user.role != 'employee':
        flash('Unauthorized.')
        return redirect(url_for('index'))
    
    job = JobListing.query.get_or_404(job_id)
    job.status = 'approved'
    db.session.commit()
    flash(f'Job {job.title} approved!')
    return redirect(url_for('dashboard'))

@app.route('/reject/<int:job_id>')
@login_required
def reject_job(job_id):
    if current_user.role != 'employee':
        flash('Unauthorized.')
        return redirect(url_for('index'))
    
    job = JobListing.query.get_or_404(job_id)
    job.status = 'rejected'
    db.session.commit()
    flash(f'Job {job.title} rejected.')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
