"""
Helper utilities for TKAG-RAG Web Application
"""

import os
import uuid
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from werkzeug.utils import secure_filename
from flask import current_app, url_for

# ==================== File Upload Helpers ====================

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_profile_pic(file, user_id: int) -> Optional[str]:
    """Save profile picture and return filename"""
    if file and allowed_file(file.filename):
        # Create secure filename
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        
        # Generate unique filename
        filename = f"profile_{user_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
        filepath = os.path.join('static/profile_pics', filename)
        
        # Save file
        file.save(filepath)
        
        return filename
    return None

# ==================== Date/Time Helpers ====================

def format_datetime(dt: datetime, format: str = '%B %d, %Y at %I:%M %p') -> str:
    """Format datetime for display"""
    if not dt:
        return ''
    return dt.strftime(format)

def time_ago(dt: datetime) -> str:
    """Get time ago string"""
    if not dt:
        return ''
    
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f'{years} year{"s" if years > 1 else ""} ago'
    if diff.days > 30:
        months = diff.days // 30
        return f'{months} month{"s" if months > 1 else ""} ago'
    if diff.days > 0:
        return f'{diff.days} day{"s" if diff.days > 1 else ""} ago'
    if diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f'{hours} hour{"s" if hours > 1 else ""} ago'
    if diff.seconds > 60:
        minutes = diff.seconds // 60
        return f'{minutes} minute{"s" if minutes > 1 else ""} ago'
    return 'just now'

# ==================== Text Processing ====================

def truncate_text(text: str, length: int = 100) -> str:
    """Truncate text to specified length"""
    if not text:
        return ''
    if len(text) <= length:
        return text
    return text[:length] + '...'

def generate_summary(text: str, max_length: int = 200) -> str:
    """Generate a simple summary from text"""
    if not text:
        return ''
    
    # Take first few sentences
    sentences = text.split('.')
    summary = '. '.join(sentences[:2]) + '.'
    
    if len(summary) > max_length:
        return summary[:max_length] + '...'
    return summary

# ==================== Statistics Helpers ====================

def calculate_stats(data: list) -> Dict[str, Any]:
    """Calculate statistics from a list of numbers"""
    if not data:
        return {
            'count': 0,
            'sum': 0,
            'avg': 0,
            'min': 0,
            'max': 0
        }
    
    return {
        'count': len(data),
        'sum': sum(data),
        'avg': sum(data) / len(data),
        'min': min(data),
        'max': max(data)
    }

# ==================== Activity Logging ====================

def log_activity(user_id: int, action: str, details: Dict = None, 
                 ip_address: str = None, user_agent: str = None):
    """Log user activity"""
    from models.database import ActivityLog, db
    
    try:
        activity = ActivityLog(
            user_id=user_id,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now()
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error logging activity: {e}")

# ==================== Email Helpers ====================

def send_async_email(app, msg):
    """Send email asynchronously"""
    from flask_mail import Message, Mail
    
    with app.app_context():
        mail = Mail(app)
        mail.send(msg)

def create_notification(user_id: int, message: str, type: str = 'info'):
    """Create a notification for user"""
    # This would be implemented with a Notification model
    pass

# ==================== Security Helpers ====================

def generate_token(length: int = 32) -> str:
    """Generate a random token"""
    return uuid.uuid4().hex[:length]

def hash_token(token: str) -> str:
    """Hash a token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()

# ==================== File Helpers ====================

def get_file_size(filepath: str) -> str:
    """Get human readable file size"""
    if not os.path.exists(filepath):
        return '0 B'
    
    size = os.path.getsize(filepath)
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def ensure_dir(directory: str):
    """Ensure directory exists"""
    if not os.path.exists(directory):
        os.makedirs(directory)

# ==================== Data Validation ====================

def validate_email(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password: str) -> Dict[str, bool]:
    """Validate password strength"""
    checks = {
        'length': len(password) >= 6,
        'uppercase': any(c.isupper() for c in password),
        'lowercase': any(c.islower() for c in password),
        'digit': any(c.isdigit() for c in password),
        'special': any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
    }
    
    checks['strong'] = all(checks.values())
    checks['medium'] = sum(checks.values()) >= 3
    
    return checks