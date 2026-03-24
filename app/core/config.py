import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input" / "excel_files"
STATEMENT_DIR = DATA_DIR / "input" / "statements"
OUTPUT_DIR = DATA_DIR / "output"

INPUT_DIR.mkdir(parents=True, exist_ok=True)
STATEMENT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./retake.db")
UNIVERSITY_RETAKES_URL = os.getenv("UNIVERSITY_RETAKES_URL", "").strip()