from app.models.user import User
from app.models.interview import Interview
from app.models.coding import CodingSubmission
from app.models.analytics import PerformanceReport
from app.schemas.analytics import AdminDashboardStats

class AdminService:
    @staticmethod
    async def get_dashboard_stats() -> AdminDashboardStats:
        total_users = await User.count()
        total_interviews = await Interview.count()
        total_coding = await CodingSubmission.count()
        
        # Calculate avg score
        reports = await PerformanceReport.find_all().to_list()
        avg_score = 0.0
        if reports:
            avg_score = sum(r.overall_score for r in reports) / len(reports)
            
        return AdminDashboardStats(
            total_users=total_users,
            total_interviews=total_interviews,
            total_coding_submissions=total_coding,
            average_interview_score=round(avg_score, 2)
        )
