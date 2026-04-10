from flask import url_for
from models.job import JobListing
from extensions import db

class JobSearchEngine:
    """Handles all job search operations with filters and sort"""

    ITEMS_PER_PAGE = 5

    @staticmethod
    def get_available_companies():
        """Return sorted list of distinct companies with approved jobs."""
        companies = db.session.query(JobListing.company)\
            .filter(JobListing.status == 'approved')\
            .distinct().order_by(JobListing.company).all()
        return [c[0] for c in companies]

    @staticmethod
    def search(keyword=None, company=None, sort_by='newest', page=1):
        """
        Perform a search on approved jobs.
        """
        query = JobListing.query.filter(JobListing.status == 'approved')

        # Keyword filter (role, company, description)
        if keyword:
            search_term = f"%{keyword}%"
            query = query.filter(
                db.or_(
                    JobListing.role.ilike(search_term),
                    JobListing.company.ilike(search_term),
                    JobListing.description.ilike(search_term)
                )
            )

        # Company filter
        if company and company != 'all':
            query = query.filter(JobListing.company == company)

        # Sorting
        if sort_by == 'newest':
            query = query.order_by(JobListing.created_at.desc())
        elif sort_by == 'oldest':
            query = query.order_by(JobListing.created_at.asc())
        elif sort_by == 'company_asc':
            query = query.order_by(JobListing.company.asc())
        elif sort_by == 'company_desc':
            query = query.order_by(JobListing.company.desc())
        else:
            query = query.order_by(JobListing.created_at.desc())

        # Pages
        paginated = query.paginate(page=page, per_page=JobSearchEngine.ITEMS_PER_PAGE, error_out=False)
        return paginated

    @staticmethod
    def build_pagination_urls(request_args, page):
        """Helper to generate page links with current filters."""
        args = request_args.copy()
        args['page'] = page
        return url_for('presenter_bp.searchJobs', **args)
