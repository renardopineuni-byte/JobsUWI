from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


# =============================================================================
# Models
# =============================================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
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

class JobListing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    employer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    employer = db.relationship('User', backref=db.backref('jobs', lazy=True))

class InterviewSlot(db.Model):
    """A time slot created by staff for mock interviews."""
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    staff = db.relationship('User', foreign_keys=[staff_id], backref=db.backref('slots', lazy=True))
    start_time = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    booked = db.Column(db.Boolean, default=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    student = db.relationship('User', foreign_keys=[student_id], backref=db.backref('bookings', lazy=True))

class ScheduleInterview(db.Model):
    """Confirmed interview — created only after a slot is successfully booked."""
    id = db.Column(db.Integer, primary_key=True)
    candidate_name = db.Column(db.String(150), nullable=False)
    interviewer_name = db.Column(db.String(150), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('interview_slot.id'), nullable=False)
    slot = db.relationship('InterviewSlot', backref=db.backref('interview', uselist=False))
    status = db.Column(db.String(50), default='scheduled')
    confirmation_code = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def generate_confirmation_code(self):
        base = f"{self.candidate_name}{self.interviewer_name}{self.date_time}{self.slot_id}"
        return f"CONF-{abs(hash(base)) % 100000:05d}"

    def __str__(self):
        return (f"Interview scheduled for {self.candidate_name} "
                f"with {self.interviewer_name} on "
                f"{self.date_time.strftime('%Y-%m-%d %H:%M')}")


# =============================================================================
# Service Objects
# =============================================================================

class JobFinder:
    @staticmethod
    def get_approved_jobs(limit=None):
        query = JobListing.query.filter_by(status='approved').order_by(JobListing.created_at.desc())
        if limit is not None:
            return query.limit(limit).all()
        return query.all()
        
    @staticmethod
    def get_employer_jobs(employer_id):
        return JobListing.query.filter_by(employer_id=employer_id).all()
        
    @staticmethod
    def get_pending_jobs():
        return JobListing.query.filter_by(status='pending').all()
        
    @staticmethod
    def submit_job(title, company, description, employer_id):
        new_job = JobListing(title=title, company=company, description=description, employer_id=employer_id)
        db.session.add(new_job)
        db.session.commit()
        return new_job

    @staticmethod
    def approve_job(job_id):
        job = JobListing.query.get_or_404(job_id)
        job.status = 'approved'
        db.session.commit()
        return job

    @staticmethod
    def reject_job(job_id):
        job = JobListing.query.get_or_404(job_id)
        job.status = 'rejected'
        db.session.commit()
        return job

class InterviewScheduler:
    @staticmethod
    def book_slot(student_user, slot_id):
        slot = InterviewSlot.query.get(slot_id)
        if not slot or slot.booked:
            return False, "That slot is no longer available.", None

        slot.booked = True
        slot.student_id = student_user.id

        interview = ScheduleInterview(
            candidate_name=student_user.username,
            interviewer_name=slot.staff.username,
            date_time=slot.start_time,
            slot_id=slot.id,
            status='scheduled',
            confirmation_code=''
        )
        db.session.add(interview)
        db.session.flush()
        interview.confirmation_code = interview.generate_confirmation_code()
        db.session.commit()
        return True, str(interview), interview
    
    @staticmethod
    def get_available_slots():
        return InterviewSlot.query.filter_by(booked=False).order_by(InterviewSlot.start_time).all()
        
    @staticmethod
    def get_student_bookings(username):
        return ScheduleInterview.query.filter_by(
            candidate_name=username, status='scheduled'
        ).order_by(ScheduleInterview.date_time).all()

    @staticmethod
    def add_slot(staff_id, start_time, duration):
        slot = InterviewSlot(staff_id=staff_id, start_time=start_time, duration_minutes=duration)
        db.session.add(slot)
        db.session.commit()
        return slot

    @staticmethod
    def cancel_interview(interview_id, username):
        interview = ScheduleInterview.query.get_or_404(interview_id)
        if interview.candidate_name != username:
            return False
        interview.status = 'cancelled'
        slot = InterviewSlot.query.get(interview.slot_id)
        if slot:
            slot.booked = False
            slot.student_id = None
        db.session.commit()
        return True

# =============================================================================
# User loader
# =============================================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =============================================================================
# Existing routes
# =============================================================================

@app.route('/')
def index():
    jobs = JobFinder.get_approved_jobs()
    return render_template('index.html', jobs=jobs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
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
            if role == 'employer':
                new_user = Employer(username=username, password=password)
            elif role == 'student':
                new_user = Student(username=username, password=password)
            elif role == 'employee':
                new_user = Employee(username=username, password=password)
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
        JobFinder.submit_job(title, company, description, current_user.id)
        flash('Job listing submitted and awaiting approval!')
        return redirect(url_for('dashboard'))
    return render_template('submit.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'employer':
        jobs = JobFinder.get_employer_jobs(current_user.id)
        return render_template('dashboard.html', jobs=jobs)
    elif current_user.role == 'employee':
        pending_jobs = JobFinder.get_pending_jobs()
        return render_template('admin.html', jobs=pending_jobs)
    elif current_user.role == 'student':
        my_bookings = InterviewScheduler.get_student_bookings(current_user.username)
        open_jobs = JobFinder.get_approved_jobs(limit=5)
        return render_template('student_dashboard.html', bookings=my_bookings, jobs=open_jobs)
    return redirect(url_for('index'))

@app.route('/approve/<int:job_id>')
@login_required
def approve_job(job_id):
    if current_user.role != 'employee':
        flash('Unauthorized.')
        return redirect(url_for('index'))
    job = JobFinder.approve_job(job_id)
    flash(f'Job {job.title} approved!')
    return redirect(url_for('dashboard'))

@app.route('/reject/<int:job_id>')
@login_required
def reject_job(job_id):
    if current_user.role != 'employee':
        flash('Unauthorized.')
        return redirect(url_for('index'))
    job = JobFinder.reject_job(job_id)
    flash(f'Job {job.title} rejected.')
    return redirect(url_for('dashboard'))


# =============================================================================
# Interview scheduling routes
# =============================================================================

@app.route('/interviews')
@login_required
def interviews():
    available_slots = InterviewScheduler.get_available_slots()
    my_bookings = InterviewScheduler.get_student_bookings(current_user.username)
    return render_template('interviews.html',
                           available_slots=available_slots,
                           my_bookings=my_bookings)

@app.route('/interviews/add_slot', methods=['GET', 'POST'])
@login_required
def add_slot():
    if current_user.role not in ('employer', 'employee'):
        flash('Only staff can add interview slots.')
        return redirect(url_for('interviews'))
    if request.method == 'POST':
        start_time_str = request.form.get('start_time')
        duration = int(request.form.get('duration', 30))
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            if start_time < datetime.now():
                flash('Cannot add a slot in the past.')
                return redirect(url_for('add_slot'))
            slot = InterviewScheduler.add_slot(current_user.id, start_time, duration)
            flash(f'Slot added: {start_time.strftime("%Y-%m-%d %H:%M")} ({duration} min)')
            return redirect(url_for('interviews'))
        except ValueError:
            flash('Invalid date/time.')
    return render_template('add_slot.html')

@app.route('/interviews/book/<int:slot_id>', methods=['POST'])
@login_required
def book_slot(slot_id):
    if current_user.role != 'student':
        flash('Only students can book interview slots.')
        return redirect(url_for('interviews'))
    success, message, interview = InterviewScheduler.book_slot(current_user, slot_id)
    if success:
        flash(f'Confirmed! {message} — Code: {interview.confirmation_code}')
    else:
        flash(message)
    return redirect(url_for('interviews'))

@app.route('/interviews/cancel/<int:interview_id>', methods=['POST'])
@login_required
def cancel_interview(interview_id):
    success = InterviewScheduler.cancel_interview(interview_id, current_user.username)
    if not success:
        flash('Unauthorized.')
    else:
        flash('Interview booking cancelled.')
    return redirect(url_for('interviews'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)