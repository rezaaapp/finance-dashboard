from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

    if not GOOGLE_SHEET_ID:
        raise ValueError("GOOGLE_SHEET_ID belum diset di .env")

settings = Settings()