from extensions import db
from models.job import JobListing
from models.user import User, Student

class JobManager:
    @staticmethod
    def getApprovedJobs(limit=None):
        query = JobListing.query.filter_by(status='approved').order_by(JobListing.created_at.desc())
        if limit is not None:
            return query.limit(limit).all()
        return query.all()

    @staticmethod
    def getPendingJobs():
        return JobListing.query.filter_by(status='pending').all()

    @staticmethod
    def getEmployerJobs(employer_id):
        return JobListing.query.filter_by(employer_id=employer_id).all()

    @staticmethod
    def submitJob(role, company, description, employer_id):
        new_job = JobListing(role=role, company=company, description=description, employer_id=employer_id)
        db.session.add(new_job)
        db.session.commit()
        return new_job

    @staticmethod
    def approveJob(job_id):
        job = JobListing.query.get_or_404(job_id)
        job.status = 'approved'
        db.session.commit()
        return job

    @staticmethod
    def rejectJob(job_id):
        job = JobListing.query.get_or_404(job_id)
        job.status = 'rejected'
        db.session.commit()
        return job

    @staticmethod
    def searchJobs(keyword):
        if not keyword:
            return []
        search = f"%{keyword}%"
        return JobListing.query.filter(
            JobListing.status == 'approved',
            (JobListing.role.ilike(search) | 
             JobListing.company.ilike(search) | 
             JobListing.description.ilike(search))
        ).all()

    @staticmethod
    def saveJob(student_id, job_id):
        student = Student.query.get(student_id)
        job = JobListing.query.get(job_id)
        if student and job and job not in student.saved_jobs:
            student.saved_jobs.append(job)
            db.session.commit()
            return True
        return False
