from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    profile_pic = db.Column(db.String(200), default='default.jpg')
    bio = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    last_active = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    searches = db.relationship('SearchHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'bio': self.bio,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    keyword = db.Column(db.Text, nullable=False)
    search_type = db.Column(db.String(50), default='full')
    results = db.Column(db.JSON)
    summary = db.Column(db.Text)
    pdf_path = db.Column(db.String(500))
    execution_time = db.Column(db.Float)
    status = db.Column(db.String(20), default='completed')
    is_favorite = db.Column(db.Boolean, default=False)
    views_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'keyword': self.keyword,
            'summary': self.summary[:200] + '...' if self.summary and len(self.summary) > 200 else self.summary,
            'execution_time': self.execution_time,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'is_favorite': self.is_favorite,
            'views_count': self.views_count
        }


class Favorite(db.Model):
    __tablename__ = 'favorites'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    search_id = db.Column(db.Integer, db.ForeignKey('search_history.id'), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    search = db.relationship('SearchHistory')


class KnowledgeGraph(db.Model):
    __tablename__ = 'knowledge_graph'
    
    id = db.Column(db.Integer, primary_key=True)
    entity_name = db.Column(db.String(200), nullable=False)
    entity_type = db.Column(db.String(50))
    relation_data = db.Column(db.JSON)
    entity_metadata = db.Column(db.JSON)  # Changed from 'metadata' to 'entity_metadata'
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (db.UniqueConstraint('entity_name', name='unique_entity'),)


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    action = db.Column(db.String(100))
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('User')