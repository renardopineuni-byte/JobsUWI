from models.application import Application
from models.job import JobListing
from models.user import User
from models.interview_slot import InterviewSlot
from datetime import datetime


class ReportService:

    @staticmethod
    def generateActivityReport(start_date, end_date):
        end_date = end_date.replace(hour=23, minute=59, second=59)

        jobs_in_period = JobListing.query.filter(
            JobListing.created_at >= start_date,
            JobListing.created_at <= end_date
        ).all()

        total_jobs    = len(jobs_in_period)
        jobs_pending  = sum(1 for j in jobs_in_period if j.status == 'pending')
        jobs_approved = sum(1 for j in jobs_in_period if j.status == 'approved')
        jobs_rejected = sum(1 for j in jobs_in_period if j.status == 'rejected')

        top_companies = {}
        for j in jobs_in_period:
            top_companies[j.company] = top_companies.get(j.company, 0) + 1
        top_companies = sorted(top_companies.items(), key=lambda x: x[1], reverse=True)[:5]

        applications = Application.query.filter(
            Application.submitted_at >= start_date,
            Application.submitted_at <= end_date
        ).all()

        total_applications = len(applications)

        app_status_counts = {}
        for app in applications:
            app_status_counts[app.status] = app_status_counts.get(app.status, 0) + 1

        total_approved_jobs = JobListing.query.filter_by(status='approved').count()
        app_to_job_ratio = round(total_applications / total_approved_jobs, 1) if total_approved_jobs > 0 else 0

        all_users          = User.query.all()
        total_registrations = len(all_users)
        students   = sum(1 for u in all_users if u.role == 'student')
        employers  = sum(1 for u in all_users if u.role == 'employer')
        employees  = sum(1 for u in all_users if u.role == 'employee')

        active_employer_ids = set(j.employer_id for j in JobListing.query.all())
        active_employers   = len(active_employer_ids)
        inactive_employers = employers - active_employers

        gpas    = [u.gpa for u in all_users if u.role == 'student' and u.gpa is not None]
        avg_gpa = round(sum(gpas) / len(gpas), 2) if gpas else None

        all_slots    = InterviewSlot.query.filter(
            InterviewSlot.start >= start_date,
            InterviewSlot.start <= end_date
        ).all()

        total_slots  = len(all_slots)
        booked_slots = sum(1 for s in all_slots if s.reserved)
        open_slots   = total_slots - booked_slots
        utilisation  = round(booked_slots / total_slots * 100) if total_slots > 0 else 0

        return {
            'start_date': start_date,
            'end_date': end_date,

            'total_jobs': total_jobs,
            'jobs_pending': jobs_pending,
            'jobs_approved': jobs_approved,
            'jobs_rejected': jobs_rejected,
            'top_companies': top_companies,

            'total_applications': total_applications,
            'app_status_counts': app_status_counts,
            'app_to_job_ratio': app_to_job_ratio,

            'total_registrations': total_registrations,
            'students': students,
            'employers': employers,
            'employees': employees,
            'active_employers': active_employers,
            'inactive_employers': inactive_employers,
            'avg_gpa': avg_gpa,

            'total_slots': total_slots,
            'booked_slots': booked_slots,
            'open_slots': open_slots,
            'utilisation': utilisation,

            'applications': applications,
        }