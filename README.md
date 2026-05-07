# NutriBin Backend

Backend service for the NutriBin project.

## Stack
- Python 3.11+
- FastAPI
- SQLite
- SQLAlchemy

## Run (local)
1. Create virtual env and install deps:
   - `python -m venv .venv`
   - `.venv\Scripts\Activate.ps1`
   - `pip install -r requirements.txt`
2. Start server:
   - `uvicorn app.main:app --reload`
3. Open docs:
   - `http://127.0.0.1:8000/docs`
