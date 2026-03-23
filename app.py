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
    role = db.Column(db.String(50), nullable=False)  # 'employer', 'employee', 'student'

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
# pickslots — core booking logic
# =============================================================================

def pickslots(student_user, slot_id):
    """
    Checks if the slot is available. If not, returns failure.
    If available, books it and creates a ScheduleInterview with confirmation.
    """
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
    jobs = JobListing.query.filter_by(status='approved').order_by(JobListing.created_at.desc()).all()
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
    elif current_user.role == 'student':
        my_bookings = ScheduleInterview.query.filter_by(
            candidate_name=current_user.username, status='scheduled'
        ).order_by(ScheduleInterview.date_time).all()
        open_jobs = JobListing.query.filter_by(status='approved').order_by(JobListing.created_at.desc()).limit(5).all()
        return render_template('student_dashboard.html', bookings=my_bookings, jobs=open_jobs)
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


# =============================================================================
# Interview scheduling routes
# =============================================================================

@app.route('/interviews')
@login_required
def interviews():
    available_slots = InterviewSlot.query.filter_by(booked=False).order_by(InterviewSlot.start_time).all()
    my_bookings = ScheduleInterview.query.filter_by(
        candidate_name=current_user.username, status='scheduled'
    ).order_by(ScheduleInterview.date_time).all()
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
            slot = InterviewSlot(staff_id=current_user.id, start_time=start_time, duration_minutes=duration)
            db.session.add(slot)
            db.session.commit()
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
    success, message, interview = pickslots(current_user, slot_id)
    if success:
        flash(f'Confirmed! {message} — Code: {interview.confirmation_code}')
    else:
        flash(message)
    return redirect(url_for('interviews'))

@app.route('/interviews/cancel/<int:interview_id>', methods=['POST'])
@login_required
def cancel_interview(interview_id):
    interview = ScheduleInterview.query.get_or_404(interview_id)
    if interview.candidate_name != current_user.username:
        flash('Unauthorized.')
        return redirect(url_for('interviews'))
    interview.status = 'cancelled'
    slot = InterviewSlot.query.get(interview.slot_id)
    if slot:
        slot.booked = False
        slot.student_id = None
    db.session.commit()
    flash('Interview booking cancelled.')
    return redirect(url_for('interviews'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)