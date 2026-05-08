"""
TKAG-RAG Application Configuration
Reads settings from environment variables (loaded from .env by python-dotenv).
"""

import os
from dotenv import load_dotenv

# Load .env file from the same directory as this file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


class Config:
    # ── Flask ────────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False

    # ── Database (PostgreSQL via Flask-SQLAlchemy) ────────────────────────────────
    # Support Render's DATABASE_URL or fallback to local settings
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        PG_HOST     = os.environ.get('PG_HOST',     'localhost')
        PG_PORT     = os.environ.get('PG_PORT',     '5432')
        PG_USER     = os.environ.get('PG_USER',     'postgres')
        PG_PASSWORD = os.environ.get('PG_PASSWORD', 'postgresql')
        PG_DB       = os.environ.get('PG_DB',       'tkrag')

        SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{PG_USER}:{PG_PASSWORD}"
            f"@{PG_HOST}:{PG_PORT}/{PG_DB}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }

    # ── API Keys ─────────────────────────────────────────────────────────────
    YOUTUBE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')   # used for YouTube + Books
    GEMINI_API_KEY  = os.environ.get('GEMINI_API_KEY',  '')

    # ── File uploads ─────────────────────────────────────────────────────────
    UPLOAD_FOLDER        = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    PROFILE_PICS_FOLDER  = os.path.join(os.path.dirname(__file__), 'static', 'profile_pics')
    MAX_CONTENT_LENGTH   = 16 * 1024 * 1024   # 16 MB
    ALLOWED_EXTENSIONS   = {'png', 'jpg', 'jpeg', 'gif'}

    # ── Pagination ───────────────────────────────────────────────────────────
    ITEMS_PER_PAGE = 10

    # ── Security ─────────────────────────────────────────────────────────────
    WTF_CSRF_ENABLED      = True
    SESSION_COOKIE_SECURE = False   # set True in production (HTTPS)
    REMEMBER_COOKIE_DURATION = 7   # days
