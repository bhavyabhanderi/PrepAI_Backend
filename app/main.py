from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.config import settings
from app.database.connection import init_db
import contextlib

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print("Starting up... Initializing Database.")
    await init_db()
    yield
    # Shutdown actions
    print("Shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],  # Specify origins when allow_credentials=True
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def root():
    return {"message": "Welcome to the AI Interview Preparation Platform API"}

from app.api.v1.auth import router as auth_router
from app.api.v1.profile import router as profile_router
from app.api.v1.resume import router as resume_router
from app.api.v1.interview import router as interview_router
from app.api.v1.voice import router as voice_router
from app.api.v1.coding import router as coding_router

from app.api.v1.analytics import router as analytics_router
from app.api.v1.admin import router as admin_router
from app.api.v1.rating import router as rating_router
from app.api.v1.syllabus import router as syllabus_router

app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(profile_router, prefix=f"{settings.API_V1_STR}/profile", tags=["profile"])
app.include_router(resume_router, prefix=f"{settings.API_V1_STR}/resume", tags=["resume"])
app.include_router(interview_router, prefix=f"{settings.API_V1_STR}/interview", tags=["interview"])
app.include_router(voice_router, prefix=f"{settings.API_V1_STR}/voice", tags=["voice"])
app.include_router(coding_router, prefix=f"{settings.API_V1_STR}/coding", tags=["coding"])
app.include_router(analytics_router, prefix=f"{settings.API_V1_STR}/analytics", tags=["analytics"])
app.include_router(admin_router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(rating_router, prefix=f"{settings.API_V1_STR}/rating", tags=["rating"])
app.include_router(syllabus_router, prefix=f"{settings.API_V1_STR}/syllabus", tags=["syllabus"])
