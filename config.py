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

    # ── Database (MySQL via Flask-SQLAlchemy) ────────────────────────────────
    MYSQL_HOST     = os.environ.get('MYSQL_HOST',     'localhost')
    MYSQL_USER     = os.environ.get('MYSQL_USER',     'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'root')
    MYSQL_DB       = os.environ.get('MYSQL_DB',       'tkrag_db')

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}/{MYSQL_DB}"
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
