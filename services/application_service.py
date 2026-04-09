import os
from extensions import db
from models.application import Application, ApplicationDocument
from models.job import JobListing
from models.user import Student
from werkzeug.utils import secure_filename
from flask import current_app

MAX_FILE_SIZE = 5 * 1024 * 1024      # 5MB per file
MAX_TOTAL_SIZE = 10 * 1024 * 1024    # 10MB total
ALLOWED_EXTENSIONS = {'pdf'}


class ApplicationService:

    @staticmethod
    def _allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @staticmethod
    def _validate_files(files):
        if not files:
            return False, 'At least one PDF document is required.'

        total_size = 0
        for f in files:
            if not f or not f.filename:
                continue
            if not ApplicationService._allowed_file(f.filename):
                return False, f'File "{f.filename}" is not a PDF. Only PDF files are accepted.'

            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(0)

            if size > MAX_FILE_SIZE:
                return False, f'File "{f.filename}" exceeds the 5MB limit.'
            total_size += size

        if total_size > MAX_TOTAL_SIZE:
            return False, 'Total file size exceeds the 10MB limit.'
        if total_size == 0:
            return False, 'At least one PDF document is required.'

        return True, None

    @staticmethod
    def hasApplied(student_id, job_id):
        return Application.query.filter_by(student_id=student_id, job_id=job_id).first() is not None

    @staticmethod
    def submitApplication(student_id, job_id, files):
        if ApplicationService.hasApplied(student_id, job_id):
            return None, 'You have already applied to this job.'

        job = JobListing.query.get(job_id)
        if not job or job.status != 'approved':
            return None, 'This job is not available for applications.'

        student = Student.query.get(student_id)
        if not student:
            return None, 'Student not found.'

        valid, error = ApplicationService._validate_files(files)
        if not valid:
            return None, error

        application = Application(
            student_id=student_id,
            job_id=job_id,
            gpa_snapshot=student.gpa,
            preferred_hours_snapshot=student.preferred_hours
        )
        db.session.add(application)
        db.session.flush()  # get application.id before saving files

        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(application.id))
        os.makedirs(upload_dir, exist_ok=True)

        for f in files:
            if not f or not f.filename:
                continue
            filename = secure_filename(f.filename)
            stored_path = os.path.join(upload_dir, filename)

            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(0)

            f.save(stored_path)

            doc = ApplicationDocument(
                application_id=application.id,
                filename=filename,
                stored_path=stored_path,
                file_size=size
            )
            db.session.add(doc)

        db.session.commit()
        return application, None

    @staticmethod
    def getStudentApplications(student_id):
        return Application.query.filter_by(student_id=student_id)\
            .order_by(Application.submitted_at.desc()).all()

    @staticmethod
    def getApplicationById(application_id):
        return Application.query.get(application_id)
