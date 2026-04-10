from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from services.job_manager import JobManager
from services.interview_scheduler import InterviewScheduler
from services.application_service import ApplicationService
from services.email_service import send_application_confirmation
from services.report_service import ReportService
from services.job_search_engine import JobSearchEngine
from extensions import db
from datetime import datetime

presenter_bp = Blueprint('presenter_bp', __name__)

@presenter_bp.route('/')
def loadJobListings():
    jobs = JobManager.getApprovedJobs()
    return render_template('index.html', jobs=jobs)

@presenter_bp.route('/job/<int:job_id>')
def job_detail(job_id):
    from models.job import JobListing
    job = JobListing.query.get_or_404(job_id)
    already_applied = False
    if current_user.is_authenticated and current_user.role == 'student':
        already_applied = ApplicationService.hasApplied(current_user.id, job_id)
    return render_template('job_detail.html', job=job, already_applied=already_applied)

@presenter_bp.route('/dashboard')
@login_required
def loadDashboard():
    if current_user.role == 'employer':
        jobs = JobManager.getEmployerJobs(current_user.id)
        return render_template('dashboard.html', jobs=jobs)
    elif current_user.role == 'employee':
        pending_jobs = JobManager.getPendingJobs()
        return render_template('admin.html', jobs=pending_jobs)
    elif current_user.role == 'student':
        # Now uses user_id
        my_bookings = InterviewScheduler.getStudentBookings(current_user.id)
        open_jobs = JobManager.getApprovedJobs(limit=5)
        return render_template('student_dashboard.html', bookings=my_bookings, jobs=open_jobs)
    return redirect(url_for('presenter_bp.loadJobListings'))

@presenter_bp.route('/interviews')
@login_required
def loadInterviewBoard():
    available_slots = InterviewScheduler.getAvailableSlots()
    if current_user.role == 'student':
        my_bookings = InterviewScheduler.getStudentBookings(current_user.id)
    else:
        my_bookings = InterviewScheduler.getStaffBookings(current_user.id)
    return render_template('interviews.html',
                           available_slots=available_slots,
                           my_bookings=my_bookings)

@presenter_bp.route('/submit', methods=['GET', 'POST'])
@login_required
def loadJobBoard():
    if current_user.role != 'employer':
        flash('Only employers can submit jobs.')
        return redirect(url_for('presenter_bp.loadJobListings'))
    if request.method == 'POST':
        role = request.form.get('title')
        company = request.form.get('company')
        description = request.form.get('description')
        JobManager.submitJob(role, company, description, current_user.id)
        flash('Job listing submitted and awaiting approval!')
        return redirect(url_for('presenter_bp.loadDashboard'))
    return render_template('submit.html')

@presenter_bp.route('/saved-jobs')
@login_required
def loadSavedJobs():
    if current_user.role != 'student':
        flash('Only students can view saved jobs.')
        return redirect(url_for('presenter_bp.loadDashboard'))
    saved_jobs = current_user.saved_jobs
    return render_template('saved_jobs.html', jobs=saved_jobs)

@presenter_bp.route('/search-jobs', methods=['GET'])
@login_required
def searchJobs():
    if current_user.role != 'student':
        flash('Only students can search jobs here.')
        return redirect(url_for('presenter_bp.loadDashboard'))

    # Get parameters
    keyword = request.args.get('keyword', '').strip()
    company = request.args.get('company', 'all')
    sort_by = request.args.get('sort', 'newest')
    page = request.args.get('page', 1, type=int)

    # Perform search using the engine
    paginated_jobs = JobSearchEngine.search(
        keyword=keyword if keyword else None,
        company=company,
        sort_by=sort_by,
        page=page
    )

    # Get distinct companies for the filter
    companies = JobSearchEngine.get_available_companies()

    return render_template(
        'search_jobs.html',
        jobs=paginated_jobs.items,
        pagination=paginated_jobs,
        keyword=keyword,
        selected_company=company,
        selected_sort=sort_by,
        companies=companies,
        # Helper for pagination URLs
        build_pagination_url=lambda p: JobSearchEngine.build_pagination_urls(request.args, p)
    )

@presenter_bp.route('/save-job/<int:job_id>', methods=['POST'])
@login_required
def saveJob(job_id):
    if current_user.role != 'student':
        flash('Unauthorized.')
        return redirect(url_for('presenter_bp.loadJobListings'))
    success = JobManager.saveJob(current_user.id, job_id)
    if success:
        flash('Job saved successfully!')
    else:
        flash('Job already saved or does not exist.')
    return redirect(request.referrer or url_for('presenter_bp.loadJobListings'))

# Job Actions
@presenter_bp.route('/approve/<int:job_id>')
@login_required
def approve_job(job_id):
    if current_user.role != 'employee':
        flash('Unauthorized.')
        return redirect(url_for('presenter_bp.loadJobListings'))
    job = JobManager.approveJob(job_id)
    flash(f'Job {job.role} approved!')
    return redirect(url_for('presenter_bp.loadDashboard'))

@presenter_bp.route('/reject/<int:job_id>')
@login_required
def reject_job(job_id):
    if current_user.role != 'employee':
        flash('Unauthorized.')
        return redirect(url_for('presenter_bp.loadJobListings'))
    job = JobManager.rejectJob(job_id)
    flash(f'Job {job.role} rejected.')
    return redirect(url_for('presenter_bp.loadDashboard'))

