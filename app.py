"""
TKAG-RAG Web Application - Complete Production Version
Flask-based web application with Temporal Knowledge Graph and RAG integration
"""

import os
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Optional

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from werkzeug.middleware.profiler import ProfilerMiddleware

from config import Config
from models.database import db, User, SearchHistory, Favorite, KnowledgeGraph, ActivityLog
from models.tkag_rag import KnowledgeSynthesizer
from utils.pdf_generator import PDFGenerator
from utils.helpers import (
    save_profile_pic, allowed_file, format_datetime, 
    generate_summary, calculate_stats, log_activity,
    send_async_email, create_notification
)

# Initialize app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)

# Initialize Login Manager AFTER app is created
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
login_manager.session_protection = 'strong'

# Initialize TKAG-RAG synthesizer
synthesizer = None

def get_synthesizer():
    global synthesizer
    if synthesizer is None:
        synthesizer = KnowledgeSynthesizer(
            api_key=Config.YOUTUBE_API_KEY,
            gemini_api_key=Config.GEMINI_API_KEY
        )
    return synthesizer


# Ensure required directories exist
REQUIRED_DIRS = [
    'static/uploads',
    'static/pdfs',
    'static/profile_pics',
    'static/temp',
    'logs',
    'cache'
]

for dir_path in REQUIRED_DIRS:
    os.makedirs(dir_path, exist_ok=True)

# ==================== User Loader ====================
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID"""
    return db.session.get(User, int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access"""
    flash('Please log in to access this page.', 'warning')
    return redirect(url_for('login', next=request.url))

# ==================== Context Processors ====================
@app.context_processor
def utility_processor():
    """Make utility functions available in templates"""
    return {
        'now': datetime.now,
        'format_datetime': format_datetime,
        'enumerate': enumerate,
        'len': len,
        'str': str,
        'int': int,
        'float': float
    }

@app.context_processor
def inject_csrf_token():
    """Inject CSRF token into all templates"""
    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=generate_csrf)

# ==================== Helper Functions ====================
def admin_required(f):
    """Admin access decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            log_activity(
                user_id=current_user.id if current_user.is_authenticated else None,
                action='unauthorized_admin_access',
                details={'page': request.endpoint},
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            flash('You need administrator privileges to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def track_activity(action: str, details: Dict = None):
    """Decorator to track user activity"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            if current_user.is_authenticated:
                log_activity(
                    user_id=current_user.id,
                    action=action,
                    details=details or {},
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string
                )
            return result
        return decorated_function
    return decorator

