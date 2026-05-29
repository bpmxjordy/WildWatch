import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Internal URL for server-side requests (container-to-container)
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
    # Public URL for browser-side JS requests
    BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:5000")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