# Interview Actions
@presenter_bp.route('/interviews/add_slot', methods=['GET', 'POST'])
@login_required
def add_slot():
    if current_user.role not in ('employer', 'employee'):
        flash('Only staff can add interview slots.')
        return redirect(url_for('presenter_bp.loadInterviewBoard'))
    if request.method == 'POST':
        start_time_str = request.form.get('start_time')
        duration = int(request.form.get('duration', 30))
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            if start_time < datetime.now():
                flash('Cannot add a slot in the past.')
                return redirect(url_for('presenter_bp.add_slot'))
            slot = InterviewScheduler.addSlot(current_user.id, start_time, duration)
            flash(f'Slot added: {start_time.strftime("%Y-%m-%d %H:%M")} ({duration} min)')
            return redirect(url_for('presenter_bp.loadInterviewBoard'))
        except ValueError:
            flash('Invalid date/time.')
    return render_template('add_slot.html')

@presenter_bp.route('/interviews/book/<int:slot_id>', methods=['POST'])
@login_required
def book_slot(slot_id):
    if current_user.role != 'student':
        flash('Only students can book interview slots.')
        return redirect(url_for('presenter_bp.loadInterviewBoard'))
    success, message, slot = InterviewScheduler.bookSlot(current_user, slot_id)
    if success:
        flash(f'Confirmed! {message} — Code: {slot.confirmationCode}')
    else:
        flash(message)
    return redirect(url_for('presenter_bp.loadInterviewBoard'))

@presenter_bp.route('/interviews/cancel/<int:slot_id>', methods=['POST'])
@login_required
def cancel_interview(slot_id):
    success = InterviewScheduler.cancelInterview(slot_id, current_user.id)
    if not success:
        flash('Unauthorized.')
    else:
        flash('Interview booking cancelled.')
    return redirect(url_for('presenter_bp.loadInterviewBoard'))

# Application Routes
@presenter_bp.route('/apply/<int:job_id>', methods=['GET', 'POST'])
@login_required
def apply_job(job_id):
    if current_user.role != 'student':
        flash('Only students can apply to jobs.')
        return redirect(url_for('presenter_bp.loadJobListings'))

    from models.job import JobListing
    job = JobListing.query.get_or_404(job_id)

    if job.status != 'approved':
        flash('This job is not accepting applications.')
        return redirect(url_for('presenter_bp.loadJobListings'))

    if ApplicationService.hasApplied(current_user.id, job_id):
        flash('You have already applied to this job.')
        return redirect(url_for('presenter_bp.my_applications'))

    if request.method == 'POST':
        files = request.files.getlist('documents')
        application, error = ApplicationService.submitApplication(
            current_user.id, job_id, files
        )
        if error:
            flash(error)
            return render_template('apply.html', job=job)

        send_application_confirmation(
            current_user.email,
            application.id,
            job.role,
            job.company
        )
        flash(f'Application submitted successfully! Your Application ID is: {application.id}')
        return redirect(url_for('presenter_bp.my_applications'))

    return render_template('apply.html', job=job)

@presenter_bp.route('/my-applications')
@login_required
def my_applications():
    if current_user.role != 'student':
        flash('Only students can view applications.')
        return redirect(url_for('presenter_bp.loadDashboard'))
    applications = ApplicationService.getStudentApplications(current_user.id)
    return render_template('my_applications.html', applications=applications)

@presenter_bp.route('/reports', methods=['GET', 'POST'])
@login_required
def activity_report():
    if current_user.role != 'employee':
        flash('Only placement staff can generate reports.')
        return redirect(url_for('presenter_bp.loadDashboard'))

    report = None
    start_date = None
    end_date = None

    if request.method == 'POST':
        start_str = request.form.get('start_date')
        end_str = request.form.get('end_date')

        try:
            start_date = None
            end_date = None
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
                try:
                    start_date = datetime.strptime(start_str, fmt)
                    end_date = datetime.strptime(end_str, fmt)
                    break
                except (ValueError, TypeError):
                    continue
            if not start_date or not end_date:
                raise ValueError('Unrecognised date format')
            if start_date > end_date:
                flash('Start date must be before end date.')
            else:
                report = ReportService.generateActivityReport(start_date, end_date)
        except (ValueError, TypeError):
            flash('Invalid date format. Please use the date picker.')

    return render_template('reports.html',
                           report=report,
                           start_date=start_date,
                           end_date=end_date)


@presenter_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.role != 'student':
        flash('Profile editing is for students only.')
        return redirect(url_for('presenter_bp.loadDashboard'))
    if request.method == 'POST':
        gpa = request.form.get('gpa')
        preferred_hours = request.form.get('preferred_hours')
        if gpa:
            try:
                gpa_val = float(gpa)
                if 0 <= gpa_val <= 4.3:
                    current_user.gpa = gpa_val
                else:
                    flash('GPA must be between 0 and 4.3.')
                    return render_template('profile.html')
            except ValueError:
                flash('Invalid GPA value.')
                return render_template('profile.html')
        current_user.preferred_hours = preferred_hours
        db.session.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('presenter_bp.profile'))
    return render_template('profile.html')