def handle_errors(f):
    """Error handling decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            app.logger.error(f"Error in {f.__name__}: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': str(e)}), 500
            flash('')
            return redirect(url_for('index'))
    return decorated_function

# ==================== Routes ====================

# Public Routes
@app.route('/')
@handle_errors
def index():
    """Home page"""
    stats = {
        'total_searches': SearchHistory.query.count(),
        'total_users': User.query.count(),
        'total_favorites': Favorite.query.count()
    }
    return render_template('index.html', stats=stats)

@app.route('/register', methods=['GET', 'POST'])
@handle_errors
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        
        # Validation
        errors = []
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters')
        if not email or '@' not in email:
            errors.append('Valid email is required')
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters')
        if password != confirm_password:
            errors.append('Passwords do not match')
        
        # Check existing user
        if User.query.filter_by(username=username).first():
            errors.append('Username already exists')
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('register'))
        
        # Create user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            is_active=True,
            is_admin=False,
            created_at=datetime.now()
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Log registration
            log_activity(
                user_id=user.id,
                action='user_registered',
                details={'username': username, 'email': email},
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Registration error: {str(e)}")
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
@handle_errors
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return redirect(url_for('login'))
            
            login_user(user, remember=remember)
            user.last_login = datetime.now()
            user.last_active = datetime.now()
            db.session.commit()
            
            # Log login
            log_activity(
                user_id=user.id,
                action='user_login',
                details={'username': username},
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            log_activity(
                user_id=None,
                action='login_failed',
                details={'username': username},
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
    
    return render_template('login.html')

@app.route('/logout')
@login_required
@track_activity('user_logout')
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@handle_errors
def dashboard():
    """User dashboard"""
    # Get recent searches
    recent_searches = SearchHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(SearchHistory.created_at.desc()).limit(5).all()
    
    # Calculate statistics
    total_searches = SearchHistory.query.filter_by(user_id=current_user.id).count()
    favorites_count = Favorite.query.filter_by(user_id=current_user.id).count()
    
    # Get activity for chart
    last_7_days = datetime.now() - timedelta(days=7)
    daily_activity = db.session.query(
        db.func.date(SearchHistory.created_at).label('date'),
        db.func.count(SearchHistory.id).label('count')
    ).filter(
        SearchHistory.user_id == current_user.id,
        SearchHistory.created_at >= last_7_days
    ).group_by(db.func.date(SearchHistory.created_at)).all()
    
    activity_labels = []
    activity_data = []
    
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).date()
        activity_labels.append(date.strftime('%a'))
        count = next((a.count for a in daily_activity if a.date == date), 0)
        activity_data.append(count)
    
    stats = {
        'total_searches': total_searches,
        'favorites': favorites_count,
        'recent_activity': len(recent_searches),
        'activity_labels': activity_labels,
        'activity_data': activity_data
    }
    
    log_activity(
        user_id=current_user.id,
        action='view_dashboard',
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    
    return render_template('dashboard.html', 
                         recent_searches=recent_searches,
                         stats=stats)

@app.route('/generate', methods=['GET', 'POST'])
@handle_errors
def generate():
    """Generate knowledge for a topic"""
    if request.method == 'POST':
        topic = request.form.get('topic', '').strip()
        
        if not topic:
            flash('Please enter a topic', 'warning')
            return redirect(url_for('generate'))
        
        if len(topic) > 2000:
            flash('Topic is too long (max 2000 characters)', 'warning')
            return redirect(url_for('generate'))
        
        try:
            # Log generation start
            log_activity(
                user_id=current_user.id,
                action='generate_started',
                details={'topic': topic},
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            # Generate knowledge
            start_time = time.time()
            knowledge = synthesizer.synthesize(topic)
            execution_time = round(time.time() - start_time, 2)
            
            # Save to history
            search = SearchHistory(
                user_id=current_user.id,
                keyword=topic,
                results={
                    'videos': knowledge.get('videos', []),
                    'books': knowledge.get('books', []),
                    'papers': knowledge.get('papers', []),
                    'knowledge_graph': knowledge.get('knowledge_graph', {}),
                    'knowledge_graph_summary': knowledge.get('knowledge_graph_summary', '')
                },
                summary=knowledge.get('complete_summary', ''),
                execution_time=execution_time,
                status='completed',
                created_at=datetime.now()
            )
            db.session.add(search)
            db.session.flush()  # Get ID without committing
            
            # Generate PDF
            try:
                pdf_filename = f"knowledge_{search.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                pdf_path = os.path.join('static/pdfs', pdf_filename)
                PDFGenerator.generate_knowledge_pdf(knowledge, pdf_path)
                search.pdf_path = pdf_filename
            except Exception as e:
                app.logger.error(f"PDF generation error: {str(e)}")
                search.pdf_path = None
            
            db.session.commit()
            
            # Log completion
            log_activity(
                user_id=current_user.id,
                action='generate_completed',
                details={'topic': topic, 'search_id': search.id, 'time': execution_time},
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            flash('Knowledge generated successfully!', 'success')
            return redirect(url_for('result', search_id=search.id))
            
        except Exception as e:
            app.logger.error(f"Generation error: {str(e)}")
            log_activity(
                user_id=current_user.id,
                action='generate_failed',
                details={'topic': topic, 'error': str(e)},
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            flash(f'Error generating knowledge: {str(e)}', 'danger')
            return redirect(url_for('generate'))
    
    # Get recent searches for quick access
    recent_searches = SearchHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(SearchHistory.created_at.desc()).limit(4).all()
    
    return render_template('generate.html', recent_searches=recent_searches)

@app.route('/api/generate', methods=['POST'])
@csrf.exempt
@login_required
@handle_errors
def api_generate():
    """API endpoint for async generation"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    topic = data.get('topic', '').strip()
    
    if not topic:
        return jsonify({'error': 'Topic required'}), 400
    
    if len(topic) > 2000:
        return jsonify({'error': 'Topic too long'}), 400
    
    try:
        # Generate knowledge
        start_time = time.time()
        knowledge = synthesizer.synthesize(topic)
        execution_time = round(time.time() - start_time, 2)
        
        # Save to history
        search = SearchHistory(
            user_id=current_user.id,
            keyword=topic,
            results={
                'videos': knowledge.get('videos', []),
                'books': knowledge.get('books', []),
                'papers': knowledge.get('papers', []),
                'knowledge_graph': knowledge.get('knowledge_graph', {}),
                'knowledge_graph_summary': knowledge.get('knowledge_graph_summary', '')
            },
            summary=knowledge.get('complete_summary', ''),
            execution_time=execution_time,
            status='completed',
            created_at=datetime.now()
        )
        db.session.add(search)
        db.session.flush()
        
        # Generate PDF
        try:
            pdf_filename = f"knowledge_{search.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join('static/pdfs', pdf_filename)
            PDFGenerator.generate_knowledge_pdf(knowledge, pdf_path)
            search.pdf_path = pdf_filename
        except Exception as e:
            app.logger.error(f"PDF generation error: {str(e)}")
            search.pdf_path = None
        
        db.session.commit()
        
        # Log activity
        log_activity(
            user_id=current_user.id,
            action='api_generate',
            details={'topic': topic, 'search_id': search.id},
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        return jsonify({
            'success': True,
            'search_id': search.id,
            'keyword': search.keyword,
            'execution_time': execution_time,
            'pdf_url': url_for('static', filename=f'pdfs/{pdf_filename}') if search.pdf_path else None,
            'redirect_url': url_for('result', search_id=search.id)
        })
        
    except Exception as e:
        app.logger.error(f"API generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/result/<int:search_id>')
@login_required
@handle_errors
def result(search_id):
    """View search result"""
    search = db.session.get(SearchHistory, search_id)
    if not search:
        abort(404)
    
    # Check ownership
    if search.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    # Increment view count
    search.views_count = (search.views_count or 0) + 1
    db.session.commit()
    
    # Get related searches (same keyword by other users)
    related_searches = SearchHistory.query.filter(
        SearchHistory.keyword == search.keyword,
        SearchHistory.user_id != current_user.id,
        SearchHistory.status == 'completed'
    ).order_by(SearchHistory.views_count.desc()).limit(5).all()
    
    log_activity(
        user_id=current_user.id,
        action='view_result',
        details={'search_id': search_id, 'keyword': search.keyword},
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    
    return render_template('result.html', 
                         search=search, 
                         related_searches=related_searches)

@app.route('/history')
@login_required
@handle_errors
def history():
    """View search history"""
    page = request.args.get('page', 1, type=int)
    per_page = getattr(Config, 'ITEMS_PER_PAGE', 10)
    
    searches = SearchHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(
        SearchHistory.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    log_activity(
        user_id=current_user.id,
        action='view_history',
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    
    return render_template('history.html', searches=searches)

@app.route('/favorite/<int:search_id>', methods=['POST'])
@csrf.exempt
@login_required
@handle_errors
def toggle_favorite(search_id):
    """Toggle favorite status"""
    search = db.session.get(SearchHistory, search_id)
    if not search:
        return jsonify({'error': 'Search not found'}), 404
    
    if search.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        search_id=search_id
    ).first()
    
    if favorite:
        db.session.delete(favorite)
        search.is_favorite = False
        message = 'Removed from favorites'
        action = 'remove_favorite'
    else:
        favorite = Favorite(
            user_id=current_user.id,
            search_id=search_id,
            created_at=datetime.now()
        )
        db.session.add(favorite)
        search.is_favorite = True
        message = 'Added to favorites'
        action = 'add_favorite'
    
    db.session.commit()
    
    log_activity(
        user_id=current_user.id,
        action=action,
        details={'search_id': search_id, 'keyword': search.keyword},
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    
    return jsonify({
        'success': True,
        'is_favorite': search.is_favorite,
        'message': message
    })

@app.route('/download-pdf/<int:search_id>')
@login_required
@handle_errors
def download_pdf(search_id):
    """Download PDF for a search result"""
    search = db.session.get(SearchHistory, search_id)
    if not search:
        abort(404)
    
    if search.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    if not search.pdf_path:
        flash('PDF not found', 'warning')
        return redirect(url_for('result', search_id=search_id))
    
    pdf_path = os.path.join('static/pdfs', search.pdf_path)
    
    if not os.path.exists(pdf_path):
        flash('PDF file not found', 'danger')
        return redirect(url_for('result', search_id=search_id))
    
    log_activity(
        user_id=current_user.id,
        action='download_pdf',
        details={'search_id': search_id, 'keyword': search.keyword},
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f"{search.keyword}_knowledge_report.pdf",
        mimetype='application/pdf'
    )

@app.route('/profile', methods=['GET', 'POST'])
@login_required
@handle_errors
def profile():
    """User profile"""
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        bio = request.form.get('bio', '').strip()
        
        # Validate email
        if email != current_user.email:
            if User.query.filter_by(email=email).first():
                flash('Email already in use', 'danger')
                return redirect(url_for('profile'))
        
        # Handle profile picture upload
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename:
                if allowed_file(file.filename):
                    filename = save_profile_pic(file, current_user.id)
                    if filename:
                        current_user.profile_pic = filename
                else:
                    flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF', 'warning')
        
        # Handle password change
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if new_password or confirm_password or current_password:
            if not current_password:
                flash('Current password is required to change password', 'warning')
            elif not current_user.check_password(current_password):
                flash('Current password is incorrect', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match', 'danger')
            elif len(new_password) < 6:
                flash('New password must be at least 6 characters', 'danger')
            else:
                current_user.set_password(new_password)
                flash('Password updated successfully', 'success')
        
        # Update user info
        current_user.full_name = full_name
        current_user.email = email
        current_user.bio = bio
        current_user.updated_at = datetime.now()
        
        db.session.commit()
        
        log_activity(
            user_id=current_user.id,
            action='update_profile',
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile'))
    
    # Get user statistics
    total_searches = SearchHistory.query.filter_by(user_id=current_user.id).count()
    favorites_count = Favorite.query.filter_by(user_id=current_user.id).count()
    days_joined = (datetime.now() - current_user.created_at).days
    
    stats = {
        'total_searches': total_searches,
        'favorites': favorites_count,
        'days_joined': max(days_joined, 1)
    }
    
    return render_template('profile.html', user=current_user, stats=stats)

@app.route('/stats')
@login_required
@handle_errors
def stats():
    """User statistics"""
    searches = SearchHistory.query.filter_by(
        user_id=current_user.id,
        status='completed'
    ).all()
    
    if not searches:
        flash('No data available for statistics', 'info')
        return redirect(url_for('dashboard'))
    
    # Calculate statistics
    total_searches = len(searches)
    favorites_count = Favorite.query.filter_by(user_id=current_user.id).count()
    total_views = sum(s.views_count or 0 for s in searches)
    
    # Time statistics
    times = [s.execution_time for s in searches if s.execution_time]
    avg_time = sum(times) / len(times) if times else 0
    fastest_time = min(times) if times else 0
    slowest_time = max(times) if times else 0
    
    # Success rate
    success_count = len([s for s in searches if s.status == 'completed'])
    success_rate = round((success_count / total_searches) * 100, 1) if total_searches > 0 else 0
    
    # Top keywords
    keyword_counts = {}
    for s in searches:
        keyword_counts[s.keyword] = keyword_counts.get(s.keyword, 0) + 1
    
    top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Activity for charts
    last_30_days = datetime.now() - timedelta(days=30)
    daily_activity = db.session.query(
        db.func.date(SearchHistory.created_at).label('date'),
        db.func.count(SearchHistory.id).label('count')
    ).filter(
        SearchHistory.user_id == current_user.id,
        SearchHistory.created_at >= last_30_days
    ).group_by(db.func.date(SearchHistory.created_at)).all()
    
    activity_labels = []
    activity_data = []
    
    for i in range(29, -1, -1):
        date = (datetime.now() - timedelta(days=i)).date()
        activity_labels.append(date.strftime('%m/%d'))
        count = next((a.count for a in daily_activity if a.date == date), 0)
        activity_data.append(count)
    
    stats_data = {
        'total_searches': total_searches,
        'favorites': favorites_count,
        'total_views': total_views,
        'avg_time': round(avg_time, 2),
        'fastest_time': round(fastest_time, 2),
        'slowest_time': round(slowest_time, 2),
        'success_rate': success_rate,
        'top_keywords': [k for k, _ in top_keywords],
        'activity_labels': activity_labels,
        'activity_data': activity_data
    }
    
    log_activity(
        user_id=current_user.id,
        action='view_stats',
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    
    return render_template('stats.html', stats=stats_data, recent_searches=searches[:10])

@app.route('/delete-search/<int:search_id>', methods=['DELETE'])
@csrf.exempt
@login_required
@handle_errors
def delete_search(search_id):
    """Delete a search result"""
    search = db.session.get(SearchHistory, search_id)
    if not search:
        return jsonify({'error': 'Search not found'}), 404
    
    if search.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Delete associated PDF
        if search.pdf_path:
            pdf_path = os.path.join('static/pdfs', search.pdf_path)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        
        # Delete favorites first
        Favorite.query.filter_by(search_id=search_id).delete()
        
        # Delete search
        db.session.delete(search)
        db.session.commit()
        
        log_activity(
            user_id=current_user.id,
            action='delete_search',
            details={'search_id': search_id, 'keyword': search.keyword},
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Delete error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/activity')
@login_required
@handle_errors
def activity():
    """View user activity log"""
    page = request.args.get('page', 1, type=int)
    per_page = getattr(Config, 'ITEMS_PER_PAGE', 10)
    
    activities = ActivityLog.query.filter_by(
        user_id=current_user.id
    ).order_by(
        ActivityLog.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Calculate activity stats
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    today_count = ActivityLog.query.filter(
        ActivityLog.user_id == current_user.id,
        db.func.date(ActivityLog.created_at) == today
    ).count()
    
    week_count = ActivityLog.query.filter(
        ActivityLog.user_id == current_user.id,
        ActivityLog.created_at >= week_ago
    ).count()
    
    # Calculate streak (consecutive days with activity)
    streak = 0
    check_date = today
    while True:
        has_activity = ActivityLog.query.filter(
            ActivityLog.user_id == current_user.id,
            db.func.date(ActivityLog.created_at) == check_date
        ).first()
        if has_activity:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    
    activity_stats = {
        'today': today_count,
        'week': week_count,
        'streak': streak
    }
    
    return render_template('activity.html', 
                         activities=activities,
                         activity_stats=activity_stats,
                         pagination=activities)

@app.route('/admin')
@admin_required
@handle_errors
def admin_panel():
    """Admin panel"""
    # System statistics
    total_users = User.query.count()
    active_today = User.query.filter(
        db.func.date(User.last_active) == datetime.now().date()
    ).count()
    
    active_week = User.query.filter(
        User.last_active >= datetime.now() - timedelta(days=7)
    ).count()
    
    inactive = total_users - active_week
    
    total_searches = SearchHistory.query.count()
    total_pdfs = SearchHistory.query.filter(SearchHistory.pdf_path.isnot(None)).count()
    
    # Database size (approximate)
    db_size = "10 MB"  # You can calculate actual size
    
    # Recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Popular topics
    popular_topics = db.session.query(
        SearchHistory.keyword,
        db.func.count(SearchHistory.id).label('count')
    ).group_by(SearchHistory.keyword).order_by(db.desc('count')).limit(10).all()
    
    # Activity for charts
    last_30_days = datetime.now() - timedelta(days=30)
    daily_searches = db.session.query(
        db.func.date(SearchHistory.created_at).label('date'),
        db.func.count(SearchHistory.id).label('count')
    ).filter(
        SearchHistory.created_at >= last_30_days
    ).group_by(db.func.date(SearchHistory.created_at)).all()
    
    daily_users = db.session.query(
        db.func.date(User.created_at).label('date'),
        db.func.count(User.id).label('count')
    ).filter(
        User.created_at >= last_30_days
    ).group_by(db.func.date(User.created_at)).all()
    
    activity_labels = []
    search_data = []
    user_data = []
    
    for i in range(29, -1, -1):
        date = (datetime.now() - timedelta(days=i)).date()
        activity_labels.append(date.strftime('%m/%d'))
        search_data.append(next((s.count for s in daily_searches if s.date == date), 0))
        user_data.append(next((u.count for u in daily_users if u.date == date), 0))
    
    stats = {
        'total_users': total_users,
        'total_searches': total_searches,
        'total_pdfs': total_pdfs,
        'db_size': db_size,
        'recent_users': recent_users,
        'popular_topics': popular_topics,
        'storage_used': '50 MB',  # Calculate actual
        'activity_labels': activity_labels,
        'activity_data': search_data,
        'user_activity_data': user_data,
        'user_stats': {
            'active_today': active_today,
            'active_week': active_week,
            'inactive': inactive
        }
    }
    
    return render_template('admin.html', stats=stats)

@app.route('/admin/user/<int:user_id>', methods=['DELETE'])
@csrf.exempt
@admin_required
@handle_errors
def admin_delete_user(user_id):
    """Admin: Delete user"""
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Delete user's PDFs
        searches = SearchHistory.query.filter_by(user_id=user_id).all()
        for search in searches:
            if search.pdf_path:
                pdf_path = os.path.join('static/pdfs', search.pdf_path)
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
        
        db.session.delete(user)
        db.session.commit()
        
        log_activity(
            user_id=current_user.id,
            action='admin_delete_user',
            details={'deleted_user_id': user_id, 'username': user.username},
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/toggle-admin/<int:user_id>', methods=['POST'])
@csrf.exempt
@admin_required
@handle_errors
def admin_toggle_admin(user_id):
    """Admin: Toggle admin status"""
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot modify your own admin status'}), 400
    
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    log_activity(
        user_id=current_user.id,
        action='admin_toggle_admin',
        details={'user_id': user_id, 'username': user.username, 'is_admin': user.is_admin},
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    
    return jsonify({
        'success': True,
        'is_admin': user.is_admin,
        'message': f"Admin status for {user.username} toggled"
    })

@app.route('/search-api')
@csrf.exempt
@login_required
@handle_errors
def search_api():
    """Search through history"""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({'results': []})
    
    # Search in search_history
    results = SearchHistory.query.filter(
        SearchHistory.user_id == current_user.id,
        SearchHistory.keyword.ilike(f'%{query}%')
    ).order_by(SearchHistory.created_at.desc()).limit(10).all()
    
    return jsonify({
        'results': [{
            'id': r.id,
            'keyword': r.keyword,
            'date': r.created_at.strftime('%Y-%m-%d %H:%M'),
            'url': url_for('result', search_id=r.id)
        } for r in results]
    })

@app.route('/export-history')
@login_required
@handle_errors
def export_history():
    """Export search history as CSV"""
    searches = SearchHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(SearchHistory.created_at.desc()).all()
    
    import csv
    from io import StringIO
    from flask import Response
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Keyword', 'Date', 'Time', 'Execution Time (s)', 'Views', 'Status', 'Favorites'])
    
    for s in searches:
        cw.writerow([
            s.keyword,
            s.created_at.strftime('%Y-%m-%d'),
            s.created_at.strftime('%H:%M:%S'),
            s.execution_time,
            s.views_count or 0,
            s.status,
            'Yes' if s.is_favorite else 'No'
        ])
    
    output = si.getvalue()
    si.close()
    
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=search_history_{datetime.now().strftime("%Y%m%d")}.csv'}
    )

# ==================== Error Handlers ====================
@app.errorhandler(404)
def not_found_error(error):
    """404 error handler"""
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden_error(error):
    """403 error handler"""
    return render_template('403.html'), 403

@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    db.session.rollback()
    app.logger.error(f"Internal server error: {str(error)}")
    return render_template('500.html'), 500

@app.errorhandler(429)
def rate_limit_error(error):
    """429 rate limit error handler"""
    return render_template('429.html'), 429

# ==================== CLI Commands ====================
@app.cli.command('create-admin')
def create_admin():
    """Create admin user"""
    username = input('Username: ')
    email = input('Email: ')
    password = input('Password: ')
    
    user = User(
        username=username,
        email=email,
        is_admin=True,
        is_active=True,
        created_at=datetime.now()
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    print(f'Admin user {username} created successfully!')

@app.cli.command('cleanup-pdfs')
def cleanup_pdfs():
    """Clean up old PDF files"""
    days = 30
    cutoff = datetime.now() - timedelta(days=days)
    
    old_searches = SearchHistory.query.filter(
        SearchHistory.created_at < cutoff,
        SearchHistory.pdf_path.isnot(None)
    ).all()
    
    count = 0
    for search in old_searches:
        if search.pdf_path:
            pdf_path = os.path.join('static/pdfs', search.pdf_path)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                count += 1
    
    print(f'Cleaned up {count} old PDF files')

@app.cli.command('db-stats')
def db_stats():
    """Show database statistics"""
    total_users = User.query.count()
    total_searches = SearchHistory.query.count()
    total_favorites = Favorite.query.count()
    
    print(f'Total Users: {total_users}')
    print(f'Total Searches: {total_searches}')
    print(f'Total Favorites: {total_favorites}')
    
    # Active users today
    today = datetime.now().date()
    active_today = User.query.filter(
        db.func.date(User.last_active) == today
    ).count()
    print(f'Active Today: {active_today}')

# ==================== Before/After Request ====================
@app.before_request
def before_request():
    """Update last active timestamp"""
    if current_user.is_authenticated:
        current_user.last_active = datetime.now()
        db.session.commit()

@app.after_request
def after_request(response):
    """Add security headers"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# ==================== Template Filters ====================
@app.template_filter('truncate')
def truncate_filter(text, length=100):
    """Truncate text filter"""
    if not text:
        return ''
    if len(text) <= length:
        return text
    return text[:length] + '...'

@app.template_filter('format_date')
def format_date_filter(date):
    """Format date filter"""
    if not date:
        return ''
    return date.strftime('%B %d, %Y')

@app.template_filter('time_ago')
def time_ago_filter(date):
    """Time ago filter"""
    if not date:
        return ''
    
    diff = datetime.now() - date
    
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

# ==================== Main Entry Point ====================
with app.app_context():
    db.create_all()

    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            username='admin',
            email='admin@tkrag.com',
            full_name='Administrator',
            is_admin=True,
            is_active=True,
            created_at=datetime.now()
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        
if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        db.create_all()
        print(" Database initialized successfully!")
        
        # Create default admin if none exists
        if not User.query.filter_by(is_admin=True).first():
            admin = User(
                username='admin',
                email='admin@tkrag.com',
                full_name='Administrator',
                is_admin=True,
                is_active=True,
                created_at=datetime.now()
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print(" Default admin user created (admin/admin123)")
        
        print(" TKAG-RAG Web Application starting...")
        print(f" Server: http://localhost:{getattr(Config, 'PORT', 5000)}")
        print(f" Environment: {'Development' if getattr(Config, 'DEBUG', True) else 'Production'}")
        print(f" Debug mode: {'ON' if getattr(Config, 'DEBUG', True) else 'OFF'}")
    
    # Run app
    port = int(os.environ.get("PORT", 10000))
   
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
    
