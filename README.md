# PrepAI - AI Interview Preparation Platform Backend

This is the backend for **PrepAI**, an AI-powered interview preparation platform. It is built using **FastAPI** and provides a scalable API for user management, resume processing, and AI-driven mock interviews.

## Features

- **Authentication**: User registration, login, and JWT-based authentication.
- **Profile Management**: User profile and settings.
- **Resume Processing**: Upload and parse resumes (PDF/DOCX).
- **AI Interviews**: AI-driven mock interview sessions using Groq.
- **Voice Interactions**: Text-to-Speech support using gTTS for realistic interview experiences.
- **Coding Assessments**: APIs for coding interview scenarios.
- **Analytics & Rating**: Track performance and provide interview ratings.

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: MongoDB (via `motor` and `beanie` ODM)
- **Authentication**: JWT (`python-jose`, `passlib`)
- **AI Integration**: [Groq](https://groq.com/)
- **Document Processing**: `PyPDF2`, `python-docx`
- **Voice**: `gTTS`
- **File Uploads**: `python-multipart`, `aiofiles`

## Prerequisites

- Python 3.9+
- MongoDB instance (Local or Atlas)
- Groq API Key

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/bhavyabhanderi/PrepAI_Backend.git
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Copy the example environment file and fill in your details (MongoDB URI, Groq API Key, JWT Secrets, etc.):
   ```bash
   cp .env.example .env
   ```

## Running the Application

To start the FastAPI development server, run:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

### API Documentation

FastAPI automatically generates interactive API documentation. Access it at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Project Structure

- `app/`: Main application code.
  - `api/v1/`: API route handlers (auth, profile, resume, interview, voice, coding, analytics, admin, rating).
  - `models/`: Database models (Beanie/MongoDB).
  - `schemas/`: Pydantic models for data validation.
  - `services/`: Core business logic and external service integrations.
  - `config/`: Application configuration and settings.
  - `database/`: Database connection setup.
- `uploads/`: Directory for storing temporary or uploaded files.
