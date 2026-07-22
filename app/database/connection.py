from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config.config import settings
import certifi

# Workaround for Beanie + Motor compatibility issue:
# MotorDatabase defines __call__ (which raises TypeError), but because it exists,
# Beanie thinks client.append_metadata is a callable database object rather than a missing method.
# We explicitly patch append_metadata on AsyncIOMotorClient to delegate to the underlying pymongo client.
if not hasattr(AsyncIOMotorClient, "append_metadata"):
    def append_metadata(self, *args, **kwargs):
        if hasattr(self.delegate, "append_metadata"):
            return self.delegate.append_metadata(*args, **kwargs)
    AsyncIOMotorClient.append_metadata = append_metadata

async def init_db():
    """
    Initialize MongoDB connection and Beanie ODM.
    """
    # Create Motor client with certifi to resolve SSL handshake issues
    client = AsyncIOMotorClient(settings.MONGODB_URL, tlsCAFile=certifi.where())
    
    # Get database instance
    db = client[settings.MONGO_DATABASE]
    
    # Initialize Beanie with all models
    # We will import and add our models to the document_models list later.
    await init_beanie(
        database=db,
        document_models=[
            "app.models.user.User",
            "app.models.user.Profile",
            "app.models.user.Admin",
            "app.models.resume.Resume",
            "app.models.resume.ResumeAnalysis",
            "app.models.interview.Interview",
            "app.models.interview.Question",
            "app.models.interview.Answer",
            "app.models.coding.CodingSubmission",
            "app.models.coding.CodingProblem",
            "app.models.analytics.PerformanceReport",
            "app.models.analytics.LearningPlan",
            "app.models.analytics.UserProgress",
            "app.models.rating.Rating",
            "app.models.syllabus.SavedSyllabus",
        ]
    )
    
    # Seed coding problems if collection is empty
    from app.models.coding import CodingProblem
    try:
        problems_count = await CodingProblem.count()
        if problems_count == 0:
            default_problem = CodingProblem(
                title="Two Sum",
                difficulty="Easy",
                description="Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.\n\nYou may assume that each input would have exactly one solution, and you may not use the same element twice.",
                examples=[
                    {
                        "input": "nums = [2,7,11,15], target = 9",
                        "output": "[0,1]",
                        "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1]."
                    },
                    {
                        "input": "nums = [3,2,4], target = 6",
                        "output": "[1,2]",
                        "explanation": ""
                    }
                ],
                constraints=[
                    "2 <= nums.length <= 10^4",
                    "-10^9 <= nums[i] <= 10^9",
                    "Only one valid answer exists."
                ],
                initial_templates={
                    "javascript": "// Write your solution here\nfunction solution(nums, target) {\n  \n}",
                    "python": "# Write your solution here\ndef solution(nums, target):\n    pass",
                    "java": "// Write your solution here\nclass Solution {\n    public int[] solve(int[] nums, int target) {\n        return new int[]{};\n    }\n}",
                    "cpp": "// Write your solution here\n#include <vector>\nusing namespace std;\n\nvector<int> solution(vector<int>& nums, int target) {\n    return {};\n}"
                },
                test_cases=[
                    {"input": "nums = [2,7,11,15], target = 9", "expected_output": "[0,1]"},
                    {"input": "nums = [3,2,4], target = 6", "expected_output": "[1,2]"}
                ]
            )
            await default_problem.insert()
            print("Successfully seeded default coding problem.")
    except Exception as e:
        print(f"Error seeding coding problems: {e}")
        
    return client
